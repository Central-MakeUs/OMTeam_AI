# OMTeam

## 실행 방법

- 1. `git clone https://github.com/wjswlgnsdlqslek/OMTeam.git`
- 2. `uv init` (uv 다운로드 필수 // https://devocean.sk.com/blog/techBoardDetail.do?ID=167420&boardType=techBlog 참고)
- 3. `uv venv .venv`
- 4. `source .venv/bin/activate`
- 5. `uv sync`
- 6. 터미널 '`uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`'
- 7. url '127.0.0.1:8000/redoc' -> 스웨거처럼 api 확인 가능

## 테스트 실행 방법

(테스트는 제가 개발하면서 사용하는 거라서, 실행 시키고 요청 보내보시면 됩니다! env파일은 디스코드에 올려놓을게요!)

- 1. 모든 테스트: `python -m unittest discover tests`
- 2. 라우팅 테스트: `python -m unittest tests.test_routing`
- 3. 엔드포인트 테스트: `python -m unittest tests.test_api_endpoints`

---

---

---

# AI Server API Usage Examples (cURL)

`curl``http://localhost:8000/{api_endpoint}` 명령어 사용 api endpoint 테스트.

### 1. 데일리 추천 미션 생성 (POST /ai/missions/daily)

설명: 사용자 온보딩 정보, 최근 미션 이력, 주간 실패 원인을 바탕으로 데일리 미션을 추천받습니다.

cURL Command:

```bash
curl -X POST "http://localhost:8000/ai/missions/daily" \
-H "Content-Type: application/json" \
-d
'{
  "userId": 1,
  "userContext": {
    "nickname": "규빈",
    "appGoal": "건강한 생활 습관 형성",
    "recentMissionSuccessRate": 0.58,
    "currentLevel": 3,
    "successCount": 18,
    "preferredExercise": "러닝",
    "lifestyleType": "REGULAR_DAYTIME"
  },
  "onboarding": {
    "appGoal": "체력 증진",
    "workTimeType": "FIXED",
    "availableStartTime": "07:00",
    "availableEndTime": "22:00",
    "minExerciseMinutes": 10,
    "preferredExercises": ["러닝", "스트레칭"],
    "lifestyleType": "VARIABLE_DAILY"
  },
  "recentMissionHistory": [
    {
      "missionType": "EXERCISE",
      "status": "FAILED",
      "performedDate": "2026-01-30",
      "failureReason": "시간 부족"
    }
  ],
  "weeklyFailureReasons": ["시간 부족", "피로"]
}'
```

---

### 2. 데일리 AI 피드백 생성 (POST /ai/analysis/daily)

설명: 오늘 미션 수행 결과와 최근 요약 정보를 바탕으로 분석형 AI 피드백 문장과 격려/응원 메시지 후보를 받습니다.

cURL Command:

```bash
curl -X POST "http://localhost:8000/ai/analysis/daily" \
-H "Content-Type: application/json" \
-d
'{
  "userId": 1,
  "targetDate": "2026-02-01",
  "userContext": {
    "nickname": "규빈",
    "appGoal": "건강한 생활 습관 형성",
    "recentMissionSuccessRate": 0.71,
    "currentLevel": 3,
    "successCount": 18,
    "preferredExercise": "러닝",
    "lifestyleType": "REGULAR_DAYTIME"
  },
  "todayMission": {
    "missionType": "EXERCISE",
    "status": "FAILED",
    "failureReason": "시간 부족"
  }
}'
```

---

### 3. 주간 AI 분석 (POST /ai/analysis/weekly)

설명: 주간 통계 및 주요 실패 원인 순위를 바탕으로 주간 분석 피드백을 받습니다.

cURL Command:

```bash
curl -X POST "http://localhost:8000/ai/analysis/weekly" \
-H "Content-Type: application/json" \
-d
'{
  "userId": 1,
  "weekStartDate": "2026-01-26",
  "weekEndDate": "2026-02-01",
  "failureReasons": ["시간 부족", "피로"],
  "userContext": {
    "nickname": "규빈",
    "appGoal": "건강한 생활 습관 형성",
    "recentMissionSuccessRate": 0.57,
    "currentLevel": 3,
    "successCount": 18,
    "preferredExercise": "러닝",
    "lifestyleType": "REGULAR_DAYTIME"
  },
  "weeklyResults": [
    {
      "date": "2026-01-27",
      "dayOfWeek": "TUESDAY",
      "status": "FAILED",
      "missionType": "EXERCISE",
      "failureReason": "시간 부족"
    }
  ],
  "monthlyDayOfWeekStats": [
    {
      "dayOfWeek": "TUESDAY",
      "totalCount": 4,
      "successCount": 1,
      "successRate": 0.25
    }
  ]
}'
```

---

### 4. 챗봇 대화 (POST /ai/chat/messages)

설명: 사용자 입력에 따라 챗봇과 대화를 이어갑니다. 텍스트 입력 또는 옵션 선택이 가능합니다.

cURL Command:

```bash
curl -X POST "http://localhost:8000/ai/chat/messages" \
-H "Content-Type: application/json" \
-d
'{
  "input": {
    "type": "TEXT",
    "text": "운동이 힘들어요",
    "value": null
  },
  "timestamp": "2026-01-11T21:10:00+09:00",
  "userContext": {
    "nickname": "규빈",
    "appGoal": "건강한 생활 습관 형성",
    "recentMissionSuccessRate": 0.71,
    "currentLevel": 3,
    "successCount": 18,
    "preferredExercise": "러닝",
    "lifestyleType": "REGULAR_DAYTIME"
  },
  "conversationHistory": [
    {
      "role": "USER",
      "type": "TEXT",
      "text": "안녕",
      "value": null,
      "options": null
    },
    {
      "role": "ASSISTANT",
      "type": null,
      "text": "안녕하세요! 무엇을 도와드릴까요?",
      "value": null,
      "options": []
    }
  ]
}'
```
