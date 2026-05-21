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
from app.agents.scene_registry import get_customer_qa_scene, load_customer_qa_scene_registry
from app.core.state import AgentState, ExecutionPlan, PlanStep
from app.core.config import get_settings
from app.db.database import Base, SessionLocal, engine
from app.db.models import AgentReflection, ConversationThread, PendingHumanInput, ThreadMessage, ThreadState
from app.db.seed import seed_demo_data
from app.main import app, create_app
from app.services.thread_store import ThreadStore
from app.services.reflection import ReflectionService
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


def test_local_defaults_use_sqlite_and_milvus_lite():
    previous_env = os.environ.get("APP_ENV")
    previous_database_url = os.environ.get("DATABASE_URL")
    previous_vector_store = os.environ.get("VECTOR_STORE")
    try:
        os.environ["APP_ENV"] = "local"
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("VECTOR_STORE", None)
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.database_url.startswith("sqlite")
        assert settings.vector_store == "milvus_lite"
    finally:
        if previous_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = previous_env
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        if previous_vector_store is None:
            os.environ.pop("VECTOR_STORE", None)
        else:
            os.environ["VECTOR_STORE"] = previous_vector_store
        get_settings.cache_clear()


def test_production_defaults_use_postgres_and_milvus():
    previous_env = os.environ.get("APP_ENV")
    previous_database_url = os.environ.get("DATABASE_URL")
    previous_vector_store = os.environ.get("VECTOR_STORE")
    try:
        os.environ["APP_ENV"] = "production"
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("VECTOR_STORE", None)
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.database_url.startswith("postgresql")
        assert settings.vector_store == "milvus"
    finally:
        if previous_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = previous_env
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        if previous_vector_store is None:
            os.environ.pop("VECTOR_STORE", None)
        else:
            os.environ["VECTOR_STORE"] = previous_vector_store
        get_settings.cache_clear()


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
        "CustomerIdentityResolveTool",
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
        "CustomerIdentityResolveTool",
        "LogSearchTool",
        "KnowledgeSearchTool",
        "CodeSearchTool",
    ]


def test_customer_qa_scene_registry_drives_steps():
    scene = get_customer_qa_scene("payment_issue_diagnosis")

    assert scene["required_context_modes"] == ["order_or_trace"]
    assert [step["tool"] for step in scene["steps"] if step["type"] == "tool_call"] == [
        "CustomerIdentityResolveTool",
        "OrderQueryTool",
        "PaymentQueryTool",
        "LogSearchTool",
        "KnowledgeSearchTool",
        "CodeSearchTool",
    ]


def test_customer_qa_workflow_registry_has_schema_and_identity_first():
    registry = load_customer_qa_scene_registry()

    assert registry["schema_version"] == "1.0"
    for scene in registry["scenes"].values():
        first_tool_step = next(step for step in scene["steps"] if step["type"] == "tool_call")
        assert first_tool_step["tool"] == "CustomerIdentityResolveTool"


def test_production_requires_internal_api_key():
    previous_env = os.environ.get("APP_ENV")
    previous_key = os.environ.get("INTERNAL_API_KEY")
    previous_tokens = os.environ.get("AUTH_TOKENS_JSON")
    previous_public_token = os.environ.get("PUBLIC_CHANNEL_TOKEN")
    try:
        os.environ["APP_ENV"] = "production"
        os.environ.pop("INTERNAL_API_KEY", None)
        os.environ["AUTH_TOKENS_JSON"] = json.dumps({"token": {"employee_id": "support_001", "role": "support"}})
        os.environ["PUBLIC_CHANNEL_TOKEN"] = "public-test-token"
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
        if previous_public_token is None:
            os.environ.pop("PUBLIC_CHANNEL_TOKEN", None)
        else:
            os.environ["PUBLIC_CHANNEL_TOKEN"] = previous_public_token
        get_settings.cache_clear()


def test_production_requires_bearer_tokens():
    previous_env = os.environ.get("APP_ENV")
    previous_key = os.environ.get("INTERNAL_API_KEY")
    previous_tokens = os.environ.get("AUTH_TOKENS_JSON")
    previous_public_token = os.environ.get("PUBLIC_CHANNEL_TOKEN")
    try:
        os.environ["APP_ENV"] = "production"
        os.environ["INTERNAL_API_KEY"] = "test-secret"
        os.environ["PUBLIC_CHANNEL_TOKEN"] = "public-test-token"
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
        if previous_public_token is None:
            os.environ.pop("PUBLIC_CHANNEL_TOKEN", None)
        else:
            os.environ["PUBLIC_CHANNEL_TOKEN"] = previous_public_token
        get_settings.cache_clear()


