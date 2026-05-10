from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Campaign,
    CampaignEvent,
    Customer,
    Order,
    Payment,
    ProductLog,
    SalesNote,
    SupportTicket,
)
from app.rag.simple_retriever import SimpleKnowledgeIndexer


def seed_demo_data(db: Session) -> None:
    if db.execute(select(Customer).limit(1)).scalar_one_or_none():
        SimpleKnowledgeIndexer(db).index_directory("data/docs")
        return

    acme = Customer(
        name="张明",
        company="Acme Education",
        industry="education",
        lifecycle_stage="trial",
        usage_level="high",
        pain_points="招生线索分散、销售跟进不及时、活动转化难衡量",
        email="zhangming@example.com",
    )
    retail = Customer(
        name="李娜",
        company="North Retail",
        industry="retail",
        lifecycle_stage="active_customer",
        usage_level="medium",
        pain_points="会员复购率下降、客服问题响应慢",
        email="lina@example.com",
    )
    db.add_all([acme, retail])
    db.flush()
    db.add_all(
        [
            SalesNote(customer_id=acme.id, note="客户关注数据安全和教育行业案例。", created_by="sales_001"),
            SalesNote(customer_id=acme.id, note="上次演示后，对活动 ROI 看板兴趣较高。", created_by="sales_001"),
        ]
    )

    order = Order(
        order_no="O20260505001",
        customer_id=retail.id,
        amount=1299.0,
        status="pending",
        trace_id="trace_pay_001",
    )
    db.add(order)
    db.flush()
    db.add(
        Payment(
            order_id=order.id,
            provider="mockpay",
            status="success",
            provider_trade_no="MOCK20260505",
            trace_id="trace_pay_001",
            callback_received=False,
        )
    )
    db.add_all(
        [
            ProductLog(
                timestamp=datetime.utcnow(),
                level="ERROR",
                service="payment",
                trace_id="trace_pay_001",
                user_id="customer_002",
                order_no="O20260505001",
                message="PAYMENT_CALLBACK_TIMEOUT payment callback timeout after provider success",
            ),
            ProductLog(
                timestamp=datetime.utcnow(),
                level="INFO",
                service="order",
                trace_id="trace_pay_001",
                user_id="customer_002",
                order_no="O20260505001",
                message="order remains pending waiting for payment callback",
            ),
        ]
    )
    db.add(
        SupportTicket(
            ticket_no="T20260505001",
            customer_id=retail.id,
            category="payment",
            question="我付款成功了，但订单一直显示待支付。",
        )
    )

    campaign = Campaign(
        name="2026 春季拉新活动",
        channel="multi_channel",
        start_date="2026-04-01",
        end_date="2026-04-30",
        goal="提升品牌声量并获取高质量新增用户",
    )
    db.add(campaign)
    db.flush()
    for day in range(1, 31):
        db.add(
            CampaignEvent(
                campaign_id=campaign.id,
                event_date=f"2026-04-{day:02d}",
                channel="search" if day % 2 else "social",
                new_users=80 + day * 3,
                active_users=420 + day * 8,
                conversions=18 + day,
                gmv=3500 + day * 210,
                day7_retained_users=25 + day,
            )
        )
    db.commit()
    SimpleKnowledgeIndexer(db).index_directory("data/docs")
