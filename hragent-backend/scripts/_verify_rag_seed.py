"""内部校验脚本：在 mock 模式下验证 RAG 规范文档对 30 个 rag 样本的检索/生成命中。

用法：
    python scripts/_verify_rag_seed.py

用 hragent_test 测试库（先建库建表，跑完不落库），逐个样本打印期望/实际/召回/关键词。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.models import Base, User  # noqa: E402
from app.services.rag_service import ask, filter_below_threshold, retrieve  # noqa: E402
from app.evaluations import eval_utils as eu  # noqa: E402
from app.evaluations.eval_seed import seed_eval_kb  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402

TEST_DB_NAME = "hragent_test"
TEST_DATABASE_URL = (
    "postgresql+asyncpg://hragent:hragent_dev_password@localhost:5432/hragent_test"
)


async def _ensure_test_db() -> None:
    conn = await asyncpg.connect(
        host="localhost", port=5432, user="hragent",
        password="hragent_dev_password", database="hragent", ssl=False,
    )
    exists = await conn.fetchval(
        "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
    )
    if not exists:
        await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    await conn.close()


async def main() -> None:
    await _ensure_test_db()
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, connect_args={"ssl": False})
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        await db.begin()
        user = User(
            username="eval_user", email="eval@example.com",
            hashed_password=get_password_hash("secret123"), role="hr_manager",
            is_superuser=False, is_active=True,
        )
        db.add(user)
        await db.flush()
        kb = await seed_eval_kb(db, user)
        await db.commit()

        total = passed = 0
        for suite in ("rag",):
            for sample in eu.load_golden(suite, BACKEND_ROOT / "evals"):
                q = sample["input"]["question"]
                exp = sample["expected"]
                exp_ids = exp["retrieval"].get("expected_doc_ids") or []
                should_refuse = exp["generation"].get("should_refuse", False)
                keywords = exp["generation"].get("should_contain_keywords") or []

                ranked = await retrieve(q, user, kb.id, db)
                above = filter_below_threshold(ranked)
                names = [r["document"].original_filename for r in above]
                recall = eu.retrieval_recall(names, exp_ids) if exp_ids else None

                result = await ask(q, user, kb.id, db)
                if should_refuse:
                    gen_ok = not result.get("answered", True)
                    gen_note = f"refuse={gen_ok}"
                else:
                    ratio = eu.keyword_match_ratio(result.get("answer", ""), keywords) if keywords else 1.0
                    gen_ok = ratio >= 0.7
                    gen_note = f"kw={ratio:.2f} ans={result.get('answer','')[:30]!r}"

                ok = (recall is None or recall >= (exp["retrieval"].get("min_recall", 0.8))) and gen_ok
                total += 1
                passed += 1 if ok else 0
                flag = "OK " if ok else "FAIL"
                print(f"{flag} {sample['id']} {q!r:30} expect={exp_ids or '-'} got={names} recall={recall} {gen_note}")

    print(f"\nrag: {passed}/{total}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
