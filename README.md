# enterprise-agentops-platform

这是一个面向生产环境的企业 Agent 服务框架。当前业务模块固定为三类：营销、销售、QA。营销和销售主要服务内部员工，QA 同时支持内部客服排障和 C 端用户公开问答、Bug 反馈工单。

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

## 业务模块

- `MarketingAgent`：检索指标口径、查询活动数据、生成活动效果分析和投放建议。
- `SalesAgent`：查询 CRM、检索销售手册、生成客户画像、销售策略和跟进话术。
- `CustomerQAAgent`：面向 C 端回答日常问题；遇到 Bug 或无法确认的问题时创建工单并返回用户可见回复。内部客服角色可继续查询订单、支付、日志、runbook 和代码，生成内部根因摘要。

## 对外 QA API

C 端产品、官网、App 或客服机器人接入：

```bash
curl http://127.0.0.1:8000/api/customer/qa \
  -H 'Content-Type: application/json' \
  -H 'X-Channel-Token: replace-with-public-channel-token' \
  -d '{
    "customer_user_id": "customer_002",
    "contact": "user@example.com",
    "channel": "web",
    "message": "页面一直报错，无法提交任务，帮我反馈一个 bug",
    "context": {
      "severity": "high",
      "reproduction_steps": "进入任务页后点击提交"
    }
  }'
```

公开 QA 入口只开放 `KnowledgeSearchTool` 和 `SupportTicketCreateTool`，不会返回内部日志、代码、数据库表或原始排障链路。

## 企业级能力

- `Session State`：只保存当前请求执行上下文。
- `Thread Store`：用共享数据库持久化 thread、消息历史和 thread lock，多 Pod 下不依赖单个 Pod 的内存。
- `Long Memory`：记录用户偏好，例如输出格式、分析指标、回复风格。
- `Tool Calling`：Agent 不能直接访问数据，只能调用受控工具。
- `RAG`：用于 FAQ、runbook、指标口径、销售手册、案例文档。
- `Code Intelligence`：用 `rg` 和 AST 定位错误码、日志关键字和相关函数。
- `RBAC`：不同角色可用工具不同，客服看不到完整代码和原始敏感日志。
- `Audit Log`：记录路由、计划、工具调用、最终回答和 memory 变更。

## 多 Pod Thread 处理

生产环境不要假设同一个 thread 会落在同一个 Pod。本服务把 Pod 设计为无状态：

```text
Client
  -> Ingress / API Gateway
  -> 任意 Agent API Pod
  -> conversation_threads / thread_messages 读取历史
  -> thread_locks 抢占 thread 执行锁
  -> Agent 执行
  -> 写回 thread_messages / audit_events / usage_events
```

客户端应该传 `thread_id`：

```json
{
  "thread_id": "thread_customer_123",
  "message": "怎么绑定钱包"
}
```

处理规则：

- 同一个 `thread_id` 的消息会写入 `thread_messages`。
- 执行前会在 `thread_locks` 抢锁，锁 TTL 由 `THREAD_LOCK_TTL_SECONDS` 控制。
- 锁被其他 Pod 持有时返回 `409 thread_busy`，客户端可稍后重试。
- 最近历史会注入 `context._thread_history`，供 QA/Agent 生成连续回复。
- 结构化 thread state 会写入 `thread_states`，例如 `order_no`、`trace_id`、`wallet_address`。
- SQLite 只适合本地开发；多 Pod 生产必须使用共享 PostgreSQL/MySQL。

## QA Workflow

QA workflow 使用 JSON 驱动，而不是写死在 Python 里：

- workflow：`app/agents/scene_registry/customer_qa_scenes.json`
- schema：`app/agents/scene_registry/customer_qa_workflow.schema.json`
- 读取/校验：`app/agents/scene_registry.py`

每个 QA scene 都遵循 TaskOn 风格的 identity-first 流程：

```text
识别 C 端用户身份
  -> 检索 FAQ / runbook / error_code
  -> 查询订单、支付、日志或创建工单
  -> 生成用户可见回复和内部摘要
  -> reflection 检查
```

身份识别支持：

