"""
LangGraph 기반 에이전트 오케스트레이션 시스템 (LangSmith tracing/sampling 버전)

요구사항 반영:
1) LangSmith 적용 (샘플링/에러 우선 수집)
2) 그래프/노드/LLM 호출까지 correlation 유지
3) 메타데이터/태깅 표준화
4) 타입/상태/메시지 처리 정리

환경변수 (.env 권장)
- UPSTAGE_API_KEY=...
- LANGCHAIN_TRACING_V2=true
- LANGCHAIN_API_KEY=lsv2_...                     # LangSmith API key
- LANGCHAIN_PROJECT=...                          # LangSmith project
- LANGSMITH_TRACING=true                         # 구버전 호환
- LANGSMITH_API_KEY=lsv2_...                     # 구버전 호환
- LANGSMITH_PROJECT=...                          # 구버전 호환
- TRACE_SAMPLE_RATE=0.1                          # prod 샘플링 비율(선택)
- TRACE_ALLOW_PII=false                          # PII 포함 시 tracing off (선택)
- APP_ENV=dev|stg|prod (선택)
- GIT_SHA=... (선택)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict, Literal, Optional, Dict, Any, List, cast
from dotenv import load_dotenv
import os
import time
import uuid
import threading
import random

from langchain_upstage import ChatUpstage
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END

# LangSmith (LangChain tracer)
try:
    from langchain.callbacks.tracers.langchain import LangChainTracer
except Exception:
    LangChainTracer = None

# -----------------------------------------------------------------------------
# Load env
# -----------------------------------------------------------------------------
load_dotenv()


def _ensure_langsmith_env_aliases() -> None:
    """LANGSMITH_* 환경변수를 LANGCHAIN_*로 보정."""
    if os.environ.get("LANGCHAIN_API_KEY") is None:
        langsmith_key = os.environ.get("LANGSMITH_API_KEY")
        if langsmith_key:
            os.environ["LANGCHAIN_API_KEY"] = langsmith_key
    if os.environ.get("LANGCHAIN_PROJECT") is None:
        langsmith_project = os.environ.get("LANGSMITH_PROJECT")
        if langsmith_project:
            os.environ["LANGCHAIN_PROJECT"] = langsmith_project
    if os.environ.get("LANGCHAIN_TRACING_V2") is None:
        langsmith_tracing = os.environ.get("LANGSMITH_TRACING")
        if langsmith_tracing:
            os.environ["LANGCHAIN_TRACING_V2"] = langsmith_tracing


_ensure_langsmith_env_aliases()

# -----------------------------------------------------------------------------
# Constants / Prompts
# -----------------------------------------------------------------------------
AgentKind = Literal["planner", "coach", "analysis"]

SAFETY_SYSTEM_PROMPT = """당신은 사용자에게 안전하고 책임감 있게 답하는 AI입니다.
반드시 한국어로 답변하세요.

안전/톤 가이드라인:
- 의료 조언, 진단, 치료법 제시는 금지합니다. 건강 관련 내용은 일반적인 생활 가이드 수준으로만 안내합니다.
- 체중/체형 비교, 죄책감 유발, 비난/강요 표현을 사용하지 않습니다.
- 극단적 다이어트, 위험한 운동/식이 습관을 권하지 않습니다.
- 사용자가 우울감/섭식장애/자해 등 민감 신호를 언급하면 따뜻하게 공감하고 전문 도움을 권합니다.
- 사용자의 현재 상황과 컨디션을 존중하고, 부담을 낮추는 현실적인 제안을 우선합니다.
"""

ORCHESTRATOR_SYSTEM_PROMPT = """당신은 사용자의 요청을 분석하여 가장 적절한 전문 에이전트를 선택하는 오케스트레이터입니다.

다음 세 가지 에이전트 중 하나를 선택하세요:
1. planner: 계획 수립, 전략 수립, 로드맵 작성 등 계획 관련 요청
2. coach: 코칭, 가이드, 조언, 학습/성장 지원 등 코칭 관련 요청
3. analysis: 데이터 분석, 문제 분석, 평가, 검토 등 분석 관련 요청

사용자 요청을 분석한 후, 반드시 다음 형식으로만 응답하세요:
- "planner"
- "coach"
- "analysis"

