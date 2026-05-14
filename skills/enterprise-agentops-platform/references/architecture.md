# 架构与业务链路

## 总体结构

核心目录：

- `app/agents/`：路由、计划、编排、结果生成
- `app/tools/`：查 CRM、活动、订单、支付、日志、知识库、代码、SQL
- `app/memory/`：长期偏好与 memory event
- `app/rag/`：知识检索
- `app/api/`：HTTP 路由
- `app/security/`：鉴权与权限策略
- `data/docs/`：业务知识库与 runbook

## 统一业务主线

入口在 `POST /api/chat`。

主流程：

1. 解析身份
2. 读取长期 memory
3. `RouterAgent` 判断业务类型
4. `PlannerAgent` 生成执行计划
5. `PlanExecutor` 调用受控工具
6. `ResultSynthesizer` 生成最终业务结果
7. 审计事件落库，必要时写回 memory

## 三条业务链路

### 销售

常见关键词：

- 销售
- 话术
- 客户画像
- 跟进
- 成交

主要组件：

- `sales_agent`
- `CRMTool`
- `KnowledgeSearchTool`
- `ExternalProfileTool`

推荐阅读顺序：

1. `app/api/routes.py`
2. `app/agents/orchestrator.py`
3. `app/agents/router.py`
4. `app/agents/planner.py`
5. `app/agents/business_agents.py`
6. `app/tools/business_tools.py`

### 市场

常见关键词：

- 活动
- 新增
- 留存
- 转化
- GMV
- ROI

主要组件：

- `marketing_agent`
- `MarketingDataTool`
- `KnowledgeSearchTool`

### 客服 QA

常见关键词：

- 订单
- 支付
- 报错
- 工单
- 原因

主要组件：

- `customer_qa_agent`
- `OrderQueryTool`
- `PaymentQueryTool`
- `LogSearchTool`
- `KnowledgeSearchTool`
- 必要时 `CodeSearchTool`

推荐阅读顺序：

1. `app/agents/planner.py`
2. `app/agents/executor.py`
3. `app/tools/business_tools.py`
4. `app/tools/knowledge_search_tool.py`
5. `app/tools/code_search_tool.py`

## docs 的角色

`data/docs/` 是业务知识库和 runbook，供 `KnowledgeSearchTool` 检索。

它们是：

- 销售手册
- 市场指标口径
- 支付排障文档
- 错误码手册

它们不是开发协作 skill。
