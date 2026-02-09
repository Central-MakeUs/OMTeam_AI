from typing import List, Optional, Dict, Any
import json
from datetime import date, time, datetime
from pydantic import BaseModel

from fastapi import HTTPException

from agent_system import run_agent_system
from app.api.schemas import (
    AiMissionRecommendRequest, AiMissionRecommendResponse,
    AiDailyAnalysisRequest, AiDailyAnalysisResponse,
    AiWeeklyAnalysisRequest, AiWeeklyAnalysisResponse,
    AiChatRequest, AiChatResponse,
)


def _call_agent_and_parse_response(
    user_request_prompt: str,
    user_id: str,
    user_payload_for_agent: Dict[str, Any],
    response_model: BaseModel
) -> BaseModel:
    """
    Calls the agent system, parses its JSON response, and validates against a Pydantic model.
    """
    agent_result = run_agent_system(
        user_request=user_request_prompt,
        user_id=user_id,
        user_payload=user_payload_for_agent
    )

    agent_response_content = agent_result.get("agent_response", "")

    try:
        json_start = agent_response_content.find("```json")
        json_end = agent_response_content.rfind("```")

        if json_start != -1 and json_end != -1 and json_start < json_end:
            json_str = agent_response_content[json_start + len("```json"):
                                               json_end].strip()
            response_data = json.loads(json_str)
        else:
            response_data = json.loads(agent_response_content)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse AI agent's response as JSON: {e}. Raw response: {agent_response_content}"
        )

    try:
        return response_model(**response_data)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI agent's response did not match the expected {response_model.__name__} schema: {e}. Parsed data: {response_data}"
        )


async def get_daily_missions_service(request: AiMissionRecommendRequest) -> AiMissionRecommendResponse:
    user_id = str(request.userId)

    # Convert request to dict for agent payload
    user_payload_for_agent = request.dict()

    user_request_prompt = f"""
    사용자 ID: {request.userId}
    사용자 컨텍스트: {request.userContext.dict()}
    온보딩 데이터: {request.onboarding.dict()}
    최근 미션 이력: {[h.dict() for h in request.recentMissionHistory]}
    주간 주요 실패 원인: {request.weeklyFailureReasons}

    위 정보를 바탕으로 사용자에게 오늘 수행할 데일리 추천 미션 3개를 추천해주세요.
    미션 이름은 최대 20자 입니다.
    미션은 EXERCISE 또는 DIET 유형으로 구성될 수 있습니다.
    난이도는 1이상 5이하 정수로 표현합니다.
    각 미션에 대해 예상 소요 시간(분)과 예상 소모 칼로리(kcal)를 함께 알려주세요.
    응답은 반드시 아래 JSON 형식으로만 해주세요:
    ```json
    {{
        "missions": [
            {{
                "name": "미션 이름 1",
                "type": "EXERCISE",
                "difficulty": 1,
                "estimatedMinutes": 20,
                "estimatedCalories": 80
            }},
            {{
                "name": "미션 이름 2",
                "type": "DIET",
                "difficulty": 3,
                "estimatedMinutes": 10,
                "estimatedCalories": 0
            }}
        ]
    }}
    ```
    """
    return _call_agent_and_parse_response(
        user_request_prompt, user_id, user_payload_for_agent, AiMissionRecommendResponse
    )


async def get_daily_feedback_service(request: AiDailyAnalysisRequest) -> AiDailyAnalysisResponse:
    user_id = str(request.userId)

    user_payload_for_agent = request.dict()

    today_mission_text = (
        request.todayMission.dict()
        if request.todayMission is not None
        else "해당 날짜의 미션 기록 없음"
    )
    
    user_request_prompt = f"""
    사용자 ID: {request.userId}
    분석 대상 날짜: {request.targetDate.isoformat()}
    사용자 컨텍스트: {request.userContext.dict()}
    해당 날짜의 미션: {today_mission_text}

    위 정보를 바탕으로 다음 내용을 분석하여 피드백을 제공해주세요.
    1. 해당 날짜의 미션 수행 결과 및 최근 기록을 반영한 분석형 AI 피드백 문장을 생성해주세요. (feedbackText)
    2. 메인 화면에 표시할 격려/응원 메시지 후보를 생성해주세요. 각 메시지는 'intent'(PRAISE, RETRY, NORMAL, PUSH), 'title', 'message'를 포함해야 합니다. (encouragementCandidates)

    응답은 반드시 아래 JSON 형식으로만 해주세요:
    ```json
    {{
        "feedbackText": "시간 부족으로 미션을 완료하지 못했어요. 최근에도 꾸준히 시도하고 있으니, 부담을 줄여 짧은 미션부터 다시 시작해보는 걸 추천해요.",
        "encouragementCandidates": [
            {{
                "intent": "PRAISE",
                "title": "잘하고 있어요",
                "message": "이대로만 하면 목표에 도달할 수 있어요."
            }},
            {{
                "intent": "RETRY",
                "title": "흐름은 다시 만들 수 있어요",
                "message": "내일은 5분짜리 미션부터 가볍게 시작해봐요."
            }}
        ]
    }}
    ```
    """
    return _call_agent_and_parse_response(
        user_request_prompt, user_id, user_payload_for_agent, AiDailyAnalysisResponse
    )


