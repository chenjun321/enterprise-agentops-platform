import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import UsageEvent


@dataclass(frozen=True)
class UsageDecision:
    allowed: bool
    reason: str = ""
    estimated_input_tokens: int = 0
    remaining_day_tokens: int = 0


class UsageGuard:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def check_and_record(
        self,
        *,
        actor_id: str,
        actor_type: str,
        route: str,
        ip_address: str,
        message: str,
        context: Dict[str, Any],
    ) -> UsageDecision:
        estimated_tokens = estimate_tokens(message, context)
        message_hash = stable_message_hash(message, context)
        if not self.settings.usage_guard_enabled:
            self._record(actor_id, actor_type, route, ip_address, message_hash, estimated_tokens, "accepted", "")
            return UsageDecision(True, estimated_input_tokens=estimated_tokens)

        reason = self._deny_reason(actor_id, route, ip_address, message_hash, estimated_tokens)
        status = "denied" if reason else "accepted"
        self._record(actor_id, actor_type, route, ip_address, message_hash, estimated_tokens, status, reason)
        self.db.commit()
        used_today = self._token_sum(actor_id, datetime.utcnow() - timedelta(days=1))
        remaining = max(self.settings.usage_day_token_limit - used_today, 0)
        return UsageDecision(not reason, reason, estimated_tokens, remaining)

    def _deny_reason(
        self,
        actor_id: str,
        route: str,
        ip_address: str,
        message_hash: str,
        estimated_tokens: int,
    ) -> str:
        now = datetime.utcnow()
        if estimated_tokens > self.settings.usage_single_input_token_limit:
            return "single_input_token_limit_exceeded"
        if self._event_count(actor_id, route, ip_address, now - timedelta(minutes=1)) >= self.settings.usage_minute_request_limit:
            return "minute_request_limit_exceeded"
        if self._event_count(actor_id, route, ip_address, now - timedelta(hours=1)) >= self.settings.usage_hour_request_limit:
            return "hour_request_limit_exceeded"
        if self._token_sum(actor_id, now - timedelta(days=1)) + estimated_tokens > self.settings.usage_day_token_limit:
            return "day_token_budget_exceeded"
        duplicate_window = now - timedelta(seconds=self.settings.usage_duplicate_window_seconds)
        if self._duplicate_count(actor_id, message_hash, duplicate_window) >= self.settings.usage_duplicate_limit:
            return "duplicate_message_limit_exceeded"
        return ""

    def _event_count(self, actor_id: str, route: str, ip_address: str, since: datetime) -> int:
        stmt = select(func.count()).select_from(UsageEvent).where(
            UsageEvent.created_at >= since,
            UsageEvent.status == "accepted",
            (UsageEvent.actor_id == actor_id) | (UsageEvent.ip_address == ip_address),
            UsageEvent.route == route,
        )
        return int(self.db.execute(stmt).scalar() or 0)

    def _duplicate_count(self, actor_id: str, message_hash: str, since: datetime) -> int:
        stmt = select(func.count()).select_from(UsageEvent).where(
            UsageEvent.created_at >= since,
            UsageEvent.status == "accepted",
            UsageEvent.actor_id == actor_id,
            UsageEvent.message_hash == message_hash,
        )
        return int(self.db.execute(stmt).scalar() or 0)

    def _token_sum(self, actor_id: str, since: datetime) -> int:
        stmt = select(func.sum(UsageEvent.estimated_input_tokens + UsageEvent.estimated_output_tokens)).where(
            UsageEvent.created_at >= since,
            UsageEvent.status == "accepted",
            UsageEvent.actor_id == actor_id,
        )
        return int(self.db.execute(stmt).scalar() or 0)

    def _record(
        self,
        actor_id: str,
        actor_type: str,
        route: str,
        ip_address: str,
        message_hash: str,
        estimated_tokens: int,
        status: str,
        reason: str,
    ) -> None:
        self.db.add(
            UsageEvent(
                actor_id=actor_id,
                actor_type=actor_type,
                route=route,
                ip_address=ip_address,
                message_hash=message_hash,
                estimated_input_tokens=estimated_tokens,
                status=status,
                reason=reason,
            )
        )


def estimate_tokens(message: str, context: Dict[str, Any]) -> int:
    payload = message + "\n" + json.dumps(context, ensure_ascii=False, sort_keys=True)
    ascii_chars = sum(1 for char in payload if ord(char) < 128)
    non_ascii_chars = len(payload) - ascii_chars
    return max(1, (ascii_chars + 3) // 4 + non_ascii_chars)


def stable_message_hash(message: str, context: Dict[str, Any]) -> str:
    normalized = json.dumps({"message": message.strip(), "context": context}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
