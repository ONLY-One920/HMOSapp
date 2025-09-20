from app import db
from app.models import AIMessage, User

def test_ai_message_storage(test_app, init_database, mock_ai_response):
    """测试AI消息存储"""
    with test_app.app_context():
        # 获取测试用户
        user = User.query.filter_by(username='123456').first()

        # 模拟AI响应
        mock_ai_response.chat.completions.create.return_value.choices[0].message.content = "测试AI回复"

        # 创建AI消息
        ai_message = AIMessage(
            user_id=user.id,
            role='assistant',
            content='测试AI回复',
            timestamp=1234567890
        )
        db.session.add(ai_message)
        db.session.commit()

        # 验证消息已存储
        messages = AIMessage.query.filter_by(user_id=user.id).all()
        assert len(messages) == 1
        assert messages[0].content == '测试AI回复'
