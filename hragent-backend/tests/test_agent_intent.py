"""意图快慢双通道单元测试（doc 43 §三）：快通道命中、缺口、删除锁定、慢通道回退、动作空间。"""
import pytest

from app.services.intent_service import (
    classify_intent_fast,
    derive_action,
    intent_classifier,
)

pytestmark = pytest.mark.l1


@pytest.mark.parametrize(
    "message,expected_intent,expected_route,missing",
    [
        ("帮我生成一份前端开发工程师的 JD", "jd", "recruitment.jd", []),
        ("写一个岗位描述，招聘产品经理", "jd", "recruitment.jd", []),
        ("帮我生成一份 JD", "jd", "recruitment.jd", ["job_title"]),
        ("把这份 JD 的任职要求改一下", "jd_edit", "recruitment.jd", []),
        ("更新 JD 里的薪资范围", "jd_edit", "recruitment.jd", []),
        ("调整一下评分标准的权重", "criteria_edit", "recruitment.scoring", []),
        ("评估这份简历", "resume_screening", "recruitment.resume", []),
        ("生成一份面试方案", "interview_plan", "recruitment.interview", []),
    ],
)
def test_classify_intent_fast(message, expected_intent, expected_route, missing):
    r = classify_intent_fast(message)
    assert r["intent"] == expected_intent
    assert r["route"] == expected_route
    assert r["missing_fields"] == missing


def test_resume_screening_by_attachment():
    assert classify_intent_fast("看看这个", ["resume"])["intent"] == "resume_screening"


def test_delete_requires_confirmation():
    r = classify_intent_fast("删除这份 JD")
    assert r["intent"] == "resource_delete"
    assert r["requires_confirmation"] is True


def test_delete_without_target_missing_fields():
    assert classify_intent_fast("删除")["missing_fields"] == ["target"]


def test_out_of_scope_returns_chat():
    assert classify_intent_fast("帮我查社保记录")["intent"] == "chat"
    assert classify_intent_fast("给候选人发面试通知邮件")["intent"] == "chat"
    assert classify_intent_fast("帮我生成考试试卷")["intent"] == "chat"


def test_chitchat_returns_chat():
    assert classify_intent_fast("你好")["intent"] == "chat"


def test_fast_channel_hit_marked_fast():
    r = intent_classifier.classify("生成一份 JD")
    assert r["source"] == "fast"


def test_slow_channel_fallback_when_llm_unconfigured():
    r = intent_classifier.classify("今天天气怎么样")
    assert r["intent"] == "chat"
    assert r["source"] == "fallback"


@pytest.mark.parametrize(
    "intent,confirmation,missing,expected_action",
    [
        ("chat", False, [], "chat"),
        ("jd", False, ["job_title"], "ask_user"),
        ("jd", False, [], "use_tool"),
        ("resource_delete", True, [], "ask_user"),
    ],
)
def test_derive_action(intent, confirmation, missing, expected_action):
    assert derive_action(intent, confirmation, missing) == expected_action
