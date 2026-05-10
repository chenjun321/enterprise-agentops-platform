import os
from pathlib import Path

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///./test_enterprise_agents.db"

from fastapi.testclient import TestClient

from app.db.database import Base, SessionLocal, engine
from app.db.seed import seed_demo_data
from app.main import app


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
