"""BigValue API module for collecting building, business, and card sales data.

Uses the BigValue REST API at rest.bigvalue.ai:
1. Login via Playwright to get accessToken from /api/auth/session
2. Get flow details and execute analysis via REST API
3. Parse report results for building/business/card-sales data

Flow execution endpoint:
  POST /workspace/channel/bundle/{bundle_id}/flow/{flow_id}/execute
  Body: {"type": "BUILDING", "key": "<cadastral_id>"}
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field

import requests

from bigvalue_search.config import config
from bigvalue_search.geocoding import Coordinates, reverse_geocode
from bigvalue_search.browser_auth import BrowserSession
from bigvalue_search.exceptions import APIError

logger = logging.getLogger(__name__)

# BigValue REST API base URL
REST_API_BASE: str = "https://rest.bigvalue.ai"

# Known bundle/flow IDs (discovered from API)
DEFAULT_BUNDLE_ID: str = "W-B-1770278691645-0PCWVHV7M88HV"  # 대신 AMC
DEFAULT_FLOW_ID: str = "W-F-1769560316113-0PA775GT53MFT"  # 사업자 정보 조회


# ─── Data Classes ────────────────────────────────────────────────────────────


@dataclass
class BuildingInfo:
    """Building information from BigValue."""

    building_id: str = ""
    building_name: str = ""
    address: str = ""
    road_address: str = ""
    building_type: str = ""
    total_floor_area: float = 0.0
    land_area: float = 0.0
    number_of_floors: int = 0
    year_built: int = 0
    latitude: float = 0.0
    longitude: float = 0.0
    distance_m: float = 0.0
    complex_key: str = ""
    pnu: str = ""
    road_name_address_management_number: str = ""
    raw_data: dict[str, object] = field(default_factory=dict)


@dataclass
class BusinessInfo:
    """Business person information from BigValue."""

    business_id: str = ""
    business_name: str = ""
    business_type: str = ""
    business_category: str = ""
    representative_name: str = ""
    employee_count: int = 0
    revenue_estimate: str = ""
    building_id: str = ""
    building_name: str = ""
    raw_data: dict[str, object] = field(default_factory=dict)


@dataclass
class CardSalesInfo:
    """Card sales information from BigValue."""

    area_id: str = ""
    area_name: str = ""
    total_sales_amount: float = 0.0
    average_sales_per_store: float = 0.0
    number_of_stores: int = 0
    sales_by_category: dict[str, float] = field(default_factory=dict)
    monthly_sales: dict[str, float] = field(default_factory=dict)
    raw_data: dict[str, object] = field(default_factory=dict)


@dataclass
class SearchResults:
    """Combined search results."""

    buildings: list[BuildingInfo] = field(default_factory=list)
    businesses: list[BusinessInfo] = field(default_factory=list)
    card_sales: list[CardSalesInfo] = field(default_factory=list)
    search_center: Coordinates | None = None
    radius_m: float = 0.0


# ─── API Client ──────────────────────────────────────────────────────────────


class BigValueAPI:
    """Client for the BigValue REST API (rest.bigvalue.ai)."""

    def __init__(self, session: BrowserSession) -> None:
        """
        Initialize BigValue API client.

        Args:
            session: Active BrowserSession from login_keep_browser()
        """
        self.session = session
        self.access_token: str = self._get_access_token()
        self.bundle_id: str = DEFAULT_BUNDLE_ID
        self.flow_id: str = DEFAULT_FLOW_ID
        self._rate_limit_delay: float = 0.5

    def _get_access_token(self) -> str:
        """Get accessToken from the browser session."""
        # 1. Use accessToken directly from BrowserSession (from /api/auth/session)
        if self.session.access_token:
            logger.info("Using accessToken from BrowserSession (length: %d)", len(self.session.access_token))
            return self.session.access_token

        # 2. Try fetching from browser's /api/auth/session endpoint
        try:
            token = self.session.page.evaluate('''async () => {
                const resp = await fetch('/api/auth/session');
                const data = await resp.json();
                return data.accessToken || '';
            }''')
            if token:
                logger.info("Got accessToken from browser /api/auth/session (length: %d)", len(token))
                return token
        except Exception as e:
            logger.warning("Failed to get accessToken from browser: %s", e)

        # 3. Fallback: use JWT token from session
        if self.session.jwt_token:
            logger.info("Using JWT token from session as fallback")
            return self.session.jwt_token

        return ""

    def _api_headers(self) -> dict[str, str]:
        """Get API headers with authorization."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, object] | None = None,
        params: dict[str, object] | None = None,
    ) -> dict[str, object] | None:
        """Make a REST API request."""
        url = f"{REST_API_BASE}{endpoint}"
        try:
            time.sleep(self._rate_limit_delay)
            resp = requests.request(
                method=method,
                url=url,
                headers=self._api_headers(),
                json=json_data,
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error for %s %s: %s", method, endpoint, e)
            if e.response is not None:
                logger.error("Response: %s", e.response.text[:500])
            return None
        except requests.exceptions.RequestException as e:
            logger.error("Request error for %s %s: %s", method, endpoint, e)
            return None

    # ── Discovery ────────────────────────────────────────────────────────────

    def discover_flows(self) -> list[dict[str, object]]:
        """
        Discover available flows from bundles.

        Returns:
            List of flow dicts with id, title, boundarySelection.
        """
        flows: list[dict[str, object]] = []

        # Get bundles
        data = self._request("GET", "/workspace/channel/bundle")
        if not data or "list" not in data:
            return flows

        bundle_list = data.get("list", [])
        if not isinstance(bundle_list, list):
            return flows

        for bundle in bundle_list:
            if not isinstance(bundle, dict):
                continue
            bundle_id = bundle.get("id", "")
            bundle_name = bundle.get("name", "")

            # Get flows for bundle
            flow_data = self._request(
                "GET",
                f"/workspace/channel/bundle/{bundle_id}/flow",
                params={"page": 1, "size": 10},
            )
            if not flow_data:
                continue

            page_data = flow_data.get("page", {})
            if not isinstance(page_data, dict):
                continue
            content = page_data.get("content", [])
            if not isinstance(content, list):
                continue
            for flow in content:
                if not isinstance(flow, dict):
                    continue
                flow["bundle_id"] = bundle_id
                flow["bundle_name"] = bundle_name
                flows.append(flow)
                logger.info(
                    "Found flow: %s (%s) in bundle %s",
                    flow.get("title", "?"),
                    flow.get("id", "?"),
                    bundle_name,
                )

        return flows

    def find_analysis_flow(self) -> tuple[str, str] | None:
        """
        Find the analysis flow (사업자 정보 조회).

        Returns:
            Tuple of (bundle_id, flow_id) or None.
        """
        flows = self.discover_flows()

        # Look for business info analysis flow
        for flow in flows:
            title = str(flow.get("title", ""))
            if "사업자" in title or "분석" in title or "조회" in title:
                return str(flow.get("bundle_id", "")), str(flow.get("id", ""))

        # Fall back to first flow
        if flows:
            return str(flows[0].get("bundle_id", "")), str(flows[0].get("id", ""))

        return None

    # ── PNU Lookup ───────────────────────────────────────────────────────────

    def get_pnu_from_address(self, address: str) -> str | None:
        """
        Get the PNU (Parcel Number Unit) for an address.

        Uses REST API endpoints to find the building/cadastral ID.

        Args:
            address: Korean address (e.g., "서울 강서구 마곡동 800-15")

        Returns:
            PNU string or None if not found.
        """
        logger.info("Looking up PNU for: %s", address)

        # Method 1: Check recent areas via REST API
        pnu = self._get_pnu_from_recent_areas(address)
        if pnu:
            logger.info("Found PNU from recent areas: %s", pnu)
            return pnu

        # Method 2: Search my areas via REST API
        pnu = self._get_pnu_from_my_areas(address)
        if pnu:
            logger.info("Found PNU from my areas: %s", pnu)
            return pnu

        # Method 3: Use browser to search and extract PNU
        pnu = self._get_pnu_from_browser(address)
        if pnu:
            logger.info("Found PNU from browser: %s", pnu)
            return pnu

        # Method 4: Use geocoding to construct PNU
        pnu = self._get_pnu_from_geocoding(address)
        if pnu:
            logger.info("Found PNU from geocoding: %s", pnu)
            return pnu

        logger.warning("Could not find PNU for: %s", address)
        return None

    def _get_pnu_from_my_areas(self, address: str) -> str | None:
        """Check my areas via REST API for matching address."""
        data = self._request("GET", "/account/my-area", params={"page": 1, "size": 100})
        if not data:
            return None

        # Handle different response formats
        areas = data if isinstance(data, list) else data.get("list", data.get("content", []))
        if not isinstance(areas, list):
            return None

        for area in areas:
            if not isinstance(area, dict):
                continue
            area_address = str(area.get("address", area.get("jibunAddress", "")))
            if address in area_address or area_address in address:
                cadastral = area.get("cadastral", {})
                if isinstance(cadastral, dict):
                    return str(cadastral.get("id", cadastral.get("pnu", "")))
                # Try direct ID fields
                for key in ["cadastralId", "pnu", "id"]:
                    if key in area:
                        return str(area[key])

        return None

    def _get_pnu_from_recent_areas(self, address: str) -> str | None:
        """Check recent areas via REST API for matching address."""
        data = self._request("GET", "/auth/recent-area")
        if not data:
            return None

        # Handle different response formats
        areas = data if isinstance(data, list) else data.get("list", data.get("content", []))
        if not isinstance(areas, list):
            return None

        for area in areas:
            if not isinstance(area, dict):
                continue
            area_address = str(area.get("address", area.get("jibunAddress", "")))
            if address in area_address or area_address in address:
                cadastral = area.get("cadastral", {})
                if isinstance(cadastral, dict):
                    return str(cadastral.get("id", cadastral.get("pnu", "")))
                # Try direct ID fields
                for key in ["cadastralId", "pnu", "id"]:
                    if key in area:
                        return str(area[key])

        return None

    def _get_pnu_from_browser(self, address: str) -> str | None:
        """Use browser to search for address and extract PNU from intercepted APIs."""
        page = self.session.page
        intercepted_pnu: list[str] = []

        def on_response(response: object) -> None:
            try:
                url = response.url  # type: ignore[union-attr]
                if 'rest.bigvalue.ai' in url and response.status == 200:  # type: ignore[union-attr]
                    ct = response.headers.get('content-type') or ''  # type: ignore[union-attr]
                    if 'json' in ct:
                        data = response.json()  # type: ignore[union-attr]
                        if isinstance(data, dict):
                            self._extract_pnus_from_data(data, intercepted_pnu)
            except Exception:
                pass

        page.on("response", on_response)

        try:
            # Search for address
            addr_input = page.query_selector('input[placeholder*="장소"], input[placeholder*="도로명"]')
            if not addr_input:
                return None

            addr_input.click()
            time.sleep(0.5)
            addr_input.fill('')
            addr_input.type(address, delay=80)
            time.sleep(3)
            addr_input.press('Enter')
            time.sleep(5)

            # Click on map center to trigger data loading
            canvas = page.query_selector('canvas')
            if canvas:
                box = canvas.bounding_box()
                if box:
                    cx = box["x"] + box["width"] / 2
                    cy = box["y"] + box["height"] / 2
                    page.mouse.click(cx, cy)
                    time.sleep(5)

            # Click analysis button
            btn = page.query_selector('button:has-text("사업자 정보"), button:has-text("대신AMC")')
            if btn:
                btn.click()
                time.sleep(5)

            return intercepted_pnu[0] if intercepted_pnu else None

        except Exception as e:
            logger.debug("Browser PNU lookup failed: %s", e)
            return None

    def _extract_pnus_from_data(self, data: dict[str, object], pnus: list[str]) -> None:
        """Recursively extract PNU-like strings from data."""
        for key, value in data.items():
            if isinstance(value, str) and re.match(r'^\d{19}$', value):
                pnus.append(value)
            elif isinstance(value, dict):
                self._extract_pnus_from_data(value, pnus)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._extract_pnus_from_data(item, pnus)

    def _get_pnu_from_geocoding(self, address: str) -> str | None:
        """Use Naver geocoding to get coordinates, then reverse geocode for PNU."""
        page = self.session.page

        try:
            # Use BigValue's Naver geocoding proxy
            geocode_data = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch("/api/naver/map-geocode/v2/geocode?query={address}");
                    return await resp.json();
                }} catch(e) {{
                    return {{error: e.message}};
                }}
            }}''')

            if not geocode_data or geocode_data.get("error"):
                logger.debug("Geocoding request failed: %s", geocode_data)
                return None

            if geocode_data.get("status") != "OK":
                logger.debug("Geocoding status not OK: %s", geocode_data.get("status"))
                return None

            addresses = geocode_data.get("addresses", [])
            if not addresses:
                return None

            # Get coordinates and address details
            addr = addresses[0]
            x = addr.get("x", "")  # longitude
            y = addr.get("y", "")  # latitude
            jibun = addr.get("jibunAddress", "")

            if not x or not y:
                return None

            logger.info("Geocoded to: (%s, %s), jibun: %s", y, x, jibun)

            # Reverse geocode to get legal code
            reverse_data = page.evaluate(f'''async () => {{
                try {{
                    const resp = await fetch("/api/naver/map-reversegeocode/v2/gc?coords={x},{y}&output=json&orders=legalcode");
                    return await resp.json();
                }} catch(e) {{
                    return {{error: e.message}};
                }}
            }}''')

            if not reverse_data or reverse_data.get("error"):
                logger.debug("Reverse geocoding request failed: %s", reverse_data)
                return None

            if reverse_data.get("status", {}).get("code") != 0:
                logger.debug("Reverse geocoding status not OK: %s", reverse_data.get("status"))
                return None

            results = reverse_data.get("results", [])
            if not results:
                return None

            # Extract legal code (10 digits: 5 시군구 + 5 법정동)
            code = results[0].get("code", {})
            legal_code = code.get("id", "")

            if not legal_code:
                return None

            logger.info("Legal code: %s", legal_code)

            # Extract region info for parcel number
            region = results[0].get("region", {})
            area3 = region.get("area3", {}).get("name", "")  # 동
            area4 = region.get("area4", {}).get("name", "")  # 리

            # Try to extract parcel number from address
            # Address format: "서울 강서구 마곡동 800-15" → 번: 800, 지: 15
            parcel_match = re.search(r'(\d+)(?:-(\d+))?', address.split(area3)[-1] if area3 in address else address)
            bun = "0000"
            ji = "0000"
            if parcel_match:
                bun = parcel_match.group(1).zfill(4)
                ji = (parcel_match.group(2) or "0").zfill(4)

            # Construct full PNU (19 digits)
            # Format: 시군구(5) + 법정동(5) + 리(1) + 번(4) + 지(4)
            full_pnu = f"{legal_code}1{bun}{ji}"

            logger.info("Constructed PNU: %s (bun=%s, ji=%s)", full_pnu, bun, ji)
            return full_pnu

        except Exception as e:
            logger.debug("Geocoding PNU lookup failed: %s", e)

        return None

    # ── Flow Execution ───────────────────────────────────────────────────────

    def execute_flow(
        self,
        area_type: str,
        key: str,
    ) -> dict[str, object] | None:
        """
        Execute a BigValue analysis flow.

        Args:
            area_type: Type of area (BUILDING, POLYGON, LAND_PARCEL, CIRCLE)
            key: Area key (PNU for BUILDING/LAND_PARCEL, coordinates for POLYGON/CIRCLE)

        Returns:
            Flow execution result dict or None.
        """
        endpoint = f"/workspace/channel/bundle/{self.bundle_id}/flow/{self.flow_id}/execute"
        body: dict[str, object] = {
            "type": area_type,
            "key": key,
        }

        logger.info("Executing flow: type=%s, key=%s", area_type, key)
        return self._request("POST", endpoint, json_data=body)

    # ── Response Parsing ─────────────────────────────────────────────────────

    def parse_flow_result(self, result: dict[str, object]) -> tuple[
        list[BuildingInfo], list[BusinessInfo], list[CardSalesInfo]
    ]:
        """
        Parse flow execution result into structured data.

        Args:
            result: Flow execution response dict.

        Returns:
            Tuple of (buildings, businesses, card_sales).
        """
        buildings: list[BuildingInfo] = []
        businesses: list[BusinessInfo] = []
        card_sales: list[CardSalesInfo] = []

        if not result:
            return buildings, businesses, card_sales

        data = result.get("data", {})
        if not isinstance(data, dict):
            return buildings, businesses, card_sales
        report = data.get("report", {})
        if not isinstance(report, dict):
            return buildings, businesses, card_sales
        report_result = report.get("result", [])
        if not isinstance(report_result, list):
            return buildings, businesses, card_sales

        for section in report_result:
            if not isinstance(section, dict):
                continue
            contents = section.get("contents", [])
            if not isinstance(contents, list):
                continue

            for item in contents:
                if not isinstance(item, dict):
                    continue

                # Determine what type of data this is
                if self._is_business_data(item):
                    businesses.append(self._parse_business(item))
                elif self._is_card_sales_data(item):
                    card_sales.append(self._parse_card_sales(item))
                elif self._is_building_data(item):
                    buildings.append(self._parse_building(item))

        return buildings, businesses, card_sales

    @staticmethod
    def _is_business_data(item: dict[str, object]) -> bool:
        """Check if item is business data."""
        biz_keys = {"상호명", "업종", "업태", "대표자", "사업자"}
        return bool(biz_keys & set(item.keys()))

    @staticmethod
    def _is_card_sales_data(item: dict[str, object]) -> bool:
        """Check if item is card sales data."""
        card_keys = {"매출", "카드", "결제", "신용카드", "체크카드"}
        return bool(card_keys & set(item.keys()))

    @staticmethod
    def _is_building_data(item: dict[str, object]) -> bool:
        """Check if item is building data."""
        bld_keys = {"건물명", "층수", "건축년도", "연면적", "대지면적"}
        return bool(bld_keys & set(item.keys()))

    @staticmethod
    def _parse_business(data: dict[str, object]) -> BusinessInfo:
        """Parse business info from flow result."""
        return BusinessInfo(
            business_name=str(data.get("상호명", data.get("name", ""))),
            business_type=str(data.get("업종_중분류", data.get("업종", data.get("type", "")))),
            business_category=str(data.get("업종_대분류", data.get("category", ""))),
            representative_name=str(data.get("대표자명", data.get("representative", ""))),
            employee_count=int(str(data.get("종업원수", data.get("employees", 0) or 0))),
            revenue_estimate=str(data.get("추정매출", data.get("revenue", ""))),
            building_name=str(data.get("건물명", "")),
            raw_data=data,
        )

    @staticmethod
    def _parse_card_sales(data: dict[str, object]) -> CardSalesInfo:
        """Parse card sales info from flow result."""
        return CardSalesInfo(
            area_name=str(data.get("지역명", data.get("area", ""))),
            total_sales_amount=float(str(data.get("총매출", data.get("total_sales", 0) or 0))),
            average_sales_per_store=float(str(data.get("점포당매출", data.get("avg_sales", 0) or 0))),
            number_of_stores=int(str(data.get("점포수", data.get("stores", 0) or 0))),
            raw_data=data,
        )

    @staticmethod
    def _parse_building(data: dict[str, object]) -> BuildingInfo:
        """Parse building info from flow result."""
        return BuildingInfo(
            building_name=str(data.get("건물명", data.get("name", ""))),
            address=str(data.get("지번주소", data.get("address", ""))),
            road_address=str(data.get("도로명주소", data.get("road_address", ""))),
            building_type=str(data.get("건물유형", data.get("type", ""))),
            number_of_floors=int(str(data.get("층수", data.get("floors", 0) or 0))),
            year_built=int(str(data.get("건축년도", data.get("year_built", 0) or 0))),
            raw_data=data,
        )

    # ── Main Entry Point ──────────────────────────────────────────────────────

    def verify_connection(self) -> bool:
        """
        Verify REST API connection by fetching user info.

        Returns:
            True if connection is valid.
        """
        data = self._request("GET", "/auth/info")
        if data:
            user_name = data.get("name", data.get("email", "Unknown"))
            logger.info("API connection verified. User: %s", user_name)
            return True
        logger.warning("API connection verification failed")
        return False

    def get_report_history(self) -> list[dict[str, object]]:
        """
        Get report history from the API.

        Returns:
            List of report history items.
        """
        data = self._request("GET", "/workspace/report/history")
        if not data:
            return []

        # Handle different response formats
        if isinstance(data, list):
            return data
        result = data.get("list", data.get("content", []))
        return result if isinstance(result, list) else []

    def collect_all_data(
        self,
        center: Coordinates,
        radius_m: float = 50,
        address: str | None = None,
    ) -> SearchResults:
        """
        Collect all available data for a location.

        Steps:
            1. Verify API connection
            2. Get PNU for the address
            3. Execute the analysis flow
            4. Parse the results

        Args:
            center: Center coordinates
            radius_m: Search radius in metres
            address: Optional explicit address string

        Returns:
            SearchResults with all collected data.
        """
        results = SearchResults(search_center=center, radius_m=radius_m)

        # Use provided address or reverse geocode
        if not address:
            address = reverse_geocode(center.latitude, center.longitude) or ""

        if not address:
            logger.error("No address to search")
            return results

        logger.info("Collecting data for: %s", address)

        # Step 1: Verify API connection
        if not self.verify_connection():
            logger.error("API connection verification failed")
            return results

        # Step 2: Get PNU
        pnu = self.get_pnu_from_address(address)
        if not pnu:
            logger.error("Could not find PNU for address: %s", address)
            return results

        logger.info("Using PNU: %s", pnu)

        # Step 3: Execute flow
        flow_result = self.execute_flow("BUILDING", pnu)
        if not flow_result:
            logger.error("Flow execution failed")
            return results

        # Step 4: Parse results
        buildings, businesses, card_sales = self.parse_flow_result(flow_result)
        results.buildings.extend(buildings)
        results.businesses.extend(businesses)
        results.card_sales.extend(card_sales)

        logger.info(
            "Total: %d buildings, %d businesses, %d card sales",
            len(results.buildings),
            len(results.businesses),
            len(results.card_sales),
        )

        return results
