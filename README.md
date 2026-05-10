# enterprise-agentops-platform

这是一个面向研究生毕业设计和面试展示的企业内部多 Agent 系统。它覆盖销售、市场、客服 QA 三类真实业务，并包含 Agent 编排、状态管理、长期记忆、RAG、代码检索、权限控制、审计和工具执行。

## 核心流程

```text
User Chat
  -> Session State 初始化
  -> Long Memory 读取用户偏好
  -> Router Agent 判断业务 Agent
  -> Planner Agent 生成结构化执行计划
  -> Plan Executor 按权限调用 Tool
  -> Tool 结果写入 State 和 Evidence
  -> Business Agent 生成业务结果
  -> Safety / Redaction 按角色裁剪敏感内容
  -> Audit Log 记录执行轨迹
  -> Memory Writer 写入明确偏好
```

## 业务 Agent

- `SalesAgent`：查询 CRM、检索销售手册、生成客户画像和销售话术。
- `MarketingAgent`：检索指标口径、查询活动数据、生成活动效果分析。
- `CustomerQAAgent`：查询订单、支付、日志、runbook 和代码，生成用户回复与内部根因摘要。

## 企业级能力

- `Session State`：只保存当前请求执行上下文。
- `Long Memory`：记录用户偏好，例如输出格式、分析指标、回复风格。
- `Tool Calling`：Agent 不能直接访问数据，只能调用受控工具。
- `RAG`：用于 FAQ、runbook、指标口径、销售手册、案例文档。
- `Code Intelligence`：用 `rg` 和 AST 定位错误码、日志关键字和相关函数。
- `RBAC`：不同角色可用工具不同，客服看不到完整代码和原始敏感日志。
- `Audit Log`：记录路由、计划、工具调用、最终回答和 memory 变更。

## 快速启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d postgres
alembic upgrade head
python scripts/seed_demo.py
uvicorn app.main:app --reload --port 8000
```

## 发布到 GitHub

默认发布到：

```text
https://github.com/chenjun321/enterprise-agentops-platform
```

一键执行：

```bash
bash scripts/publish_to_github.sh
```

可选参数：

```bash
OWNER=chenjun321 REPO=enterprise-agentops-platform VISIBILITY=public bash scripts/publish_to_github.sh
```

打开：

```text
http://127.0.0.1:8000/docs
```

应用默认使用 PostgreSQL。生产环境下，应用启动不会自动建表，也不会自动写入 demo 数据；schema 变更必须通过 Alembic 迁移执行。

## 生产数据库

默认连接串：

```text
postgresql+psycopg://agent_app:change_me@127.0.0.1:5432/enterprise_agents
```

关键配置：

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://agent_app:change_me@127.0.0.1:5432/enterprise_agents
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_RECYCLE_SECONDS=1800
DATABASE_ECHO=false
```

迁移：

```bash
alembic upgrade head
```

检查数据库连通性：

```bash
python scripts/check_db.py
curl http://127.0.0.1:8000/health/db
```

写入 demo 数据只用于演示环境：

```bash
python scripts/seed_demo.py
```

生产环境不开放 HTTP 初始化数据库入口，演示数据只能通过受控脚本写入。

## 烟测

```bash
pip install -r requirements-dev.txt
pytest -q
```

端到端演示需要先启动 PostgreSQL、执行迁移并写入 demo 数据：

```bash
python scripts/smoke.py
```

## 示例请求

销售：

```json
{
  "employee_id": "sales_001",
  "role": "sales",
  "message": "帮我根据客户信息生成教育行业销售话术",
  "context": {
    "customer_name": "张明",
    "company": "Acme Education"
  }
}
```

市场：

```json
{
  "employee_id": "marketing_001",
  "role": "marketing",
  "message": "分析一下 2026 春季拉新活动的新增用户质量和留存",
  "context": {
    "campaign_name": "2026 春季拉新活动"
  }
}
```

客服 QA：

```json
{
  "employee_id": "support_001",
  "role": "support",
  "message": "用户付款成功了，但是订单一直显示待支付，帮我查原因",
  "context": {
    "order_no": "O20260505001"
  }
}
```

## LlamaIndex 如何接入

当前 `SimpleKnowledgeRetriever` 是本地可运行版本，适合毕业设计 demo。生产级可以替换为：

```text
KnowledgeSearchTool
  -> LlamaIndexKnowledgeAdapter
  -> VectorStoreIndex
  -> pgvector / Qdrant / Chroma
```

保持 Tool 接口不变，Agent 编排层无需修改。

## 推荐后续增强

- Router 和 Planner 改成 LLM strict JSON schema 输出。
- RAG 使用 LlamaIndex + embedding + metadata filter。
- CodeSearchTool 增加调用链、Git commit、PR diff 检索。
- 增加 Human Approval 节点，高风险回复先人工确认。
- 增加前端工作台展示 plan、tool trace、evidence 和 final answer。
