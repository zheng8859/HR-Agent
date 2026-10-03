"""Dify 聊天助手客户端（方案 A：单应用单 API Key，靠 inputs.type=1~4 在应用内分支）。

type=1 JD 生成 / type=2 评分标准生成 / type=3 简历评估 / type=4 面试方案。

用户的实际 Dify 应用是「聊天助手 / Chatflow（advanced-chat）」应用，走 `/v1/chat-messages`，
输出在 `answer` 字段（自由文本）——不是工作流应用的 `/v1/workflows/run` 的 structured
`outputs`。因此 `answer` 既可能是 JSON（type=3 现状）也可能是 markdown（type=1/2/4 现状）。
客户端统一「优先按 JSON 解析，解析失败退回 `content`」：结构化字段（dimensions / total_score
/ reason 等）能否拿到，取决于 Dify 应用内各 type 分支是否按要求输出 JSON。

结构化契约（与各 MOCK_* 常量一致，Dify 应用需按此输出 JSON）：
- type=1 JD：{"content": markdown, "department","location","salary_range","experience_level",
  "education","job_type","skills","requirements"}（title 由服务层本地解析，不依赖 Dify）
- type=2 评分标准：{"title","content","total_score","dimensions":[{"name","weight","max_score","description"}]}
- type=3 简历评估：{"candidate_name","candidate_position","work_years","education_level","school",
  "dimensions":[{"name","score","max","reason"}]}（total_score 由维度之和推算，不信任返回）
- type=4 面试方案：{"goal","process","core_questions":[...],"follow_up","dimensions","scoring_advice","risk_points"}

输入映射（后端 service 输入 → Dify 应用输入变量）：
- jobName            ← title / job_title（岗位名称）
- jobResponsibilities ← description（JD 生成用的岗位职责描述）
- jd                 ← job_content（评分/评估/面试用的 JD 内容）
- jianli             ← resume_content（简历内容）
- evaluationModel    ← 面试用的简历评估结果 JSON（仅 type=4）

未配置密钥（无 .env）时进入 mock 模式，返回确定性产物（见各 MOCK_*），保证测试与本地联调可跑
（见 36 文档前置检查「如果暂时没有，测试使用 mock 数据」）。
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from app.core.config import settings

# 确定性 mock 产物（结构对齐真实工作流输出契约）
MOCK_JD_OUTPUT: dict[str, Any] = {
    "title": "前端开发工程师",
    "department": "技术部",
    "location": "上海",
    "salary_range": "20K-35K",
    "experience_level": "3-5年",
    "education": "本科及以上",
    "job_type": "全职",
    "skills": ["Vue", "TypeScript", "Vite", "Element Plus"],
    "requirements": ["负责前端页面开发", "参与系统架构设计", "优化前端性能"],
    "content": (
        "【岗位职责】\n1. 负责核心业务前端开发，使用 Vue 3 + TypeScript。\n"
        "2. 参与前端架构设计与组件库建设。\n"
        "3. 与后端协作完成接口联调与性能优化。\n\n"
        "【任职要求】\n1. 3-5 年前端开发经验。\n"
        "2. 熟练掌握 Vue 3、Vite、Element Plus。\n"
        "3. 本科及以上学历，计算机相关专业优先。"
    ),
}

# 流式 mock 按内容分块，供 SSE delta 打字机效果
MOCK_JD_CONTENT_CHUNKS: list[str] = [
    "【岗位职责】\n1. 负责核心业务前端开发，使用 Vue 3 + TypeScript。\n",
    "2. 参与前端架构设计与组件库建设。\n3. 与后端协作完成接口联调与性能优化。\n\n",
    "【任职要求】\n1. 3-5 年前端开发经验。\n2. 熟练掌握 Vue 3、Vite、Element Plus。\n"
    "3. 本科及以上学历，计算机相关专业优先。",
]

MOCK_SCORING_OUTPUT: dict[str, Any] = {
    "title": "前端开发工程师 评分标准",
    "job_title": "前端开发工程师",
    "content": "针对前端开发岗位的简历评分标准，总分 100 分，含四维度。",
    "total_score": 100,
    "dimensions": [
        {"name": "技能匹配", "weight": 40, "max_score": 40, "description": "硬技能与 JD 要求匹配度"},
        {"name": "工作经验", "weight": 30, "max_score": 30, "description": "相关年限与经验深度"},
        {"name": "项目经验", "weight": 20, "max_score": 20, "description": "项目经历与岗位相关性"},
        {"name": "综合素质", "weight": 10, "max_score": 10, "description": "沟通与稳定性"},
    ],
}

# type=3 简历评估 mock：五维度各带 score/max/reason，维度之和 = total_score（78）
MOCK_RESUME_OUTPUT: dict[str, Any] = {
    "candidate_name": "张三",
    "candidate_position": "前端开发工程师",
    "education_level": "本科",
    "school": "示例大学",
    "work_years": 5,
    "total_score": 78,
    "dimensions": [
        {"name": "学历匹配度", "score": 16, "max": 20, "reason": "本科学历，与岗位要求本科及以上匹配"},
        {"name": "工作经验", "score": 20, "max": 25, "reason": "五年相关工作经验，经验深度达标"},
        {"name": "技能匹配度", "score": 22, "max": 25, "reason": "掌握 Vue/TypeScript 等核心技能"},
        {"name": "项目经验匹配度", "score": 14, "max": 20, "reason": "有中台与微前端项目经验"},
        {"name": "综合素质", "score": 6, "max": 10, "reason": "沟通表达清晰，稳定性良好"},
    ],
}


# type=4 面试方案 mock：七要素（面试目标/流程/核心问题/追问建议/考察维度/评分建议/候选人风险点）
MOCK_INTERVIEW_OUTPUT: dict[str, Any] = {
    "goal": "评估候选人张三（前端开发工程师）与岗位要求的匹配度，重点验证 Vue/TypeScript 实战能力与项目深度。",
    "process": (
        "1. 开场自我介绍（3 分钟）；2. 技术面：Vue 3 响应式原理与 TypeScript 类型设计（20 分钟）；"
        "3. 项目面：中台/微前端项目难点复盘（15 分钟）；4. 行为面：协作与稳定性（10 分钟）；"
        "5. 候选人反问与答疑（5 分钟）。"
    ),
    "core_questions": [
        "请说明 Vue 3 响应式系统与 Vue 2 的核心差异，以及你如何在项目中利用这些特性优化性能？",
        "描述一个你用 TypeScript 重构既有代码的案例，遇到过哪些类型设计难点？",
        "介绍你参与过的微前端/中台项目，你在其中承担什么角色、解决了什么关键技术问题？",
        "遇到过线上性能瓶颈吗？你是如何定位并优化的？",
    ],
    "follow_up": "对候选人回答中模糊的细节追问「具体数据/指标」「你在其中的个人贡献」「失败案例与复盘」；技术回答需追问边界条件与取舍。",
    "dimensions": "重点考察：技能匹配度（22/25，优势项）、项目经验匹配度（14/20，需深挖）、综合素质（6/10，稳定性需确认）。",
    "scoring_advice": "建议沿用简历评估五维度权重（学历20/经验25/技能25/项目20/综合10），面试表现按 0-10 打分后折算，重点扣分项写明依据。",
    "risk_points": "项目经验匹配度偏低（14/20）且微前端细节需验证；沟通表达需观察稳定性；注意候选人期望薪资是否在岗位区间内。",
}


class DifyClient:
    """Dify 聊天助手客户端。无密钥时 mock 模式。"""

    def __init__(self) -> None:
        self.base_url = settings.dify_base_url.rstrip("/")
        self.api_key = settings.dify_api_key
        self.timeout = settings.dify_timeout_seconds

    @property
    def mock_mode(self) -> bool:
        return not settings.dify_configured

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def _chat(self, inputs: dict[str, Any], query: str) -> str:
        """阻塞式调用聊天助手 /v1/chat-messages，返回 answer 文本。"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat-messages",
                headers=self._headers(),
                json={
                    "inputs": inputs,
                    "query": query,
                    "response_mode": "blocking",
                    "conversation_id": "",
                    "user": "hr-agent",
                },
            )
            resp.raise_for_status()
            return resp.json().get("answer", "") or ""

    @staticmethod
    def _parse_answer(answer: str) -> dict[str, Any]:
        """把 answer 解析为结构化 dict：JSON 直接解析；markdown 退回 {"content": answer}。"""
        text = (answer or "").strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
        return {"content": answer}

    async def run_jd_workflow(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """type=1：生成 JD。"""
        if self.mock_mode:
            return MOCK_JD_OUTPUT
        answer = await self._chat(
            {
                "type": 1,
                "jobName": inputs.get("title", ""),
                "jobResponsibilities": inputs.get("description", ""),
            },
            "请根据岗位名称与职责生成一份完整的 JD",
        )
        return self._parse_answer(answer)

    async def run_scoring_workflow(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """type=2：生成评分标准。"""
        if self.mock_mode:
            return MOCK_SCORING_OUTPUT
        answer = await self._chat(
            {
                "type": 2,
                "jobName": inputs.get("job_title", ""),
                "jd": inputs.get("job_content", ""),
            },
            "请根据岗位生成评分标准",
        )
        return self._parse_answer(answer)

    async def run_resume_workflow(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """type=3：简历评估（五维度打分 + 理由）。"""
        if self.mock_mode:
            return MOCK_RESUME_OUTPUT
        answer = await self._chat(
            {
                "type": 3,
                "jianli": inputs.get("resume_content", ""),
                "jobName": inputs.get("job_title", ""),
                "jd": inputs.get("job_content", ""),
            },
            "请评估简历",
        )
        return self._parse_answer(answer)

    async def run_interview_workflow(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """type=4：面试方案（七要素）。"""
        if self.mock_mode:
            return MOCK_INTERVIEW_OUTPUT
        eval_model = {
            "total_score": inputs.get("total_score"),
            "evaluation_metrics": inputs.get("evaluation_metrics", []),
        }
        answer = await self._chat(
            {
                "type": 4,
                "jianli": inputs.get("resume_content", ""),
                "jobName": inputs.get("job_title", ""),
                "jd": inputs.get("job_content", ""),
                "evaluationModel": json.dumps(eval_model, ensure_ascii=False),
            },
            "请生成面试方案",
        )
        return self._parse_answer(answer)

    async def stream_jd_workflow(self, inputs: dict[str, Any]) -> AsyncIterator[str]:
        """type=1 流式：逐块 yield 文本片段（mock 按固定分块；真实按 message 事件增量）。"""
        if self.mock_mode:
            for chunk in MOCK_JD_CONTENT_CHUNKS:
                yield chunk
            return
        body = {
            "inputs": {
                "type": 1,
                "jobName": inputs.get("title", ""),
                "jobResponsibilities": inputs.get("description", ""),
            },
            "query": "请根据岗位名称与职责生成一份完整的 JD",
            "response_mode": "streaming",
            "conversation_id": "",
            "user": "hr-agent",
        }
        prev = ""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat-messages",
                headers=self._headers(),
                json=body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[len("data:"):].strip()
                    if not payload or payload == "[DONE]":
                        continue
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if event.get("event") != "message":
                        continue
                    answer = event.get("answer", "")
                    delta = answer[len(prev):] if answer.startswith(prev) else answer
                    prev = answer
                    if delta:
                        yield delta


# 服务层共享的默认客户端
dify_client = DifyClient()
