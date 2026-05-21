import json
from dataclasses import dataclass
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.state import AgentState
from app.db.models import AgentReflection


SENSITIVE_KEYS = {"raw_log", "provider_trade_no", "password", "secret", "token", "api_key"}
SENSITIVE_TEXT_MARKERS = ["sk-", "secretKey", "password=", "provider_trade_no"]


@dataclass(frozen=True)
class ReflectionCheck:
    name: str
    passed: bool
    severity: str = "low"
    detail: str = ""


@dataclass(frozen=True)
class ReflectionResult:
    passed: bool
    risk_level: str
    rewrite_required: bool
    checks: List[ReflectionCheck]
    final_answer: Dict[str, Any]


class ReflectionService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def reflect(self, state: AgentState, answer: Dict[str, Any]) -> ReflectionResult:
        if not self.settings.reflection_enabled:
            result = ReflectionResult(True, "low", False, [], answer)
            self._record(state, result)
            return result

        checks = [
            self._check_answer_completeness(answer),
            self._check_sensitive_info(answer),
            self._check_tool_evidence_alignment(state),
            self._check_customer_qa_shape(state, answer),
            self._check_bug_ticket_escalation(state, answer),
        ]
        rewrite_required = any(check.name == "sensitive_info_leak" and not check.passed for check in checks)
        final_answer = self._sanitize_answer(answer) if rewrite_required else answer
        passed = all(check.passed for check in checks)
        risk_level = self._risk_level(checks)
        result = ReflectionResult(passed, risk_level, rewrite_required, checks, final_answer)
        self._record(state, result)
        return result

    def _check_answer_completeness(self, answer: Dict[str, Any]) -> ReflectionCheck:
        if not answer:
            return ReflectionCheck("answer_completeness", False, "high", "empty answer")
        if answer.get("type") == "needs_user_input":
            return ReflectionCheck("answer_completeness", True, "low", "asking for missing fields")
        has_user_reply = bool(answer.get("user_reply"))
        has_business_output = any(key in answer for key in ["summary", "pitch", "sales_strategy", "campaign"])
        if has_user_reply or has_business_output:
            return ReflectionCheck("answer_completeness", True)
        return ReflectionCheck("answer_completeness", False, "medium", "answer lacks user-facing content")

    def _check_sensitive_info(self, answer: Dict[str, Any]) -> ReflectionCheck:
        payload = json.dumps(answer, ensure_ascii=False, default=str)
        leaked_markers = [marker for marker in SENSITIVE_TEXT_MARKERS if marker in payload]
        leaked_keys = self._find_sensitive_keys(answer)
        if leaked_markers or leaked_keys:
            detail = f"markers={leaked_markers}, keys={sorted(leaked_keys)}"
            return ReflectionCheck("sensitive_info_leak", False, "high", detail)
        return ReflectionCheck("sensitive_info_leak", True)

    def _check_tool_evidence_alignment(self, state: AgentState) -> ReflectionCheck:
        if not state.plan or state.final_response and state.final_response.get("type") == "execution_error":
            return ReflectionCheck("tool_evidence_alignment", True)
        missing = []
        failed = []
        for step in state.plan.steps:
            if step.type != "tool_call" or not step.required:
                continue
            result = state.step_results.get(step.step_id)
            if not result:
                missing.append(step.step_id)
            elif not result.get("ok"):
                failed.append(step.step_id)
        if missing or failed:
            return ReflectionCheck("tool_evidence_alignment", False, "high", f"missing={missing}, failed={failed}")
        return ReflectionCheck("tool_evidence_alignment", True)

    def _check_customer_qa_shape(self, state: AgentState, answer: Dict[str, Any]) -> ReflectionCheck:
        if state.intent != "customer_daily_question":
            return ReflectionCheck("customer_qa_response_shape", True)
        if answer.get("answer_type") != "operation_guide":
            return ReflectionCheck("customer_qa_response_shape", False, "medium", "daily QA should return operation_guide")
        steps = answer.get("steps") or []
        user_reply = answer.get("user_reply", "")
        if len(steps) < 1 or "1." not in user_reply:
            return ReflectionCheck("customer_qa_response_shape", False, "medium", "operation guide lacks numbered steps")
        return ReflectionCheck("customer_qa_response_shape", True)

    def _check_bug_ticket_escalation(self, state: AgentState, answer: Dict[str, Any]) -> ReflectionCheck:
        if state.intent != "bug_report_submission":
            return ReflectionCheck("bug_ticket_escalation", True)
        if answer.get("ticket"):
            return ReflectionCheck("bug_ticket_escalation", True)
        return ReflectionCheck("bug_ticket_escalation", False, "high", "bug report did not create ticket")

    def _sanitize_answer(self, answer: Dict[str, Any]) -> Dict[str, Any]:
        return self._sanitize_value(answer)

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            sanitized = {}
            for key, item in value.items():
                if key.lower() in SENSITIVE_KEYS:
                    sanitized[key] = "[redacted]"
                else:
                    sanitized[key] = self._sanitize_value(item)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, str):
            cleaned = value
            for marker in SENSITIVE_TEXT_MARKERS:
                if marker in cleaned:
                    cleaned = cleaned.replace(marker, "[redacted]")
            return cleaned
        return value

    def _find_sensitive_keys(self, value: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in SENSITIVE_KEYS:
                    found.add(key)
                found.update(self._find_sensitive_keys(item))
        elif isinstance(value, list):
            for item in value:
                found.update(self._find_sensitive_keys(item))
        return found

    def _risk_level(self, checks: List[ReflectionCheck]) -> str:
        severities = [check.severity for check in checks if not check.passed]
        if "high" in severities:
            return "high"
        if "medium" in severities:
            return "medium"
        return "low"

    def _record(self, state: AgentState, result: ReflectionResult) -> None:
        self.db.add(
            AgentReflection(
                session_id=state.session_id,
                employee_id=state.employee_id,
                target_agent=state.target_agent,
                intent=state.intent,
                passed=result.passed,
                risk_level=result.risk_level,
                rewrite_required=result.rewrite_required,
                checks=json.dumps([check.__dict__ for check in result.checks], ensure_ascii=False),
                notes="; ".join(check.detail for check in result.checks if check.detail),
            )
        )
        self.db.flush()
