"""Tests for BigValue API module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from bigvalue_search.bigvalue_api import (
    BuildingInfo,
    BusinessInfo,
    CardSalesInfo,
    SearchResults,
)
from bigvalue_search.data_export import export_to_excel, export_to_json


class TestDataClasses:
    """Tests for data class defaults."""

    def test_building_info_defaults(self) -> None:
        b = BuildingInfo()
        assert b.building_id == ""
        assert b.total_floor_area == 0.0
        assert b.number_of_floors == 0

    def test_business_info_defaults(self) -> None:
        b = BusinessInfo()
        assert b.business_id == ""
        assert b.employee_count == 0

    def test_card_sales_info_defaults(self) -> None:
        s = CardSalesInfo()
        assert s.total_sales_amount == 0.0
        assert s.sales_by_category == {}

    def test_search_results_defaults(self) -> None:
        r = SearchResults()
        assert r.buildings == []
        assert r.businesses == []
        assert r.card_sales == []
        assert r.search_center is None


class TestExport:
    """Tests for data export."""

    def test_export_excel(
        self,
        tmp_path: Path,
        sample_search_results: SearchResults,
    ) -> None:
        """Test Excel export."""
        from bigvalue_search.config import config as cfg
        original = cfg.OUTPUT_DIR
        cfg.OUTPUT_DIR = str(tmp_path)
        try:
            filepath = export_to_excel(sample_search_results, "test.xlsx")
            assert filepath.exists()
            assert filepath.suffix == ".xlsx"
        finally:
            cfg.OUTPUT_DIR = original

    def test_export_json(
        self,
        tmp_path: Path,
        sample_search_results: SearchResults,
    ) -> None:
        """Test JSON export."""
        from bigvalue_search.config import config as cfg
        original = cfg.OUTPUT_DIR
        cfg.OUTPUT_DIR = str(tmp_path)
        try:
            filepath = export_to_json(sample_search_results, "test.json")
            assert filepath.exists()
            assert filepath.suffix == ".json"

            data = json.loads(filepath.read_text(encoding="utf-8"))
            assert "buildings" in data
            assert "businesses" in data
            assert "card_sales" in data
            assert data["summary"]["total_buildings"] == 1
        finally:
            cfg.OUTPUT_DIR = original

    def test_json_content_structure(
        self,
        tmp_path: Path,
        sample_search_results: SearchResults,
    ) -> None:
        """Test JSON output structure."""
        from bigvalue_search.config import config as cfg
        original = cfg.OUTPUT_DIR
        cfg.OUTPUT_DIR = str(tmp_path)
        try:
            filepath = export_to_json(sample_search_results, "test.json")
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


class TestTokenCache:
    """Tests for token caching."""

    def test_save_and_load_cache(self, tmp_path: Path) -> None:
        """Test token cache save/load."""
        from bigvalue_search.browser_auth import (
            AuthResult,
            _save_token_cache,
            _load_token_cache,
        )
        import bigvalue_search.browser_auth as ba

        original = ba.TOKEN_CACHE_FILE
        cache_file = tmp_path / ".token_cache.json"
        ba.TOKEN_CACHE_FILE = cache_file
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
            ba.TOKEN_CACHE_FILE = original

    def test_load_nonexistent_cache(self, tmp_path: Path) -> None:
        """Test loading when no cache exists."""
        from bigvalue_search.browser_auth import _load_token_cache
        import bigvalue_search.browser_auth as ba

        original = ba.TOKEN_CACHE_FILE
        ba.TOKEN_CACHE_FILE = tmp_path / "nonexistent.json"
        try:
            result = _load_token_cache()
            assert result is None
        finally:
            ba.TOKEN_CACHE_FILE = original
