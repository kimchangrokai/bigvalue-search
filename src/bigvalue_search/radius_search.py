"""Radius search algorithm using grid points with Haversine distance."""

from __future__ import annotations

import math
from dataclasses import dataclass

from bigvalue_search.geocoding import Coordinates


# Earth radius in meters
EARTH_RADIUS_M: float = 6_371_000


def haversine_distance(coord1: Coordinates, coord2: Coordinates) -> float:
    """
    Calculate the great-circle distance between two points using the Haversine formula.

    Args:
        coord1: First coordinate
        coord2: Second coordinate

    Returns:
        Distance in meters.
    """
    lat1, lon1 = math.radians(coord1.latitude), math.radians(coord1.longitude)
    lat2, lon2 = math.radians(coord2.latitude), math.radians(coord2.longitude)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * c


def meters_to_lat_offset(meters: float) -> float:
    """Convert meters to approximate latitude offset."""
    return meters / 111_320  # 1 degree latitude ≈ 111,320 meters


def meters_to_lon_offset(meters: float, latitude: float) -> float:
    """Convert meters to approximate longitude offset at given latitude."""
    lat_rad = math.radians(latitude)
    return meters / (111_320 * math.cos(lat_rad))


@dataclass(frozen=True)
class GridPoint:
    """A grid point with coordinates and distance from center."""

    coordinates: Coordinates
    distance_m: float


def generate_grid_points(
    center: Coordinates,
    radius_m: float,
    interval_m: float = 8.0,
) -> list[GridPoint]:
    """
    Generate grid points within a circular radius.

    Creates a square grid of points and filters to those within the specified
    radius using Haversine distance.

    Args:
        center: Center coordinates
        radius_m: Search radius in meters
        interval_m: Spacing between grid points in meters

    Returns:
        List of GridPoint objects within the radius, sorted by distance.
    """
    lat_offset = meters_to_lat_offset(radius_m)
    lon_offset = meters_to_lon_offset(radius_m, center.latitude)

    lat_step = meters_to_lat_offset(interval_m)
    lon_step = meters_to_lon_offset(interval_m, center.latitude)

    grid_points: list[GridPoint] = []

    # Generate points in a square grid
    lat = center.latitude - lat_offset
    while lat <= center.latitude + lat_offset:
        lon = center.longitude - lon_offset
        while lon <= center.longitude + lon_offset:
            point = Coordinates(latitude=lat, longitude=lon)
            distance = haversine_distance(center, point)

            if distance <= radius_m:
                grid_points.append(GridPoint(
                    coordinates=point,
                    distance_m=round(distance, 2),
                ))

            lon += lon_step
        lat += lat_step

    # Sort by distance from center
    grid_points.sort(key=lambda p: p.distance_m)

    return grid_points


def deduplicate_nearby_points(
    points: list[GridPoint],
    min_distance_m: float = 5.0,
) -> list[GridPoint]:
    """
    Remove grid points that are too close to each other.

    Args:
        points: List of grid points
        min_distance_m: Minimum distance between kept points

    Returns:
        Deduplicated list of grid points.
    """
    if not points:
        return []

    kept: list[GridPoint] = [points[0]]

    for point in points[1:]:
        too_close = False
        for kept_point in kept:
            if haversine_distance(point.coordinates, kept_point.coordinates) < min_distance_m:
                too_close = True
                break
        if not too_close:
            kept.append(point)

    return kept