다른 설명이나 추가 텍스트 없이 위 세 가지 중 하나만 응답하세요.
"""

# -----------------------------------------------------------------------------
# In-memory personalization store (MVP) - 멀티워커/멀티프로세스에서는 불안정
# -----------------------------------------------------------------------------
_USER_STORE: Dict[str, Dict[str, Any]] = {}
_USER_STORE_LOCK = threading.Lock()
_MAX_USER_EVENTS = 30
_USER_TTL_SECONDS = 60 * 60 * 24 * 14  # 14 days


def _now_ts() -> float:
    return time.time()


def _prune_expired_user(user_id: str) -> None:
    with _USER_STORE_LOCK:
        record = _USER_STORE.get(user_id)
        if not record:
            return
        if _now_ts() - record.get("updated_at", 0) > _USER_TTL_SECONDS:
            _USER_STORE.pop(user_id, None)


def _ensure_user_record(user_id: str) -> Dict[str, Any]:
    _prune_expired_user(user_id)
    with _USER_STORE_LOCK:
        record = _USER_STORE.get(user_id)
        if record is None:
            record = {
                "preferences": {},
                "events": [],
                "stats": {"success": 0, "fail": 0},
                "updated_at": _now_ts(),
            }
            _USER_STORE[user_id] = record
        return record


def update_user_context(user_id: str, payload: Optional[Dict[str, Any]]) -> None:
    """개인화용 유저 컨텍스트를 인메모리에 업데이트(MVP)."""
    if not user_id:
        return
    record = _ensure_user_record(user_id)
    with _USER_STORE_LOCK:
        if not payload:
            record["updated_at"] = _now_ts()
            return

        preferences = payload.get("preferences") or {}
        if isinstance(preferences, dict):
            record["preferences"].update(preferences)

        event = payload.get("event")
        if isinstance(event, dict):
            event = {**event, "ts": _now_ts()}
            record["events"].append(event)
            record["events"] = record["events"][-_MAX_USER_EVENTS:]

            if event.get("mission_result") == "success":
                record["stats"]["success"] += 1
            elif event.get("mission_result") == "fail":
                record["stats"]["fail"] += 1

        record["updated_at"] = _now_ts()


def summarize_user_context(user_id: Optional[str]) -> str:
    """유저 컨텍스트를 요약하여 프롬프트에 주입."""
    if not user_id:
        return ""
    _prune_expired_user(user_id)
    with _USER_STORE_LOCK:
        record = _USER_STORE.get(user_id)
        if not record:
            return ""

        prefs = record.get("preferences", {})
        events = list(record.get("events", []))
        stats = dict(record.get("stats", {}))

    recent = events[-3:] if events else []
    recent_strs: List[str] = []
    for e in recent:
        parts: List[str] = []
        if e.get("mission"):
            parts.append(f"미션:{e.get('mission')}")
        if e.get("mission_result"):
            parts.append(f"결과:{e.get('mission_result')}")
        if e.get("fail_reason"):
            parts.append(f"실패이유:{e.get('fail_reason')}")
        if e.get("condition"):
            parts.append(f"컨디션:{e.get('condition')}")
        if e.get("schedule"):
            parts.append(f"일정:{e.get('schedule')}")
        if parts:
            recent_strs.append(" / ".join(parts))

    prefs_str = ", ".join([f"{k}:{v}" for k, v in prefs.items()]) if prefs else "없음"
    recent_str = " | ".join(recent_strs) if recent_strs else "없음"
    total_success = stats.get("success", 0)
    total_fail = stats.get("fail", 0)

    return (
        "유저 컨텍스트 요약:\n"
        f"- 선호/기본값: {prefs_str}\n"
        f"- 최근 기록(최대 3건): {recent_str}\n"
        f"- 누적 통계: 성공 {total_success}회 / 실패 {total_fail}회\n"
        "이 정보를 고려해 개인화된 답변을 제공하세요."
    )


def build_context_message(user_context_summary: str) -> Optional[SystemMessage]:
    if not user_context_summary:
        return None
    return SystemMessage(content=user_context_summary)


# -----------------------------------------------------------------------------
# Tracing: LangSmith callbacks
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class TraceContext:
    request_id: str
    user_id: Optional[str]
    thread_id: str
    app_env: str
    git_sha: str


def _get_env_first(*keys: str) -> Optional[str]:
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None


def _parse_sample_rate(app_env: str) -> float:
    raw = os.environ.get("TRACE_SAMPLE_RATE")
    if raw:
        try:
            rate = float(raw)
            return max(0.0, min(1.0, rate))
        except ValueError:
            pass
    return 0.2 if app_env == "prod" else 1.0


def should_trace_request(app_env: str, user_context_summary: str) -> bool:
    allow_pii = os.environ.get("TRACE_ALLOW_PII", "").lower() in {"true", "1", "yes"}
    if user_context_summary and not allow_pii:
        return False
    return random.random() < _parse_sample_rate(app_env)


def _langsmith_tracing_enabled() -> bool:
    return _get_env_first("LANGCHAIN_TRACING_V2", "LANGSMITH_TRACING") in {"true", "1", "yes", "True"}


def _langsmith_project() -> Optional[str]:
    return _get_env_first("LANGCHAIN_PROJECT", "LANGSMITH_PROJECT")


_CACHED_LANGSMITH_TRACER: Optional[object] = None


def get_langsmith_tracer() -> Optional[object]:
    global _CACHED_LANGSMITH_TRACER
    if _CACHED_LANGSMITH_TRACER is not None:
        return _CACHED_LANGSMITH_TRACER
    if not _langsmith_tracing_enabled() or LangChainTracer is None:
        return None
    project = _langsmith_project() or "omteam"
    try:
        _CACHED_LANGSMITH_TRACER = LangChainTracer(project_name=project)
    except Exception:
        _CACHED_LANGSMITH_TRACER = None
    return _CACHED_LANGSMITH_TRACER


def build_callbacks(trace_enabled: bool) -> List[object]:
    if not trace_enabled:
        return []
    tracer = get_langsmith_tracer()
    return [tracer] if tracer else []


def node_event(
    name: str,
    stage: Literal["start", "end", "error"],
    tc: TraceContext,
    extra: Dict[str, Any],
    trace_enabled: bool,
) -> None:
    """LangSmith는 노드 이벤트를 별도로 기록하지 않음."""
    return


# -----------------------------------------------------------------------------
# LLM (cached)
# -----------------------------------------------------------------------------
_CACHED_LLM: Optional[ChatUpstage] = None

def get_llm() -> ChatUpstage:
    global _CACHED_LLM
    if _CACHED_LLM is None:
        api_key = os.environ.get("UPSTAGE_API_KEY")
        if not api_key:
            raise RuntimeError("UPSTAGE_API_KEY 환경 변수가 필요합니다.")

        _CACHED_LLM = ChatUpstage(
            model="solar-pro2",
            upstage_api_key=api_key,
        )
    return _CACHED_LLM


# -----------------------------------------------------------------------------
# State / Validation
# -----------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: List[BaseMessage]
    user_request: str
    user_id: Optional[str]
    user_context_summary: str
    selected_agent: Optional[AgentKind]
    agent_response: str
    task_completed: bool

    # tracing / correlation
    request_id: str
    thread_id: str
    app_env: str
    git_sha: str
    trace_enabled: bool


def validate_user_request(user_request: str) -> Optional[str]:
    if not user_request or not user_request.strip():
        return "요청 내용이 비어 있어요. 구체적인 질문이나 요청을 입력해 주세요."
    return None


def build_error_response() -> str:
    return "지금은 응답을 생성하는 데 문제가 발생했어요. 잠시 후 다시 시도해 주세요."


def _extract_last_human(messages: List[BaseMessage]) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def _normalize_agent_choice(raw: str, fallback_request: str) -> AgentKind:
    s = (raw or "").strip().lower()
    if "planner" in s:
        return "planner"
    if "coach" in s:
        return "coach"
    if "analysis" in s:
        return "analysis"

    # fallback heuristics
    r = (fallback_request or "").lower()
    if any(k in r for k in ["계획", "전략", "로드맵", "plan", "strategy"]):
        return "planner"
    if any(k in r for k in ["코칭", "가이드", "조언", "coach", "guide", "advice"]):
        return "coach"
    return "analysis"


def _trace_context_from_state(state: AgentState) -> TraceContext:
    return TraceContext(
        request_id=state["request_id"],
        user_id=state.get("user_id"),
        thread_id=state["thread_id"],
        app_env=state["app_env"],
        git_sha=state["git_sha"],
    )


def _llm_config_from_state(state: AgentState, node_name: str) -> RunnableConfig:
    """
    핵심: LangGraph 실행과 LLM 호출을 같은 correlation key로 묶기 위한 config.
    - callbacks: LangSmith (LLM tracing)
    - tags/metadata: 노드 단위 관측용 필터링 키
    """
    return cast(
        RunnableConfig,
        {
            "callbacks": build_callbacks(state["trace_enabled"]),
            "tags": [state["app_env"], f"node:{node_name}"],
            "metadata": {
                "request_id": state["request_id"],
                "thread_id": state["thread_id"],
                "user_id": state.get("user_id"),
                "git_sha": state["git_sha"],
                "node": node_name,
            },
            # LangGraph에서 configurable을 쓰면 thread_id 같은 값이 sub-run에도 전달되기 쉬움
            "configurable": {
                "thread_id": state["thread_id"],
                "request_id": state["request_id"],
                "user_id": state.get("user_id"),
            },
        },
    )

# -----------------------------------------------------------------------------
# Nodes
# -----------------------------------------------------------------------------
def orchestrator_node(state: AgentState) -> AgentState:
    user_request = state.get("user_request") or _extract_last_human(state["messages"])
    tc = _trace_context_from_state(state)

    node_event("orchestrator", "start", tc, {"user_request_len": len(user_request)}, state["trace_enabled"])

    messages: List[BaseMessage] = [SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT)]
    ctx_msg = build_context_message(state.get("user_context_summary", ""))
    if ctx_msg:
        messages.append(ctx_msg)

    messages.append(
        HumanMessage(
            content=(
                f"사용자 요청: {user_request}\n\n"
                "이 요청에 가장 적절한 에이전트를 선택하세요 (planner/coach/analysis 중 하나만):"
            )
        )
    )

    try:
        resp = get_llm().invoke(messages, config=_llm_config_from_state(state, "orchestrator"))
        selected = _normalize_agent_choice(resp.content, user_request)
    except Exception as exc:
        # tracing은 LangSmith가 수행하므로, 여기서는 상태만 안정적으로 처리
        selected = _normalize_agent_choice("", user_request)
        node_event("orchestrator", "error", tc, {"error": type(exc).__name__}, state["trace_enabled"])

    node_event("orchestrator", "end", tc, {"selected_agent": selected}, state["trace_enabled"])

    return {
        **state,
        "user_request": user_request,
        "selected_agent": selected,
        "messages": state["messages"] + [AIMessage(content=f"[Orchestrator] 선택된 에이전트: {selected}")],
    }


def _agent_node_common(
    *,
    state: AgentState,
    node_name: AgentKind,
    system_prompt: str,
) -> AgentState:
    user_request = state.get("user_request") or _extract_last_human(state["messages"])
    tc = _trace_context_from_state(state)

    node_event(node_name, "start", tc, {"user_request_len": len(user_request)}, state["trace_enabled"])

    messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]
    ctx_msg = build_context_message(state.get("user_context_summary", ""))
    if ctx_msg:
        messages.append(ctx_msg)
    messages.append(HumanMessage(content=user_request))

    try:
        resp = get_llm().invoke(messages, config=_llm_config_from_state(state, node_name))
        agent_response = resp.content
        node_event(node_name, "end", tc, {"status": "success"}, state["trace_enabled"])
    except Exception as exc:
        agent_response = build_error_response()
        node_event(node_name, "error", tc, {"error": type(exc).__name__}, state["trace_enabled"])

    return {
        **state,
        "agent_response": agent_response,
        "task_completed": True,
        "messages": state["messages"] + [AIMessage(content=f"[{node_name.upper()}]\n{agent_response}")],
    }


def planner_agent_node(state: AgentState) -> AgentState:
    system_prompt = f"""{SAFETY_SYSTEM_PROMPT}
