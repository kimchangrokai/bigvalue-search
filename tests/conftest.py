"""Shared test fixtures for BigValue search tool."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bigvalue_search.geocoding import Coordinates
from bigvalue_search.bigvalue_api import (
    SearchResults,
    BuildingInfo,
    BusinessInfo,
    CardSalesInfo,
)


@pytest.fixture
def seoul_coordinates() -> Coordinates:
    """Seoul city center coordinates."""
    return Coordinates(latitude=37.5665, longitude=126.9780)


@pytest.fixture
def busan_coordinates() -> Coordinates:
    """Busan city center coordinates."""
    return Coordinates(latitude=35.1796, longitude=129.0756)


@pytest.fixture
def sample_buildings() -> list[BuildingInfo]:
    """Sample building data for testing."""
    return [
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
    ]


@pytest.fixture
def sample_businesses() -> list[BusinessInfo]:
    """Sample business data for testing."""
    return [
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
    ]


@pytest.fixture
def sample_card_sales() -> list[CardSalesInfo]:
    """Sample card sales data for testing."""
    return [
        CardSalesInfo(
            area_id="A001",
            area_name="마곡동",
            total_sales_amount=100_000_000.0,
            average_sales_per_store=5_000_000.0,
            number_of_stores=20,
            sales_by_category={"음식": 50_000_000, "소매": 30_000_000},
            monthly_sales={"2024-01": 10_000_000, "2024-02": 12_000_000},
        ),
    ]


@pytest.fixture
def sample_search_results(
    seoul_coordinates: Coordinates,
    sample_buildings: list[BuildingInfo],
    sample_businesses: list[BusinessInfo],
    sample_card_sales: list[CardSalesInfo],
) -> SearchResults:
    """Sample search results for testing."""
    return SearchResults(
        search_center=seoul_coordinates,
        radius_m=50.0,
        buildings=sample_buildings,
        businesses=sample_businesses,
        card_sales=sample_card_sales,
    )


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
