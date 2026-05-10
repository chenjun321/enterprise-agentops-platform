---
title: 支付回调延迟排障手册
domain: customer_qa
doc_type: runbook
permission_level: support
version: v1
---

# 支付回调延迟排障手册

当支付渠道返回成功，但订单仍显示 pending 或 unpaid 时，优先检查支付回调和对账任务。

典型证据：

- payments.status = success
- orders.status = pending
- 日志包含 PAYMENT_CALLBACK_TIMEOUT 或 payment callback timeout
- callback_received = false

处理动作：

1. 告知用户支付状态同步可能有延迟。
2. 内部触发 payment_reconcile_job。
3. 如果对账仍失败，转工程排查 payment callback handler。

