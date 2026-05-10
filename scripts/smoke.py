import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.main import app


def run_case(client, name, payload):
    response = client.post("/api/chat", json=payload)
    response.raise_for_status()
    body = response.json()
    print(f"\n=== {name} ===")
    print("agent:", body["target_agent"])
    print("intent:", body["intent"])
    print("answer:", body["answer"])
    print("plan:", body["plan"]["plan_id"])


if __name__ == "__main__":
    with TestClient(app) as client:
        run_case(
            client,
            "sales",
            {
                "employee_id": "sales_001",
                "role": "sales",
                "message": "帮我根据客户信息生成教育行业销售话术",
                "context": {"customer_name": "张明", "company": "Acme Education"},
            },
        )
        run_case(
            client,
            "marketing",
            {
                "employee_id": "marketing_001",
                "role": "marketing",
                "message": "分析一下 2026 春季拉新活动的新增用户质量和留存",
                "context": {"campaign_name": "2026 春季拉新活动"},
            },
        )
        run_case(
            client,
            "support",
            {
                "employee_id": "support_001",
                "role": "support",
                "message": "用户付款成功了，但是订单一直显示待支付，帮我查原因",
                "context": {"order_no": "O20260505001"},
            },
        )
