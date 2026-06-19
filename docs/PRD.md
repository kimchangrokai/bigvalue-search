# BigValue Search Tool - PRD (Product Requirements Document)

**Version**: 1.0.0
**Last Updated**: 2026-06-20
**Status**: Active

---

## 1. Product Overview

### 1.1 Product Name
BigValue.ai 건물 검색 도구 (BigValue Search Tool)

### 1.2 Product Description
BigValue Search Tool은 BigValue.ai 플랫폼의 REST API를 활용하여 특정 주소 반경 내 건물, 사업자, 카드매출 정보를 수집하는 Python CLI 도구입니다. Playwright 브라우저 자동화를 통해 인증 및 데이터 수집을 수행하고, 결과를 Excel 및 JSON 형식으로 내보냅니다.

### 1.3 Target Users
- 부동산 개발자/투자자
- 상권 분석가
- 프랜차이즈 본사 담당자
- 지리 기반 데이터 분석가

### 1.4 Business Objectives
- BigValue.ai 플랫폼 데이터의 프로그래밍적 접근 제공
- 반복적인 수동 검색 작업 자동화
- 대량 데이터 수집 및 분석 지원

---

## 2. Functional Requirements

### 2.1 Core Features

#### F-001: 주소-좌표 변환 (Geocoding)
| 항목 | 설명 |
|------|------|
| **설명** | 한국어 주소를 위도/경도 좌표로 변환 |
| **구현** | OpenStreetMap Nominatim API 활용 |
| **확장** | 한국 도시 약어 자동 확장 (서울→서울특별시 등) |
| **예외처리** | GeocodingError 발생 시 사용자 친화적 메시지 출력 |

#### F-002: 반경 내 그리드 포인트 생성
| 항목 | 설명 |
|------|------|
| **설명** | 중심 좌표 기준 반경 내 격자 포인트 생성 |
| **알고리즘** | Haversine 공식 기반 거리 계산 |
| **중복제거** | 5m 이내 중복 포인트 자동 제거 |
| **파라미터** | 반경(m), 간격(m) 조정 가능 |

#### F-003: 브라우저 인증 (Browser Authentication)
| 항목 | 설명 |
|------|------|
| **설명** | Playwright를 통한 BigValue.ai 로그인 자동화 |
| **토큰추출** | JWT, accessToken 추출 (4가지 방법) |
| **캐싱** | .token_cache.json 파일에 토큰 캐싱 |
| **세션관리** | BrowserSession 클래스로 브라우저 세션 유지 |

#### F-004: BigValue REST API 연동
| 항목 | 설명 |
|------|------|
| **설명** | BigValue.ai REST API를 통한 데이터 수집 |
| **엔드포인트** | rest.bigvalue.ai |
| **PNU 조회** | 4가지 방법으로 PNU(Parcel Number Unit) 조회 |
| **Flow 실행** | 건물/사업자/카드매출 분석 Flow 실행 |

#### F-005: 데이터 내보내기 (Data Export)
| 항목 | 설명 |
|------|------|
| **형식** | Excel(.xlsx), JSON |
| **구조** | 건물정보, 사업자정보, 카드매출정보, 검색요약 시트 |
| **스타일링** | Excel 헤더 스타일링, 자동 컬럼 너비 조정 |
| **타임스탬프** | 파일명에 검색 시각 포함 |

### 2.2 CLI Options

| 옵션 | 설명 | 기본값 | 필수 |
|------|------|--------|------|
| `--address`, `-a` | 검색할 주소 | - | ✓ |
| `--radius`, `-r` | 검색 반경 (미터) | 50 | |
| `--output`, `-o` | 출력 형식 (excel, json, both) | both | |
| `--interval`, `-i` | 그리드 포인트 간격 (미터) | 8 | |
| `--no-auth` | 인증 없이 좌표만 출력 | false | |
| `--clear-cache` | 캐시된 JWT 토큰 삭제 | false | |
| `--headless` | 헤드리스 모드로 브라우저 실행 | true | |
| `--verbose`, `-v` | 상세 로그 출력 | false | |

---

## 3. Non-Functional Requirements

### 3.1 성능 (Performance)
| 항목 | 요구사항 |
|------|----------|
| 응답 시간 | 단일 주소 검색 30초 이내 |
| 동시성 | 단일 사용자 CLI 도구 |
| 메모리 | 최대 1000개 그리드 포인트 처리 가능 |

### 3.2 신뢰성 (Reliability)
| 항목 | 요구사항 |
|------|----------|
| 오류 복구 | 네트워크 오류 시 재시도 로직 |
| 토큰 만료 | 캐시된 토큰 자동 갱신 |
| 브라우저 세션 | 비정상 종료 시 정리 보장 |

### 3.3 보안 (Security)
| 항목 | 요구사항 |
|------|----------|
| 인증 정보 | .env 파일에만 저장, 하드코딩 금지 |
| 토큰 캐시 | .gitignore 처리 |
| HTTPS | 모든 API 통신 HTTPS 필수 |

### 3.4 호환성 (Compatibility)
| 항목 | 요구사항 |
|------|----------|
| OS | Windows, macOS, Linux |
| Python | 3.10 이상 |
| 브라우저 | Chromium (Playwright 내장) |

---

## 4. Data Model

### 4.1 핵심 데이터 클래스

#### BuildingInfo (건물 정보)
```python
@dataclass
class BuildingInfo:
    building_id: str
    building_name: str
    address: str
    road_address: str
    building_type: str
    total_floor_area: float
    land_area: float
    number_of_floors: int
    year_built: int
    latitude: float
    longitude: float
    distance_m: float
    complex_key: str
    pnu: str
    road_name_address_management_number: str
    raw_data: dict[str, object]
```

