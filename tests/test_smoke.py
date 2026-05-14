import os
from pathlib import Path
import json

import pytest

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_enterprise_agents.db"

from fastapi.testclient import TestClient

from app.agents.executor import PlanExecutor
from app.agents.planner import PlannerAgent
from app.agents.router import RouterAgent
from app.agents.scene_registry import get_customer_qa_scene
from app.core.state import AgentState, ExecutionPlan, PlanStep
from app.core.config import get_settings
from app.db.database import Base, SessionLocal, engine
from app.db.seed import seed_demo_data
from app.main import app, create_app
from app.tools.base import BaseTool, ToolRegistry


def setup_module():
    Path("test_enterprise_agents.db").unlink(missing_ok=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    Path("test_enterprise_agents.db").unlink(missing_ok=True)


def test_sales_route():
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "employee_id": "sales_001",
                "role": "sales",
                "message": "帮我生成销售话术",
                "context": {"customer_name": "张明", "company": "Acme Education"},
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["target_agent"] == "sales_agent"
    assert "pitch" in body["answer"]


def test_support_route():
    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={
                "employee_id": "support_001",
                "role": "support",
                "message": "用户支付成功但订单待支付，查一下原因",
                "context": {"order_no": "O20260505001"},
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert body["target_agent"] == "customer_qa_agent"
    assert "internal_summary" in body["answer"]


def test_router_and_planner_choose_payment_tool_combo():
    state = AgentState(
        employee_id="support_001",
        role="support",
        message="用户支付成功但订单待支付，查一下原因",
        context={"order_no": "O20260505001"},
    )
    RouterAgent().route(state)
    plan = PlannerAgent().plan(state)

    assert state.intent == "payment_issue_diagnosis"
    tool_names = [step.tool for step in plan.steps if step.type == "tool_call"]
    assert tool_names == [
        "OrderQueryTool",
        "PaymentQueryTool",
        "LogSearchTool",
        "KnowledgeSearchTool",
        "CodeSearchTool",
    ]


def test_router_and_planner_choose_login_tool_combo():
    state = AgentState(
        employee_id="support_001",
        role="support",
        message="用户登录失败，帮我排查一下签名问题",
        context={"user_id": "customer_003"},
    )
    RouterAgent().route(state)
    plan = PlannerAgent().plan(state)

    assert state.intent == "login_issue_diagnosis"
    tool_names = [step.tool for step in plan.steps if step.type == "tool_call"]
    assert tool_names == [
        "LogSearchTool",
        "KnowledgeSearchTool",
        "CodeSearchTool",
    ]


def test_customer_qa_scene_registry_drives_steps():
    scene = get_customer_qa_scene("payment_issue_diagnosis")

    assert scene["required_context_modes"] == ["order_or_trace"]
    assert [step["tool"] for step in scene["steps"] if step["type"] == "tool_call"] == [
        "OrderQueryTool",
        "PaymentQueryTool",
        "LogSearchTool",
        "KnowledgeSearchTool",
        "CodeSearchTool",
    ]


def test_production_requires_internal_api_key():
    previous_env = os.environ.get("APP_ENV")
    previous_key = os.environ.get("INTERNAL_API_KEY")
    previous_tokens = os.environ.get("AUTH_TOKENS_JSON")
    try:
        os.environ["APP_ENV"] = "production"
        os.environ.pop("INTERNAL_API_KEY", None)
        os.environ["AUTH_TOKENS_JSON"] = json.dumps({"token": {"employee_id": "support_001", "role": "support"}})
        get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="INTERNAL_API_KEY must be configured"):
            create_app()
    finally:
        if previous_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = previous_env
        if previous_key is None:
            os.environ.pop("INTERNAL_API_KEY", None)
        else:
            os.environ["INTERNAL_API_KEY"] = previous_key
        if previous_tokens is None:
            os.environ.pop("AUTH_TOKENS_JSON", None)
        else:
            os.environ["AUTH_TOKENS_JSON"] = previous_tokens
        get_settings.cache_clear()


def test_production_requires_bearer_tokens():
    previous_env = os.environ.get("APP_ENV")
    previous_key = os.environ.get("INTERNAL_API_KEY")
    previous_tokens = os.environ.get("AUTH_TOKENS_JSON")
    try:
        os.environ["APP_ENV"] = "production"
        os.environ["INTERNAL_API_KEY"] = "test-secret"
        os.environ["AUTH_TOKENS_JSON"] = "{}"
        get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="AUTH_TOKENS_JSON must configure at least one bearer token"):
            create_app()
    finally:
        if previous_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = previous_env
        if previous_key is None:
            os.environ.pop("INTERNAL_API_KEY", None)
        else:
            os.environ["INTERNAL_API_KEY"] = previous_key
        if previous_tokens is None:
            os.environ.pop("AUTH_TOKENS_JSON", None)
        else:
            os.environ["AUTH_TOKENS_JSON"] = previous_tokens
        get_settings.cache_clear()


