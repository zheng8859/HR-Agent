"""意图识别快慢双通道（doc 16 §三 / doc 43）。

快通道 `classify_intent_fast`（关键词 + 附件启发式）是**规范实现**——doc 42 的评测参考规则
（`agent_eval.classify_intent_fast`）自 doc 43 起改为从本模块引用，保证「实现 / 评测」同一份规则，
消除双写漂移。快通道命中则不走 LLM；未命中才走慢通道 `_plan_agent_action`（受控 ReAct），
动作空间硬性限定 `chat / use_tool / ask_user`，LLM 失败或无 key 时回退快通道规则（`source=fallback`）。
"""
from __future__ import annotations

import re
from typing import Any

from app.core.config import settings

DELETE_KEYWORDS = ("删除", "删掉", "删了", "移除", "清理", "撤销", "不要了")
OUT_OF_SCOPE_KEYWORDS = ("社保", "邮件", "试卷", "考试", "发票", "工资条")
RESUME_RE = re.compile(r"简历|候选人|筛选|评估|打分|合适|筛人|筛")
EDIT_RE = re.compile(r"改|修改|编辑|更新|调整|润色|完善")
JD_RE = re.compile(r"JD|岗位|职位描述|招聘|启事")
JOB_TITLE_RE = re.compile(r"工程师|经理|专员|设计师|测试|运营|销售|算法|人力|财务|客服|数据分析")
RESOURCE_RE = re.compile(r"JD|岗位|评分标准|简历|候选人|面试|文档|记录")

# 意图 → 路由（确定性，doc 16 §二）
INTENT_ROUTE = {
    "jd": "recruitment.jd",
    "jd_edit": "recruitment.jd",
    "criteria_edit": "recruitment.scoring",
    "resume_screening": "recruitment.resume",
    "interview_plan": "recruitment.interview",
    "resource_delete": "resource",
    "chat": "chat",
}

# 触发工具的角色白名单（doc 14：employee 不能触发招聘工具，仅闲聊/知识问答）
TOOL_ROLES = ("admin", "hr_manager", "hr_specialist")


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
    """确定性意图快通道：返回 intent/route/tool/requires_confirmation/missing_fields。"""
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


def derive_action(intent: str, requires_confirmation: bool = False, missing_fields=None) -> str:
    """把意图/缺口映射到受限动作空间 chat / use_tool / ask_user（doc 16 §三）。"""
    if intent == "chat":
        return "chat"
    if requires_confirmation or (missing_fields or []):
        return "ask_user"
    return "use_tool"


class IntentClassifier:
    """快慢双通道意图分类器（doc 16 §3.2）。"""

    def classify(self, message: str, attachments=None, memory: str | None = None) -> dict:
        """快通道命中则直接返回；未命中走慢通道（受控 ReAct，失败回退）。"""
        fast = classify_intent_fast(message, attachments)
        if fast["intent"] != "chat":
            fast["source"] = "fast"
            fast["action"] = derive_action(
                fast["intent"], fast["requires_confirmation"], fast["missing_fields"]
            )
            return fast
        return self._plan_agent_action(message, attachments, memory)

    def _plan_agent_action(self, message: str, attachments=None, memory: str | None = None) -> dict:
        """慢通道受控 ReAct：动作空间 chat/use_tool/ask_user，use_tool 只能选注册表 intent。

        LLM 未配置或调用失败时回退快通道规则（`source=fallback`）。
        """
        if not settings.llm_configured:
            result = classify_intent_fast(message, attachments)
            result["source"] = "fallback"
            result["action"] = derive_action(
                result["intent"], result["requires_confirmation"], result["missing_fields"]
            )
            return result
        try:
            raw = self._llm_plan_remote(message, attachments, memory)
            return self._validate_plan(raw, message, attachments)
        except Exception:
            result = classify_intent_fast(message, attachments)
            result["source"] = "fallback"
            result["action"] = derive_action(
                result["intent"], result["requires_confirmation"], result["missing_fields"]
            )
            return result

    # ---------- 真实 LLM 钩子（未接入，doc 16 §3.2） ----------

    def _llm_plan_remote(self, message: str, attachments=None, memory: str | None = None) -> dict[str, Any]:
        """调用 Qwen，硬性限定动作空间并返回结构化 JSON。"""
        raise NotImplementedError("真实 LLM 慢通道尚未接入")

    def _validate_plan(self, raw: dict[str, Any], message: str, attachments=None) -> dict:
        """校验慢通道返回：动作空间与 intent 合法性，非法则回退快通道。"""
        intent = raw.get("intent")
        action = raw.get("action")
        if intent not in INTENT_ROUTE:
            raise ValueError(f"慢通道返回非法 intent: {intent}")
        if action not in ("chat", "use_tool", "ask_user"):
            raise ValueError(f"慢通道返回非法 action: {action}")
        return {
            "intent": intent,
            "route": INTENT_ROUTE[intent],
            "tool": "" if intent == "chat" else intent,
            "requires_confirmation": bool(raw.get("requires_confirmation", False)),
            "missing_fields": list(raw.get("missing_fields") or []),
            "source": "slow",
            "action": action,
        }


# 服务层共享的默认分类器
intent_classifier = IntentClassifier()