def test_production_requires_public_channel_token():
    previous_env = os.environ.get("APP_ENV")
    previous_key = os.environ.get("INTERNAL_API_KEY")
    previous_tokens = os.environ.get("AUTH_TOKENS_JSON")
    previous_public_token = os.environ.get("PUBLIC_CHANNEL_TOKEN")
    try:
        os.environ["APP_ENV"] = "production"
        os.environ["INTERNAL_API_KEY"] = "test-secret"
        os.environ["AUTH_TOKENS_JSON"] = json.dumps({"token": {"employee_id": "support_001", "role": "support"}})
        os.environ.pop("PUBLIC_CHANNEL_TOKEN", None)
        get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="PUBLIC_CHANNEL_TOKEN must be configured"):
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
        if previous_public_token is None:
            os.environ.pop("PUBLIC_CHANNEL_TOKEN", None)
        else:
            os.environ["PUBLIC_CHANNEL_TOKEN"] = previous_public_token
        get_settings.cache_clear()


def test_production_hides_internal_traces_and_enforces_auth():
    previous_env = os.environ.get("APP_ENV")
    previous_database_url = os.environ.get("DATABASE_URL")
    previous_vector_store = os.environ.get("VECTOR_STORE")
    previous_key = os.environ.get("INTERNAL_API_KEY")
    previous_tokens = os.environ.get("AUTH_TOKENS_JSON")
    previous_docs = os.environ.get("ENABLE_API_DOCS")
    previous_traces = os.environ.get("EXPOSE_INTERNAL_TRACES")
    previous_public_token = os.environ.get("PUBLIC_CHANNEL_TOKEN")
    try:
        os.environ["APP_ENV"] = "production"
        os.environ["DATABASE_URL"] = "postgresql+psycopg://agent_app:change_me@127.0.0.1:5432/enterprise_agents"
        os.environ["VECTOR_STORE"] = "milvus"
        os.environ["INTERNAL_API_KEY"] = "test-secret"
        os.environ["PUBLIC_CHANNEL_TOKEN"] = "public-test-token"
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
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        if previous_vector_store is None:
            os.environ.pop("VECTOR_STORE", None)
        else:
            os.environ["VECTOR_STORE"] = previous_vector_store
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
        if previous_public_token is None:
            os.environ.pop("PUBLIC_CHANNEL_TOKEN", None)
        else:
            os.environ["PUBLIC_CHANNEL_TOKEN"] = previous_public_token
        get_settings.cache_clear()


