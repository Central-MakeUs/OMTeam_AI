# OMTeam

## 실행 방법

- 1. `git clone https://github.com/wjswlgnsdlqslek/OMTeam.git`
- 2. `uv init` (uv 다운로드 필수 // https://devocean.sk.com/blog/techBoardDetail.do?ID=167420&boardType=techBlog 참고)
- 3. `uv venv .venv`
- 4. `source .venv/bin/activate`
- 5. `uv sync`
- 6. 터미널 '`uv run uvicorn app.main:app --host 0.0.0.0 --reload --port 8000`'
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
-d '{
  "userId": 12345,
  "onboarding": {
    "appGoal": "체중 감량",
    "workTimeType": "FIXED",
    "availableStartTime": "18:30:00",
    "availableEndTime": "22:00:00",
    "minExerciseMinutes": 20,
    "preferredExercises": ["러닝", "훌라후프"],
    "lifestyleType": "NIGHT"
  },
  "recentMissionHistory": [
    {
      "date": "2026-01-08",
      "missionType": "EXERCISE",
      "difficulty": "NORMAL",
      "result": "FAILURE",
      "failureReason": "시간 부족"
    },
    {
      "date": "2026-01-09",
      "missionType": "EXERCISE",
      "difficulty": "EASY",
      "result": "SUCCESS"
    }
  ],
  "weeklyFailureReasons": ["시간 부족", "동기 부족"]
}'
```

---

### 2. 데일리 AI 피드백 생성 (POST /ai/analysis/daily)

설명: 오늘 미션 수행 결과와 최근 요약 정보를 바탕으로 분석형 AI 피드백 문장과 격려/응원 메시지 후보를 받습니다.

cURL Command:

```bash
curl -X POST "http://localhost:8000/ai/analysis/daily" \
-H "Content-Type: application/json" \
-d '{
  "userId": 12345,
  "targetDate": "2026-01-10",
  "todayMission": {
    "missionType": "EXERCISE",
    "difficulty": "NORMAL",
    "result": "FAILURE",
    "failureReason": "시간 부족"
  },
  "recentSummary": {
    "successDays": 3,
    "failureDays": 2
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
-d '{
  "userId": 12345,
  "weekRange": {
    "start": "2026-01-05",
    "end": "2026-01-11"
  },
  "weeklyStats": {
    "totalDays": 7,
    "successDays": 3,
    "failureDays": 4
  },
  "failureReasonsRanked": [
    {"reason": "시간 부족", "count": 3},
    {"reason": "동기 부족", "count": 1}
  ]
}'
```

---

### 4. 채팅 세션 생성 (POST /ai/chat/sessions)

설명: 새로운 채팅 세션을 시작하고 초기 챗봇 메시지를 받습니다.

cURL Command:

```bash
curl -X POST "http://localhost:8000/ai/chat/sessions" \
-H "Content-Type: application/json" \
-d '{
  "sessionId": 1001,
  "userId": 12345,
  "initialContext": {
    "appGoal": "체중 감량",
    "lifestyleType": "NIGHT"
  }
}'
```

---

### 5. 챗봇 대화 (POST /ai/chat/messages)

설명: 사용자 입력에 따라 챗봇과 대화를 이어갑니다. 텍스트 입력 또는 옵션 선택이 가능합니다.

cURL Command (텍스트 입력):

```bash
curl -X POST "http://localhost:8000/ai/chat/messages" \
-H "Content-Type: application/json" \
-d '{
  "sessionId": 1,
  "userId": 12345,
  "input": {
    "type": "TEXT",
    "text": "운동이 너무 힘들어요"
  },
  "timestamp": "2026-01-11T21:10:00+09:00"
}'
```

cURL Command (옵션 선택):

```bash
curl -X POST "http://localhost:8000/ai/chat/messages" \
-H "Content-Type: application/json" \
-d '{
  "sessionId": 1,
  "userId": 12345,
  "input": {
    "type": "OPTION",
    "value": "TIME_SHORTAGE"
  },
  "timestamp": "2026-01-11T21:10:00+09:00"
}'
```

1. chat -> routing

- 채팅으로 유저 입력 들어오면 의도 구분해서 에이전트 실행

- 에이전트 실행할 때, 앱 서버에서 유저 정보 받아와야 함.(다시 수정 필요)
-
