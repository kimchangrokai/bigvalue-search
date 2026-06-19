"""Tests for BigValue search tool modules."""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ─── Geocoding Tests ────────────────────────────────────────────────────────

from bigvalue_search.geocoding import Coordinates


class TestCoordinates:
    """Tests for Coordinates dataclass."""

    def test_valid_coordinates(self) -> None:
        coord = Coordinates(latitude=37.5665, longitude=126.9780)
        assert coord.latitude == 37.5665
        assert coord.longitude == 126.9780

    def test_invalid_latitude(self) -> None:
        with pytest.raises(ValueError, match="Invalid latitude"):
            Coordinates(latitude=91.0, longitude=126.9780)

    def test_invalid_longitude(self) -> None:
        with pytest.raises(ValueError, match="Invalid longitude"):
            Coordinates(latitude=37.5665, longitude=181.0)

    def test_boundary_values(self) -> None:
        # These should not raise
        Coordinates(latitude=90.0, longitude=180.0)
        Coordinates(latitude=-90.0, longitude=-180.0)


# ─── Radius Search Tests ────────────────────────────────────────────────────

from bigvalue_search.radius_search import (
    haversine_distance,
    meters_to_lat_offset,
    meters_to_lon_offset,
    generate_grid_points,
    deduplicate_nearby_points,
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

    def test_grid_points_within_radius(self) -> None:
        center = Coordinates(latitude=37.5665, longitude=126.9780)
        points = generate_grid_points(center, radius_m=50, interval_m=10)

        assert len(points) > 0
        for point in points:
            assert point.distance_m <= 50.0

    def test_grid_center_is_closest(self) -> None:
        center = Coordinates(latitude=37.5665, longitude=126.9780)
        points = generate_grid_points(center, radius_m=50, interval_m=10)

        # Center point should be in the grid (or very close)
        min_distance = min(p.distance_m for p in points)
        assert min_distance < 10.0  # within one grid step

    def test_larger_radius_more_points(self) -> None:
        center = Coordinates(latitude=37.5665, longitude=126.9780)
        small = generate_grid_points(center, radius_m=20, interval_m=10)
        large = generate_grid_points(center, radius_m=50, interval_m=10)
        assert len(large) > len(small)

    def test_smaller_interval_more_points(self) -> None:
        center = Coordinates(latitude=37.5665, longitude=126.9780)
        coarse = generate_grid_points(center, radius_m=50, interval_m=15)
        fine = generate_grid_points(center, radius_m=50, interval_m=5)
        assert len(fine) > len(coarse)

    def test_sorted_by_distance(self) -> None:
        center = Coordinates(latitude=37.5665, longitude=126.9780)
        points = generate_grid_points(center, radius_m=50, interval_m=10)
        distances = [p.distance_m for p in points]
        assert distances == sorted(distances)


class TestDeduplication:
    """Tests for grid point deduplication."""

    def test_empty_list(self) -> None:
        assert deduplicate_nearby_points([]) == []

    def test_single_point(self) -> None:
        from bigvalue_search.radius_search import GridPoint
        point = GridPoint(
            coordinates=Coordinates(latitude=37.5665, longitude=126.9780),
            distance_m=0.0,
        )
        result = deduplicate_nearby_points([point])
        assert len(result) == 1

    def test_removes_nearby(self) -> None:
        center = Coordinates(latitude=37.5665, longitude=126.9780)
        points = generate_grid_points(center, radius_m=50, interval_m=3)
        deduped = deduplicate_nearby_points(points, min_distance_m=10.0)
        assert len(deduped) < len(points)


# ─── Data Export Tests ──────────────────────────────────────────────────────

from bigvalue_search.bigvalue_api import SearchResults, BuildingInfo, BusinessInfo, CardSalesInfo
from bigvalue_search.data_export import export_to_excel, export_to_json


class TestExport:
    """Tests for data export."""

    def _make_test_results(self) -> SearchResults:
        """Create test search results."""
        return SearchResults(
            search_center=Coordinates(latitude=37.5665, longitude=126.9780),
            radius_m=50.0,
            buildings=[
                BuildingInfo(
                    building_id="B001",
                    building_name="테스트빌딩",
                    address="서울 강서구 마곡동 800-15",
                    road_address="서울 강서구 공항대로 200",
                    building_type="업무시설",
                    total_floor_area=5000.0,
                    land_area=1000.0,
                    number_of_floors=15,
                    year_built=2020,
                    latitude=37.5665,
                    longitude=126.9780,
                    distance_m=0.0,
                ),
            ],
            businesses=[
                BusinessInfo(
                    business_id="P001",
                    business_name="테스트카페",
                    business_type="음식점",
                    business_category="카페",
                    representative_name="홍길동",
                    employee_count=5,
                    revenue_estimate="5억",
                    building_id="B001",
                    building_name="테스트빌딩",
                ),
            ],
            card_sales=[
                CardSalesInfo(
                    area_id="A001",
                    area_name="마곡동",
                    total_sales_amount=100_000_000.0,
                    average_sales_per_store=5_000_000.0,
                    number_of_stores=20,
                    sales_by_category={"음식": 50_000_000, "소매": 30_000_000},
                    monthly_sales={"2024-01": 10_000_000, "2024-02": 12_000_000},
                ),
            ],
        )

    def test_export_excel(self, tmp_path: Path) -> None:
        """Test Excel export."""
        from bigvalue_search import config as cfg
        original = cfg.OUTPUT_DIR
        cfg.OUTPUT_DIR = str(tmp_path)
        try:
            results = self._make_test_results()
            filepath = export_to_excel(results, "test.xlsx")
            assert filepath.exists()
            assert filepath.suffix == ".xlsx"
        finally:
            cfg.OUTPUT_DIR = original

    def test_export_json(self, tmp_path: Path) -> None:
        """Test JSON export."""
        from bigvalue_search import config as cfg
        original = cfg.OUTPUT_DIR
        cfg.OUTPUT_DIR = str(tmp_path)
        try:
            results = self._make_test_results()
            filepath = export_to_json(results, "test.json")
            assert filepath.exists()
            assert filepath.suffix == ".json"

            data = json.loads(filepath.read_text(encoding="utf-8"))
            assert "buildings" in data
            assert "businesses" in data
            assert "card_sales" in data
            assert data["summary"]["total_buildings"] == 1
        finally:
            cfg.OUTPUT_DIR = original

    def test_json_content_structure(self, tmp_path: Path) -> None:
        """Test JSON output structure."""
        from bigvalue_search import config as cfg
        original = cfg.OUTPUT_DIR
        cfg.OUTPUT_DIR = str(tmp_path)
        try:
            results = self._make_test_results()
            filepath = export_to_json(results, "test.json")
            data = json.loads(filepath.read_text(encoding="utf-8"))

            # Check search_info
            assert data["search_info"]["radius_m"] == 50.0
            assert data["search_info"]["center"]["latitude"] == 37.5665

            # Check building fields
            building = data["buildings"][0]
            assert building["building_id"] == "B001"
            assert building["building_name"] == "테스트빌딩"
            assert building["latitude"] == 37.5665
        finally:
            cfg.OUTPUT_DIR = original


# ─── Browser Auth Tests ─────────────────────────────────────────────────────

from bigvalue_search.browser_auth import AuthResult, _save_token_cache, _load_token_cache, clear_token_cache


class TestTokenCache:
    """Tests for token caching."""

    def test_save_and_load_cache(self, tmp_path: Path) -> None:
        """Test token cache save/load."""
        from bigvalue_search import browser_auth
        original = browser_auth.TOKEN_CACHE_FILE
        cache_file = tmp_path / ".token_cache.json"
        browser_auth.TOKEN_CACHE_FILE = cache_file
        try:
            auth = AuthResult(
                jwt_token="test_token_12345",
                success=True,
                cookies={"session": "abc123"},
            )
            _save_token_cache(auth)

            loaded = _load_token_cache()
            assert loaded is not None
            assert loaded.jwt_token == "test_token_12345"
            assert loaded.success is True
            assert loaded.cookies == {"session": "abc123"}
        finally:
            browser_auth.TOKEN_CACHE_FILE = original

    def test_load_nonexistent_cache(self, tmp_path: Path) -> None:
        """Test loading when no cache exists."""
        from bigvalue_search import browser_auth
        original = browser_auth.TOKEN_CACHE_FILE
        browser_auth.TOKEN_CACHE_FILE = tmp_path / "nonexistent.json"
        try:
            result = _load_token_cache()
            assert result is None
        finally:
            browser_auth.TOKEN_CACHE_FILE = original


# ─── BigValue API Tests ─────────────────────────────────────────────────────

class TestBigValueAPI:
    """Tests for BigValue API client."""

    def test_building_info_defaults(self) -> None:
        """Test BuildingInfo default values."""
        b = BuildingInfo()
        assert b.building_id == ""
        assert b.total_floor_area == 0.0
        assert b.number_of_floors == 0

    def test_business_info_defaults(self) -> None:
        """Test BusinessInfo default values."""
        b = BusinessInfo()
        assert b.business_id == ""
        assert b.employee_count == 0

    def test_card_sales_info_defaults(self) -> None:
        """Test CardSalesInfo default values."""
        s = CardSalesInfo()
        assert s.total_sales_amount == 0.0
        assert s.sales_by_category == {}

    def test_search_results_defaults(self) -> None:
        """Test SearchResults default values."""
        r = SearchResults()
        assert r.buildings == []
        assert r.businesses == []
        assert r.card_sales == []
        assert r.search_center is None

    def test_api_init(self) -> None:
        """Test API client initialization with mocked session."""
        from unittest.mock import MagicMock
        from bigvalue_search.bigvalue_api import BigValueAPI
        from bigvalue_search.browser_auth import BrowserSession

        mock_session = MagicMock(spec=BrowserSession)
        mock_session.access_token = "test_token"
        mock_session.jwt_token = ""
        api = BigValueAPI(session=mock_session)
        assert api.access_token == "test_token"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
