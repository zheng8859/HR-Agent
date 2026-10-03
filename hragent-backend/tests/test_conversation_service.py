"""会话/消息服务测试（doc 43 §十七）：CRUD、所有权隔离、反馈、记忆组装。"""
import pytest
from fastapi import HTTPException

from app.core.security import get_password_hash
from app.models import User
from app.services import conversation_service


async def _make_user(db_session, username, role="hr_manager"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash("secret123"),
        role=role,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_create_and_list_conversation(db_session, eval_user):
    conv = await conversation_service.create_conversation(eval_user, db_session, "测试会话")
    assert conv.user_id == eval_user.id
    lst = await conversation_service.list_conversations(eval_user, db_session)
    assert any(c.id == conv.id for c in lst)


async def test_conversation_ownership_isolation(db_session):
    owner = await _make_user(db_session, "owner")
    other = await _make_user(db_session, "other")
    conv = await conversation_service.create_conversation(owner, db_session)

    with pytest.raises(HTTPException) as e:
        await conversation_service.get_conversation(other, conv.id, db_session)
    assert e.value.status_code == 404

    assert len(await conversation_service.list_conversations(other, db_session)) == 0
    assert len(await conversation_service.list_conversations(owner, db_session)) == 1


async def test_delete_conversation_soft(db_session, eval_user):
    conv = await conversation_service.create_conversation(eval_user, db_session)
    await conversation_service.delete_conversation(eval_user, conv.id, db_session)
    assert len(await conversation_service.list_conversations(eval_user, db_session)) == 0


async def test_add_and_list_messages(db_session, eval_user):
    conv = await conversation_service.create_conversation(eval_user, db_session)
    parent = await conversation_service.add_message(db_session, conv.id, "user", "问")
    await conversation_service.add_message(
        db_session, conv.id, "assistant", "答", parent_message_id=parent.id
    )
    msgs = await conversation_service.list_messages(eval_user, conv.id, db_session)
    assert len(msgs) == 2
    assert msgs[1].parent_message_id == parent.id


async def test_add_feedback(db_session, eval_user):
    conv = await conversation_service.create_conversation(eval_user, db_session)
    msg = await conversation_service.add_message(db_session, conv.id, "assistant", "答")
    updated = await conversation_service.add_feedback(eval_user, msg.id, 5, db_session)
    assert updated.feedback_score == 5


async def test_feedback_ownership_isolated(db_session):
    owner = await _make_user(db_session, "owner")
    other = await _make_user(db_session, "other")
    conv = await conversation_service.create_conversation(owner, db_session)
    msg = await conversation_service.add_message(db_session, conv.id, "assistant", "答")

    with pytest.raises(HTTPException) as e:
        await conversation_service.add_feedback(other, msg.id, 5, db_session)
    assert e.value.status_code == 404


async def test_feedback_only_assistant_message(db_session, eval_user):
    conv = await conversation_service.create_conversation(eval_user, db_session)
    user_msg = await conversation_service.add_message(db_session, conv.id, "user", "问")
    with pytest.raises(HTTPException) as e:
        await conversation_service.add_feedback(eval_user, user_msg.id, 5, db_session)
    assert e.value.status_code == 400