당신은 전문 계획 수립 에이전트(Planner Agent)입니다.
- 명확하고 구체적인 단계별 계획 수립
- 현실적인 타임라인 제시
- 리소스 및 우선순위 고려
- 실행 가능한 액션 아이템 제공

사용자의 요청에 대해 상세하고 실용적인 계획을 제공하세요.
"""
    return _agent_node_common(state=state, node_name="planner", system_prompt=system_prompt)


def coach_agent_node(state: AgentState) -> AgentState:
    system_prompt = f"""{SAFETY_SYSTEM_PROMPT}
당신은 전문 코칭 에이전트(Coach Agent)입니다.
- 실용적이고 실행 가능한 조언
- 단계별 가이드 제공
- 학습/성장 지원 중심
- 과장된 격려보다는 현실적 코칭

사용자의 요청에 대해 도움이 되는 코칭과 가이드를 제공하세요.
"""
    return _agent_node_common(state=state, node_name="coach", system_prompt=system_prompt)


def analysis_agent_node(state: AgentState) -> AgentState:
    system_prompt = f"""{SAFETY_SYSTEM_PROMPT}
당신은 전문 분석 에이전트(Analysis Agent)입니다.
- 객관적이고 체계적인 분석
- 근본 원인 파악
- 명확한 결론 및 권장사항 제시

