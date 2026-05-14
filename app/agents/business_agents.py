from typing import Any, Dict, List

from app.core.state import AgentState
from app.security.policies import redact_for_role


class SalesAgent:
    def synthesize(self, state: AgentState) -> Dict[str, Any]:
        crm = state.step_results.get("crm_profile", {}).get("data", {}).get("customers", [])
        knowledge = state.step_results.get("sales_knowledge", {}).get("data", {}).get("chunks", [])
        public_profile = state.step_results.get("public_profile", {}).get("data", {}).get("public_profile", {})
        profile = crm[0] if crm else public_profile
        pain_points = profile.get("pain_points", "数据效率、增长转化、内部协作")
        tone = self._memory_hint(state.long_memory, "语气偏专业、克制")
        answer = {
            "customer_profile": profile,
            "sales_strategy": f"围绕 {pain_points} 展开，先确认业务目标，再连接产品能力，最后推进一次小范围试点。",
            "pitch": {
                "opening": f"您好，结合贵司当前阶段，我想先确认一下近期在 {pain_points} 上的优先级。",
                "value_proposition": "我们可以把客户数据、活动数据和客服反馈串起来，帮助团队更快识别高价值机会。",
                "objection_handling": [
                    "如果担心接入成本，可以先从一个业务线试点。",
                    "如果关注数据安全，可以先走只读权限和审计模式。",
                ],
                "closing": "如果您方便，我建议约 30 分钟把当前流程和试点范围对齐。",
            },
            "memory_applied": tone,
            "knowledge_sources": [item["source"] for item in knowledge],
            "confidence": 0.84 if crm else 0.68,
        }
        return answer

    def _memory_hint(self, memories: List[Dict[str, Any]], fallback: str) -> str:
        return memories[0]["content"] if memories else fallback


class MarketingAgent:
    def synthesize(self, state: AgentState) -> Dict[str, Any]:
        metrics = state.step_results.get("campaign_metrics", {}).get("data", {}).get("metrics", {})
        campaign = state.step_results.get("campaign_metrics", {}).get("data", {}).get("campaign", {})
        docs = state.step_results.get("metric_definition", {}).get("data", {}).get("chunks", [])
        new_users = metrics.get("new_users", 0)
        retention = metrics.get("day7_retention_rate", 0)
        conversion = metrics.get("conversion_rate", 0)
        impact = "正向明显" if new_users >= 1000 and retention >= 0.25 else "有短期拉新，但质量需要继续验证"
        return {
            "campaign": campaign,
            "summary": f"本次活动累计新增 {new_users} 人，转化率 {conversion:.2%}，7日留存 {retention:.2%}，整体判断为：{impact}。",
            "key_metrics": metrics,
            "insights": [
                "活动带来了明确新增用户，但需要结合留存判断用户质量。",
                "如果渠道新增高但留存低，下次应优化投放人群和首日承接路径。",
            ],
            "recommendations": [
                "把新增用户按渠道分群比较 7 日留存。",
                "对低留存渠道降低预算，对高转化渠道增加再营销。",
                "建立活动前后 14 天基线，避免只看活动期绝对值。",
            ],
            "metric_sources": [item["source"] for item in docs],
            "confidence": 0.82 if metrics else 0.45,
        }


