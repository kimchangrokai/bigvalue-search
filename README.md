# BigValue Search Tool

BigValue.ai 건물 검색 도구 - 반경 내 건물, 사업자, 카드매출 정보를 수집합니다.

## 설치

```bash
pip install -e .
```

개발 의존성 포함 설치:

```bash
pip install -e ".[dev]"
playwright install chromium
```

## 설정

`.env` 파일에 BigValue.ai 계정 정보를 설정하세요:

```bash
cp .env.example .env
```

`.env` 파일 편집:

```
BIGVALUE_EMAIL=your_email@example.com
BIGVALUE_PASSWORD=your_password
```

## 사용법

### CLI 실행

```bash
bigvalue-search --address "서울 강서구 마곡동 800-15" --radius 50 --output both
```

### Python 모듈 실행

```bash
python -m bigvalue_search --address "서울 강서구 마곡동 800-15" --radius 50 --output both
```

### CLI 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--address`, `-a` | 검색할 주소 | 필수 |
| `--radius`, `-r` | 검색 반경 (미터) | 50 |
| `--output`, `-o` | 출력 형식 (excel, json, both) | both |
| `--interval`, `-i` | 그리드 포인트 간격 (미터) | 8 |
| `--no-auth` | 인증 없이 좌표만 출력 | false |
| `--clear-cache` | 캐시된 JWT 토큰 삭제 | false |
| `--headless` | 헤드리스 모드로 브라우저 실행 | false |
| `--verbose`, `-v` | 상세 로그 출력 | false |

### Python API 사용

```python
from bigvalue_search import (
    geocode_address,
    generate_grid_points,
    BigValueAPI,
    export_results,
)

# 주소 변환
center = geocode_address("서울 강서구 마곡동 800-15")

# 그리드 포인트 생성
points = generate_grid_points(center, radius_m=50, interval_m=8)

# API를 통한 데이터 수집
api = BigValueAPI(session=session)
results = api.collect_all_data(center, radius_m=50)

# 결과 내보내기
export_results(results, output_format="both")
```

## 테스트

```bash
pytest tests/
```

커버리지 포함:

```bash
pytest tests/ --cov=bigvalue_search --cov-report=html
```

## 린트

```bash
make lint
```

자동 수정:

```bash
make format
```

## 프로젝트 구조

```
bigvalue-search/
├── pyproject.toml          # 프로젝트 설정
├── Makefile                # 유틸리티 명령어
├── README.md               # 문서
├── .env.example            # 환경 변수 예시
├── src/
│   └── bigvalue_search/
│       ├── __init__.py     # 패키지 초기화
│       ├── __main__.py     # 모듈 실행 진입점
│       ├── cli.py          # CLI 인터페이스
│       ├── config.py       # 설정 관리
│       ├── exceptions.py   # 커스텀 예외
│       ├── geocoding.py    # 주소 변환
│       ├── browser_auth.py # 브라우저 인증
│       ├── radius_search.py# 반경 검색 알고리즘
│       ├── bigvalue_api.py # BigValue API 클라이언트
│       └── data_export.py  # 데이터 내보내기
└── tests/
    ├── conftest.py         # 테스트 픽스처
    ├── test_geocoding.py   # 지오코딩 테스트
    ├── test_radius_search.py# 반경 검색 테스트
    └── test_bigvalue_api.py# API 테스트
```

## 라이선스

MIT
