# OMTeam AI Server

## 실행 방법

- 1. `git clone https://github.com/wjswlgnsdlqslek/OMTeam.git`
- 2. `uv init` (uv 다운로드 필수 // https://devocean.sk.com/blog/techBoardDetail.do?ID=167420&boardType=techBlog 참고)
- 3. `uv venv .venv`
- 4. `source .venv/bin/activate`
- 5. `uv sync`
- 6. 터미널 '`uv run uvicorn app.main:app --host 0.0.0.0 --reload --port 8000`'
- 7. url '127.0.0.1:8000/redoc' -> 스웨거UI api 확인 가능

## 테스트 실행 방법

(테스트는 제가 개발하면서 사용하는 거라서, 실행 시키고 요청 보내보시면 됩니다! env파일은 디스코드에 올려놓을게요!)

- 1. 모든 테스트: `python -m unittest discover tests`
- 2. 라우팅 테스트: `python -m unittest tests.test_routing`
- 3. 엔드포인트 테스트: `python -m unittest tests.test_api_endpoints`

---

## AI Server API 사용 방법 (cURL 예시)

### 아키텍처 변경 개요 및 통합 API 안내

기존에는 기능별로 나뉘어 있던 여러 API 엔드포인트(`missions/daily`, `analysis/daily`, `chat/sessions`, `chat/messages`)가 이제 **`POST /ai/chat/messages` 단일 엔드포인트로 통합**되었습니다.

이는 AI 서버가 자체적인 오케스트레이터를 통해 사용자의 요청 의도를 분석하고, `userId` 기반의 컨텍스트를 서버에서 직접 관리하며, 필요에 따라 적절한 전문 에이전트(미션 플래너, 분석가, 코치)를 실행하는 새로운 아키텍처를 반영합니다.

App 서버는 모든 AI 관련 요청을 `/ai/chat/messages`로 보내고, 응답으로 받는 **`UnifiedAIResponse`** 모델을 통해 어떤 AI 기능의 결과가 반환되었는지 확인합니다.

### 통합 AI 채팅 (Unified AI Chat)

모든 AI 기능 요청 및 일반 대화를 처리하는 유일한 엔드포인트입니다.

- **method**: POST
- **url**: `/ai/chat/messages`

#### 1. 일반 채팅 요청 (General Chat Request)

설명: 사용자의 일반적인 자연어 질문이나 대화를 AI 에이전트에게 전달합니다.

cURL Command:

```bash
curl -X POST "http://localhost:8000/ai/chat/messages" \
-H "Content-Type: application/json" \
-d '{
  "sessionId": 1,
  "userId": 12345,
  "input": {
    "type": "TEXT",
    "text": "운동이 너무 힘들어요. 동기부여가 안돼요."
  },
  "timestamp": "2026-01-11T21:10:00+09:00"
}'
```

예상 응답 (UnifiedAIResponse):

```json
{
  "dailyMission": null,
  "dailyFeedback": null,
  "weeklyAnalysis": null,
  "chat": {
    "botMessage": {
      "messageId": 1709865600, // timestamp 기반 ID
      "text": "어떤 점이 가장 힘드셨나요? 제가 어떻게 도와드릴 수 있을까요?",
      "options": []
    },
    "state": {
      "isTerminal": false
    }
  },
  "error": null
}
```

#### 2. 특정 기능 요청 (예: 데일리 미션 생성)

설명: App 서버에서 '오늘의 미션 추천'과 같은 특정 UI 액션을 통해 AI 기능을 호출할 때 사용합니다. `input.text`에 요청 내용을 명시하고, 필요한 구조화된 데이터는 `context` 필드에 추가할 수 있습니다. `context`에 포함된 데이터는 `services.py`에서 프롬프트 생성 시 활용됩니다.

cURL Command:

```bash
curl -X POST "http://localhost:8000/ai/chat/messages" \
-H "Content-Type: application/json" \
-d '{
  "sessionId": 2,
  "userId": 12345,
  "input": {
    "type": "TEXT",
    "text": "오늘의 미션을 추천해줘."
  },
  "context": {
    "onboarding": {
      "appGoal": "체중 감량",
      "workTimeType": "FIXED",
      "availableStartTime": "18:30:00",
      "availableEndTime": "22:00:00",
      "minExerciseMinutes": 20,
      "preferredExercises": ["러닝", "홈트"],
      "lifestyleType": "NIGHT"
    },
    "recentMissionHistory": [
      {
        "date": "2026-01-08",
        "missionType": "EXERCISE",
        "difficulty": "NORMAL",
        "result": "FAILURE",
        "failureReason": "시간 부족"
      }
    ],
    "weeklyFailureReasons": ["시간 부족"]
  },
  "timestamp": "2026-01-12T10:05:00+09:00"
}'
```

예상 응답 (UnifiedAIResponse):

```json
{
  "dailyMission": {
    "missions": [
      {
        "name": "저녁 스트레칭 20분",
        "type": "EXERCISE",
        "difficulty": "EASY",
        "estimatedMinutes": 20,
        "estimatedCalories": 80
      }
    ]
  },
  "dailyFeedback": null,
  "weeklyAnalysis": null,
  "chat": null,
  "error": null
}
```

---

### Deprecated API Endpoints (참고용)

아래 엔드포인트들은 이제 사용되지 않으며, 모든 기능은 위 `/ai/chat/messages` 통합 엔드포인트를 통해 접근할 수 있습니다. 이 섹션은 과거 API 명세를 이해하기 위한 참고용입니다.

- `POST /ai/missions/daily`
- `POST /ai/analysis/daily`
- `POST /ai/analysis/weekly`
- `POST /ai/chat/sessions`
- `POST /ai/chat/messages` (기존 채팅 기능)