- `customer_user_id`
- `user_id`
- `wallet_address`
- `twitter_handle`
- `username`
- `order_no`
- `trace_id`

缺字段时会进入 human-in-loop：

```text
发现缺少 order_no_or_trace_id
  -> 创建 pending_human_inputs
  -> thread 状态变为 waiting_for_input
  -> 返回明确补充问题
  -> 用户下一轮补充订单号/trace_id
  -> 写入 thread_states
  -> 自动恢复原 workflow intent
```

## 快速启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/run_local.py
```

打开：

```text
http://127.0.0.1:8000/
```

本地默认使用 `sqlite:///./data/app.db` 和 Milvus Lite `./data/milvus_lite.db`。首次启动会自动建 SQLite 表、写入 demo 数据、同步 `data/docs` 知识库到 Milvus Lite。开发环境如果不启用 API key 和 bearer token，仍然可以沿用请求体中的 `employee_id` 和 `role`。

生产环境使用 PostgreSQL + 真实 Milvus Standalone/Cluster。启动本地真实 Milvus 验证生产依赖：

```bash
docker compose up -d etcd minio milvus
python scripts/check_milvus.py
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
OWNER=chenjun321 REPO=enterprise-agentops-platform VISIBILITY=private bash scripts/publish_to_github.sh
```

打开：

```text
http://127.0.0.1:8000/docs
```

生产环境如果切换 PostgreSQL，应用启动不会自动建表，也不会自动写入 demo 数据；schema 变更必须通过 Alembic 迁移执行。

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
VECTOR_STORE=milvus
MILVUS_URI=http://milvus-standalone:19530
MILVUS_TOKEN=
LLM_PROVIDER=dashscope
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
DASHSCOPE_API_KEY=replace-with-env-secret
INTERNAL_API_KEY=replace-with-long-random-secret
PUBLIC_CHANNEL_TOKEN=replace-with-public-channel-token
PUBLIC_CHANNEL_HEADER_NAME=X-Channel-Token
AUTH_TOKENS_JSON={"support-token":{"employee_id":"support_001","role":"support"},"sales-token":{"employee_id":"sales_001","role":"sales"},"marketing-token":{"employee_id":"marketing_001","role":"marketing"},"admin-token":{"employee_id":"admin_001","role":"admin"}}
ENABLE_API_DOCS=false
EXPOSE_INTERNAL_TRACES=false
LOG_LEVEL=INFO
```

生产环境启动时会强校验三件事：

- 必须配置 `INTERNAL_API_KEY`
- 必须配置至少一个 bearer token 映射 `AUTH_TOKENS_JSON`
- 必须配置 `PUBLIC_CHANNEL_TOKEN`

bearer token 用来把调用方身份绑定到服务端的 `employee_id` / `role`，避免客户端在请求体里自报身份。

示例请求：

```bash
curl http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: replace-with-long-random-secret' \
  -H 'Authorization: Bearer support-token' \
  -d '{
    "message": "用户付款成功了，但是订单一直显示待支付，帮我查原因",
    "context": {"order_no": "O20260505001"}
  }'
```

查看当前认证身份：

```bash
curl http://127.0.0.1:8000/api/me \
  -H 'X-API-Key: replace-with-long-random-secret' \
  -H 'Authorization: Bearer support-token'
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

## 生产部署

应用默认暴露：

- `/health`：基础存活检查
- `/health/db`：数据库就绪检查，需要 `X-API-Key`
- `/api/me`：验证当前 bearer token 映射到的员工身份
- `/api/customer/qa`：C 端 QA 与 Bug 反馈入口，需要 `X-Channel-Token`

容器构建：

```bash
docker build -t enterprise-agentops-platform:latest .
```

容器运行：

```bash
docker run --rm -p 8000:8000 --env-file .env enterprise-agentops-platform:latest
```

应用镜像不会自动执行数据库迁移。上线前请先执行：

```bash
alembic upgrade head
```

## 烟测

```bash
pip install -r requirements-dev.txt
pytest -q
```

端到端演示需要先启动 PostgreSQL、执行迁移并写入 demo 数据：

```bash
SMOKE_BEARER_TOKEN=support-token python scripts/smoke.py
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