class CustomerQAAgent:
    def synthesize(self, state: AgentState) -> Dict[str, Any]:
        orders = state.step_results.get("order_state", {}).get("data", {}).get("orders", [])
        payments = state.step_results.get("payment_state", {}).get("data", {}).get("payments", [])
        logs = state.step_results.get("logs", {}).get("data", {}).get("logs", [])
        runbook = state.step_results.get("runbook", {}).get("data", {}).get("chunks", [])
        code = state.step_results.get("code", {}).get("data", {}).get("matches", [])

        order = orders[0] if orders else {}
        payment = payments[0] if payments else {}
        log_messages = [item.get("message", "") for item in logs]
        if state.intent == "payment_issue_diagnosis":
            internal, user_reply = self._payment_summary(order, payment, log_messages, runbook, code)
        elif state.intent == "login_issue_diagnosis":
            internal, user_reply = self._login_summary(log_messages, runbook, code)
        elif state.intent == "order_issue_diagnosis":
            internal, user_reply = self._order_summary(order, log_messages, runbook, code)
        else:
            internal, user_reply = self._generic_summary(order, payment, log_messages, runbook, code)

        return {
            "user_reply": user_reply,
            "internal_summary": redact_for_role(state.role, internal),
            "confidence": internal["confidence"],
        }

    def _payment_summary(
        self,
        order: Dict[str, Any],
        payment: Dict[str, Any],
        log_messages: List[str],
        runbook: List[Dict[str, Any]],
        code: List[Dict[str, Any]],
    ) -> tuple[Dict[str, Any], str]:
        callback_delay = (
            payment.get("status") == "success"
            and order.get("status") in {"pending", "unpaid"}
            and any("callback" in item.lower() or "timeout" in item.lower() for item in log_messages)
        )
        root_cause = "payment_callback_delay" if callback_delay else "insufficient_evidence"
        internal = {
            "root_cause": root_cause,
            "evidence": [
                f"order.status={order.get('status', 'unknown')}",
                f"payment.status={payment.get('status', 'unknown')}",
                f"log_count={len(log_messages)}",
            ],
            "related_files": code,
            "runbook_sources": [item["source"] for item in runbook],
            "suggested_action": "trigger_payment_reconcile_job" if callback_delay else "collect_more_trace_context",
            "confidence": 0.91 if callback_delay else 0.52,
        }
        user_reply = (
            "我们查到您的支付结果已经成功返回，但订单状态同步存在延迟。系统会继续自动核对，"
            "如果短时间内仍未更新，客服可以根据订单号发起人工核对。"
            if callback_delay
            else "目前还需要更多订单或流水信息才能准确判断原因。请补充订单号、支付时间或截图中的交易流水号。"
        )
        return internal, user_reply

    def _login_summary(
        self,
        log_messages: List[str],
        runbook: List[Dict[str, Any]],
        code: List[Dict[str, Any]],
    ) -> tuple[Dict[str, Any], str]:
        auth_flow_issue = any(
            keyword in item.lower()
            for item in log_messages
            for keyword in ["login", "auth", "token", "signature", "wallet"]
        )
        root_cause = "authentication_flow_issue" if auth_flow_issue else "insufficient_evidence"
        internal = {
            "root_cause": root_cause,
            "evidence": [f"log_count={len(log_messages)}"],
            "related_files": code,
            "runbook_sources": [item["source"] for item in runbook],
            "suggested_action": "check_auth_provider_and_signature_flow" if auth_flow_issue else "collect_login_trace_context",
            "confidence": 0.78 if auth_flow_issue else 0.4,
        }
        user_reply = (
            "我们正在核对登录和签名链路，当前看起来更像鉴权流程异常。建议您先确认钱包网络、重新连接后再试一次。"
            if auth_flow_issue
            else "目前还需要更多登录时间、钱包地址或报错截图，才能准确判断问题原因。"
        )
        return internal, user_reply

    def _order_summary(
        self,
        order: Dict[str, Any],
        log_messages: List[str],
        runbook: List[Dict[str, Any]],
        code: List[Dict[str, Any]],
    ) -> tuple[Dict[str, Any], str]:
        order_pending = order.get("status") in {"pending", "unpaid"}
        root_cause = "order_still_pending" if order_pending else "insufficient_evidence"
        internal = {
            "root_cause": root_cause,
            "evidence": [
                f"order.status={order.get('status', 'unknown')}",
                f"log_count={len(log_messages)}",
            ],
            "related_files": code,
            "runbook_sources": [item["source"] for item in runbook],
            "suggested_action": "continue_order_state_followup" if order_pending else "collect_more_order_context",
            "confidence": 0.75 if order_pending else 0.46,
        }
        user_reply = (
            "我们查到当前订单仍处于处理中或待确认状态，建议稍后刷新后再次查看；如果长时间未更新，客服可以继续跟进。"
            if order_pending
            else "目前还需要更多订单号或链路信息，才能准确判断订单状态异常的原因。"
        )
        return internal, user_reply

    def _generic_summary(
        self,
        order: Dict[str, Any],
        payment: Dict[str, Any],
        log_messages: List[str],
        runbook: List[Dict[str, Any]],
        code: List[Dict[str, Any]],
    ) -> tuple[Dict[str, Any], str]:
        internal = {
            "root_cause": "insufficient_evidence",
            "evidence": [
                f"order.status={order.get('status', 'unknown')}",
                f"payment.status={payment.get('status', 'unknown')}",
                f"log_count={len(log_messages)}",
            ],
            "related_files": code,
            "runbook_sources": [item["source"] for item in runbook],
            "suggested_action": "collect_more_trace_context",
            "confidence": 0.42,
        }
        user_reply = "目前还需要更多订单号、流水号、登录时间或报错截图，才能准确判断原因。"
        return internal, user_reply


class ResultSynthesizer:
    def __init__(self) -> None:
        self.sales = SalesAgent()
        self.marketing = MarketingAgent()
        self.qa = CustomerQAAgent()

    def synthesize(self, state: AgentState) -> Dict[str, Any]:
        if state.final_response:
            return state.final_response
        if state.target_agent == "sales_agent":
            return self.sales.synthesize(state)
        if state.target_agent == "marketing_agent":
            return self.marketing.synthesize(state)
        if state.target_agent == "customer_qa_agent":
            return self.qa.synthesize(state)
        return {
            "type": "clarify",
            "message": "我还不能确定这是销售、市场还是客服 QA 任务，请补充业务目标。",
        }
