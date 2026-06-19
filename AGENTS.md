# PROJECT KNOWLEDGE BASE

**Generated:** 2026-06-19
**Commit:** be22e5e
**Branch:** master

## OVERVIEW

BigValue.ai 건물 검색 도구 — 반경 내 건물, 사업자, 카드매출 정보를 수집하는 Python CLI. Playwright 브라우저 자동화로 BigValue.ai REST API를 호출하고 Excel/JSON으로 내보낸다.

## STRUCTURE

```
search-tool/
├── src/bigvalue_search/    # 메인 패키지 (flat 구조)
│   ├── cli.py              # CLI 진입점 (main)
│   ├── config.py           # .env 기반 설정 (singleton)
│   ├── geocoding.py        # Nominatim 주소→좌표 변환
│   ├── radius_search.py    # 그리드 포인트 생성 (Haversine)
│   ├── browser_auth.py     # Playwright 로그인 + JWT 추출
│   ├── bigvalue_api.py     # REST API 클라이언트 + PNU 조회
│   ├── data_export.py      # Excel/JSON 내보내기
│   └── exceptions.py       # 예외 계층
├── tests/                  # pytest 테스트
├── Makefile                # 개발 명령어
└── pyproject.toml          # 프로젝트 설정
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| CLI 옵션 추가 | `cli.py:parse_args()` | argparse 기반 |
| API 엔드포인트 변경 | `bigvalue_api.py` | REST_API_BASE, DEFAULT_BUNDLE_ID/FLOW_ID |
| 새 데이터 소스 | `bigvalue_api.py:collect_all_data()` | 파이프라인 중앙 |
| 내보내기 형식 추가 | `data_export.py` | export_to_excel/json 패턴 |
| 인증 방식 변경 | `browser_auth.py` | Playwright 기반, JWT 캐시 |
| 주소 변환 로직 | `geocoding.py` | 한국어 주소 확장 패턴 |
| 설정 추가 | `config.py` + `.env.example` | 환경변수 기반 |
| 테스트 추가 | `tests/` | conftest.py 픽스처 사용 |

## CODE MAP

| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `main()` | function | cli.py:202 | CLI 진입점, 전체 파이프라인 오케스트레이션 |
| `Config` | class | config.py:18 | 환경변수 기반 설정 (singleton) |
| `Coordinates` | dataclass | geocoding.py:28 | 위도/경도 쌍 (frozen) |
| `geocode_address()` | function | geocoding.py:55 | Nominatim 주소 변환 |
| `GridPoint` | dataclass | radius_search.py:50 | 그리드 포인트 + 거리 |
| `generate_grid_points()` | function | radius_search.py:57 | 원형 영역 그리드 생성 |
| `haversine_distance()` | function | radius_search.py:15 | Haversine 거리 계산 |
| `BrowserSession` | class | browser_auth.py:34 | Playwright 세션 관리 |
| `login_keep_browser()` | function | browser_auth.py:389 | 로그인 + 세션 유지 |
| `BigValueAPI` | class | bigvalue_api.py:106 | REST API 클라이언트 |
| `SearchResults` | dataclass | bigvalue_api.py:93 | 검색 결과 컨테이너 |
| `BuildingInfo` | dataclass | bigvalue_api.py:41 | 건물 정보 |
| `BusinessInfo` | dataclass | bigvalue_api.py:63 | 사업자 정보 |
| `CardSalesInfo` | dataclass | bigvalue_api.py:79 | 카드매출 정보 |
| `export_results()` | function | data_export.py:324 | Excel/JSON 내보내기 |
| `BigValueError` | exception | exceptions.py:6 | 기본 예외 클래스 |

## CONVENTIONS

- **Python 3.10+**: `from __future__ import annotations` 필수, `X | Y` union syntax
- **타입 어노테이션**: `disallow_untyped_defs = true` — 모든 함수에 타입 필수
- **라인 길이**: 100자 (ruff, E501 무시)
- **import 정렬**: ruff `I` 규칙 (isort)
- **네이밍**: ruff `N` 규칙 (pep8-naming)
- **모던 문법**: ruff `UP` 규칙 (pyupgrade 3.10+)

## ANTI-PATTERNS (THIS PROJECT)

- **`except Exception:` 금지**: 12곳에서 bare except 사용 중 — 특정 예외로 좁혀야 함
- **`# type: ignore` 금지**: 16곳에서 타입 시스템 억제 중 — 적절한 타입 narrowing 필요
- **하드코딩된 magic number 금지**: `DEFAULT_BUNDLE_ID`, `DEFAULT_FLOW_ID`, sleep() 값들
- **중복 코드 금지**: `login_with_playwright()`와 `login_keep_browser()`가 80% 동일
- **그리드 포인트 미사용**: `generate_grid_points()`가 메인 경로에서 호출되지만 사용되지 않음

## COMMANDS

```bash
# 개발 환경 설정
pip install -e ".[dev]"
playwright install chromium

# 린트 + 포맷
make lint        # ruff check + mypy
make format      # ruff format + ruff check --fix

# 테스트
make test        # pytest tests/
make test-cov    # pytest --cov=bigvalue_search

# 실행
bigvalue-search --address "서울 강서구 마곡동 800-15" --radius 50 --output both
python -m bigvalue_search --address "서울 강서구 마곡동 800-15" --radius 50

# 빌드
pip install -e .
```

## NOTES

- **Playwright 의존성**: `playwright install chromium` 필수 (runtime 의존성)
- **`.env` 필수**: `BIGVALUE_EMAIL`, `BIGVALUE_PASSWORD` 설정 필요
- **`.token_cache.json`**: JWT 캐시 파일 (gitignore 처리됨)
- **Windows 환경**: Makefile clean 타겟이 PowerShell 사용
- **CI/CD 없음**: 수동 린트/테스트만 가능
- **테스트 커버리지 gaps**: `cli.py`, `config.py`, `browser_auth.py`, `bigvalue_api.py` 테스트 부족

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `skill` tool with `skill: "graphify"` before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
