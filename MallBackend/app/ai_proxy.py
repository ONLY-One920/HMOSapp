import os
import time
import json
import requests
from flask import request, jsonify, Blueprint, current_app
from openai import OpenAI
from .models import AIMessage
from .auth import token_required

ai_api = Blueprint('ai_api', __name__)


@ai_api.route('/chat', methods=['POST'])
@token_required
def ai_chat_proxy(current_user):
    # 使用应用上下文中的 db 对象
    db = current_app.extensions['sqlalchemy']

    # 配置火山方舟客户端
    client = OpenAI(
        base_url=current_app.config['ARK_BASE_URL'],
        api_key=current_app.config['ARK_API_KEY']
    )

    # 获取请求数据
    payload = request.json
    model = payload.get('model', current_app.config['ARK_DEFAULT_MODEL'])

    # 提取并保存用户消息
    user_messages = [msg for msg in payload['messages'] if msg['role'] == 'user']
    if user_messages:
        last_user_message = user_messages[-1]

        # 处理多模态消息内容
        content = last_user_message.get('content')
        if isinstance(content, list):
            # 将多模态内容转换为可存储的 JSON 字符串
            content_data = []
            for item in content:
                if item['type'] == 'text':
                    content_data.append({'type': 'text', 'value': item['text']})
                elif item['type'] == 'image_url':
                    content_data.append({'type': 'image_url', 'value': item['image_url']['url']})
            content_str = json.dumps(content_data)
        elif isinstance(content, str):
            content_str = content
        else:
            content_str = str(content)

        # 添加消息去重检查 (5秒内相同内容视为重复)
        duplicate_window = 5000  # 5秒时间窗口
        duplicate = AIMessage.query.filter(
            AIMessage.user_id == current_user.id,
            AIMessage.content == content_str,
            AIMessage.timestamp >= int(time.time() * 1000) - duplicate_window
        ).first()

        # 保存消息到数据库（仅当无重复时）
        if not duplicate:
            user_msg = AIMessage(
                user_id=current_user.id,
                role='user',
                content=content_str,
                timestamp=int(time.time() * 1000)
            )
            db.session.add(user_msg)
            db.session.commit()

    try:
        # 确保消息格式符合火山方舟 API 要求
        validated_messages = []
        for msg in payload['messages']:
            # 确保 content 字段存在且为字符串
            content = msg.get('content', "")
            if isinstance(content, list):
                # 提取所有文本内容并拼接
                text_parts = [item['text'] for item in content if item['type'] == 'text']
                content = ''.join(text_parts)
            elif not isinstance(content, str):
                content = str(content)

            validated_messages.append({
                'role': msg['role'],
                'content': content
            })

        # 调用火山方舟 API
        response = client.chat.completions.create(
            model=model,
            messages=validated_messages  # 使用验证后的消息
        )

        # 提取 AI 回复内容
        ai_content = response.choices[0].message.content

        # 构建符合前端要求的响应
        chat_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": ai_content
                }
            }]
        }

        # 保存 AI 回复 - 添加去重检查
        ai_duplicate_window = 3000  # 3秒时间窗口
        ai_duplicate = AIMessage.query.filter(
            AIMessage.user_id == current_user.id,
            AIMessage.content == ai_content,
            AIMessage.timestamp >= int(time.time() * 1000) - ai_duplicate_window
        ).first()

        if not ai_duplicate:
            ai_msg = AIMessage(
                user_id=current_user.id,
                role='assistant',
                content=ai_content,
                timestamp=int(time.time() * 1000)
            )
            db.session.add(ai_msg)
            db.session.commit()

        return jsonify(chat_response), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'AI 代理错误: {str(e)}')
        return jsonify({
            'error': '内部服务器错误',
            'message': str(e)
        }), 500