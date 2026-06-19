# BigValue Search Tool - Documentation

이 디렉토리에는 BigValue Search Tool의 프로젝트 문서가 포함되어 있습니다.

## 문서 목록

| 문서 | 설명 |
|------|------|
| [PRD.md](PRD.md) | Product Requirements Document - 제품 요구사항 문서 |
| [specification.md](specification.md) | Technical Specification - 기술 사양서 |

## 문서 활용 가이드

### PRD.md
- 제품 개요 및 비즈니스 목표
- 기능 요구사항 (F-001 ~ F-005)
- 비기능 요구사항 (성능, 보안, 호환성)
- 데이터 모델
- 시스템 아키텍처
- 사용자 스토리

### specification.md
- 모듈별 상세 사양
- 함수/클래스 API 문서
- 데이터 클래스 필드 정의
- 외부 API 사양
- 파일 형식 사양
- 보안 및 성능 사양

## Comet 프로세스 연동

이 문서들은 Comet SDD+TDD 워크플로우의 기반으로 활용됩니다:

1. **Open Stage**: PRD.md 기반 변경 제안 생성
2. **Design Stage**: specification.md 기반 기술 설계
3. **Build Stage**: 사양서 기반 TDD 구현
4. **Verify Stage**: 사양 대조 검증
5. **Archive Stage**: 변경 이력 관리

## 문서 업데이트

문서 업데이트는 Comet 프로세스를 통해 진행합니다:

```bash
/comet "문서 업데이트: [변경 내용]"
```
