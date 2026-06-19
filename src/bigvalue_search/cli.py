"""CLI interface for BigValue search tool."""

from __future__ import annotations

import argparse
import io
import logging
import sys
from pathlib import Path

# Force UTF-8 encoding on Windows for emoji/unicode output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from bigvalue_search.config import config
from bigvalue_search.geocoding import geocode_address, Coordinates
from bigvalue_search.radius_search import generate_grid_points, deduplicate_nearby_points
from bigvalue_search.browser_auth import login_keep_browser, clear_token_cache
from bigvalue_search.bigvalue_api import BigValueAPI
from bigvalue_search.data_export import export_results
from bigvalue_search.exceptions import BigValueError, GeocodingError


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="bigvalue-search",
        description="BigValue.ai 건물 검색 도구 - 반경 내 건물, 사업자, 카드매출 정보를 수집합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  bigvalue-search --address "서울 강서구 마곡동 800-15" --radius 50 --output both
  bigvalue-search --address "서울 강서구 마곡동 800-15" --radius 30 --output excel
  bigvalue-search --address "서울 강서구 마곡동 800-15" --output json --verbose
        """,
    )

    parser.add_argument(
        "--address", "-a",
        type=str,
        required=True,
        help="검색할 주소 (예: 서울 강서구 마곡동 800-15)",
    )
    parser.add_argument(
        "--radius", "-r",
        type=float,
        default=50.0,
        help="검색 반경 (미터, 기본값: 50)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        choices=["excel", "json", "both"],
        default="both",
        help="출력 형식 (excel, json, both, 기본값: both)",
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=8.0,
        help="그리드 포인트 간격 (미터, 기본값: 8)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="인증 없이 좌표 및 그리드 포인트만 출력",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="캐시된 JWT 토큰 삭제 후 재인증",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=None,
        help="헤드리스 모드로 브라우저 실행",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="상세 로그 출력",
    )

    return parser.parse_args()


def print_grid_info(center: Coordinates, radius_m: float, interval_m: float) -> None:
    """Print grid point information."""
    grid_points = generate_grid_points(center, radius_m, interval_m)
    deduped = deduplicate_nearby_points(grid_points, min_distance_m=5.0)

    print(f"\n{'='*60}")
    print(f"  그리드 포인트 정보")
    print(f"{'='*60}")
    print(f"  중심 좌표: ({center.latitude:.6f}, {center.longitude:.6f})")
    print(f"  검색 반경: {radius_m}m")
    print(f"  그리드 간격: {interval_m}m")
    print(f"  생성된 포인트: {len(grid_points)}개")
    print(f"  중복제거 후: {len(deduped)}개")
    print(f"{'='*60}")

    # Print first few grid points as sample
    print(f"\n  샘플 그리드 포인트 (처음 5개):")
    for i, gp in enumerate(deduped[:5]):
        print(f"    [{i+1}] ({gp.coordinates.latitude:.6f}, {gp.coordinates.longitude:.6f}) - {gp.distance_m:.1f}m")

    if len(deduped) > 5:
        print(f"    ... 외 {len(deduped) - 5}개")


def run_search(args: argparse.Namespace) -> int:
    """
    Execute the search workflow using browser automation.

    Returns:
        Exit code (0 for success).
    """
    logger = logging.getLogger(__name__)

    # Step 1: Geocode the address
    print(f"\n📍 주소 변환 중: {args.address}")
    try:
        center = geocode_address(args.address)
        print(f"   ✅ 좌표: ({center.latitude:.6f}, {center.longitude:.6f})")
    except GeocodingError as e:
        print(f"   ❌ 주소 변환 실패: {e}")
        return 1

    # Step 2: Generate grid points
    print(f"\n🔲 그리드 포인트 생성 중 (반경: {args.radius}m, 간격: {args.interval}m)")
    grid_points = generate_grid_points(center, args.radius, args.interval)
    deduped = deduplicate_nearby_points(grid_points, min_distance_m=5.0)
    print(f"   ✅ {len(grid_points)}개 포인트 생성, 중복제거 후 {len(deduped)}개")

    if args.no_auth:
        print_grid_info(center, args.radius, args.interval)
        return 0

    # Step 3: Authenticate with BigValue using browser (keep open)
    print("\n🔐 BigValue.ai 브라우저 로그인 중...")

    if args.clear_cache:
        clear_token_cache()
        logger.info("Token cache cleared")

    session = login_keep_browser(
        headless=args.headless,
        use_cache=True,
    )

    if not session:
        print("   ❌ 로그인 실패")
        print("   💡 .env 파일에 BIGVALUE_EMAIL과 BIGVALUE_PASSWORD를 설정하세요.")
        print("   💡 --no-auth 옵션으로 인증 없이 좌표 정보만 확인할 수 있습니다.")
        return 1

    print("   ✅ 로그인 성공 (브라우저 세션 유지)")

    try:
        # Step 4: Collect data using browser automation
        print("\n📊 BigValue 데이터 수집 중 (브라우저 자동화)...")
        api = BigValueAPI(session=session)

        results = api.collect_all_data(center, args.radius, address=args.address)

        print(f"\n{'='*60}")
        print(f"  수집 결과 요약")
        print(f"{'='*60}")
        print(f"  건물: {len(results.buildings)}개")
        print(f"  사업자: {len(results.businesses)}개")
        print(f"  카드매출: {len(results.card_sales)}건")
        print(f"{'='*60}")

        # Step 5: Export results
        print(f"\n💾 결과 내보내기 중 (형식: {args.output})...")
        output_files = export_results(results, args.output)

        for fmt, filepath in output_files.items():
            print(f"   ✅ {fmt.upper()}: {filepath}")

        print(f"\n✅ 검색 완료!")
        return 0

    finally:
        # Always close the browser session
        session.close()
        logger.info("Browser session closed")


def main() -> int:
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)

    # Validate config (only if auth is needed)
    if not args.no_auth:
        errors = config.validate()
        if errors:
            print("⚠️  설정 오류:")
            for err in errors:
                print(f"   - {err}")
            print("\n💡 .env 파일을 확인하세요. (.env.example 참조)")
            print("   --no-auth 옵션으로 인증 없이 좌표 정보만 확인할 수 있습니다.\n")

    try:
        return run_search(args)
    except KeyboardInterrupt:
        print("\n\n⏹️  사용자에 의해 중단됨")
        return 130
    except BigValueError as e:
        logging.getLogger(__name__).exception("BigValue error")
        print(f"\n❌ 오류: {e}")
        return 1
    except Exception as e:
        logging.getLogger(__name__).exception("Unexpected error")
        print(f"\n❌ 예상치 못한 오류: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
