import json
from typing import Dict

from sqlalchemy.orm import Session

from app.core.state import AgentState
from app.db.models import AuditEvent


class AuditLogger:
    def __init__(self, db: Session):
        self.db = db

    def record(self, state: AgentState, event_type: str, detail: Dict) -> None:
        state.add_audit(event_type, detail)
        self.db.add(
            AuditEvent(
                session_id=state.session_id,
                employee_id=state.employee_id,
                event_type=event_type,
                detail=json.dumps(detail, ensure_ascii=False),
            )
        )
        self.db.commit()

