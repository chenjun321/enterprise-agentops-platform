from typing import Any, Dict

from app.agents.scene_registry import get_customer_qa_scene, get_missing_fields_for_scene
from app.core.state import AgentState, ExecutionPlan, PlanStep


class PlannerAgent:
    """Builds an executable plan after routing.

    The plan is intentionally structured. LLMs may propose plans, but the
    executor validates and owns actual tool execution.
    """

    def plan(self, state: AgentState) -> ExecutionPlan:
        if state.target_agent == "sales_agent":
            return self._sales_plan(state)
        if state.target_agent == "marketing_agent":
            return self._marketing_plan(state)
        if state.target_agent == "customer_qa_agent":
            return self._qa_plan(state)
        return ExecutionPlan(
            plan_id="clarify_v1",
            target_agent="unknown",
            intent="clarify_intent",
            needs_user_input=True,
            missing_fields=["business_domain"],
            steps=[],
        )

    def _sales_plan(self, state: AgentState) -> ExecutionPlan:
        missing = []
        if not (state.context.get("customer_name") or state.context.get("company")):
            missing.append("customer_name_or_company")
        return ExecutionPlan(
            plan_id="sales_pitch_v1",
            target_agent="sales_agent",
            intent=state.intent,
            needs_user_input=bool(missing),
            missing_fields=missing,
            steps=[
                PlanStep(
                    step_id="crm_profile",
                    type="tool_call",
                    name="查询 CRM 客户画像",
                    tool="CRMTool",
                    input={
                        "customer_name": state.context.get("customer_name", ""),
                        "company": state.context.get("company", ""),
                    },
                ),
                PlanStep(
                    step_id="sales_knowledge",
                    type="tool_call",
                    name="检索销售话术与行业方案",
                    tool="KnowledgeSearchTool",
                    input={
                        "query": state.message,
                        "domain": "sales",
                        "doc_types": ["sales_playbook", "case_study"],
                    },
                ),
                PlanStep(
                    step_id="public_profile",
                    type="tool_call",
                    name="内部资料不足时检索公开画像",
                    tool="ExternalProfileTool",
                    input={"company": state.context.get("company", "")},
                    required=False,
                ),
                PlanStep(step_id="sales_synthesis", type="analysis", name="生成销售策略", agent="sales_agent"),
            ],
        )

    def _marketing_plan(self, state: AgentState) -> ExecutionPlan:
        missing = []
        if not state.context.get("campaign_name"):
            missing.append("campaign_name")
        return ExecutionPlan(
            plan_id="campaign_analysis_v1",
            target_agent="marketing_agent",
            intent=state.intent,
            needs_user_input=bool(missing),
            missing_fields=missing,
            steps=[
                PlanStep(
                    step_id="metric_definition",
                    type="tool_call",
                    name="检索市场指标口径",
                    tool="KnowledgeSearchTool",
                    input={
                        "query": "新增用户 活跃用户 转化率 7日留存 活动归因",
                        "domain": "marketing",
                        "doc_types": ["metric_definition", "campaign_report"],
                    },
                ),
                PlanStep(
                    step_id="campaign_metrics",
                    type="tool_call",
                    name="查询活动指标",
                    tool="MarketingDataTool",
                    input={"campaign_name": state.context.get("campaign_name", "")},
                ),
                PlanStep(step_id="marketing_synthesis", type="analysis", name="生成活动效果分析", agent="marketing_agent"),
            ],
        )

    def _qa_plan(self, state: AgentState) -> ExecutionPlan:
        scene = get_customer_qa_scene(state.intent)
        missing = get_missing_fields_for_scene(scene, state.context)
        return ExecutionPlan(
            plan_id=f"{state.intent}_v1",
            target_agent="customer_qa_agent",
            intent=state.intent,
            needs_user_input=bool(missing),
            missing_fields=missing,
            steps=[self._build_scene_step(step, state) for step in scene["steps"]],
        )

    def _build_scene_step(self, step: Dict[str, Any], state: AgentState) -> PlanStep:
        return PlanStep(
            step_id=step["step_id"],
            type=step["type"],
            name=step["name"],
            tool=step.get("tool"),
            agent=step.get("agent"),
            input=self._resolve_scene_payload(step.get("input", {}), state),
            depends_on=step.get("depends_on", []),
            required=step.get("required", True),
        )

    def _resolve_scene_payload(self, payload: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        resolved: Dict[str, Any] = {}
        for key, value in payload.items():
            if isinstance(value, dict):
                if value.get("from_message"):
                    resolved[key] = state.message
                    continue
                if "from_context" in value:
                    resolved[key] = state.context.get(value["from_context"], "")
                    continue
            resolved[key] = value
        return resolved