def test_public_customer_qa_creates_bug_ticket():
    with TestClient(app) as client:
        response = client.post(
            "/api/customer/qa",
            json={
                "customer_user_id": "customer_002",
                "contact": "user@example.com",
                "channel": "web",
                "message": "页面一直报错，无法提交任务，帮我反馈一个 bug",
                "context": {"severity": "high", "reproduction_steps": "进入任务页后点击提交"},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "bug_report_submission"
    assert "工单号" in body["answer"]["user_reply"]
    assert body["ticket"]["status"] == "open"
    assert body["ticket"]["severity"] == "high"


def test_public_customer_qa_returns_numbered_operation_steps():
    with TestClient(app) as client:
        response = client.post(
            "/api/customer/qa",
            json={
                "customer_user_id": "customer_steps_001",
                "channel": "web",
                "message": "怎么绑定钱包",
                "context": {},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "customer_daily_question"
    assert body["answer"]["answer_type"] == "operation_guide"
    assert len(body["answer"]["steps"]) >= 3
    assert body["answer"]["steps"][0]["title"] == "进入账号设置"
    assert "1. 进入账号设置" in body["answer"]["user_reply"]
    assert "2. 选择绑定钱包" in body["answer"]["user_reply"]


def test_reflection_record_is_written_for_customer_qa():
    thread_id = "thread_reflection_001"
    with TestClient(app) as client:
        response = client.post(
            "/api/customer/qa",
            json={
                "thread_id": thread_id,
                "customer_user_id": "customer_reflection_001",
                "channel": "web",
                "message": "怎么绑定钱包",
                "context": {},
            },
        )

    assert response.status_code == 200
    db = SessionLocal()
    try:
        reflection = db.query(AgentReflection).filter(AgentReflection.session_id == thread_id).one()
        assert reflection.passed is True
        assert reflection.risk_level == "low"
        assert "customer_qa_response_shape" in reflection.checks
    finally:
        db.close()


def test_reflection_sanitizes_sensitive_answer_payload():
    db = SessionLocal()
    try:
        state = AgentState(
            session_id="reflection_sensitive_001",
            employee_id="support_001",
            role="support",
            message="test",
            target_agent="customer_qa_agent",
            intent="issue_diagnosis",
        )
        result = ReflectionService(db).reflect(
            state,
            {
                "user_reply": "ok",
                "internal_summary": {
                    "raw_log": "secretKey=abc",
                    "provider_trade_no": "TRADE123",
                },
            },
        )
        assert result.rewrite_required is True
        assert result.risk_level == "high"
        assert result.final_answer["internal_summary"]["raw_log"] == "[redacted]"
        assert result.final_answer["internal_summary"]["provider_trade_no"] == "[redacted]"
    finally:
        db.rollback()
        db.close()


def test_thread_id_persists_user_and_assistant_messages():
    thread_id = "thread_test_steps_001"
    with TestClient(app) as client:
        response = client.post(
            "/api/customer/qa",
            json={
                "thread_id": thread_id,
                "customer_user_id": "customer_thread_001",
                "channel": "web",
                "message": "怎么绑定钱包",
                "context": {},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == thread_id
    assert body["session_id"] == thread_id

    db = SessionLocal()
    try:
        thread = db.get(ConversationThread, thread_id)
        messages = db.query(ThreadMessage).filter(ThreadMessage.thread_id == thread_id).all()
        assert thread is not None
        assert thread.message_count == 2
        assert [item.role for item in messages] == ["user", "assistant"]
    finally:
        db.close()


def test_same_thread_returns_busy_when_lock_is_held():
    thread_id = "thread_busy_001"
    db = SessionLocal()
    owner_id = "test_owner"
    try:
        assert ThreadStore(db).acquire_lock(thread_id, owner_id)
        with TestClient(app) as client:
            response = client.post(
                "/api/customer/qa",
                json={
                    "thread_id": thread_id,
                    "customer_user_id": "customer_busy_001",
                    "message": "怎么绑定钱包",
                    "context": {},
                },
            )
        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "thread_busy"
    finally:
        ThreadStore(db).release_lock(thread_id, owner_id)
        db.close()


def test_missing_order_context_opens_human_loop_then_resumes():
    thread_id = "thread_human_loop_payment_001"
    with TestClient(app) as client:
        first = client.post(
            "/api/chat",
            json={
                "thread_id": thread_id,
                "employee_id": "support_001",
                "role": "support",
                "message": "用户支付成功但订单待支付，帮我查一下原因",
                "context": {},
            },
        )
        second = client.post(
            "/api/chat",
            json={
                "thread_id": thread_id,
                "employee_id": "support_001",
                "role": "support",
                "message": "订单号是 O20260505001",
                "context": {},
            },
        )

    assert first.status_code == 200
    first_body = first.json()
    assert first_body["answer"]["type"] == "needs_user_input"
    assert first_body["answer"]["thread_status"] == "waiting_for_input"
    assert "订单号" in first_body["answer"]["question"]

    assert second.status_code == 200
    second_body = second.json()
    assert second_body["intent"] == "payment_issue_diagnosis"
    assert second_body["answer"]["internal_summary"]["root_cause"] == "payment_callback_delay"

    db = SessionLocal()
    try:
        pending = db.query(PendingHumanInput).filter(PendingHumanInput.thread_id == thread_id).one()
        state = db.get(ThreadState, thread_id)
        assert pending.status == "resolved"
        assert "O20260505001" in state.state_json
    finally:
        db.close()


def test_usage_guard_rejects_oversized_input():
    previous_limit = os.environ.get("USAGE_SINGLE_INPUT_TOKEN_LIMIT")
    try:
        os.environ["USAGE_SINGLE_INPUT_TOKEN_LIMIT"] = "5"
        get_settings.cache_clear()
        limited_app = create_app()
        with TestClient(limited_app) as client:
            response = client.post(
                "/api/customer/qa",
                json={
                    "customer_user_id": "abuse_oversized",
                    "message": "这是一段明显超过测试 token 限制的输入",
                    "context": {},
                },
            )

        assert response.status_code == 429
        assert response.json()["detail"]["reason"] == "single_input_token_limit_exceeded"
    finally:
        if previous_limit is None:
            os.environ.pop("USAGE_SINGLE_INPUT_TOKEN_LIMIT", None)
        else:
            os.environ["USAGE_SINGLE_INPUT_TOKEN_LIMIT"] = previous_limit
        get_settings.cache_clear()


def test_usage_guard_rejects_duplicate_messages():
    previous_duplicate_limit = os.environ.get("USAGE_DUPLICATE_LIMIT")
    previous_window = os.environ.get("USAGE_DUPLICATE_WINDOW_SECONDS")
    try:
        os.environ["USAGE_DUPLICATE_LIMIT"] = "1"
        os.environ["USAGE_DUPLICATE_WINDOW_SECONDS"] = "3600"
        get_settings.cache_clear()
        limited_app = create_app()
        payload = {
            "customer_user_id": "abuse_duplicate",
            "message": "怎么绑定钱包",
            "context": {},
        }
        with TestClient(limited_app) as client:
            first = client.post("/api/customer/qa", json=payload)
            second = client.post("/api/customer/qa", json=payload)

        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["detail"]["reason"] == "duplicate_message_limit_exceeded"
    finally:
        if previous_duplicate_limit is None:
            os.environ.pop("USAGE_DUPLICATE_LIMIT", None)
        else:
            os.environ["USAGE_DUPLICATE_LIMIT"] = previous_duplicate_limit
        if previous_window is None:
            os.environ.pop("USAGE_DUPLICATE_WINDOW_SECONDS", None)
        else:
            os.environ["USAGE_DUPLICATE_WINDOW_SECONDS"] = previous_window
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
