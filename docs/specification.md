# BigValue Search Tool - 사양서 (Specification)

**Version**: 1.0.0
**Last Updated**: 2026-06-20
**Status**: Active

---

## 1. 시스템 사양

### 1.1 실행 환경

| 항목 | 최소 사양 | 권장 사양 |
|------|----------|----------|
| OS | Windows 10, macOS 12, Ubuntu 20.04 | 최신 버전 |
| Python | 3.10 | 3.12 |
| 메모리 | 4GB RAM | 8GB RAM |
| 디스크 | 500MB 여유 공간 | 1GB |
| 네트워크 | 인터넷 연결 필수 | 안정적인 연결 |

### 1.2 필수 소프트웨어

| 소프트웨어 | 버전 | 용도 |
|-----------|------|------|
| Python | ≥3.10 | 런타임 |
| pip | 최신 | 패키지 관리 |
| Playwright | ≥1.40 | 브라우저 자동화 |
| Chromium | Playwright 내장 | 브라우저 엔진 |

---

## 2. 모듈 상세 사양

### 2.1 cli.py - CLI 오케스트레이터

#### 함수 사양

##### `setup_logging(verbose: bool = False) -> None`
| 항목 | 설명 |
|------|------|
| **목적** | 로깅 설정 |
| **파라미터** | `verbose`: True 시 DEBUG 레벨, False 시 INFO 레벨 |
| **출력 포맷** | `%(asctime)s [%(levelname)s] %(name)s: %(message)s` |
| **날짜 포맷** | `%Y-%m-%d %H:%M:%S` |

##### `parse_args() -> argparse.Namespace`
| 항목 | 설명 |
|------|------|
| **목적** | CLI 인자 파싱 |
| **반환값** | 파싱된 인자 네임스페이스 |
| **필수 인자** | `--address` |
| **선택 인자** | `--radius`, `--output`, `--interval`, `--no-auth`, `--clear-cache`, `--headless`, `--verbose` |

##### `run_search(args: argparse.Namespace) -> int`
| 항목 | 설명 |
|------|------|
| **목적** | 검색 워크플로우 실행 |
| **반환값** | 종료 코드 (0: 성공, 1: 실패, 130: 중단) |
| **예외** | `KeyboardInterrupt`, `BigValueError` |

##### `main() -> int`
| 항목 | 설명 |
|------|------|
| **목적** | 메인 진입점 |
| **반환값** | 종료 코드 |

---

### 2.2 config.py - 설정 관리

#### 클래스: `Config`

| 속성 | 타입 | 기본값 | 환경변수 | 설명 |
|------|------|--------|----------|------|
| `BIGVALUE_EMAIL` | `str` | `""` | `BIGVALUE_EMAIL` | BigValue 로그인 이메일 |
| `BIGVALUE_PASSWORD` | `str` | `""` | `BIGVALUE_PASSWORD` | BigValue 로그인 비밀번호 |
| `BIGVALUE_API_BASE` | `str` | `"https://service.bigvalue.ai"` | `BIGVALUE_API_BASE` | BigValue 서비스 URL |
| `BIGVALUE_API_URL` | `str` | `"https://api.bigvalue.co.kr"` | `BIGVALUE_API_URL` | BigValue API URL |
| `HEADLESS` | `bool` | `True` | `HEADLESS` | 헤드리스 모드 여부 |
| `BROWSER_TIMEOUT` | `int` | `30000` | `BROWSER_TIMEOUT` | 브라우저 타임아웃 (ms) |
| `NOMINATIM_USER_AGENT` | `str` | `"bigvalue-search-tool/1.0"` | - | Nominatim User-Agent |
| `DEFAULT_RADIUS_M` | `int` | `50` | - | 기본 검색 반경 (m) |
| `GRID_INTERVAL_M` | `int` | `8` | - | 기본 그리드 간격 (m) |
| `OUTPUT_DIR` | `str` | `"output"` | `OUTPUT_DIR` | 출력 디렉토리 |

#### 메서드: `validate() -> list[str]`
| 항목 | 설명 |
|------|------|
| **목적** | 필수 설정 검증 |
| **반환값** | 누락된 필드 목록 |
| **검증 대상** | `BIGVALUE_EMAIL`, `BIGVALUE_PASSWORD` |

