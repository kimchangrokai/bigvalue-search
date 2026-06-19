"""Tests for radius search module."""

from __future__ import annotations

import pytest

from bigvalue_search.geocoding import Coordinates
from bigvalue_search.radius_search import (
    haversine_distance,
    meters_to_lat_offset,
    meters_to_lon_offset,
    generate_grid_points,
    deduplicate_nearby_points,
    GridPoint,
)


class TestHaversine:
    """Tests for Haversine distance calculation."""

    def test_same_point(self) -> None:
        coord = Coordinates(latitude=37.5665, longitude=126.9780)
        assert haversine_distance(coord, coord) == pytest.approx(0.0, abs=0.01)

    def test_known_distance(self) -> None:
        # Seoul to Busan ≈ 325 km
        seoul = Coordinates(latitude=37.5665, longitude=126.9780)
        busan = Coordinates(latitude=35.1796, longitude=129.0756)
        distance = haversine_distance(seoul, busan)
        assert 320_000 < distance < 330_000  # ~325 km

    def test_short_distance(self) -> None:
        # Two points ~100m apart (0.001 degree latitude ≈ 111m)
        p1 = Coordinates(latitude=37.5665, longitude=126.9780)
        p2 = Coordinates(latitude=37.5675, longitude=126.9780)
        distance = haversine_distance(p1, p2)
        assert 100 < distance < 120  # ~111m per 0.001 degree latitude

    def test_symmetry(self) -> None:
        p1 = Coordinates(latitude=37.5665, longitude=126.9780)
        p2 = Coordinates(latitude=35.1796, longitude=129.0756)
        assert haversine_distance(p1, p2) == pytest.approx(
            haversine_distance(p2, p1), rel=1e-10
        )


class TestMeterConversions:
    """Tests for meter-to-degree conversions."""

    def test_lat_offset(self) -> None:
        # 111,320 meters ≈ 1 degree latitude
        assert meters_to_lat_offset(111_320) == pytest.approx(1.0, rel=0.01)

    def test_lon_offset_at_equator(self) -> None:
        # At equator, 1 degree longitude ≈ 111,320 meters
        offset = meters_to_lon_offset(111_320, 0.0)
        assert offset == pytest.approx(1.0, rel=0.01)

    def test_lon_offset_at_seoul(self) -> None:
        # At Seoul's latitude (~37.5°), 1 degree longitude is shorter
        offset = meters_to_lon_offset(111_320, 37.5)
        assert offset > 1.0  # need more degrees to cover same meters


class TestGridGeneration:
    """Tests for grid point generation."""

    def test_grid_points_within_radius(self, seoul_coordinates: Coordinates) -> None:
        points = generate_grid_points(seoul_coordinates, radius_m=50, interval_m=10)

        assert len(points) > 0
        for point in points:
            assert point.distance_m <= 50.0

    def test_grid_center_is_closest(self, seoul_coordinates: Coordinates) -> None:
        points = generate_grid_points(seoul_coordinates, radius_m=50, interval_m=10)

        # Center point should be in the grid (or very close)
        min_distance = min(p.distance_m for p in points)
        assert min_distance < 10.0  # within one grid step

    def test_larger_radius_more_points(self, seoul_coordinates: Coordinates) -> None:
        small = generate_grid_points(seoul_coordinates, radius_m=20, interval_m=10)
        large = generate_grid_points(seoul_coordinates, radius_m=50, interval_m=10)
        assert len(large) > len(small)

    def test_smaller_interval_more_points(self, seoul_coordinates: Coordinates) -> None:
        coarse = generate_grid_points(seoul_coordinates, radius_m=50, interval_m=15)
        fine = generate_grid_points(seoul_coordinates, radius_m=50, interval_m=5)
        assert len(fine) > len(coarse)

    def test_sorted_by_distance(self, seoul_coordinates: Coordinates) -> None:
        points = generate_grid_points(seoul_coordinates, radius_m=50, interval_m=10)
        distances = [p.distance_m for p in points]
        assert distances == sorted(distances)


class TestDeduplication:
    """Tests for grid point deduplication."""

    def test_empty_list(self) -> None:
        assert deduplicate_nearby_points([]) == []

    def test_single_point(self) -> None:
        point = GridPoint(
            coordinates=Coordinates(latitude=37.5665, longitude=126.9780),
            distance_m=0.0,
        )
        result = deduplicate_nearby_points([point])
        assert len(result) == 1

    def test_removes_nearby(self, seoul_coordinates: Coordinates) -> None:
        points = generate_grid_points(seoul_coordinates, radius_m=50, interval_m=3)
        deduped = deduplicate_nearby_points(points, min_distance_m=10.0)
        assert len(deduped) < len(points)
