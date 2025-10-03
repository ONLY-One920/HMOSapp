def test_ai_chat_api(authenticated_client, mock_ai_response):
    """测试AI聊天API"""
    response = authenticated_client.post(
        "/api/ai/chat",
        json={
            "model": "test-model",
            "messages": [{"role": "user", "content": "你好，推荐一款手机"}],
        },
    )

    assert response.status_code == 200
    assert "choices" in response.json
    assert "products" in response.json
    assert response.json["choices"][0]["message"]["content"] == "这是一个AI回复"


def test_get_ai_messages_api(authenticated_client, init_database):
    """测试获取AI消息API"""
    response = authenticated_client.get("/api/ai/messages")

    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_delete_ai_message_api(authenticated_client, init_database):
    """测试删除AI消息API"""
    # 使用测试客户端直接创建消息
    response = authenticated_client.post('/api/ai/messages', json={
        'role': 'user',
        'content': '测试删除消息',
        'timestamp': 1234567890
    })

    assert response.status_code == 201

    # 获取所有消息找到刚创建的消息
    messages_response = authenticated_client.get('/api/ai/messages')
    assert messages_response.status_code == 200

    messages = messages_response.json
    assert len(messages) > 0

    # 找到包含测试内容的消息
    test_message = None
    for msg in messages:
        if msg['content'] == '测试删除消息':
            test_message = msg
            break

    assert test_message is not None, "测试消息未找到"

    # 删除消息
    message_id = test_message['id']
    response = authenticated_client.delete(f'/api/ai/messages/{message_id}')

    assert response.status_code == 200
    assert '消息已删除' in response.json['message']

    # 验证消息已被删除
    messages_after_delete = authenticated_client.get('/api/ai/messages').json
    remaining_ids = [msg['id'] for msg in messages_after_delete]
    assert message_id not in remaining_ids, "消息删除后仍然存在"


def test_reload_keywords_api(authenticated_client):
    """测试重新加载关键词API"""
    response = authenticated_client.post("/api/ai/reload-keywords")

    assert response.status_code == 200
    assert "成功加载" in response.json["message"]
    assert "keywords_count" in response.json


def test_ai_chat_with_empty_message(authenticated_client):
    """测试空消息的AI聊天"""
    response = authenticated_client.post(
        "/api/ai/chat",
        json={"model": "test-model", "messages": [{"role": "user", "content": ""}]},
    )
    assert response.status_code == 200


def test_ai_chat_with_image_message(authenticated_client, mock_ai_response):
    """测试带图片消息的AI聊天"""
    response = authenticated_client.post(
        "/api/ai/chat",
        json={
            "model": "test-model",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "这个图片是什么商品"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "http://example.com/image.jpg"},
                        },
                    ],
                }
            ],
        },
    )
    assert response.status_code == 200


def test_reload_keywords_without_auth(test_client):
    """测试未认证重新加载关键词"""
    response = test_client.post("/api/ai/reload-keywords")
    assert response.status_code == 401
