from pydantic import BaseModel, Field
from typing import List, Optional, Union
from enum import Enum
from datetime import date, datetime

# --- Common Models ---

class UserContext(BaseModel):
    nickname: str
    appGoal: str
    recentMissionSuccessRate: float
    currentLevel: int
    successCount: int
    preferredExercise: str
    lifestyleType: str

# --- /ai/missions/daily Models ---

class OnboardingData(BaseModel):
    appGoal: str
    workTimeType: str
    availableStartTime: str # HH:mm
    availableEndTime: str # HH:mm
    minExerciseMinutes: int
    preferredExercises: List[str]
    lifestyleType: str

class MissionHistory(BaseModel):
    missionType: str
    status: str
    performedDate: date
    failureReason: Optional[str] = None

class AiMissionRecommendRequest(BaseModel):
    userId: int
    userContext: UserContext
    onboarding: OnboardingData
    recentMissionHistory: List[MissionHistory]
    weeklyFailureReasons: List[str]

class RecommendedMission(BaseModel):
    name: str
    type: str # 'EXERCISE' or 'DIET'
    difficulty: int
    estimatedMinutes: int
    estimatedCalories: int

class AiMissionRecommendResponse(BaseModel):
    missions: List[RecommendedMission]


# --- /ai/analysis/daily Models ---

class TodayMission(BaseModel):
    missionType: str
    status: str
    failureReason: Optional[str] = None

class AiDailyAnalysisRequest(BaseModel):
    userId: int
    targetDate: date
    userContext: UserContext
    todayMission: TodayMission

class EncouragementCandidate(BaseModel):
    intent: str # 'PRAISE', 'RETRY', 'NORMAL', 'PUSH'
    title: str
    message: str

class AiDailyAnalysisResponse(BaseModel):
    feedbackText: str
    encouragementCandidates: List[EncouragementCandidate]


# --- /ai/analysis/weekly Models ---

class DailyResultSummary(BaseModel):
    date: date
    dayOfWeek: str # 'MONDAY' ~ 'SUNDAY'
    status: str
    missionType: str
    failureReason: Optional[str] = None

class DayOfWeekStats(BaseModel):
    dayOfWeek: str
    totalCount: int
    successCount: int
    successRate: float

class AiWeeklyAnalysisRequest(BaseModel):
    userId: int
    weekStartDate: date
    weekEndDate: date
    failureReasons: List[str]
    userContext: UserContext
    weeklyResults: List[DailyResultSummary]
    monthlyDayOfWeekStats: List[DayOfWeekStats]

class FailureReasonRank(BaseModel):
    rank: int
    category: str
    count: int

class DayOfWeekFeedback(BaseModel):
    title: str
    content: str

class AiWeeklyAnalysisResponse(BaseModel):
    failureReasonRanking: List[FailureReasonRank]
    weeklyFeedback: str
    dayOfWeekFeedback: DayOfWeekFeedback


# --- /ai/chat/messages Models ---

class ChatInput(BaseModel):
    type: str # 'TEXT' or 'OPTION'
    text: Optional[str] = None
    value: Optional[str] = None

class ChatMessageOption(BaseModel):
    label: str
    value: str

class ConversationMessage(BaseModel):
    role: str # 'USER' or 'ASSISTANT'
    type: Optional[str] = None
    text: Optional[str] = None
    value: Optional[str] = None
    options: Optional[List[ChatMessageOption]] = None

class AiChatRequest(BaseModel):
    input: Optional[ChatInput] = None
    timestamp: datetime
    userContext: UserContext
    conversationHistory: List[ConversationMessage]

class BotMessage(BaseModel):
    text: str
    options: Optional[List[ChatMessageOption]] = None

class ChatState(BaseModel):
    isTerminal: bool

class AiChatResponse(BaseModel):
    botMessage: BotMessage
    state: ChatState