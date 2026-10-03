"""L1 单元测试（doc 42 §7：30 道）——评测纯函数与确定性参考规则。

覆盖：意图匹配 8 + 缺口分类 6 + 状态机 8 + 评分求和 4 + 工具/契约边界 4。
全部为无 DB 的纯函数，`@pytest.mark.l1`。
"""
import pytest

from app.evaluations import eval_utils as eu
from app.evaluations.agent_eval import classify_intent_fast

pytestmark = pytest.mark.l1


# ---------- 意图匹配（8） ----------

def test_intent_match_exact_true():
    assert eu.intent_match("jd", "jd") is True


def test_intent_match_exact_false():
    assert eu.intent_match("jd", "jd_edit") is False


def test_route_match_exact():
    assert eu.route_match("recruitment.jd", "recruitment.jd") is True
    assert eu.route_match("recruitment.jd", "recruitment.resume") is False


def test_classify_intent_jd():
    r = classify_intent_fast("帮我写一个前端开发工程师的 JD")
    assert r["intent"] == "jd"
    assert r["route"] == "recruitment.jd"
    assert r["missing_fields"] == []


def test_classify_intent_jd_edit():
    r = classify_intent_fast("修改这个 JD 的任职要求")
    assert r["intent"] == "jd_edit"
    assert r["route"] == "recruitment.jd"


def test_classify_intent_criteria_edit():
    r = classify_intent_fast("更新这份评分标准")
    assert r["intent"] == "criteria_edit"
    assert r["route"] == "recruitment.scoring"


def test_classify_intent_resume_screening():
    r = classify_intent_fast("评估这批候选人的简历")
    assert r["intent"] == "resume_screening"
    assert r["route"] == "recruitment.resume"


def test_classify_intent_interview_plan():
    r = classify_intent_fast("帮我设计一套面试方案")
    assert r["intent"] == "interview_plan"
    assert r["route"] == "recruitment.interview"


# ---------- 缺口分类（6） ----------

def test_missing_fields_match_full():
    assert eu.missing_fields_match(["job_title"], ["job_title"]) == 1.0


def test_missing_fields_match_partial():
    assert eu.missing_fields_match(["job_title"], ["job_title", "jd_id"]) == 0.5


def test_classify_jd_missing_job_title():
    r = classify_intent_fast("帮我写个 JD")
    assert r["intent"] == "jd"
    assert r["missing_fields"] == ["job_title"]


def test_classify_delete_missing_target():
    r = classify_intent_fast("删掉这个")
    assert r["intent"] == "resource_delete"
    assert r["missing_fields"] == ["target"]


def test_classify_delete_requires_confirmation():
    r = classify_intent_fast("删除这个候选人")
    assert r["intent"] == "resource_delete"
    assert r["requires_confirmation"] is True
    assert r["missing_fields"] == []


def test_classify_chat_no_missing_fields():
    r = classify_intent_fast("帮我看看社保政策")
    assert r["intent"] == "chat"
    assert r["tool"] == ""
    assert r["missing_fields"] == []


# ---------- 状态机（SSE 事件序列 / 结构完整性，8） ----------

def test_sse_chat_sequence_complete():
    assert eu.sse_event_sequence_complete(["thinking", "plan", "delta", "final"]) is True


def test_sse_task_sequence_complete():
    assert (
        eu.sse_event_sequence_complete(
            ["progress", "delta", "artifact", "final"], task_mode=True
        )
        is True
    )


def test_sse_sequence_incomplete():
    assert eu.sse_event_sequence_complete(["thinking", "plan", "delta"]) is False


def test_sse_sequence_order_matters():
    assert (
        eu.sse_event_sequence_complete(["delta", "thinking", "plan", "final"]) is False
    )


def test_sse_sequence_extra_event_allowed():
    # 允许在必备事件之间插入额外事件，但必备事件须按序出现
    assert (
        eu.sse_event_sequence_complete(
            ["thinking", "progress", "plan", "delta", "final"]
        )
        is True
    )


def test_build_sse_event_valid():
    frame = eu.build_sse_event("delta", {"text": "hi"})
    assert frame == 'event: delta\ndata: {"text": "hi"}\n\n'


def test_build_sse_event_invalid_raises():
    with pytest.raises(ValueError):
        eu.build_sse_event("bogus", {})


def test_structure_completeness_string():
    assert (
        eu.structure_completeness(
            "岗位职责与任职要求如下", ["岗位职责", "任职要求", "技能要求"]
        )
        == pytest.approx(2 / 3)
    )
    assert eu.structure_completeness(["岗位职责", "技能要求"], ["岗位职责", "技能要求"]) == 1.0


# ---------- 评分求和（4） ----------

def test_score_sum_valid_true():
    dims = [{"name": "专业能力", "max_score": 40}, {"name": "沟通", "max_score": 60}]
    assert eu.score_sum_valid(dims, 100) is True


def test_score_sum_valid_false():
    dims = [{"max_score": 40}, {"max_score": 50}]
    assert eu.score_sum_valid(dims, 100) is False


def test_score_sum_valid_resume_key():
    # 简历评估维度分键为 score
    dims = [{"name": "匹配度", "score": 80}, {"name": "潜力", "score": 20}]
    assert eu.score_sum_valid(dims, 100, key="score") is True


def test_score_sum_valid_empty_dims():
    assert eu.score_sum_valid([], 0) is True
    assert eu.score_sum_valid([], 100) is False


# ---------- 工具 / 契约边界（4） ----------

def test_is_registered_tool_true():
    assert eu.is_registered_tool("resume_screening") is True


def test_is_registered_tool_false():
    assert eu.is_registered_tool("email_notification") is False


def test_is_out_of_scope_tool():
    assert eu.is_out_of_scope_tool("exam_generate") is True
    assert eu.is_out_of_scope_tool("jd") is False


def test_contract_fields_complete():
    required = list(eu.AGENT_CONTRACT_FIELDS)
    assert eu.contract_fields_complete(required) is True
    assert eu.contract_fields_complete(required[:-1]) is False