---

### 2.3 geocoding.py - 주소 변환

#### 데이터 클래스: `Coordinates`

| 필드 | 타입 | 설명 |
|------|------|------|
| `latitude` | `float` | 위도 (-90 ~ 90) |
| `longitude` | `float` | 경도 (-180 ~ 180) |

#### 상수: `CITY_EXPANSIONS`

| 약어 | 확장 |
|------|------|
| 서울 | 서울특별시 |
| 부산 | 부산광역시 |
| 대구 | 대구광역시 |
| 인천 | 인천광역시 |
| 광주 | 광주광역시 |
| 대전 | 대전광역시 |
| 울산 | 울산광역시 |
| 세종 | 세종특별자치시 |
| 제주 | 제주특별자치도 |

#### 함수 사양

##### `geocode_address(address: str) -> Coordinates`
| 항목 | 설명 |
|------|------|
| **목적** | 한국어 주소를 좌표로 변환 |
| **파라미터** | `address`: 전체 주소 문자열 |
| **반환값** | `Coordinates` 객체 |
| **예외** | `GeocodingError`: 변환 실패 시 |
| **시도 순서** | 원본 → 국가코드 바이어스 → 도시 확장 변형 |

##### `reverse_geocode(lat: float, lon: float) -> str | None`
| 항목 | 설명 |
|------|------|
| **목적** | 좌표를 주소로 역변환 |
| **파라미터** | `lat`: 위도, `lon`: 경도 |
| **반환값** | 주소 문자열 또는 `None` |

##### `_expand_address_variants(address: str) -> list[str]`
| 항목 | 설명 |
|------|------|
| **목적** | 주소 변형 생성 |
| **반환값** | 변형된 주소 목록 |

---

### 2.4 radius_search.py - 그리드 포인트 생성

#### 상수

| 상수 | 값 | 설명 |
|------|-----|------|
| `EARTH_RADIUS_M` | `6_371_000` | 지구 반지름 (m) |

#### 데이터 클래스: `GridPoint`

| 필드 | 타입 | 설명 |
|------|------|------|
| `coordinates` | `Coordinates` | 좌표 |
| `distance_m` | `float` | 중심까지의 거리 (m) |

#### 함수 사양

##### `haversine_distance(coord1: Coordinates, coord2: Coordinates) -> float`
| 항목 | 설명 |
|------|------|
| **목적** | Haversine 공식으로 두 지점 간 거리 계산 |
| **반환값** | 거리 (미터) |

##### `meters_to_lat_offset(meters: float) -> float`
| 항목 | 설명 |
|------|------|
| **목적** | 미터를 위도 오프셋으로 변환 |
| **변환값** | 1도 ≈ 111,320m |

##### `meters_to_lon_offset(meters: float, latitude: float) -> float`
| 항목 | 설명 |
|------|------|
| **목적** | 미터를 경도 오프셋으로 변환 |
| **고려사항** | 위도에 따른 경도 간격 차이 |

##### `generate_grid_points(center: Coordinates, radius_m: float, interval_m: float = 8.0) -> list[GridPoint]`
| 항목 | 설명 |
|------|------|
| **목적** | 원형 반경 내 격자 포인트 생성 |
| **알고리즘** | 사각 격자 생성 후 원형 필터링 |
| **정렬** | 중심까지 거리 기준 오름차순 |
| **반환값** | `GridPoint` 목록 |

##### `deduplicate_nearby_points(points: list[GridPoint], min_distance_m: float = 5.0) -> list[GridPoint]`
| 항목 | 설명 |
|------|------|
| **목적** | 인근 포인트 중복 제거 |
| **기준** | `min_distance_m` 이내 포인트 제거 |
| **반환값** | 중복 제거된 `GridPoint` 목록 |

---

### 2.5 browser_auth.py - 브라우저 인증

#### 상수

| 상수 | 값 | 설명 |
|------|-----|------|
| `SIGN_IN_URL` | `{BIGVALUE_API_BASE}/sign-in` | 로그인 페이지 URL |
| `TOKEN_CACHE_FILE` | 프로젝트 루트/.token_cache.json | 토큰 캐시 파일 |