def test_production_hides_internal_traces_and_enforces_auth():
    previous_env = os.environ.get("APP_ENV")
    previous_key = os.environ.get("INTERNAL_API_KEY")
    previous_tokens = os.environ.get("AUTH_TOKENS_JSON")
    previous_docs = os.environ.get("ENABLE_API_DOCS")
    previous_traces = os.environ.get("EXPOSE_INTERNAL_TRACES")
    try:
        os.environ["APP_ENV"] = "production"
        os.environ["INTERNAL_API_KEY"] = "test-secret"
        os.environ["AUTH_TOKENS_JSON"] = json.dumps(
            {
                "support-token": {"employee_id": "support_001", "role": "support"},
                "admin-token": {"employee_id": "admin_001", "role": "admin"},
            }
        )
        os.environ["ENABLE_API_DOCS"] = "false"
        os.environ["EXPOSE_INTERNAL_TRACES"] = "false"
        get_settings.cache_clear()
        production_app = create_app()

        with TestClient(production_app) as client:
            unauthorized = client.post(
                "/api/chat",
                headers={"X-API-Key": "test-secret"},
                json={
                    "employee_id": "support_001",
                    "role": "support",
                    "message": "用户支付成功但订单待支付，查一下原因",
                    "context": {"order_no": "O20260505001"},
                },
            )
            assert unauthorized.status_code == 401

            response = client.post(
                "/api/chat",
                headers={"X-API-Key": "test-secret", "Authorization": "Bearer support-token"},
                json={
                    "employee_id": "support_001",
                    "role": "support",
                    "message": "用户支付成功但订单待支付，查一下原因",
                    "context": {"order_no": "O20260505001"},
                },
            )

            assert response.status_code == 200
            body = response.json()
            assert body["evidence"] == []
            assert body["plan"] == {}
            assert body["audit_events"] == []
            assert response.headers["X-Request-ID"].startswith("req_")
            assert client.get("/docs").status_code == 404

            me_response = client.get(
                "/api/me",
                headers={"X-API-Key": "test-secret", "Authorization": "Bearer support-token"},
            )
            assert me_response.status_code == 200
            assert me_response.json()["employee_id"] == "support_001"

            denied_memory = client.get(
                "/api/memory/sales_001",
                headers={"X-API-Key": "test-secret", "Authorization": "Bearer support-token"},
            )
            assert denied_memory.status_code == 403

            admin_memory = client.get(
                "/api/memory/support_001",
                headers={"X-API-Key": "test-secret", "Authorization": "Bearer admin-token"},
            )
            assert admin_memory.status_code == 200
    finally:
        if previous_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = previous_env
        if previous_key is None:
            os.environ.pop("INTERNAL_API_KEY", None)
        else:
            os.environ["INTERNAL_API_KEY"] = previous_key
        if previous_tokens is None:
            os.environ.pop("AUTH_TOKENS_JSON", None)
        else:
            os.environ["AUTH_TOKENS_JSON"] = previous_tokens
        if previous_docs is None:
            os.environ.pop("ENABLE_API_DOCS", None)
        else:
            os.environ["ENABLE_API_DOCS"] = previous_docs
        if previous_traces is None:
            os.environ.pop("EXPOSE_INTERNAL_TRACES", None)
        else:
            os.environ["EXPOSE_INTERNAL_TRACES"] = previous_traces
        get_settings.cache_clear()


class FailingTool(BaseTool):
    name = "FailingTool"
    description = "Fails for resilience tests."

    def run(self, payload):
        raise RuntimeError("boom")


def test_executor_gracefully_handles_tool_failure():
    registry = ToolRegistry()
    registry.register(FailingTool())
    executor = PlanExecutor(registry)
    state = AgentState(
        employee_id="engineer_001",
        role="admin",
        message="diagnose",
        plan=ExecutionPlan(
            plan_id="test_plan",
            target_agent="unknown",
            intent="diagnose",
            steps=[
                PlanStep(
                    step_id="failing_step",
                    type="tool_call",
                    name="Failing step",
                    tool="FailingTool",
                    input={},
                )
            ],
        ),
    )

    updated = executor.execute(state)

    assert updated.final_response == {
        "type": "execution_error",
        "message": "系统暂时无法完成当前请求，请稍后重试或联系管理员。",
        "failed_step": "failing_step",
    }
    assert updated.step_results["failing_step"]["ok"] is False
    assert updated.step_results["failing_step"]["error"] == "tool_execution_failed"
