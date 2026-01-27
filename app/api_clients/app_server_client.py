from typing import Any, Dict
from datetime import date, time

from app.api.schemas import WorkTimeType, LifestyleType, MissionType, Difficulty, MissionResult


async def get_user_ai_data(user_id: int) -> Dict[str, Any]:
    """
    메인 앱 서버를 호출하여 특정 유저의 AI 데이터(온보딩, 미션 히스토리 등)를 가져옵니다.
    (현재는 Mock 데이터를 반환)
    """
    print(f"[Mock App Server] Fetching data for user_id: {user_id}")

    # 이 함수는 실제로는 `httpx`를 사용하여 메인 앱 서버의 API를 호출해야 합니다.
    # 예: async with httpx.AsyncClient() as client:
    #         response = await client.get(f"https://main-app-server.com/api/ai-data?userId={user_id}")
    #         return response.json()

    # 지금은 테스트를 위한 하드코딩된 Mock 데이터를 반환합니다.
    mock_data = {
        "onboarding": {
            "appGoal": "체중 감량",
            "workTimeType": WorkTimeType.FIXED,
            "availableStartTime": time(18, 30, 0),
            "availableEndTime": time(22, 0, 0),
            "minExerciseMinutes": 20,
            "preferredExercises": ["주짓수", "격투기"],
            "lifestyleType": LifestyleType.NIGHT,
        },
        "recentMissionHistory": [
            {
                "date": date(2026, 1, 8),
                "missionType": MissionType.EXERCISE,
                "difficulty": Difficulty.NORMAL,
                "result": MissionResult.FAILURE,
                "failureReason": "시간 부족",
            },
            {
                "date": date(2026, 1, 9),
                "missionType": MissionType.EXERCISE,
                "difficulty": Difficulty.EASY,
                "result": MissionResult.SUCCESS,
            },
        ],
        "weeklyFailureReasons": ["시간 부족", "회식 및 일정"],
        "targetDate": date(2026, 1, 10),
        "todayMission": {
            "missionType": MissionType.EXERCISE,
            "difficulty": Difficulty.NORMAL,
            "result": MissionResult.FAILURE,
            "failureReason": "시간 부족",
        },
        "recentSummary": {
            "successDays": 3,
            "failureDays": 2,
        },
        "weekRange": {
            "start": date(2026, 1, 5),
            "end": date(2026, 1, 11),
        },
        "weeklyStats": {
            "totalDays": 7,
            "successDays": 3,
            "failureDays": 4,
        },
        "failureReasonsRanked": [
            {"reason": "시간 부족", "count": 3},
            {"reason": "동기 부족", "count": 1},
        ],
    }
    return mock_data