#### 데이터 클래스: `AuthResult`

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `jwt_token` | `str` | `""` | JWT 토큰 |
| `access_token` | `str` | `""` | accessToken |
| `success` | `bool` | `False` | 인증 성공 여부 |
| `error` | `str` | `""` | 오류 메시지 |
| `cookies` | `dict[str, str]` | `{}` | 쿠키 정보 |

#### 클래스: `BrowserSession`

| 속성 | 타입 | 설명 |
|------|------|------|
| `page` | `Page` | Playwright 페이지 |
| `context` | `BrowserContext` | 브라우저 컨텍스트 |
| `browser` | `Browser` | 브라우저 인스턴스 |
| `_playwright` | `object` | Playwright 인스턴스 |
| `jwt_token` | `str` | JWT 토큰 |
| `access_token` | `str` | accessToken |
| `cookies` | `dict[str, str]` | 쿠키 정보 |

##### 메서드: `close() -> None`
| 항목 | 설명 |
|------|------|
| **목적** | 브라우저 및 리소스 정리 |

#### 함수 사양

##### `login_keep_browser(email, password, headless, use_cache) -> BrowserSession | None`
| 항목 | 설명 |
|------|------|
| **목적** | 로그인 후 브라우저 세션 유지 |
| **반환값** | `BrowserSession` 또는 `None` |
| **토큰 추출 순서** | accessToken → 네트워크 캡처 → 페이지 추출 → 쿠키 |

##### `login_with_playwright(email, password, headless, use_cache) -> AuthResult`
| 항목 | 설명 |
|------|------|
| **목적** | 로그인 후 브라우저 종료 |
| **반환값** | `AuthResult` |
| **비고** | 미사용 함수 (삭제 대상) |

##### `clear_token_cache() -> None`
| 항목 | 설명 |
|------|------|
| **목적** | 캐시된 토큰 파일 삭제 |

#### 선택자 상수

| 이름 | 용도 |
|------|------|
| `EMAIL_SELECTORS` | 이메일 입력 필드 선택자 목록 |
| `PASSWORD_SELECTORS` | 비밀번호 입력 필드 선택자 목록 |
| `LOGIN_BUTTON_SELECTORS` | 로그인 버튼 선택자 목록 |

---

### 2.6 bigvalue_api.py - REST API 클라이언트

#### 상수

| 상수 | 값 | 설명 |
|------|-----|------|
| `REST_API_BASE` | `"https://rest.bigvalue.ai"` | REST API 베이스 URL |
| `DEFAULT_BUNDLE_ID` | `"W-B-1770278691645-0PCWVHV7M88HV"` | 기본 번들 ID (대신 AMC) |
| `DEFAULT_FLOW_ID` | `"W-F-1769560316113-0PA775GT53MFT"` | 기본 Flow ID (사업자 정보 조회) |

#### 데이터 클래스

##### `BuildingInfo`
| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `building_id` | `str` | `""` | 건물 ID |
| `building_name` | `str` | `""` | 건물명 |
| `address` | `str` | `""` | 지번주소 |
| `road_address` | `str` | `""` | 도로명주소 |
| `building_type` | `str` | `""` | 건물 유형 |
| `total_floor_area` | `float` | `0.0` | 연면적 (㎡) |
| `land_area` | `float` | `0.0` | 대지면적 (㎡) |
| `number_of_floors` | `int` | `0` | 층수 |
| `year_built` | `int` | `0` | 건축년도 |
| `latitude` | `float` | `0.0` | 위도 |
| `longitude` | `float` | `0.0` | 경도 |
| `distance_m` | `float` | `0.0` | 중심까지 거리 |
| `complex_key` | `str` | `""` | 단지 키 |
| `pnu` | `str` | `""` | 토지 고유번호 |
| `road_name_address_management_number` | `str` | `""` | 도로명주소 관리번호 |
| `raw_data` | `dict[str, object]` | `{}` | 원본 데이터 |

