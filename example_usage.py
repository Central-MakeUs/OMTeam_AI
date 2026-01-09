"""
에이전트 시스템 사용 예제
"""

from agent_system import run_agent_system


def example_planner():
    """Planner 에이전트 예제"""
    print("\n" + "="*60)
    print("예제 1: Planner 에이전트")
    print("="*60)
    request = "내년 상반기 마케팅 전략을 수립해줘"
    print(f"요청: {request}\n")
    
    user_payload = {
        "preferences": {
            "운동_선호": "걷기",
            "최소_가능_시간": "5분",
        },
        "event": {
            "mission": "자기 전 스트레칭 5분",
            "mission_result": "success",
            "condition": "보통",
            "schedule": "여유 있음",
        },
    }
    result = run_agent_system(request, user_id="user_001", user_payload=user_payload)
    print(f"선택된 에이전트: {result['selected_agent']}")
    print(f"\n응답:\n{result['agent_response']}")


def example_coach():
    """Coach 에이전트 예제"""
    print("\n" + "="*60)
    print("예제 2: Coach 에이전트")
    print("="*60)
    request = "Python으로 API를 만드는 방법을 단계별로 알려줘"
    print(f"요청: {request}\n")
    
    user_payload = {
        "event": {
            "mission": "퇴근길 5분 빠르게 걷기",
            "mission_result": "fail",
            "fail_reason": "야근",
            "condition": "피곤",
            "schedule": "야근",
        },
    }
    result = run_agent_system(request, user_id="user_001", user_payload=user_payload)
    print(f"선택된 에이전트: {result['selected_agent']}")
    print(f"\n응답:\n{result['agent_response']}")


def example_analysis():
    """Analysis 에이전트 예제"""
    print("\n" + "="*60)
    print("예제 3: Analysis 에이전트")
    print("="*60)
    request = "최근 3개월간의 사용자 증가율과 이탈률 데이터를 분석해줘"
    print(f"요청: {request}\n")
    
    result = run_agent_system(request, user_id="user_001")
    print(f"선택된 에이전트: {result['selected_agent']}")
    print(f"\n응답:\n{result['agent_response']}")


if __name__ == "__main__":
    print("에이전트 시스템 사용 예제\n")
    
    # 각 에이전트 타입별 예제 실행
    example_planner()
    example_coach()
    example_analysis()
    
    print("\n" + "="*60)
    print("모든 예제 실행 완료")
    print("="*60)
