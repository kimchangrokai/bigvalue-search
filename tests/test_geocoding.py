"""Tests for geocoding module."""

from __future__ import annotations

import pytest

from bigvalue_search.geocoding import Coordinates, _expand_address_variants


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

    def test_frozen(self) -> None:
        coord = Coordinates(latitude=37.5665, longitude=126.9780)
        with pytest.raises(AttributeError):
            coord.latitude = 38.0  # type: ignore[misc]


class TestExpandAddressVariants:
    """Tests for address variant expansion."""

    def test_original_address_first(self) -> None:
        variants = _expand_address_variants("서울 강서구 마곡동 800-15")
        assert variants[0] == "서울 강서구 마곡동 800-15"

    def test_seoul_expansion(self) -> None:
        variants = _expand_address_variants("서울 강서구 마곡동 800-15")
        assert "서울특별시 강서구 마곡동 800-15" in variants

    def test_no_expansion_for_full_name(self) -> None:
        variants = _expand_address_variants("서울특별시 강서구 마곡동 800-15")
        assert len(variants) == 1

    def test_busan_expansion(self) -> None:
        variants = _expand_address_variants("부산 해운대구 우동")
        assert "부산광역시 해운대구 우동" in variants
