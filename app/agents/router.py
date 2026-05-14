from typing import Dict

from app.agents.scene_registry import match_customer_qa_intent
from app.core.state import AgentName, AgentState


class RouterAgent:
    """Classifies user intent into a business agent.

    The heuristic implementation keeps the demo deterministic. In production,
    this class can call an LLM with strict JSON schema output.
    """

    def route(self, state: AgentState) -> Dict:
        message = state.message.lower()
        context = state.context

        if any(word in message for word in ["销售", "话术", "客户画像", "跟进", "成交"]):
            target: AgentName = "sales_agent"
            intent = "generate_sales_pitch"
        elif any(word in message for word in ["活动", "市场", "新增", "留存", "转化", "gmv", "roi", "品牌"]):
            target = "marketing_agent"
            intent = "campaign_effect_analysis"
        elif any(word in message for word in ["客服", "支付", "订单", "报错", "登录", "失败", "原因", "工单"]):
            target = "customer_qa_agent"
            intent = match_customer_qa_intent(message)
        elif context.get("customer_name") or context.get("company"):
            target = "sales_agent"
            intent = "generate_sales_pitch"
        elif context.get("campaign_name"):
            target = "marketing_agent"
            intent = "campaign_effect_analysis"
        elif context.get("order_no") or context.get("trace_id"):
            target = "customer_qa_agent"
            intent = "order_issue_diagnosis"
        else:
            target = "unknown"
            intent = "clarify_intent"

        state.target_agent = target
        state.intent = intent
        state.add_audit("routed", {"target_agent": target, "intent": intent})
        return {"target_agent": target, "intent": intent, "confidence": 0.86}
