"""知识问答评测器（doc 42 §6.2）：检索指标（recall/hit/rank）+ 生成指标。

检索与生成分开测：检索样本测 recall/hit/rank，生成样本测关键词覆盖 / 无依据拒答，
并顺带输出忠实度/相关性/引用准确率。
"""
from __future__ import annotations

from typing import Any

from app.evaluations import eval_utils as eu
from app.evaluations.base import BaseEvaluator, EvalResult
from app.services.rag_service import ask, filter_below_threshold, retrieve


class RagEvaluator(BaseEvaluator):
    suite = "rag"
    threshold = 0.70

    def __init__(
        self,
        user: Any = None,
        knowledge_base_id: Any = None,
        db: Any = None,
        mock: bool = True,
    ) -> None:
        super().__init__(mock)
        self.user = user
        self.knowledge_base_id = knowledge_base_id
        self.db = db

    async def evaluate_one(self, sample: dict) -> EvalResult:
        question = sample["input"]["question"]
        expected = sample.get("expected") or {}
        retrieval = expected.get("retrieval") or {}
        generation = expected.get("generation") or {}
        expected_doc_ids = retrieval.get("expected_doc_ids") or []
        metrics: dict[str, float] = {}
        recall_ok = True

        # 检索指标（期望文档非空才测）
        if expected_doc_ids:
            ranked = await retrieve(question, self.user, self.knowledge_base_id, self.db)
            ranked = filter_below_threshold(ranked)
            names = [
                r["document"].original_filename or r["document"].filename
                for r in ranked
            ]
            recall = eu.retrieval_recall(names, expected_doc_ids)
            hit = eu.retrieval_hit_at_k(names, expected_doc_ids, 5)
            mrr = eu.retrieval_rank(names, expected_doc_ids)
            metrics["recall"] = recall
            metrics["hit_at_5"] = hit
            metrics["mrr"] = mrr
            recall_ok = recall >= retrieval.get("min_recall", 0.8)

        # 生成指标
        result = await ask(question, self.user, self.knowledge_base_id, self.db)
        should_refuse = generation.get("should_refuse", False)
        if should_refuse:
            refused = not result.get("answered", True)
            metrics["refuse_correct"] = 1.0 if refused else 0.0
            gen_ok = refused
        else:
            answer = result.get("answer", "")
            keywords = generation.get("should_contain_keywords") or []
            ratio = eu.keyword_match_ratio(answer, keywords) if keywords else 1.0
            chunks = result.get("document_chunks") or []
            source_texts = [c.get("chunk_text", "") for c in chunks]
            metrics["keyword_ratio"] = ratio
            metrics["faithfulness"] = eu.faithfulness(answer, source_texts)
            metrics["relevance"] = eu.relevance(answer, question)
            tol = (sample.get("tolerance") or {}).get("keyword_match_ratio", 0.7)
            gen_ok = ratio >= tol

        passed = recall_ok and gen_ok
        category = "retrieval" if expected_doc_ids else "generation"
        return EvalResult(
            sample_id=sample["id"],
            passed=passed,
            metrics=metrics,
            category=category,
            detail=question,
        )
