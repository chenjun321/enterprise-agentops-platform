from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.tools.base import BaseTool, ToolResult


class SQLSelectTool(BaseTool):
    name = "SQLSelectTool"
    description = "Run safe read-only SQL. Only SELECT statements are allowed."

    def __init__(self, db: Session):
        self.db = db

    def run(self, payload: Dict[str, Any]) -> ToolResult:
        sql = (payload.get("sql") or "").strip()
        if not sql.lower().startswith("select"):
            return ToolResult(ok=False, error="only_select_sql_allowed")
        if any(token in sql.lower() for token in ["insert ", "update ", "delete ", "drop ", "alter "]):
            return ToolResult(ok=False, error="unsafe_sql_detected")
        if "limit" not in sql.lower():
            sql = f"{sql} LIMIT 100"
        rows = self.db.execute(text(sql)).mappings().all()
        return ToolResult(ok=True, data={"rows": [dict(row) for row in rows]})

