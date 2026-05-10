from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import MemoryEvent, UserMemory


class MemoryStore:
    """Controlled long-memory store for user preferences."""

    def __init__(self, db: Session):
        self.db = db

    def list_memories(
        self,
        employee_id: str,
        memory_types: Optional[List[str]] = None,
        limit: int = 8,
    ) -> List[Dict]:
        stmt = select(UserMemory).where(
            UserMemory.employee_id == employee_id,
            UserMemory.status == "active",
        )
        if memory_types:
            stmt = stmt.where(UserMemory.memory_type.in_(memory_types))
        stmt = stmt.order_by(UserMemory.updated_at.desc()).limit(limit)
        rows = self.db.execute(stmt).scalars().all()

        now = datetime.utcnow()
        result = []
        for row in rows:
            row.last_used_at = now
            self.db.add(
                MemoryEvent(
                    memory_id=row.id,
                    employee_id=employee_id,
                    event_type="used",
                    reason="retrieved_for_agent_context",
                )
            )
            result.append(
                {
                    "id": row.id,
                    "memory_type": row.memory_type,
                    "content": row.content,
                    "source": row.source,
                    "confidence": row.confidence,
                    "updated_at": row.updated_at.isoformat(),
                }
            )
        self.db.commit()
        return result

    def create_memory(
        self,
        employee_id: str,
        memory_type: str,
        content: str,
        source: str = "explicit_user_request",
        confidence: float = 1.0,
        status: str = "active",
    ) -> Dict:
        memory = UserMemory(
            employee_id=employee_id,
            memory_type=memory_type,
            content=content,
            source=source,
            confidence=confidence,
            status=status,
        )
        self.db.add(memory)
        self.db.flush()
        self.db.add(
            MemoryEvent(
                memory_id=memory.id,
                employee_id=employee_id,
                event_type="created",
                new_content=content,
                reason=source,
            )
        )
        self.db.commit()
        self.db.refresh(memory)
        return {
            "id": memory.id,
            "memory_type": memory.memory_type,
            "content": memory.content,
            "source": memory.source,
            "confidence": memory.confidence,
            "status": memory.status,
        }

    def infer_memory_candidate(self, employee_id: str, message: str) -> Optional[Dict]:
        lowered = message.lower()
        explicit_markers = ["记住", "以后", "默认", "我喜欢", "偏好"]
        if not any(marker in message for marker in explicit_markers):
            return None

        memory_type = "communication_preference"
        if "活动" in message or "指标" in message or "留存" in message:
            memory_type = "analysis_preference"
        elif "话术" in message or "销售" in message:
            memory_type = "sales_preference"
        elif "客服" in message or "回复" in message:
            memory_type = "support_response_preference"
        elif "report" in lowered or "报告" in message:
            memory_type = "report_format_preference"

        return {
            "employee_id": employee_id,
            "memory_type": memory_type,
            "content": message,
            "source": "explicit_user_request",
            "confidence": 0.95,
            "status": "active",
        }

