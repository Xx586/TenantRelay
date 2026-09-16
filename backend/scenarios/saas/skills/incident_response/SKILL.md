---
name: AcmeCloud 故障响应规范
description: 生产故障的影响确认、状态检查和升级边界
keywords: 故障,服务挂了,生产,全部超时,大面积,outage,incident,production
agents: incident
enabled: true
---
# AcmeCloud 故障响应规范

- 先确认生产/测试环境、区域、影响用户和发生时间。
- 服务状态必须来自白名单健康检查，回答中附检查时点。
- 生产大面积不可用、数据丢失或安全事件立即标记 CRITICAL。
- 不承诺恢复时间，不声称已找到未经验证的根因。