#### BusinessInfo (사업자 정보)
```python
@dataclass
class BusinessInfo:
    business_id: str
    business_name: str
    business_type: str
    business_category: str
    representative_name: str
    employee_count: int
    revenue_estimate: str
    building_id: str
    building_name: str
    raw_data: dict[str, object]
```

#### CardSalesInfo (카드매출 정보)
```python
@dataclass
class CardSalesInfo:
    area_id: str
    area_name: str
    total_sales_amount: float
    average_sales_per_store: float
    number_of_stores: int
    sales_by_category: dict[str, float]
    monthly_sales: dict[str, float]
    raw_data: dict[str, object]
```

#### SearchResults (검색 결과 컨테이너)
```python
@dataclass
class SearchResults:
    buildings: list[BuildingInfo]
    businesses: list[BusinessInfo]
    card_sales: list[CardSalesInfo]
    search_center: Coordinates | None
    radius_m: float
```

---

## 5. System Architecture

### 5.1 모듈 구조

```
bigvalue_search/
├── __init__.py         # 공개 API 재내보내기
├── __main__.py         # python -m 진입점
├── cli.py              # CLI 오케스트레이터
├── config.py           # 환경변수 기반 설정
├── exceptions.py       # 커스텀 예외 계층
├── geocoding.py        # Nominatim 주소 변환
├── radius_search.py    # 그리드 포인트 생성
├── browser_auth.py     # Playwright 인증
├── bigvalue_api.py     # REST API 클라이언트
└── data_export.py      # Excel/JSON 내보내기
```

### 5.2 데이터 흐름

```
[사용자 입력]
    │
    ▼
[CLI 파싱] cli.py:parse_args()
    │
    ▼
[주소 변환] geocoding.py:geocode_address()
    │
    ▼
[그리드 생성] radius_search.py:generate_grid_points()
    │
    ▼
[브라우저 인증] browser_auth.py:login_keep_browser()
    │
    ▼
[API 호출] bigvalue_api.py:BigValueAPI.collect_all_data()
    │
    ├─► [PNU 조회] get_pnu_from_address()
    │       ├─ recent-areas API
    │       ├─ my-areas API
    │       ├─ 브라우저 스크래핑
    │       └─ 지오코딩 역추적
    │
    ├─► [Flow 실행] execute_flow()
    │
    └─► [결과 파싱] parse_flow_result()
            │
            ▼
    [데이터 내보내기] data_export.py:export_results()
            │
            ├─► Excel (.xlsx)
            └─► JSON (.json)
```

### 5.3 외부 의존성

| 라이브러리 | 용도 |
|------------|------|
| playwright | 브라우저 자동화 |
| requests | HTTP 클라이언트 |
| geopy | Nominatim 지오코딩 |
| openpyxl | Excel 파일 생성 |
| python-dotenv | 환경변수 관리 |

---

## 6. User Stories

### US-001: 기본 검색
```
As a 부동산 분석가,
I want to 주소를 입력하면 반경 내 건물 정보를 자동으로 수집하고 싶다,
So that 수동 검색 시간을 절약할 수 있다.
```

### US-002: 다양한 출력 형식
```
As a 데이터 분석가,
I want to 검색 결과를 Excel과 JSON 형식으로 내보내고 싶다,
So that 다양한 분석 도구에서 활용할 수 있다.
```

### US-003: 인증 관리
```
As a 반복 사용자,
I want to 로그인 정보를 캐싱하여 매번 입력하지 않아도 되고 싶다,
So that工作效率를 높일 수 있다.
```

### US-004: 디버깅 지원
```
As a 개발자,
I want to 상세 로그를 확인하여 문제를 진단하고 싶다,
So that 오류를 빠르게 해결할 수 있다.
```

---

## 7. Constraints & Assumptions

### 7.1 제약사항
- BigValue.ai 계정 필수
- Playwright Chromium 브라우저 설치 필요
- 인터넷 연결 필수
- 단일 스레드 실행

### 7.2 가정사항
- 사용자가 한국어 주소를 입력
- BigValue.ai API가 안정적으로 동작
- Nominatim 서비스 가용성 보장

---

## 8. Success Metrics

| 지표 | 목표 |
|------|------|
| 검색 성공률 | 95% 이상 |
| 평균 실행 시간 | 30초 이내 |
| 데이터 정확도 | BigValue.ai 웹 UI와 동일 |
| 사용자 만족도 | CLI 사용 편의성 |

---

## 9. Future Enhancements

### 9.1 Phase 2 (v2.0)
- [ ] 다중 주소 일괄 검색
- [ ] 검색 결과 비교 분석
- [ ] 커스텀 Flow ID 지원
- [ ] 비동기 병렬 처리

### 9.2 Phase 3 (v3.0)
- [ ] 웹 UI 대시보드
- [ ] 실시간 모니터링
- [ ] 데이터 시각화
- [ ] API 서버 모드

---

## 10. Appendix

### 10.1 Glossary

| 용어 | 설명 |
|------|------|
| PNU | Parcel Number Unit, 토지 고유번호 (19자리) |
| Flow | BigValue.ai의 분석 워크플로우 |
| Bundle | 관련 Flow의 그룹 |
| Nominatim | OpenStreetMap 기반 지오코딩 서비스 |
| Haversine | 두 지점 간 대원거리 계산 공식 |

### 10.2 References
- BigValue.ai 공식 문서
- Playwright 공식 문서
- Nominatim API 문서
- OpenPyXL 문서
