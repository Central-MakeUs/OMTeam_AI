from typing import List, Optional, Dict, Any
import json
from datetime import date, time, datetime
from pydantic import BaseModel

from fastapi import HTTPException

from agent_system import run_agent_system
from app.api.schemas import (
    DailyMissionRequest, DailyMissionResponse, Mission,
    DailyFeedbackRequest, DailyFeedbackResponse, EncouragementCandidate, Intent,
    WeeklyAnalysisRequest, WeeklyAnalysisResponse,
    ChatSessionRequest, ChatSessionResponse, BotMessage, BotMessageOption,
    ChatMessageRequest, ChatMessageResponse, ChatInputType, ChatState
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


async def get_daily_missions_service(request: DailyMissionRequest) -> DailyMissionResponse:
    user_id = str(request.userId)

    user_payload_for_agent = {
        "preferences": {
            "appGoal": request.onboarding.appGoal,
            "workTimeType": request.onboarding.workTimeType.value,
            "availableTime": f"{request.onboarding.availableStartTime.isoformat()}-{request.onboarding.availableEndTime.isoformat()}",
            "minExerciseMinutes": request.onboarding.minExerciseMinutes,
            "preferredExercises": ", ".join(request.onboarding.preferredExercises),
            "lifestyleType": request.onboarding.lifestyleType.value,
        },
        "event": {
            "weeklyFailureReasons": ", ".join(request.weeklyFailureReasons)
        }
    }
    for mission_item in request.recentMissionHistory:
        user_payload_for_agent["event"] = {
            "date": mission_item.date.isoformat(),
            "missionType": mission_item.missionType.value,
            "difficulty": mission_item.difficulty.value,
            "mission_result": mission_item.result.value,
            "fail_reason": mission_item.failureReason,
            **user_payload_for_agent.get("event", {})
        }

    user_request_prompt = f"""
    사용자 ID: {request.userId}
    사용자 목표: {request.onboarding.appGoal}
    근무 시간 유형: {request.onboarding.workTimeType.value}
    운동 가능 시간: {request.onboarding.availableStartTime.isoformat()} ~ {request.onboarding.availableEndTime.isoformat()} ({request.onboarding.minExerciseMinutes}분 이상)
    선호 운동: {', '.join(request.onboarding.preferredExercises)}
    생활 패턴: {request.onboarding.lifestyleType.value}

    최근 미션 이력:
    {    '\n'.join([
        f"- 날짜: {item.date.isoformat()}, 유형: {item.missionType.value}, 난이도: {item.difficulty.value}, 결과: {item.result.value}{f', 실패 사유: {item.failureReason}' if item.failureReason else ''}"
        for item in request.recentMissionHistory
    ]) if request.recentMissionHistory else '- 없음'}

    주간 주요 실패 원인: {', '.join(request.weeklyFailureReasons) if request.weeklyFailureReasons else '없음'}

    위 정보를 바탕으로 사용자에게 오늘 수행할 데일리 추천 미션 2~3개를 추천해주세요.
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
        user_request_prompt, user_id, user_payload_for_agent, DailyMissionResponse
    )


async def get_daily_feedback_service(request: DailyFeedbackRequest) -> DailyFeedbackResponse:
    user_id = str(request.userId)

    user_payload_for_agent = {
        "event": {
            "date": request.targetDate.isoformat(),
            "missionType": request.todayMission.missionType.value,
            "difficulty": request.todayMission.difficulty.value,
            "mission_result": request.todayMission.result.value,
            "fail_reason": request.todayMission.failureReason,
            "successDays_recent": request.recentSummary.successDays,
            "failureDays_recent": request.recentSummary.failureDays,
        }
    }

    user_request_prompt = f"""
    사용자 ID: {request.userId}
    분석 대상 날짜: {request.targetDate.isoformat()}
    오늘 수행한 미션:
    - 유형: {request.todayMission.missionType.value}
    - 난이도: {request.todayMission.difficulty.value}
    - 결과: {request.todayMission.result.value}{f' (실패 사유: {request.todayMission.failureReason})' if request.todayMission.failureReason else ''}
    최근 요약:
    - 성공 일수: {request.recentSummary.successDays}일
    - 실패 일수: {request.recentSummary.failureDays}일

    위 정보를 바탕으로 다음 내용을 분석하여 피드백을 제공해주세요.
    1. 오늘 미션 수행 결과 및 최근 기록을 반영한 분석형 AI 피드백 문장을 생성해주세요.
    2. 메인 화면에 표시할 격려/응원 메시지 후보 2~4개를 생성해주세요. 각 메시지는 'intent'(PRAISE, RETRY, NORMAL, PUSH 중 하나), 'title', 'message'를 포함해야 합니다.
       - PRAISE: 잘하고 있을 때 칭찬 및 목표 상기.
       - RETRY: 실패가 반복되거나 재도전이 필요할 때 격려.
       - NORMAL: 보통일 때 목표 달성을 격려.
       - PUSH: 행동을 촉구할 때.

    응답은 반드시 아래 JSON 형식으로만 해주세요:
    ```json
    {{
        "feedbackText": "오늘 미션 수행 결과 및 최근 기록을 반영한 분석형 AI 피드백 문장",
        "encouragementCandidates": [
            {{
                "intent": "PRAISE",
                "title": "잘하고 있어요",
                "message": "이대로만 하면 목표에 도달할 수 있어요."
            }},
            {{
                "intent": "RETRY",
                "title": "다음은 다시 도전해봐요",
                "message": "내일은 5분짜리 미션부터 가볍게 시작해봐요."
            }}
        ]
    }}
    ```
    """
    return _call_agent_and_parse_response(
        user_request_prompt, user_id, user_payload_for_agent, DailyFeedbackResponse
    )


async def get_weekly_analysis_service(request: WeeklyAnalysisRequest) -> WeeklyAnalysisResponse:
    user_id = str(request.userId)

    user_payload_for_agent = {
        "preferences": {},
        "event": {
            "week_start": request.weekRange.start.isoformat(),
            "week_end": request.weekRange.end.isoformat(),
            "totalDays_weekly": request.weeklyStats.totalDays,
            "successDays_weekly": request.weeklyStats.successDays,
            "failureDays_weekly": request.weeklyStats.failureDays,
            "failureReasons_ranked": ", ".join([f"{item.reason} ({item.count}회)" for item in request.failureReasonsRanked]),
        }
    }

    user_request_prompt = f"""
    사용자 ID: {request.userId}
    주간 분석 범위: {request.weekRange.start.isoformat()} ~ {request.weekRange.end.isoformat()}
    주간 통계:
    - 총 일수: {request.weeklyStats.totalDays}일
    - 성공 일수: {request.weeklyStats.successDays}일
    - 실패 일수: {request.weeklyStats.failureDays}일
    주요 실패 원인 (횟수 기준):
    {    '\n'.join([
        f"- {item.reason}: {item.count}회"
        for item in request.failureReasonsRanked
    ]) if request.failureReasonsRanked else '- 없음'}

    위 주간 데이터를 종합적으로 분석하여 사용자에게 다음 두 가지 정보를 제공해주세요.
    1. 주간 주요 실패 원인을 요약한 문장 (mainFailureReason).
    2. 사용자 유지/개선 중심의 종합 피드백 문장 (overallFeedback).

    응답은 반드시 아래 JSON 형식으로만 해주세요:
    ```json
    {{
        "mainFailureReason": "주간 주요 실패 원인 요약 (예: 운동 가능 시간 확보 실패)",
        "overallFeedback": "유지/개선 중심 종합 피드백 (예: 이번 주에는 일정 제약으로 미션 실패가 많았네요. 다음 주에는 시간을 조금 더 확보해보세요.)"
    }}
    ```
    """
    return _call_agent_and_parse_response(
        user_request_prompt, user_id, user_payload_for_agent, WeeklyAnalysisResponse
    )


async def create_chat_session_service(request: ChatSessionRequest) -> ChatSessionResponse:
    user_id = str(request.userId)

    user_payload_for_agent = {
        "preferences": {
            "appGoal": request.initialContext.appGoal,
            "lifestyleType": request.initialContext.lifestyleType.value,
        }
    }

    user_request_prompt = f"""
    새로운 채팅 세션이 시작되었습니다.
    사용자 ID: {request.userId}
    세션 ID: {request.sessionId}
    사용자 초기 컨텍스트:
    - 앱 사용 목적: {request.initialContext.appGoal}
    - 생활 패턴: {request.initialContext.lifestyleType.value}

    이 정보를 바탕으로 사용자에게 친근하게 인사하고, 어떤 점이 가장 고민되는지 물어보는 초기 챗봇 메시지를 생성해주세요.
    메시지에는 2~3개의 선택지 옵션을 포함하여 사용자가 쉽게 대화를 시작할 수 있도록 유도해주세요.
    응답은 반드시 아래 JSON 형식으로만 해주세요:
    ```json
    {{
        "botMessage": {{
            "messageId": 5001,
            "text": "안녕하세요! 요즘 운동이나 생활 습관에서 가장 고민되는 부분이 무엇인가요?",
            "options": [
                {{"label": "운동이 너무 힘들어요", "value": "EXERCISE_HARD"}},
                {{"label": "식단 관리가 어려워요", "value": "DIET_HARD"}}
            ]
        }}
    }}
    ```
    """
    return _call_agent_and_parse_response(
        user_request_prompt, user_id, user_payload_for_agent, ChatSessionResponse
    )


async def handle_chat_message_service(request: ChatMessageRequest) -> ChatMessageResponse:
    user_id = str(request.userId)
    
    user_input_content = ""
    if request.input.type == ChatInputType.TEXT and request.input.text:
        user_input_content = f"사용자 텍스트 입력: {request.input.text}"
    elif request.input.type == ChatInputType.OPTION and request.input.value:
        user_input_content = f"사용자 선택지 입력: {request.input.value}"

    user_payload_for_agent = {
        "event": {
            "session_id": request.sessionId,
            "input_type": request.input.type.value,
            "input_content": user_input_content,
            "timestamp": request.timestamp.isoformat(),
        }
    }

    user_request_prompt = f"""
    이전 대화 세션 ID: {request.sessionId}
    사용자 ID: {request.userId}
    사용자 입력: {user_input_content}
    입력 시각: {request.timestamp.isoformat()}

    사용자의 입력에 대해 챗봇 메시지를 생성해주세요.
    필요하다면 2~3개의 선택지 옵션을 제공해주세요.
    대화가 종료되어야 할 시점에는 "state.isTerminal"을 true로 설정해주세요.
    응답은 반드시 아래 JSON 형식으로만 해주세요:
    ```json
    {{
        "botMessage": {{
            "messageId": 5002,
            "text": "사용자의 입력에 대한 챗봇 응답 메시지",
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
        user_request_prompt, user_id, user_payload_for_agent, ChatMessageResponse
    )
