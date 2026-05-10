from typing import Any, Dict, List


ROLE_TOOL_POLICY = {
    "sales": {"CRMTool", "KnowledgeSearchTool", "ExternalProfileTool"},
    "marketing": {"MarketingDataTool", "KnowledgeSearchTool"},
    "support": {
        "OrderQueryTool",
        "PaymentQueryTool",
        "LogSearchTool",
        "KnowledgeSearchTool",
        "CodeSearchTool",
    },
    "engineer": {
        "OrderQueryTool",
        "PaymentQueryTool",
        "LogSearchTool",
        "KnowledgeSearchTool",
        "CodeSearchTool",
        "SQLSelectTool",
    },
    "admin": {"*"},
}


def can_use_tool(role: str, tool_name: str) -> bool:
    allowed = ROLE_TOOL_POLICY.get(role, set())
    return "*" in allowed or tool_name in allowed


def redact_for_role(role: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if role in {"engineer", "admin"}:
        return payload

    redacted = dict(payload)
    sensitive_keys = {"raw_log", "code_snippet", "provider_trade_no", "email"}
    for key in sensitive_keys:
        if key in redacted:
            redacted[key] = "[redacted]"

    if "related_files" in redacted and role == "support":
        redacted["related_files"] = [
            {"file": item.get("file"), "function": item.get("function")}
            for item in redacted.get("related_files", [])
        ]
    return redacted


def validate_plan_steps(role: str, steps: List[Dict[str, Any]]) -> List[str]:
    errors = []
    for step in steps:
        tool = step.get("tool")
        if tool and not can_use_tool(role, tool):
            errors.append(f"role={role} cannot use tool={tool}")
    return errors

