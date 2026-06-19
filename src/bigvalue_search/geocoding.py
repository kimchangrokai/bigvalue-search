"""Geocoding module using OpenStreetMap Nominatim."""

from __future__ import annotations

from dataclasses import dataclass

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

from bigvalue_search.config import config
from bigvalue_search.exceptions import GeocodingError

# Korean city abbreviations to full names
CITY_EXPANSIONS: dict[str, str] = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "제주": "제주특별자치도",
}


@dataclass(frozen=True)
class Coordinates:
    """Latitude/longitude pair."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}")


def _expand_address_variants(address: str) -> list[str]:
    """Generate address variants by expanding Korean city abbreviations.

    Tries the original address first, then variants with expanded city names.
    """
    variants: list[str] = [address]

    for abbrev, full in CITY_EXPANSIONS.items():
        if address.startswith(abbrev + " ") or address.startswith(abbrev + ","):
            variants.append(full + address[len(abbrev):])

    return variants


def geocode_address(address: str) -> Coordinates:
    """
    Geocode a Korean address using OpenStreetMap Nominatim.

    Tries multiple address formats:
    1. Original address
    2. With country code bias (kr)
    3. Expanded city abbreviations (e.g., 서울 → 서울특별시)

    Args:
        address: Full address string (e.g., "서울 강서구 마곡동 800-15")

    Returns:
        Coordinates with latitude and longitude.

    Raises:
        GeocodingError: If address cannot be geocoded.
    """
    geolocator = Nominatim(user_agent=config.NOMINATIM_USER_AGENT)

    for variant in _expand_address_variants(address):
        try:
            location = geolocator.geocode(variant, language="ko", timeout=10)
        except GeocoderTimedOut as e:
            raise GeocodingError(f"Nominatim timed out for address: {variant}") from e
        except GeocoderServiceError as e:
            raise GeocodingError(f"Geocoding service error: {e}") from e

        if location is not None:
            return Coordinates(latitude=location.latitude, longitude=location.longitude)

        # Try with country code bias
        try:
            location = geolocator.geocode(
                variant, language="ko", timeout=10,
                country_codes="kr"
            )
        except (GeocoderTimedOut, GeocoderServiceError):
            pass

        if location is not None:
            return Coordinates(latitude=location.latitude, longitude=location.longitude)

    raise GeocodingError(f"Could not geocode address: {address}")


def reverse_geocode(lat: float, lon: float) -> str | None:
    """
    Reverse geocode coordinates to address.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Address string or None if not found.
    """
    geolocator = Nominatim(user_agent=config.NOMINATIM_USER_AGENT)

    try:
        location = geolocator.reverse((lat, lon), language="ko", timeout=10)
        return location.address if location else None
    except (GeocoderTimedOut, GeocoderServiceError):
        return None
