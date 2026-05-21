---
title: C 端 Bug 反馈处理口径
domain: customer_qa
doc_type: bug_policy
permission_level: public
version: v1
---

# C 端 Bug 反馈处理口径

Bug 反馈需要记录 customer_user_id、联系方式、发生页面、发生时间、设备、浏览器、复现步骤、截图或录屏。缺少这些信息时也应先创建工单，再引导用户补充。

对用户的回复应明确三件事：已收到反馈、工单号、后续处理方式。不要向用户暴露内部日志、代码文件、数据库表名、服务名或未经确认的根因。

严重程度建议：

- critical：无法登录、无法支付、资金或奖励异常、影响大量用户。
- high：核心任务无法完成、数据展示明显错误。
- normal：单个页面体验异常、提示文案不清晰、偶发错误。

客服和工程内部可继续通过 trace_id、订单号、用户 ID、日志和 runbook 做二次排查。
