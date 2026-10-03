"""Evals 共享种子：RAG 检索评测用的规范知识库文档（doc 42 §1.3 检索样本依赖）。

检索样本的 `expected_doc_ids` 以文档「文件名」为稳定引用，本模块提供规范文档内容与
幂等的种子函数（`embedding` 走 mock 向量，供 `retrieve` 离线态词面检索命中）。
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, DocumentStatus, KnowledgeBase
from app.services.embedding_service import embed_text

SEED_KB_NAME = "评测规范知识库"

# 规范文档：文件名作为检索样本 expected_doc_ids 的稳定引用。
# 内容采用「政策正文 + 常见问题」FAQ 形式，确保离线态 mock 检索（词面覆盖）能稳定命中。
SEED_DOCS: list[tuple[str, str]] = [
    (
        "考勤管理制度.txt",
        "公司实行弹性考勤制度，员工每日上下班需通过打卡系统记录考勤。"
        "公司考勤怎么打卡，通过打卡系统记录上下班考勤。"
        "公司对考勤有什么规定，迟到早退会怎么样，迟到早退需提前向直属主管说明并补签；"
        "迟到扣多少钱，迟到早退按规定扣减绩效；"
        "请假需要谁审批，请假需在系统提交请假申请并经直属主管审批；"
        "请假有几种类型，请假类型包括事假、病假、年假、调休等几种；"
        "加班怎么申请，加班需提前申请报备；"
        "加班有加班费吗，加班费按国家规定标准发放。",
    ),
    (
        "薪酬保密制度.txt",
        "公司薪酬实行保密制度，员工薪资待遇属保密信息，不得相互打听或泄露。"
        "薪资是保密的吗，是，公司薪酬实行保密制度。"
        "薪酬结构包含哪些，薪酬结构包括基本工资、绩效奖金与岗位津贴。"
        "绩效奖金怎么发，绩效奖金按季度考核结果发放，具体标准见绩效管理办法。"
        "薪资保密有什么规定，员工薪资待遇属保密信息，不得相互打听或泄露。",
    ),
    (
        "入职离职流程.txt",
        "新员工入职需携带身份证、学历证书、离职证明等材料办理入职手续。"
        "入职需要准备什么材料，携带身份证、学历证书、离职证明等材料。"
        "入职第一天需要带什么，携带身份证、学历证书、离职证明等材料。"
        "入职流程是怎样的，入职需携带材料办理入职手续。"
        "试用期一般多久，试用期一般为三个月。"
        "试用期工资怎么算，试用期工资按转正工资的百分之八十发放。"
        "离职需要怎么交接，员工离职需办理工作交接与离职手续。"
        "离职要提前多久通知，员工离职需提前三十日书面通知。",
    ),
    (
        "年假休假制度.txt",
        "员工累计工作满一年可享受带薪年假。"
        "年假有几天，年假天数按工龄确定，入职满一年五天起。"
        "年假怎么申请，休假需提前在系统提交休假申请。"
        "休假申请怎么提交，休假需提前在系统提交休假申请并经审批。"
        "年假可以累计吗，年假当年有效可结转至次年三月。",
    ),
]


async def seed_eval_kb(db: AsyncSession, user) -> KnowledgeBase:
    """创建规范知识库与 4 篇文档（含 mock embedding），返回知识库对象。幂等按名称。"""
    kb = KnowledgeBase(
        name=SEED_KB_NAME, description="Evals 检索评测用规范知识库", is_public=True
    )
    db.add(kb)
    await db.flush()
    for filename, content in SEED_DOCS:
        db.add(
            Document(
                filename=filename,
                original_filename=filename,
                extracted_content=content,
                embedding=embed_text(content),
                status=DocumentStatus.processed.value,
                chunk_count=1,
                user_id=user.id,
                knowledge_base_id=kb.id,
            )
        )
    await db.flush()
    return kb
