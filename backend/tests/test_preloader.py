"""
사전 식립 데이터 로더 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.services.data_preloader import data_preloader


def test_preloader():
    """사전 식립 데이터 로더 테스트"""
    print("=" * 80)
    print("사전 식립 데이터 로더 테스트")
    print("=" * 80)

    result = data_preloader.load_preloaded_data()

    print("\n결과:")
    print(f"  Success: {result['success']}")
    print(f"  Message: {result['message']}")
    print(f"  Sessions: {result['sessions']}")

    if result['success']:
        print("\n✅ 사전 식립 데이터 로딩 성공!")
        for hospital, session_id in result['sessions'].items():
            print(f"   - {hospital}: {session_id}")

            # 기본 세션 조회 테스트
            default_session = data_preloader.get_default_session(hospital)
            assert default_session == session_id
            print(f"     → 기본 세션 조회: {default_session}")
    else:
        print(f"\n⚠️  사전 식립 데이터 로딩 실패: {result['message']}")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)

    return result['success']


if __name__ == "__main__":
    success = test_preloader()
    exit(0 if success else 1)
