# bigvalue_search 패키지

BigValue.ai REST API 클라이언트 + 브라우저 자동화 + 데이터 내보내기.

## STRUCTURE

```
bigvalue_search/
├── __init__.py         # 공개 API 재내보내기 (__all__)
├── __main__.py         # python -m 진입점 → cli.main()
├── cli.py              # CLI 오케스트레이터 (argparse)
├── config.py           # .env 기반 Config 싱글톤
├── exceptions.py       # BigValueError 계층
├── geocoding.py        # Nominatim 주소→좌표 (Coordinates)
├── radius_search.py    # Haversine 그리드 생성 (GridPoint)
├── browser_auth.py     # Playwright 로그인 (BrowserSession)
├── bigvalue_api.py     # REST API 클라이언트 (BigValueAPI)
└── data_export.py      # Excel/JSON 내보내기
```

## WHERE TO LOOK

| Task | File | Key Symbols |
|------|------|-------------|
| CLI 옵션 추가 | `cli.py` | `parse_args()`, `run_search()` |
| API 호출 수정 | `bigvalue_api.py` | `BigValueAPI.collect_all_data()` |
| 새 엔드포인트 | `bigvalue_api.py` | `REST_API_BASE`, `_api_headers()` |
| 인증 로직 | `browser_auth.py` | `login_keep_browser()`, `BrowserSession` |
| 주소 변환 | `geocoding.py` | `geocode_address()`, `CITY_EXPANSIONS` |
| 그리드 생성 | `radius_search.py` | `generate_grid_points()`, `deduplicate_nearby_points()` |
| 내보내기 형식 | `data_export.py` | `export_to_excel()`, `export_to_json()` |
| 예외 추가 | `exceptions.py` | `BigValueError` 상속 |

## DATA FLOW

```
Address → geocode_address() → Coordinates
    → generate_grid_points() → GridPoint[] (표시용, 미사용)
    → login_keep_browser() → BrowserSession
    → BigValueAPI(session).collect_all_data()
        → PNU 조회 → Flow 실행 → BuildingInfo/BusinessInfo/CardSalesInfo
    → export_results() → Excel + JSON
```

## CONVENTIONS

- 모든 함수에 타입 어노테이션 필수 (`disallow_untyped_defs = true`)
- `from __future__ import annotations` 사용
- dataclass 필드: `field(default_factory=...)` 패턴
- Playwright 콜백: `object` 타입 사용 (타입 narrowing 필요)

## ANTI-PATTERNS

- **bare `except Exception:`**: browser_auth.py 11곳, bigvalue_api.py 1곳 — 특정 예외로 좁혀야 함
- **`# type: ignore[union-attr]`**: browser_auth.py 8곳, bigvalue_api.py 5곳 — Playwright 콜백 타입 미정의
- **중복 로그인 코드**: `login_with_playwright()` 미사용 — 삭제 대상
- **하드코딩 sleep()**: 8곳 (0.5~8초) — 브라우저 자동화 타이밍

## KEY DECISIONS

- **PNU 조회 4가지 방법**: recent-areas → my-areas → browser scraping → geocoding 순서
- **JWT 캐시**: `.token_cache.json`에 저장 (프로젝트 루트)
- **그리드 포인트**: 생성되지만 `collect_all_data()`에서 미사용 — 레거시 코드
