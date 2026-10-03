"""走库判断测试：闲聊关键词预筛 + LLM 分类 KB/GENERAL。"""
from app.services.kb_selection_service import is_chitchat, should_use_kb


def test_chitchat_pure_greeting():
    assert is_chitchat("你好") is True
    assert is_chitchat("谢谢") is True
    assert is_chitchat("你是谁") is True
    assert is_chitchat("  你好  ") is True


def test_chitchat_with_question_not_chitchat():
    assert is_chitchat("你好，请问年假怎么算") is False
    assert is_chitchat("出差住宿标准是多少") is False


def test_chitchat_empty():
    assert is_chitchat("") is True


def test_should_use_kb_policy():
    assert should_use_kb("年假休假规则") is True


def test_should_use_kb_chitchat():
    assert should_use_kb("你好") is False


def test_should_use_kb_general_smalltalk():
    assert should_use_kb("讲个笑话") is False