사용자의 요청에 대해 깊이 있는 분석과 인사이트를 제공하세요.
"""
    return _agent_node_common(state=state, node_name="analysis", system_prompt=system_prompt)


def route_to_agent(state: AgentState) -> AgentKind:
    selected = state.get("selected_agent")
    if selected in ("planner", "coach", "analysis"):
        return cast(AgentKind, selected)
    return "analysis"


# -----------------------------------------------------------------------------
# Graph (cached)
# -----------------------------------------------------------------------------
_CACHED_GRAPH = None

def create_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("planner", planner_agent_node)
    workflow.add_node("coach", coach_agent_node)
    workflow.add_node("analysis", analysis_agent_node)

    workflow.set_entry_point("orchestrator")
    workflow.add_conditional_edges(
        "orchestrator",
        route_to_agent,
        {
            "planner": "planner",
            "coach": "coach",
            "analysis": "analysis",
        },
    )
    workflow.add_edge("planner", END)
    workflow.add_edge("coach", END)
    workflow.add_edge("analysis", END)
    return workflow.compile()


def get_agent_graph():
    global _CACHED_GRAPH
    if _CACHED_GRAPH is None:
        _CACHED_GRAPH = create_agent_graph()
    return _CACHED_GRAPH


# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------
def run_agent_system(
    user_request: str,
    user_id: Optional[str] = None,
    user_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    validation_error = validate_user_request(user_request)
    if validation_error:
        return {
            "messages": [],
            "user_request": user_request,
            "selected_agent": None,
            "agent_response": validation_error,
            "task_completed": False,
        }

    # 개인화 업데이트(MVP)
    if user_id:
        update_user_context(user_id, user_payload)

    request_id = str(uuid.uuid4())
    thread_id = user_id or str(uuid.uuid4())  # 유저가 없으면 임시 thread
    app_env = os.environ.get("APP_ENV", "dev")
    git_sha = os.environ.get("GIT_SHA", "unknown")

    user_context_summary = summarize_user_context(user_id)
    trace_enabled = should_trace_request(app_env, user_context_summary)

    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_request)],
        "user_request": user_request,
        "user_id": user_id,
        "user_context_summary": user_context_summary,
        "selected_agent": None,
        "agent_response": "",
        "task_completed": False,
        "request_id": request_id,
        "thread_id": thread_id,
        "app_env": app_env,
        "git_sha": git_sha,
        "trace_enabled": trace_enabled,
    }

    graph = get_agent_graph()

    # 핵심: graph.invoke 레벨에도 callbacks/metadata 주입해서 "그래프 전체"를 하나의 상관관계로 묶음
    graph_config: RunnableConfig = cast(
        RunnableConfig,
        {
            "callbacks": build_callbacks(trace_enabled),
            "tags": [app_env, "graph:agent_orchestration"],
            "metadata": {
                "request_id": request_id,
                "thread_id": thread_id,
                "user_id": user_id,
                "git_sha": git_sha,
            },
            "configurable": {
                "thread_id": thread_id,
                "request_id": request_id,
                "user_id": user_id,
            },
        },
    )

    result = graph.invoke(initial_state, config=graph_config)
    return result


# -----------------------------------------------------------------------------
# Local test
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    test_request = "살뺴고 싶어. 어떻게 하면 6개월 내에 내가 원하는 목표까지 포기하지 않고 건강하게 체중을 감량할 수 있을까?"
    print(f"사용자 요청: {test_request}\n")

    result = run_agent_system(test_request, user_id="demo_user_1")

    print(f"\n선택된 에이전트: {result['selected_agent']}")
    print(f"\n에이전트 응답:\n{result['agent_response']}")
