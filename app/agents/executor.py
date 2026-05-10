from typing import Any, Dict

from app.core.state import AgentState
from app.security.policies import can_use_tool
from app.tools.base import ToolRegistry


class PlanExecutor:
    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(self, state: AgentState) -> AgentState:
        if not state.plan:
            raise ValueError("state.plan is required")

        if state.plan.needs_user_input:
            state.final_response = {
                "type": "needs_user_input",
                "message": "还需要补充信息才能继续执行。",
                "missing_fields": state.plan.missing_fields,
            }
            return state

        for step in state.plan.steps:
            if step.type != "tool_call":
                continue
            if not step.tool:
                continue
            if not can_use_tool(state.role, step.tool):
                state.step_results[step.step_id] = {"ok": False, "error": "permission_denied"}
                state.add_audit("tool_denied", {"step_id": step.step_id, "tool": step.tool})
                if step.required:
                    break
                continue

            payload = self._resolve_payload(step.input, state)
            tool = self.registry.get(step.tool)
            result = tool.run(payload)
            state.step_results[step.step_id] = result.model_dump()
            state.add_audit(
                "tool_called",
                {"step_id": step.step_id, "tool": step.tool, "ok": result.ok, "error": result.error},
            )
            if result.ok:
                state.evidence.append({"step_id": step.step_id, "tool": step.tool, "data": result.data})
            elif step.required:
                break
        return state

    def _resolve_payload(self, payload: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        resolved = dict(payload)
        order_result = state.step_results.get("order_state", {}).get("data", {})
        orders = order_result.get("orders") or []
        if orders:
            first = orders[0]
            if not resolved.get("order_id"):
                resolved["order_id"] = first.get("id")
            if not resolved.get("trace_id"):
                resolved["trace_id"] = first.get("trace_id")
            if not resolved.get("order_no"):
                resolved["order_no"] = first.get("order_no")
        return resolved

