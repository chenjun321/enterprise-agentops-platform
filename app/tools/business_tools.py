from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    Campaign,
    CampaignEvent,
    Customer,
    Order,
    Payment,
    ProductLog,
    SalesNote,
)
from app.tools.base import BaseTool, ToolResult


class CRMTool(BaseTool):
    name = "CRMTool"
    description = "Search CRM customer profile, usage level, lifecycle stage, and sales notes."

    def __init__(self, db: Session):
        self.db = db

    def run(self, payload: Dict[str, Any]) -> ToolResult:
        name = payload.get("customer_name") or payload.get("name") or ""
        company = payload.get("company") or ""
        stmt = select(Customer)
        if name:
            stmt = stmt.where(Customer.name.ilike(f"%{name}%"))
        if company:
            stmt = stmt.where(Customer.company.ilike(f"%{company}%"))
        customers = self.db.execute(stmt.limit(5)).scalars().all()
        results: List[Dict[str, Any]] = []
        for customer in customers:
            notes = self.db.execute(
                select(SalesNote).where(SalesNote.customer_id == customer.id).limit(5)
            ).scalars().all()
            results.append(
                {
                    "customer_id": customer.id,
                    "name": customer.name,
                    "company": customer.company,
                    "industry": customer.industry,
                    "lifecycle_stage": customer.lifecycle_stage,
                    "usage_level": customer.usage_level,
                    "pain_points": customer.pain_points,
                    "email": customer.email,
                    "sales_notes": [note.note for note in notes],
                }
            )
        return ToolResult(ok=True, data={"customers": results})


class ExternalProfileTool(BaseTool):
    name = "ExternalProfileTool"
    description = "Fallback public profile search. Demo implementation returns synthetic public signals."

    def run(self, payload: Dict[str, Any]) -> ToolResult:
        company = payload.get("company") or "unknown company"
        return ToolResult(
            ok=True,
            data={
                "public_profile": {
                    "company": company,
                    "signals": [
                        "recently discussed operational efficiency",
                        "shows interest in data-driven growth",
                    ],
                    "source": "demo_public_profile",
                }
            },
        )


class MarketingDataTool(BaseTool):
    name = "MarketingDataTool"
    description = "Aggregate campaign metrics for marketing analysis."

    def __init__(self, db: Session):
        self.db = db

    def run(self, payload: Dict[str, Any]) -> ToolResult:
        campaign_name = payload.get("campaign_name") or payload.get("name") or ""
        stmt = select(Campaign)
        if campaign_name:
            stmt = stmt.where(Campaign.name.ilike(f"%{campaign_name}%"))
        campaign = self.db.execute(stmt.limit(1)).scalar_one_or_none()
        if not campaign:
            return ToolResult(ok=False, error="campaign_not_found")

        agg = self.db.execute(
            select(
                func.sum(CampaignEvent.new_users),
                func.sum(CampaignEvent.active_users),
                func.sum(CampaignEvent.conversions),
                func.sum(CampaignEvent.gmv),
                func.sum(CampaignEvent.day7_retained_users),
            ).where(CampaignEvent.campaign_id == campaign.id)
        ).one()

        new_users = int(agg[0] or 0)
        conversions = int(agg[2] or 0)
        retained = int(agg[4] or 0)
        return ToolResult(
            ok=True,
            data={
                "campaign": {
                    "id": campaign.id,
                    "name": campaign.name,
                    "channel": campaign.channel,
                    "start_date": campaign.start_date,
                    "end_date": campaign.end_date,
                    "goal": campaign.goal,
                },
                "metrics": {
                    "new_users": new_users,
                    "active_users": int(agg[1] or 0),
                    "conversions": conversions,
                    "gmv": float(agg[3] or 0),
                    "day7_retained_users": retained,
                    "conversion_rate": round(conversions / new_users, 4) if new_users else 0,
                    "day7_retention_rate": round(retained / new_users, 4) if new_users else 0,
                },
            },
        )


class OrderQueryTool(BaseTool):
    name = "OrderQueryTool"
    description = "Query order state by order_no, trace_id, or customer_id."

    def __init__(self, db: Session):
        self.db = db

    def run(self, payload: Dict[str, Any]) -> ToolResult:
        stmt = select(Order)
        if payload.get("order_no"):
            stmt = stmt.where(Order.order_no == payload["order_no"])
        elif payload.get("trace_id"):
            stmt = stmt.where(Order.trace_id == payload["trace_id"])
        elif payload.get("customer_id"):
            stmt = stmt.where(Order.customer_id == int(payload["customer_id"]))
        orders = self.db.execute(stmt.limit(5)).scalars().all()
        return ToolResult(
            ok=True,
            data={
                "orders": [
                    {
                        "id": order.id,
                        "order_no": order.order_no,
                        "customer_id": order.customer_id,
                        "amount": order.amount,
                        "status": order.status,
                        "trace_id": order.trace_id,
                    }
                    for order in orders
                ]
            },
        )


class PaymentQueryTool(BaseTool):
    name = "PaymentQueryTool"
    description = "Query payment state by order id or trace id."

    def __init__(self, db: Session):
        self.db = db

    def run(self, payload: Dict[str, Any]) -> ToolResult:
        stmt = select(Payment)
        if payload.get("order_id"):
            stmt = stmt.where(Payment.order_id == int(payload["order_id"]))
        elif payload.get("trace_id"):
            stmt = stmt.where(Payment.trace_id == payload["trace_id"])
        else:
            return ToolResult(ok=True, data={"payments": []})
        payments = self.db.execute(stmt.limit(5)).scalars().all()
        return ToolResult(
            ok=True,
            data={
                "payments": [
                    {
                        "id": payment.id,
                        "order_id": payment.order_id,
                        "provider": payment.provider,
                        "status": payment.status,
                        "provider_trade_no": payment.provider_trade_no,
                        "trace_id": payment.trace_id,
                        "callback_received": payment.callback_received,
                    }
                    for payment in payments
                ]
            },
        )


class LogSearchTool(BaseTool):
    name = "LogSearchTool"
    description = "Search product logs by trace id, user id, order number, service, or keyword."

    def __init__(self, db: Session):
        self.db = db

    def run(self, payload: Dict[str, Any]) -> ToolResult:
        stmt = select(ProductLog)
        if payload.get("trace_id"):
            stmt = stmt.where(ProductLog.trace_id == payload["trace_id"])
        if payload.get("user_id"):
            stmt = stmt.where(ProductLog.user_id == payload["user_id"])
        if payload.get("order_no"):
            stmt = stmt.where(ProductLog.order_no == payload["order_no"])
        if payload.get("service"):
            stmt = stmt.where(ProductLog.service == payload["service"])
        if payload.get("keyword"):
            stmt = stmt.where(ProductLog.message.ilike(f"%{payload['keyword']}%"))
        logs = self.db.execute(stmt.order_by(ProductLog.timestamp.desc()).limit(20)).scalars().all()
        return ToolResult(
            ok=True,
            data={
                "logs": [
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "level": log.level,
                        "service": log.service,
                        "trace_id": log.trace_id,
                        "order_no": log.order_no,
                        "message": log.message,
                        "raw_log": log.message,
                    }
                    for log in logs
                ]
            },
        )
