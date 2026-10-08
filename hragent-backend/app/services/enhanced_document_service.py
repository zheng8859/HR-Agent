"""文档处理服务：上传哈希、文本提取、语义切片、向量化、状态机、删除级联、所有权隔离。

设计要点（doc 15 §4.1 + doc 17 §2.4 + doc 39）：
- 上传仅限 PDF/DOC/DOCX/TXT，默认 ≤20MB，服务端强制（`validate_document`）。
- 语义切片：每段 ≤500 字、严禁 >800，超长强制切分、过短合并（`chunk_text`）。
- 状态机 `uploaded → processing → processed / failed`，解析失败记录原因，可重新处理。
- 文档按 `user_id` 隔离，list/get 仅返回本人，他人 404。
- 删文档 = 删整行（向量随行移除）+ 清理原始文件，删除后不再被检索。
"""
from __future__ import annotations

import hashlib
import io
import os
import re
import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Document, DocumentChunk, DocumentStatus, KnowledgeBase, User
from app.services.embedding_service import embed_text


class ExtractionError(Exception):
    """文本提取失败（内容为空或解析异常），供状态机标记 failed。"""


# ---------- 哈希与校验 ----------


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_document(filename: str, size: int) -> str:
    """校验扩展名与大小，返回规范化小写扩展名；不合法抛 422。"""
    if "." not in filename:
        raise HTTPException(status_code=422, detail="不支持的文件格式")
    ext = filename.rsplit(".", 1)[1].lower()
    allowed = [t.strip().lower() for t in settings.document_allowed_types.split(",")]
    if ext not in allowed:
        raise HTTPException(status_code=422, detail=f"不支持的文件格式：{ext}")
    max_bytes = settings.document_max_size_mb * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"文件大小超过限制（{settings.document_max_size_mb}MB）",
        )
    return ext


# ---------- 文本提取 ----------


def _extract_pdf(content: bytes) -> str:
    import pdfplumber

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages)


def _extract_docx(content: bytes) -> str:
    import docx

    d = docx.Document(io.BytesIO(content))
    return "\n".join(p.text for p in d.paragraphs)


def extract_text(file_type: str, content: bytes) -> str:
    """按文件类型提取纯文本；内容为空或解析失败抛 ExtractionError（标记 failed，而非 422）。"""
    if not content or not content.strip():
        raise ExtractionError("无法从文档中提取文本内容")
    try:
        if file_type == "pdf":
            text = _extract_pdf(content)
        elif file_type == "docx":
            text = _extract_docx(content)
        elif file_type == "doc":
            try:
                text = _extract_docx(content)
            except Exception:
                text = content.decode("utf-8", errors="ignore")
        elif file_type == "txt":
            text = content.decode("utf-8", errors="ignore")
        else:
            raise ExtractionError(f"不支持的文件格式：{file_type}")
    except ExtractionError:
        raise
    except Exception:
        raise ExtractionError("无法从文档中提取文本内容") from None

    if not text or not text.strip():
        raise ExtractionError("无法从文档中提取文本内容")
    return text.strip()


# ---------- 语义切片 ----------


def chunk_text(
    text: str | None,
    max_chars: int | None = None,
    force_split: int | None = None,
    min_chars: int | None = None,
) -> list[str]:
    """语义切片：优先按段落/句子边界切分，超长强制切分，过短合并。

    `max_chars`（默认 500）为单段目标上限，`force_split`（默认 800）为严禁越过的硬上限，
    `min_chars`（默认 50）以下的尾部片段向上合并，避免碎片化。
    """
    max_chars = settings.chunk_max_chars if max_chars is None else max_chars
    min_chars = settings.chunk_min_chars if min_chars is None else min_chars
    text = (text or "").strip()
    if not text:
        return []

    # 1. 按空行切段
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[str] = []
    for p in paragraphs:
        if len(p) <= max_chars:
            units.append(p)
            continue
        # 2. 超长段先按句子边界切分
        sentences = [s.strip() for s in re.split(r"(?<=[。！？!?])\s*", p) if s.strip()]
        for s in sentences:
            if len(s) <= max_chars:
                units.append(s)
            else:
                # 3. 仍超长：强制按 max_chars 切分（保证无 >800）
                units.extend(s[i : i + max_chars] for i in range(0, len(s), max_chars))

    # 4. 相邻片段合并至 ≤ max_chars
    chunks: list[str] = []
    for u in units:
        if chunks and len(chunks[-1]) + 1 + len(u) <= max_chars:
            chunks[-1] = chunks[-1] + "\n" + u
        else:
            chunks.append(u)

    # 5. 过短片段（< min_chars）向上合并
    merged: list[str] = []
    for u in chunks:
        if merged and len(u) < min_chars:
            merged[-1] = merged[-1] + "\n" + u
        else:
            merged.append(u)
    return merged


# ---------- 状态机处理 ----------


