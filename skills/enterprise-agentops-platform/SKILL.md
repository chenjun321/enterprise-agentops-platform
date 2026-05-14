---
name: enterprise-agentops-platform
description: "Enterprise AgentOps Platform 仓库协作技能。用于阅读这个项目的统一入口、销售/市场/客服 QA 三条业务链路，进行本地启动、测试、鉴权调整、Agent 编排和工具层修改。"
---

# Enterprise AgentOps Platform

用于这个仓库的开发、排查和代码阅读。

## 什么时候用

- 用户想阅读这个仓库的业务逻辑
- 用户想修改 `/api/chat` 的行为
- 用户想排查销售、市场、客服 QA 的 agent 流程
- 用户想调整工具权限、memory、RAG、审计或鉴权
- 用户想在本地启动、测试或准备生产部署

## 快速入口

先看这些文件：

- `app/main.py`
- `app/api/routes.py`
- `app/agents/orchestrator.py`
- `app/agents/router.py`
- `app/agents/planner.py`
- `app/agents/executor.py`
- `app/agents/business_agents.py`

## 工作方式

这个项目是“一个统一 API 入口 + 内部多 Agent 分流”。

统一入口：

- `POST /api/chat`

优先按下面顺序理解问题：

1. 先判断是销售、市场还是客服 QA
2. 再看 planner 生成了哪些步骤
3. 再看 executor 调用了哪些 tools
4. 最后看 synthesizer 如何组装输出

## 参考资料

需要更详细信息时再读：

- 业务链路与模块分层：`references/architecture.md`
- 本地启动、测试、生产约束：`references/runtime.md`

## 修改时注意

- 不要把请求体里的 `employee_id` / `role` 当成生产可信身份
- 改工具行为时，同时检查 `app/security/policies.py`
- 改响应结构时，同时检查 `tests/test_smoke.py`
- 改数据库结构时，补 Alembic migration
- 不要把 `data/docs/` 里的业务手册误当成开发 skill
