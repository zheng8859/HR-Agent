# Tasks

## 1. 纯逻辑与测试（RED 先行）

- [x] 1.1 `src/utils/resume.js`：`validateResumeFile(filename, size)`（扩展名 `pdf/doc/docx`、默认 ≤10MB，返回 `{ok, ext?, error?}`）与 `dimensionPct(score, max)`（0–100，max≤0 返回 0）。验证：非法扩展名/超限/合法大写扩展名/百分比。
- [x] 1.2 `tests/resume.test.js`：覆盖上述纯逻辑。

## 2. API 客户端

- [x] 2.1 `src/api/resumeEvaluation.js`：`uploadResume(file)`（multipart）、`evaluateResume(payload)`、`listResumes()`、`updateResumeStatus(id, status)`、`exportResume(id)`。验证：与后端端点路径一致。

## 3. 页面组件

- [x] 3.1 `src/views/ResumeScreeningView.vue`：上传区（点击/拖拽 + 校验提示）、JD/评分标准选择、评估进度态与重复提交防护、候选人表格（行点击联动）、评分卡（总分 + 维度分/理由 + 进度条）、状态流转下拉、导出、空态/失败态。验证：`vite build` 通过。

## 4. 路由与菜单

- [x] 4.1 `src/router/index.js` 注册 `resume-screening` 路由（title「简历筛选」）。
- [x] 4.2 `src/layouts/MainLayout.vue` 启用「简历筛选」菜单项（去掉 `disabled`）。

## 5. 联调与验收

- [x] 5.1 前后端启动，跑通「上传 → 评估 → 展示 → 状态 → 导出」全流程（mock 模式）。
- [x] 5.2 `npm run test` 全绿 + `npm run build` 通过。
