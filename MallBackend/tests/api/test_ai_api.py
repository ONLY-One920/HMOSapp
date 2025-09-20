
def test_ai_chat_api(authenticated_client, mock_ai_response):
    """测试AI聊天API"""
    response = authenticated_client.post('/api/ai/chat', json={
        'model': 'test-model',
        'messages': [
            {'role': 'user', 'content': '你好，推荐一款手机'}
        ]
    })

    assert response.status_code == 200
    assert 'choices' in response.json
    assert 'products' in response.json
    assert response.json['choices'][0]['message']['content'] == '这是一个AI回复'


def test_get_ai_messages_api(authenticated_client, init_database):
    """测试获取AI消息API"""
    response = authenticated_client.get('/api/ai/messages')

    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_delete_ai_message_api(authenticated_client, init_database):
    """测试删除AI消息API"""
    # 先创建一条测试消息
    from app import db
    from app.models import AIMessage, User

    with authenticated_client.application.app_context():
        user = User.query.filter_by(username='123456').first()
        message = AIMessage(
            user_id=user.id,
            role='user',
            content='测试消息',
            timestamp=1234567890
        )
        db.session.add(message)
        db.session.commit()
        message_id = message.id

    # 删除消息
    response = authenticated_client.delete(f'/api/ai/messages/{message_id}')

    assert response.status_code == 200
    assert '消息已删除' in response.json['message']


def test_reload_keywords_api(authenticated_client):
    """测试重新加载关键词API"""
    response = authenticated_client.post('/api/ai/reload-keywords')

    assert response.status_code == 200
    assert '成功加载' in response.json['message']
    assert 'keywords_count' in response.json

def test_ai_chat_with_empty_message(authenticated_client):
    """测试空消息的AI聊天"""
    response = authenticated_client.post('/api/ai/chat', json={
        'model': 'test-model',
        'messages': [{'role': 'user', 'content': ''}]
    })
    assert response.status_code == 200

def test_ai_chat_with_image_message(authenticated_client, mock_ai_response):
    """测试带图片消息的AI聊天"""
    response = authenticated_client.post('/api/ai/chat', json={
        'model': 'test-model',
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': '这个图片是什么商品'},
                {'type': 'image_url', 'image_url': {'url': 'http://example.com/image.jpg'}}
            ]
        }]
    })
    assert response.status_code == 200

def test_reload_keywords_without_auth(test_client):
    """测试未认证重新加载关键词"""
    response = test_client.post('/api/ai/reload-keywords')
    assert response.status_code == 401