##### `BusinessInfo`
| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `business_id` | `str` | `""` | 사업자 ID |
| `business_name` | `str` | `""` | 상호명 |
| `business_type` | `str` | `""` | 업종 |
| `business_category` | `str` | `""` | 업태 |
| `representative_name` | `str` | `""` | 대표자명 |
| `employee_count` | `int` | `0` | 종업원 수 |
| `revenue_estimate` | `str` | `""` | 추정매출 |
| `building_id` | `str` | `""` | 건물 ID |
| `building_name` | `str` | `""` | 건물명 |
| `raw_data` | `dict[str, object]` | `{}` | 원본 데이터 |

##### `CardSalesInfo`
| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `area_id` | `str` | `""` | 지역 ID |
| `area_name` | `str` | `""` | 지역명 |
| `total_sales_amount` | `float` | `0.0` | 총매출금액 |
| `average_sales_per_store` | `float` | `0.0` | 점포당 평균매출 |
| `number_of_stores` | `int` | `0` | 점포 수 |
| `sales_by_category` | `dict[str, float]` | `{}` | 카테고리별 매출 |
| `monthly_sales` | `dict[str, float]` | `{}` | 월별 매출 |
| `raw_data` | `dict[str, object]` | `{}` | 원본 데이터 |

##### `SearchResults`
| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `buildings` | `list[BuildingInfo]` | `[]` | 건물 목록 |
| `businesses` | `list[BusinessInfo]` | `[]` | 사업자 목록 |
| `card_sales` | `list[CardSalesInfo]` | `[]` | 카드매출 목록 |
| `search_center` | `Coordinates \| None` | `None` | 검색 중심 좌표 |
| `radius_m` | `float` | `0.0` | 검색 반경 |

#### 클래스: `BigValueAPI`

##### 생성자: `__init__(session: BrowserSession)`
| 항목 | 설명 |
|------|------|
| **파라미터** | `session`: 활성 BrowserSession |
| **초기화** | access_token, bundle_id, flow_id |

##### 메서드 사양

| 메서드 | 반환값 | 설명 |
|--------|--------|------|
| `_get_access_token()` | `str` | accessToken 추출 |
| `_api_headers()` | `dict[str, str]` | API 헤더 생성 |
| `_request(method, endpoint, json_data, params)` | `dict \| None` | REST API 요청 |
| `discover_flows()` | `list[dict]` | 사용 가능한 Flow 탐색 |
| `find_analysis_flow()` | `tuple[str, str] \| None` | 분석 Flow 검색 |
| `get_pnu_from_address(address)` | `str \| None` | PNU 조회 |
| `execute_flow(area_type, key)` | `dict \| None` | Flow 실행 |
| `parse_flow_result(result)` | `tuple[list, list, list]` | 결과 파싱 |
| `verify_connection()` | `bool` | API 연결 확인 |
| `get_report_history()` | `list[dict]` | 리포트 히스토리 조회 |
| `collect_all_data(center, radius_m, address)` | `SearchResults` | 전체 데이터 수집 |

##### PNU 조회 메서드

| 메서드 | 우선순위 | 설명 |
|--------|----------|------|
| `_get_pnu_from_recent_areas(address)` | 1 | 최근 지역 API |
| `_get_pnu_from_my_areas(address)` | 2 | 내 지역 API |
| `_get_pnu_from_browser(address)` | 3 | 브라우저 스크래핑 |
| `_get_pnu_from_geocoding(address)` | 4 | 지오코딩 역추적 |

##### 결과 파싱 메서드

| 메서드 | 설명 |
|--------|------|
| `_is_business_data(item)` | 사업자 데이터 여부 확인 |
| `_is_card_sales_data(item)` | 카드매출 데이터 여부 확인 |
| `_is_building_data(item)` | 건물 데이터 여부 확인 |
| `_parse_business(data)` | 사업자 정보 파싱 |
| `_parse_card_sales(data)` | 카드매출 정보 파싱 |
| `_parse_building(data)` | 건물 정보 파싱 |

---

### 2.7 data_export.py - 데이터 내보내기

#### 스타일 상수

