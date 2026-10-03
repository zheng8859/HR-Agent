# Tasks

## 1. API 与纯逻辑

- [x] 1.1 `src/api/interviewPlan.js`：`generatePlan`/`regeneratePlan`/`listPlans`/`getPlan`/`updatePlan`/`exportPlan`（blob）。验证：导出走 blob。
- [x] 1.2 `src/utils/interview.js`：`INTERVIEW_SECTION_TITLES` + `parsePlanSections`（markdown 七分区解析）。验证：分区解析正确。

## 2. 页面组件

- [x] 2.1 `src/views/SmartInterviewView.vue`：候选人选择栏（已完成评估过滤）、生成、七要素分区展示、编辑保存、导出、重新生成、空态。验证：交互完整、空态引导。

## 3. 路由与菜单

- [x] 3.1 `src/router/index.js` 注册 `interview` 路由。验证：路由可访问。
- [x] 3.2 `src/layouts/MainLayout.vue` 启用「智能面试」菜单项。验证：菜单可点击。

## 4. 测试

- [x] 4.1 `tests/interview.test.js`：`parsePlanSections` 七分区、核心问题编号、空内容、缺分区。验证：全绿。
