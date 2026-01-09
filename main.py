"""
메인 실행 파일 - 에이전트 시스템 실행
"""

from agent_system import run_agent_system


def main():
    """메인 함수"""
    print("=" * 60)
    print("에이전트 오케스트레이션 시스템")
    print("=" * 60)
    print("\n사용 가능한 에이전트:")
    print("- Planner: 계획 수립 및 전략 개발")
    print("- Coach: 코칭 및 가이드 제공")
    print("- Analysis: 데이터 분석 및 문제 분석")
    print("\n" + "-" * 60)
    
    # 예제 실행
    examples = [
        "내년 프로젝트를 위한 6개월 로드맵을 만들어줘",
        "코딩 실력을 향상시키는 방법을 알려줘",
        "최근 매출 데이터를 분석해줘"
    ]
    
    for i, request in enumerate(examples, 1):
        print(f"\n[예제 {i}]")
        print(f"요청: {request}")
        print("-" * 60)
        
        result = run_agent_system(request)
        
        print(f"선택된 에이전트: {result['selected_agent']}")
        print(f"\n응답:\n{result['agent_response']}")
        print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