async def get_weekly_analysis_service(request: AiWeeklyAnalysisRequest) -> AiWeeklyAnalysisResponse:
    user_id = str(request.userId)

    user_payload_for_agent = request.dict()

    user_request_prompt = f"""
    사용자 ID: {request.userId}
    분석 주간: {request.weekStartDate.isoformat()} ~ {request.weekEndDate.isoformat()}
    사용자 컨텍스트: {request.userContext.dict()}
    주간 실패 사유: {request.failureReasons}
    주간 결과: {[r.dict() for r in request.weeklyResults]}
    월간 요일별 통계: {[s.dict() for s in request.monthlyDayOfWeekStats]}

    위 주간 데이터를 종합적으로 분석하여 사용자에게 다음 정보를 제공해주세요.
    1. 이번 주 실패 원인 순위 (failureReasonRanking)
    2. 이번 주 종합 피드백 (weeklyFeedback)
    3. 요일별 분석 기반 피드백 (dayOfWeekFeedback)

    응답은 반드시 아래 JSON 형식으로만 해주세요:
    ```json
    {{
      "failureReasonRanking": [
        {{ "rank": 1, "category": "시간 부족", "count": 3 }},
        {{ "rank": 2, "category": "피로", "count": 2 }}
      ],
      "weeklyFeedback": "이번 주는 시간 관리가 어려웠던 한 주였네요. 점심시간을 활용한 짧은 운동을 추천드립니다.",
      "dayOfWeekFeedback": {{
        "title": "화요일과 목요일에 집중해보세요",
        "content": "지난 한 달간 화요일과 목요일에 실패가 많았습니다. 출근 전 10분 스트레칭으로 시작해보는 건 어떨까요?"
      }}
    }}
    ```
    """
    return _call_agent_and_parse_response(
        user_request_prompt, user_id, user_payload_for_agent, AiWeeklyAnalysisResponse
    )


async def handle_chat_message_service(request: AiChatRequest) -> AiChatResponse:
    user_id = str(request.userContext.nickname) # Assuming nickname is unique identifier

    user_payload_for_agent = request.dict()

    history_formatted = "\n".join([f"- {msg.role}: {msg.text}" for msg in request.conversationHistory])

    user_request_prompt = f"""
    사용자 컨텍스트: {request.userContext.dict()}
    현재 대화 내역:
    {history_formatted}
    
    사용자 마지막 입력: {request.input.dict() if request.input else "없음 (대화 시작)"}
    요청 시각: {request.timestamp.isoformat()}

    위 대화의 흐름과 사용자 정보를 바탕으로 다음 챗봇 메시지를 생성해주세요.
    필요하다면 사용자에게 선택지를 제공할 수 있습니다.
    대화가 자연스럽게 종료되어야 할 시점이라고 판단되면 "state.isTerminal"을 true로 설정해주세요.
    
    응답은 반드시 아래 JSON 형식으로만 해주세요:
    ```json
    {{
        "botMessage": {{
            "text": "챗봇 응답 메시지",
            "options": [
                {{"label": "선택지 1", "value": "VALUE_1"}},
                {{"label": "선택지 2", "value": "VALUE_2"}}
            ]
        }},
        "state": {{
            "isTerminal": false
        }}
    }}
    ```
    """
    return _call_agent_and_parse_response(
        user_request_prompt, user_id, user_payload_for_agent, AiChatResponse
    )