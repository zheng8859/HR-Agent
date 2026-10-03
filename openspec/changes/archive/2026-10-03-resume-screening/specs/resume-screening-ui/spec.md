# resume-screening-ui Specification

## Purpose
定义简历筛选页的前端交互能力：简历上传与前端校验、选择 JD/评分标准触发评估、评估中进度态与重复提交防护、评分卡展示总分与维度分/理由、候选人状态流转、导出报告、空态与失败态。

## ADDED Requirements

### Requirement: 简历上传与前端校验

页面 SHALL 支持点击或拖拽上传 PDF/DOC/DOCX 简历，格式或大小不符给出明确提示（与后端校验一致）。

#### Scenario: 非法格式提示
- **WHEN** 用户选择非 PDF/DOC/DOCX 文件
- **THEN** 页面提示支持的格式，不发起上传

#### Scenario: 超限提示
- **WHEN** 用户选择超过 10MB 的文件
- **THEN** 页面提示大小上限，不发起上传

### Requirement: 选择 JD 与评分标准后评估

页面 SHALL 要求选择岗位 JD（必选）方可触发评估，评分标准可选；未选 JD 时禁用评估操作。

#### Scenario: 未选 JD 禁用评估
- **WHEN** 未选择 JD
- **THEN** 评估按钮禁用或提示先选择 JD

#### Scenario: 触发评估
- **WHEN** 已上传简历并选择 JD 后触发评估
- **THEN** 调用后端评估接口，成功后展示评分结果

### Requirement: 评估中进度态与重复提交防护

页面 SHALL 在评估进行中展示进度态，并禁止重复提交。

#### Scenario: 评估中禁止重复提交
- **WHEN** 评估请求进行中
- **THEN** 评估按钮展示加载态且不可再次点击

### Requirement: 评分卡展示总分与维度分/理由

页面 SHALL 展示候选人的总分与各维度 `score/max/reason`，评分结果以接口返回为准，不前端臆算。

#### Scenario: 维度与理由完整展示
- **WHEN** 选中一条评估记录
- **THEN** 评分卡展示总分、各维度得分、满分与评分理由

### Requirement: 候选人状态流转

页面 SHALL 支持 HR 通过状态下拉更新候选人状态（`pending`/`interview`/`rejected`）。

#### Scenario: 更新状态
- **WHEN** HR 将候选人状态更新为 `interview` 或 `rejected`
- **THEN** 调用后端状态接口，状态更新生效

### Requirement: 导出报告

页面 SHALL 支持将评估结果导出为可下载报告，包含总分、维度分与理由。

#### Scenario: 导出报告
- **WHEN** 用户点击导出报告
- **THEN** 触发评估结果下载

### Requirement: 空态与失败态

页面 SHALL 在无评估记录时展示空态引导，评估或上传失败时展示明确错误提示。

#### Scenario: 无记录空态
- **WHEN** 当前无评估记录
- **THEN** 展示「先上传并评估简历」的空态引导

#### Scenario: 失败提示
- **WHEN** 上传或评估失败
- **THEN** 展示后端返回的明确错误信息
