from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import date, time, datetime


# --- Enums for API Models ---
class WorkTimeType(str, Enum):
    FIXED = "FIXED"
    SHIFT = "SHIFT"
    FREE = "FREE"

class LifestyleType(str, Enum):
    MORNING = "MORNING"
    NIGHT = "NIGHT"
    IRREGULAR = "IRREGULAR"

class MissionType(str, Enum):
    EXERCISE = "EXERCISE"
    DIET = "DIET"

class Difficulty(str, Enum):
    EASY = "EASY"
    NORMAL = "NORMAL"
    HARD = "HARD"

class MissionResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

# --- /ai/missions/daily Models ---
class OnboardingData(BaseModel):
    appGoal: str
    workTimeType: WorkTimeType
    availableStartTime: time
    availableEndTime: time
    minExerciseMinutes: int
    preferredExercises: List[str]
    lifestyleType: LifestyleType

class RecentMissionHistoryItem(BaseModel):
    date: date
    missionType: MissionType
    difficulty: Difficulty
    result: MissionResult
    failureReason: Optional[str] = None

class DailyMissionRequest(BaseModel):
    userId: int
    onboarding: OnboardingData
    recentMissionHistory: List[RecentMissionHistoryItem]
    weeklyFailureReasons: List[str]

class Mission(BaseModel):
    name: str
    type: MissionType
    difficulty: Difficulty
    estimatedMinutes: int
    estimatedCalories: int

class DailyMissionResponse(BaseModel):
    missions: List[Mission]

# --- /ai/analysis/daily Models ---
class Intent(str, Enum):
    PRAISE = "PRAISE"
    RETRY = "RETRY"
    NORMAL = "NORMAL"
    PUSH = "PUSH"

class TodayMissionData(BaseModel):
    missionType: MissionType
    difficulty: Difficulty
    result: MissionResult
    failureReason: Optional[str] = None

class RecentSummaryData(BaseModel):
    successDays: int
    failureDays: int

class DailyFeedbackRequest(BaseModel):
    userId: int
    targetDate: date
    todayMission: TodayMissionData
    recentSummary: RecentSummaryData

class EncouragementCandidate(BaseModel):
    intent: Intent
    title: str
    message: str

class DailyFeedbackResponse(BaseModel):
    feedbackText: str
    encouragementCandidates: List[EncouragementCandidate]

# --- /ai/analysis/weekly Models ---
class WeekRangeData(BaseModel):
    start: date
    end: date

class WeeklyStatsData(BaseModel):
    totalDays: int
    successDays: int
    failureDays: int

class FailureReasonRankedItem(BaseModel):
    reason: str
    count: int

class WeeklyAnalysisRequest(BaseModel):
    userId: int
    weekRange: WeekRangeData
    weeklyStats: WeeklyStatsData
    failureReasonsRanked: List[FailureReasonRankedItem]

class WeeklyAnalysisResponse(BaseModel):
    mainFailureReason: str
    overallFeedback: str

# --- /ai/chat/sessions Models ---
class InitialChatContext(BaseModel):
    appGoal: str
    lifestyleType: LifestyleType

class ChatSessionRequest(BaseModel):
    sessionId: int
    userId: int
    initialContext: InitialChatContext

class BotMessageOption(BaseModel):
    label: str
    value: str

class BotMessage(BaseModel):
    messageId: int
    text: str
    options: List[BotMessageOption]

class ChatSessionResponse(BaseModel):
    botMessage: BotMessage

# --- /ai/chat/messages Models ---
class ChatInputType(str, Enum):
    TEXT = "TEXT"
    OPTION = "OPTION"

class ChatInput(BaseModel):
    type: ChatInputType
    text: Optional[str] = None
    value: Optional[str] = None

class ChatMessageRequest(BaseModel):
    sessionId: int
    userId: int
    input: ChatInput
    timestamp: datetime # Use datetime for ISO-8601 string

class ChatState(BaseModel):
    isTerminal: bool

class ChatMessageResponse(BaseModel):
    botMessage: BotMessage # Re-use BotMessage model
    state: ChatState


# --- Unified AI Response Model ---
# To provide a consistent response structure for the app server, all AI server responses
# are wrapped in this model. Based on the user's request, only one of the
# optional fields below will be populated.
class UnifiedAIResponse(BaseModel):
    dailyMission: Optional[DailyMissionResponse] = None
    dailyFeedback: Optional[DailyFeedbackResponse] = None
    weeklyAnalysis: Optional[WeeklyAnalysisResponse] = None
    chat: Optional[ChatMessageResponse] = None
    # A general text field for errors or simple messages that don't fit other schemas.
    error: Optional[str] = None