| 이름 | 값 | 설명 |
|------|-----|------|
| `HEADER_FONT` | 맑은 고딕 11pt Bold | 헤더 폰트 |
| `HEADER_FILL` | #2F5496 | 헤더 배경색 |
| `HEADER_ALIGNMENT` | 중앙 정렬 | 헤더 정렬 |
| `DATA_FONT` | 맑은 고딕 10pt | 데이터 폰트 |
| `THIN_BORDER` | 얇은 테두리 | 셀 테두리 |

#### 헤더 상수

| 이름 | 필드 |
|------|------|
| `BUILDING_HEADERS` | 건물 ID, 건물명, 지번주소, 도로명주소, 건물유형, 연면적, 대지면적, 층수, 건축년도, 위도, 경도, 중심거리 |
| `BUSINESS_HEADERS` | 사업자 ID, 상호명, 업종, 업태, 대표자명, 종업원수, 추정매출, 건물 ID, 건물명 |
| `CARD_SALES_HEADERS` | 지역 ID, 지역명, 총매출금액, 점포당평균매출, 점포수, 카테고리별매출, 월별매출 |

#### 함수 사양

##### `_ensure_output_dir() -> Path`
| 항목 | 설명 |
|------|------|
| **목적** | 출력 디렉토리 생성 |
| **반환값** | 디렉토리 Path |

##### `_timestamp() -> str`
| 항목 | 설명 |
|------|------|
| **목적** | 타임스탬프 문자열 생성 |
| **포맷** | `%Y%m%d_%H%M%S` |

##### `export_to_excel(results: SearchResults, filename: str | None = None) -> Path`
| 항목 | 설명 |
|------|------|
| **목적** | Excel 파일로 내보내기 |
| **시트** | 건물정보, 사업자정보, 카드매출정보, 검색요약 |
| **반환값** | 파일 Path |

##### `export_to_json(results: SearchResults, filename: str | None = None) -> Path`
| 항목 | 설명 |
|------|------|
| **목적** | JSON 파일로 내보내기 |
| **구조** | search_info, buildings, businesses, card_sales, summary |
| **반환값** | 파일 Path |

##### `export_results(results: SearchResults, output_format: str = "both") -> dict[str, Path]`
| 항목 | 설명 |
|------|------|
| **목적** | 형식별 내보내기 |
| **파라미터** | `output_format`: "excel", "json", "both" |
| **반환값** | 형식별 파일 Path 딕셔너리 |

---

### 2.8 exceptions.py - 예외 계층

#### 예외 클래스

| 클래스 | 부모 | 설명 |
|--------|------|------|
| `BigValueError` | `Exception` | 기본 예외 |
| `GeocodingError` | `BigValueError` | 지오코딩 실패 |
| `AuthenticationError` | `BigValueError` | 인증 실패 |
| `APIError` | `BigValueError` | API 요청 실패 |
| `ConfigError` | `BigValueError` | 설정 오류 |
| `ExportError` | `BigValueError` | 내보내기 실패 |

---

## 3. API 사양

### 3.1 BigValue REST API

#### 인증
- **방식**: Bearer Token (JWT)
- **헤더**: `Authorization: Bearer {token}`

#### 엔드포인트

| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/auth/info` | 사용자 정보 조회 |
| GET | `/auth/recent-area` | 최근 지역 조회 |
| GET | `/account/my-area` | 내 지역 조회 |
| GET | `/workspace/channel/bundle` | 번들 목록 조회 |
| GET | `/workspace/channel/bundle/{id}/flow` | Flow 목록 조회 |
| POST | `/workspace/channel/bundle/{id}/flow/{id}/execute` | Flow 실행 |
| GET | `/workspace/report/history` | 리포트 히스토리 |

#### Flow 실행 요청

```json
{
  "type": "BUILDING",
  "key": "1150010800100800015"
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `type` | `string` | 영역 유형 (BUILDING, POLYGON, LAND_PARCEL, CIRCLE) |
| `key` | `string` | 영역 키 (PNU 또는 좌표) |

### 3.2 Nominatim API

#### 지오코딩
- **URL**: `https://nominatim.openstreetmap.org/search`
- **파라미터**: `q`, `format`, `language`, `country_codes`

#### 역지오코딩
- **URL**: `https://nominatim.openstreetmap.org/reverse`
- **파라미터**: `lat`, `lon`, `format`, `language`

---

## 4. 파일 형식 사양

### 4.1 토큰 캐시 파일 (.token_cache.json)

```json
{
  "jwt_token": "eyJ...",
  "access_token": "eyJ...",
  "cookies": {
    "session_id": "abc123"
  }
}
```

### 4.2 Excel 출력 파일

| 시트 | 내용 |
|------|------|
| 건물정보 | 건물 상세 정보 |
| 사업자정보 | 사업자 상세 정보 |
| 카드매출정보 | 카드매출 상세 정보 |
| 검색요약 | 검색 조건 및 결과 요약 |

### 4.3 JSON 출력 파일

```json
{
  "search_info": {
    "timestamp": "2026-06-20T12:00:00",
    "center": {"latitude": 37.5, "longitude": 127.0},
    "radius_m": 50
  },
  "buildings": [...],
  "businesses": [...],
  "card_sales": [...],
  "summary": {
    "total_buildings": 10,
    "total_businesses": 25,
    "total_card_sales": 5
  }
}
```

---

## 5. 보안 사양

### 5.1 인증 정보 관리

| 항목 | 사양 |
|------|------|
| 저장 위치 | `.env` 파일 (프로젝트 루트) |
| 버전 관리 | `.gitignore` 처리 |
| 하드코딩 | 금지 |
| 전송 | HTTPS 필수 |

### 5.2 토큰 관리

| 항목 | 사양 |
|------|------|
| 캐시 파일 | `.token_cache.json` |
| 권한 | 소유자 읽기/쓰기만 허용 |
| 만료 처리 | 자동 갱신 시도 |
| 삭제 | `--clear-cache` 옵션 |

---

## 6. 성능 사양

### 6.1 응답 시간

| 작업 | 목표 시간 |
|------|----------|
| 주소 변환 | 2초 이내 |
| 그리드 생성 | 1초 이내 |
| 로그인 | 15초 이내 |
| 데이터 수집 | 10초 이내 |
| 파일 내보내기 | 2초 이내 |
| **전체 프로세스** | **30초 이내** |

### 6.2 리소스 사용

| 리소스 | 제한 |
|--------|------|
| 메모리 | 500MB 이내 |
| CPU | 단일 코어 |
| 네트워크 | 동시 연결 1개 |

---

## 7. 오류 처리 사양

### 7.1 오류 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 일반 오류 |
| 130 | 사용자 중단 (Ctrl+C) |

### 7.2 오류 메시지 포맷

```
❌ 오류: {에러 메시지}
💡 해결 방법: {힌트}
```

### 7.3 로그 레벨

| 레벨 | 사용 시점 |
|------|----------|
| DEBUG | 상세 디버그 정보 |
| INFO | 일반 진행 상태 |
| WARNING | 잠재적 문제 |
| ERROR | 오류 발생 |

---

## 8. 테스트 사양

### 8.1 단위 테스트

| 모듈 | 테스트 대상 |
|------|------------|
| geocoding | 주소 변환, 좌표 변환 |
| radius_search | 그리드 생성, 중복 제거 |
| bigvalue_api | API 응답 파싱 |
| data_export | 파일 생성 |

### 8.2 통합 테스트

| 시나리오 | 설명 |
|----------|------|
| 전체 워크플로우 | 주소 입력 → 결과 내보내기 |
| 인증 실패 | 잘못된 계정 정보 |
| 네트워크 오류 | API 연결 실패 |

---

## 9. 배포 사양

### 9.1 설치 방법

```bash
# 개발 모드
pip install -e ".[dev]"

# 프로덕션
pip install .
```

### 9.2 실행 방법

```bash
# CLI
bigvalue-search --address "서울 강서구 마곡동 800-15"

# Python 모듈
python -m bigvalue_search --address "서울 강서구 마곡동 800-15"
```

### 9.3 설정 파일

| 파일 | 용도 |
|------|------|
| `.env` | 환경변수 |
| `.token_cache.json` | 토큰 캐시 |
| `pyproject.toml` | 프로젝트 설정 |

---

## 10. 변경 이력

| 버전 | 날짜 | 변경사항 |
|------|------|----------|
| 1.0.0 | 2026-06-20 | 최초 작성 |