async def process_document(
    doc: Document, content: bytes, file_type: str, db: AsyncSession
) -> Document:
    """处理文档：提取 → 切片 → 逐段向量化，成功 processed、失败 failed（记录原因）。

    doc 15 §4.1：语义切片后对每个切片单独生成向量写入 `document_chunks`，检索按切片
    max-pool。长文档不再被 `_MAX_EMBED_CHARS` 截断，靠后小节（如资产分类）同样可召回。
    """
    doc.status = DocumentStatus.processing.value
    doc.error_message = None
    await db.flush()
    try:
        text = extract_text(file_type, content)
        doc.extracted_content = text
        chunks = chunk_text(text)
        doc.chunk_count = len(chunks)
        # 逐段向量化：先清旧切片再写入新切片（重新处理幂等）
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
        for i, c in enumerate(chunks):
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=i,
                    chunk_text=c,
                    embedding=embed_text(c),
                )
            )
        # 文档级单向量不再使用（会被 1800 字截断），置空；检索走切片表
        doc.embedding = None
        doc.status = DocumentStatus.processed.value
    except ExtractionError as e:
        doc.status = DocumentStatus.failed.value
        doc.error_message = str(e)
    except Exception as e:  # 向量化等其它异常同样落 failed，可重新处理
        doc.status = DocumentStatus.failed.value
        doc.error_message = f"文档处理失败：{e}"
    await db.flush()
    # updated_at 带 onupdate=now()，刷新避免惰性 IO（MissingGreenlet）
    await db.refresh(doc)
    return doc


# ---------- 上传 ----------


async def upload_document(
    file: UploadFile,
    knowledge_base_id: uuid.UUID | None,
    category: str | None,
    tags: str | None,
    user: User,
    db: AsyncSession,
) -> Document:
    """上传文档：校验 → 落盘 uploads → 建记录 → 处理（提取/切片/向量化）。"""
    content = await file.read()
    ext = validate_document(file.filename or "", len(content))

    kb: KnowledgeBase | None = None
    if knowledge_base_id is not None:
        kb = await db.get(KnowledgeBase, knowledge_base_id)
        if kb is None:
            raise HTTPException(status_code=404, detail="知识库不存在")

    # 原始文件落盘
    os.makedirs(settings.upload_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(settings.upload_dir, stored_name)
    with open(file_path, "wb") as fh:
        fh.write(content)

    doc = Document(
        filename=stored_name,
        original_filename=file.filename or "",
        file_path=file_path,
        file_size=len(content),
        file_hash=compute_sha256(content),
        mime_type=file.content_type or "",
        status=DocumentStatus.uploaded.value,
        chunk_count=0,
        category=category,
        tags=tags,
        user_id=user.id,
        knowledge_base_id=knowledge_base_id,
    )
    db.add(doc)
    await db.flush()

    if kb is not None:
        kb.document_count = (kb.document_count or 0) + 1
        await db.flush()

    return await process_document(doc, content, ext, db)


# ---------- 重新处理 / 查询 / 删除（所有权：仅本人） ----------


async def reprocess_document(doc_id: uuid.UUID, user: User, db: AsyncSession) -> Document:
    """重新处理失败的文档：从落盘原始文件重提取、重切片、重向量化。"""
    doc = await get_document(doc_id, user, db)
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="原始文件不存在，无法重新处理")
    with open(doc.file_path, "rb") as fh:
        content = fh.read()
    ext = doc.file_path.rsplit(".", 1)[-1].lower() if "." in doc.file_path else "txt"
    return await process_document(doc, content, ext, db)


async def list_documents(
    user: User,
    db: AsyncSession,
    knowledge_base_id: uuid.UUID | None = None,
) -> list[Document]:
    stmt = select(Document).where(Document.user_id == user.id)
    if knowledge_base_id is not None:
        stmt = stmt.where(Document.knowledge_base_id == knowledge_base_id)
    result = await db.execute(stmt.order_by(Document.created_at.desc()))
    return list(result.scalars().all())


async def get_document(doc_id: uuid.UUID, user: User, db: AsyncSession) -> Document:
    doc = await db.get(Document, doc_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


async def get_document_chunks(
    doc_id: uuid.UUID, user: User, db: AsyncSession
) -> list[str]:
    """返回文档的语义切片（前端「查看切片」）。"""
    doc = await get_document(doc_id, user, db)
    return chunk_text(doc.extracted_content)


async def delete_document(doc_id: uuid.UUID, user: User, db: AsyncSession) -> None:
    """删除文档：清理原始文件 + 删除整行（向量随行移除）+ 维护知识库计数。"""
    doc = await get_document(doc_id, user, db)
    kb_id = doc.knowledge_base_id

    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError:
            pass

    await db.delete(doc)
    if kb_id is not None:
        kb = await db.get(KnowledgeBase, kb_id)
        if kb is not None and (kb.document_count or 0) > 0:
            kb.document_count = kb.document_count - 1
    await db.flush()
