import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ConversationThread, ThreadLock, ThreadMessage


class ThreadBusyError(RuntimeError):
    pass


class ThreadStore:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def resolve_thread_id(self, provided: Optional[str]) -> str:
        return provided or f"thread_{uuid4().hex[:12]}"

    def ensure_thread(self, *, thread_id: str, actor_id: str, actor_type: str, channel: str) -> ConversationThread:
        thread = self.db.get(ConversationThread, thread_id)
        if thread:
            thread.updated_at = datetime.utcnow()
            return thread
        thread = ConversationThread(
            thread_id=thread_id,
            actor_id=actor_id,
            actor_type=actor_type,
            channel=channel,
        )
        self.db.add(thread)
        self.db.flush()
        return thread

    @contextmanager
    def lock(self, thread_id: str, owner_id: str) -> Iterator[None]:
        if not self.acquire_lock(thread_id, owner_id):
            raise ThreadBusyError(f"thread is already processing: {thread_id}")
        try:
            yield
        finally:
            self.release_lock(thread_id, owner_id)

    def acquire_lock(self, thread_id: str, owner_id: str) -> bool:
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.settings.thread_lock_ttl_seconds)
        self._delete_expired_locks(now)
        try:
            self.db.add(ThreadLock(thread_id=thread_id, owner_id=owner_id, acquired_at=now, expires_at=expires_at))
            self.db.flush()
            self.db.commit()
            return True
        except IntegrityError:
            self.db.rollback()

        stmt = (
            update(ThreadLock)
            .where(ThreadLock.thread_id == thread_id, ThreadLock.expires_at < now)
            .values(owner_id=owner_id, acquired_at=now, expires_at=expires_at)
        )
        result = self.db.execute(stmt)
        self.db.flush()
        acquired = bool(result.rowcount)
        if acquired:
            self.db.commit()
        return acquired

    def release_lock(self, thread_id: str, owner_id: str) -> None:
        self.db.execute(delete(ThreadLock).where(ThreadLock.thread_id == thread_id, ThreadLock.owner_id == owner_id))
        self.db.flush()
        self.db.commit()

    def append_message(self, *, thread_id: str, role: str, content: str, payload: Optional[Dict[str, Any]] = None) -> None:
        self.db.add(
            ThreadMessage(
                thread_id=thread_id,
                role=role,
                content=content,
                payload=json.dumps(payload or {}, ensure_ascii=False, default=str),
            )
        )
        thread = self.db.get(ConversationThread, thread_id)
        if thread:
            thread.message_count += 1
            thread.updated_at = datetime.utcnow()
            thread.summary = self._compact_summary(thread.summary, role, content)
        self.db.flush()

    def recent_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        stmt = (
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == thread_id)
            .order_by(ThreadMessage.created_at.desc(), ThreadMessage.id.desc())
            .limit(self.settings.thread_history_limit)
        )
        rows = list(reversed(self.db.execute(stmt).scalars().all()))
        return [
            {
                "role": row.role,
                "content": row.content,
                "payload": json.loads(row.payload or "{}"),
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    def _delete_expired_locks(self, now: datetime) -> None:
        self.db.execute(delete(ThreadLock).where(ThreadLock.expires_at < now))
        self.db.flush()

    def _compact_summary(self, current: str, role: str, content: str) -> str:
        line = f"{role}: {content.strip()}"
        if len(line) > 240:
            line = line[:237] + "..."
        combined = "\n".join([item for item in [current, line] if item])
        return combined[-2000:]
