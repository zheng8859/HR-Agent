"""Rerank 服务测试：mock 保持原始召回排序并截断，失败降级回退不中断。"""
from app.services import rerank_service


def test_rerank_mock_truncates_top_k():
    # 输入按原始召回分降序（id0=4 最高）
    items = [{"id": i, "score": float(4 - i)} for i in range(5)]
    out = rerank_service.rerank("q", items, top_k=2)
    assert len(out) == 2
    # mock 保持原始召回排序，仅截断
    assert [i["id"] for i in out] == [0, 1]


def test_rerank_or_fallback_returns_original_on_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("rerank down")

    monkeypatch.setattr(rerank_service, "rerank", boom)
    items = [{"id": "a", "score": 0.9}, {"id": "b", "score": 0.5}]
    out = rerank_service.rerank_or_fallback("q", items, top_k=10)
    # 失败回退为原始召回排序，不抛异常
    assert [i["id"] for i in out] == ["a", "b"]


def test_rerank_or_fallback_truncates_on_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("rerank down")

    monkeypatch.setattr(rerank_service, "rerank", boom)
    items = [{"id": i, "score": float(4 - i)} for i in range(5)]
    out = rerank_service.rerank_or_fallback("q", items, top_k=2)
    assert [i["id"] for i in out] == [0, 1]
