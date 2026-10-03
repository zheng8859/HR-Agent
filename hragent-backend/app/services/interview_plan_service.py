"""面试方案服务：数据依赖守卫、三要素渲染、候选人解析四态、状态联动、所有权隔离。

设计要点（doc 15 §2.4 + doc 38）：
- 防空转：面试方案必须绑定一条已完成简历评估（`total_score` 非空），未关联/未完成明确拒绝。
- 方案三要素：面试目标/面试流程/面试题目（题目不少于 5 道），渲染为 markdown 落库。
- 状态联动：生成/重新生成后把关联评估状态置为 `interview`（幂等）。
- 候选人解析四态：matched/no_match/ambiguous/no_specific，供 Agent 解析口语化指代。
- 面试方案属敏感信息，list/get 仅返回本人（`user_id` 过滤），他人 404。
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    InterviewPlan,
    JobDescription,
    ResumeEvaluation,
    ResumeEvaluationStatus,
    User,
)
from app.schemas.interview_plan import (
    InterviewPlanGenerateRequest,
    InterviewPlanUpdate,
)
from app.services.dify_service import dify_client

# 方案三要素分区标题（顺序即渲染顺序）
INTERVIEW_SECTION_TITLES: tuple[str, ...] = (
    "面试目标",
    "面试流程",
    "面试题目",
)


# ---------- 候选人解析四态 ----------


@dataclass
class CandidateResolution:
    """口语化候选人指代解析结果（供 Agent 流程复用）。"""

    state: str  # matched / no_match / ambiguous / no_specific
    matches: Sequence[Any] = field(default_factory=list)
    message: str = ""


def resolve_candidate(query: str, candidates: Sequence[Any]) -> CandidateResolution:
    """把候选人口语化指代解析为四态。`query` 为空 → no_specific；命中 0/1/N 条 → no_match/matched/ambiguous。"""
    if not query or not query.strip():
        return CandidateResolution(state="no_specific", message="请指明候选人姓名")
    matches = [
        c for c in candidates if c.candidate_name and query in c.candidate_name
    ]
    if len(matches) == 0:
        return CandidateResolution(state="no_match", message=f"未找到候选人：{query}")
    if len(matches) == 1:
        return CandidateResolution(state="matched", matches=matches, message="已命中候选人")
    return CandidateResolution(
        state="ambiguous", matches=matches, message="候选人指代有歧义，请说明得更具体"
    )


# ---------- 三要素渲染 ----------


def format_plan(output: dict[str, Any]) -> str:
    """把 Dify 三要素输出渲染为 markdown 分区。"""
    questions = output.get("core_questions") or []
    lines: list[str] = []
    for title in INTERVIEW_SECTION_TITLES:
        lines.append(f"## {title}")
        if title == "面试题目":
            for i, q in enumerate(questions, 1):
                lines.append(f"{i}. {q}")
        else:
            key = "goal" if title == "面试目标" else "process"
            lines.append(str(output.get(key) or "").strip())
        lines.append("")
    return "\n".join(lines).strip()


# ---------- 输入构造 ----------


def _build_inputs(ev: ResumeEvaluation, jd: JobDescription | None) -> dict[str, Any]:
    """面试方案只依赖简历 + JD（三要素简化版，doc 38）。"""
    return {
        "resume_content": ev.resume_content or "",
        "job_title": jd.title if jd else "",
        "job_content": jd.content if jd else "",
    }


async def _resolve_jd(ev: ResumeEvaluation, db: AsyncSession) -> JobDescription | None:
    if ev.job_description_id is None:
        return None
    return await db.get(JobDescription, ev.job_description_id)


# ---------- 生成 / 重新生成 ----------


async def generate_plan(
    request: InterviewPlanGenerateRequest, user: User, db: AsyncSession
) -> InterviewPlan:
    """绑定已完成简历评估生成面试方案，成功后把评估状态置为 interview。"""
    ev = await db.get(ResumeEvaluation, request.resume_evaluation_id)
    if ev is None or ev.user_id != user.id:
        raise HTTPException(status_code=404, detail="简历评估不存在")
    if ev.total_score is None:
        raise HTTPException(status_code=422, detail="该简历尚未完成评估，无法生成面试方案")

    jd = await _resolve_jd(ev, db)
    output = await dify_client.run_interview_workflow(_build_inputs(ev, jd))

    plan = InterviewPlan(
        candidate_name=ev.candidate_name,
        candidate_position=ev.candidate_position,
        content=format_plan(output),
        resume_evaluation_id=ev.id,
        user_id=user.id,
    )
    db.add(plan)
    ev.status = ResumeEvaluationStatus.interview.value
    await db.flush()
    # updated_at/created_at 为 server_default，刷新避免响应序列化时触发惰性 IO（MissingGreenlet）
    await db.refresh(plan)
    return plan


async def regenerate_plan(
    plan_id: uuid.UUID, user: User, db: AsyncSession
) -> InterviewPlan:
    """对已有方案重新生成并再次触发状态联动。"""
    plan = await get_plan(plan_id, user, db)
    ev = await db.get(ResumeEvaluation, plan.resume_evaluation_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="关联的简历评估不存在")

    jd = await _resolve_jd(ev, db)
    output = await dify_client.run_interview_workflow(_build_inputs(ev, jd))

    plan.content = format_plan(output)
    plan.candidate_name = ev.candidate_name
    plan.candidate_position = ev.candidate_position
    ev.status = ResumeEvaluationStatus.interview.value
    await db.flush()
    # updated_at 带 onupdate=now()，UPDATE 后属性过期；刷新避免 MissingGreenlet
    await db.refresh(plan)
    return plan


# ---------- 查询 / 编辑 / 导出（所有权：仅本人） ----------


async def list_plans(user: User, db: AsyncSession) -> list[InterviewPlan]:
    result = await db.execute(
        select(InterviewPlan)
        .where(InterviewPlan.user_id == user.id)
        .order_by(InterviewPlan.created_at.desc())
    )
    return list(result.scalars().all())


async def get_plan(plan_id: uuid.UUID, user: User, db: AsyncSession) -> InterviewPlan:
    plan = await db.get(InterviewPlan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail="面试方案不存在")
    return plan


async def update_plan(
    plan_id: uuid.UUID, request: InterviewPlanUpdate, user: User, db: AsyncSession
) -> InterviewPlan:
    """编辑保存（AI 出初稿、人定终稿）。"""
    plan = await get_plan(plan_id, user, db)
    if request.content is not None:
        plan.content = request.content
    if request.candidate_name is not None:
        plan.candidate_name = request.candidate_name
    await db.flush()
    await db.refresh(plan)
    return plan


async def export_plan(
    plan_id: uuid.UUID, fmt: str, user: User, db: AsyncSession
) -> str:
    """导出方案纯文本（md/txt 内容一致，端点层区分 media_type 与文件名）。"""
    plan = await get_plan(plan_id, user, db)
    return plan.content or ""
