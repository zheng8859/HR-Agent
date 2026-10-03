"""对话模型单元测试：Conversation + Message 回复树。"""
from app.models import Conversation, Message, MessageRole


async def test_conversation_and_message_roundtrip(db_session):
    conv = Conversation(title="JD 生成会话")
    db_session.add(conv)
    await db_session.flush()

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.user.value,
        content="帮我写一个后端 JD",
    )
    db_session.add(msg)
    await db_session.flush()

    assert msg.conversation_id == conv.id
    assert msg.role == MessageRole.user.value


async def test_message_reply_tree(db_session):
    conv = Conversation(title="多轮")
    db_session.add(conv)
    await db_session.flush()

    parent = Message(conversation_id=conv.id, role=MessageRole.user.value, content="q")
    reply = Message(
        conversation_id=conv.id,
        role=MessageRole.assistant.value,
        content="a",
        # 两者均 transient 时建立关联：内存中即可断言，避免异步下的惰性加载（MissingGreenlet）
        parent=parent,
    )
    db_session.add_all([parent, reply])
    await db_session.flush()

    assert reply.parent_message_id == parent.id
    assert reply.parent is parent
    assert parent.replies == [reply]
