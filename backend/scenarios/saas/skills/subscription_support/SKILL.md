---
name: AcmeCloud 订阅套餐规范
description: 套餐、功能权限、配额与到期时间说明
keywords: 套餐,订阅,权限,配额,基础版,专业版,企业版,降级,subscription,plan
agents: subscription
enabled: true
---
# AcmeCloud 订阅套餐规范

- 套餐与功能结论必须来自 `check_subscription`。
- 区分套餐包含、租户开关和用户角色三层权限。
- 不执行升降级、退费、合同变更或价格承诺。
- 需要变更时说明由租户管理员或人工审核。
