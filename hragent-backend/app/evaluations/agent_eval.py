"""Agent 编排评测器（doc 42 §6.2）：意图匹配、契约检查、确认判定、工具边界。

Agent 编排层（文档 43）尚未实现，故本模块提供「确定性参考规则」`classify_intent_fast`
（编码 16 号文档 §二/§三契约：意图枚举、路由、工具注册表、缺口分类、高风险确认）。
用于 (a) 校验 Golden 样本自洽；(b) L3 `agent_cases` 无真实 Agent 时以 mock 跑通框架。
文档 43 落地时，其快通道实现须与本参考规则在 Golden 样本上行为一致。
"""
from __future__ import annotations

import re

from app.evaluations import eval_utils as eu
from app.evaluations.base import BaseEvaluator, EvalResult

DELETE_KEYWORDS = ("删除", "删掉", "删了", "移除", "清理", "撤销", "不要了")
OUT_OF_SCOPE_KEYWORDS = ("社保", "邮件", "试卷", "考试", "发票", "工资条")
RESUME_RE = re.compile(r"简历|候选人|筛选|评估|打分|合适|筛人|筛")
EDIT_RE = re.compile(r"改|修改|编辑|更新|调整|润色|完善")
JD_RE = re.compile(r"JD|岗位|职位描述|招聘|启事")
JOB_TITLE_RE = re.compile(r"工程师|经理|专员|设计师|测试|运营|销售|算法|人力|财务|客服|数据分析")
RESOURCE_RE = re.compile(r"JD|岗位|评分标准|简历|候选人|面试|文档|记录")

# 意图 → 路由（确定性）
INTENT_ROUTE = {
    "jd": "recruitment.jd",
    "jd_edit": "recruitment.jd",
    "criteria_edit": "recruitment.scoring",
    "resume_screening": "recruitment.resume",
    "interview_plan": "recruitment.interview",
    "resource_delete": "resource",
    "chat": "chat",
}


def _intent(intent: str, requires_confirmation: bool = False, missing_fields=None) -> dict:
    tool = "" if intent == "chat" else intent
    return {
        "intent": intent,
        "route": INTENT_ROUTE[intent],
        "tool": tool,
        "requires_confirmation": requires_confirmation,
        "missing_fields": missing_fields or [],
    }


def classify_intent_fast(message: str, attachments=None) -> dict:
    """确定性意图快通道参考规则：返回 intent/route/tool/requires_confirmation/missing_fields。"""
    attachments = attachments or []
    m = message or ""
    # 1. 删除类 → 高风险锁定
    if any(k in m for k in DELETE_KEYWORDS):
        missing = [] if RESOURCE_RE.search(m) else ["target"]
        return _intent("resource_delete", requires_confirmation=True, missing_fields=missing)
    # 2. 清单外 → 普通回复（明确办不了）
    if any(k in m for k in OUT_OF_SCOPE_KEYWORDS):
        return _intent("chat")
    # 3. 面试
    if "面试" in m:
        return _intent("interview_plan")
    # 4. 评分标准
    if "评分标准" in m:
        return _intent("criteria_edit")
    # 5. 简历筛选/评估
    if RESUME_RE.search(m) or "resume" in attachments:
        return _intent("resume_screening")
    # 6. 编辑 JD
    if JD_RE.search(m) and EDIT_RE.search(m):
        return _intent("jd_edit")
    # 7. 生成 JD
    if JD_RE.search(m):
        missing = [] if JOB_TITLE_RE.search(m) else ["job_title"]
        return _intent("jd", missing_fields=missing)
    # 8. 兜底 → 普通回复
    return _intent("chat")


class AgentEvaluator(BaseEvaluator):
    """Agent 编排评测器：规则检查为主，语义裁判挂点见 _llm_judge。"""

    suite = "agent"
    threshold = 0.90

    async def evaluate_one(self, sample: dict) -> EvalResult:
        actual = classify_intent_fast(
            sample["input"]["message"], sample["input"].get("attachments")
        )
        expected = sample.get("expected") or {}
        metrics: dict[str, float] = {}

        intent_ok = eu.intent_match(actual["intent"], expected.get("intent"))
        metrics["intent_match"] = 1.0 if intent_ok else 0.0

        route_ok = eu.route_match(actual["route"], expected.get("route"))
        metrics["route_match"] = 1.0 if route_ok else 0.0

        confirm_ok = eu.requires_confirmation_match(
            actual["requires_confirmation"], expected.get("requires_confirmation", False)
        )
        metrics["requires_confirmation"] = 1.0 if confirm_ok else 0.0

        # 工具边界：期望工具须在注册表内（chat 无工具）
        expected_tool = expected.get("tool")
        tool_ok = True if not expected_tool else eu.is_registered_tool(expected_tool)
        metrics["tool_registered"] = 1.0 if tool_ok else 0.0

        mf_score = eu.missing_fields_match(
            actual["missing_fields"], expected.get("missing_fields") or []
        )
        metrics["missing_fields"] = mf_score

        passed = intent_ok and route_ok and confirm_ok and tool_ok
        detail = f"actual={actual['intent']} expected={expected.get('intent')}"
        return EvalResult(
            sample_id=sample["id"],
            passed=passed,
            metrics=metrics,
            category=sample.get("category", ""),
            detail=detail,
        )

    def _llm_judge(self, sample: dict, actual: dict) -> float:
        """LLM 语义裁判挂点（真实 L3 慢速路径预留）。mock 阶段不调用。"""
        return 1.0
