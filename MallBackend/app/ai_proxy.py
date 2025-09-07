import time
import json
from flask import request, jsonify, Blueprint, current_app
from openai import OpenAI
from .models import AIMessage, Product
from .auth import token_required
import jieba  # 用于中文分词
from collections import Counter

ai_api = Blueprint('ai_api', __name__)

# 初始化jieba分词，添加商品相关词汇
jieba.initialize()
product_words = ['手机', '华为', '小米', '苹果', '花朵', '卡片', '耳机', '手表', '智能', '无线', '蓝牙', '降噪', '健康',
                 '运动', '防水']
for word in product_words:
    jieba.add_word(word)


def extract_product_keywords(message):
    """使用分词技术从用户消息中提取商品相关关键词"""
    # 使用jieba分词
    words = jieba.cut(message)

    # 过滤出可能的产品相关词汇
    product_related_words = []
    for word in words:
        # 长度至少为2，且不是停用词
        if len(word) >= 2 and word not in ['什么', '怎么', '如何', '请问', '可以', '想要', '推荐']:
            product_related_words.append(word)

    # 统计词频并返回前3个最相关的词
    word_counts = Counter(product_related_words)
    return [word for word, count in word_counts.most_common(3)]


def search_products_by_keywords(keywords):
    """根据关键词动态搜索商品"""
    try:
        from sqlalchemy import or_

        # 构建查询条件
        conditions = []
        for keyword in keywords:
            # 对每个关键词，搜索名称和描述
            conditions.append(Product.name.ilike(f'%{keyword}%'))
            conditions.append(Product.description.ilike(f'%{keyword}%'))

        # 如果有条件，执行查询
        if conditions:
            products = Product.query.filter(or_(*conditions)).limit(5).all()
            return products
        else:
            # 如果没有关键词，返回空列表
            return []

    except Exception as e:
        current_app.logger.error(f"商品搜索错误: {str(e)}")
        return []


def format_products_for_ai(products):
    """将商品信息格式化为AI可理解的文本"""
    if not products:
        return ""

    product_text = "商城中有以下相关商品：\n"
    for i, product in enumerate(products, 1):
        product_text += f"{i}. {product.name} - 价格: ¥{product.price}\n"
        product_text += f"   描述: {product.description[:100]}...\n"

    return product_text


def is_product_related_query(message):
    """判断用户消息是否与商品相关"""
    product_keywords = ['手机', '华为', '小米', '苹果', '花朵', '卡片', '商品', '产品',
                        '推荐', '价格', '购买', '多少钱', '买什么', '哪个好', '性价比']

    message_lower = message.lower()
    return any(keyword in message_lower for keyword in product_keywords)


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

        # 检查用户最后一条消息是否与商品相关
        last_user_content = ""
        for msg in payload['messages']:
            if msg['role'] == 'user':
                content = msg.get('content', '')
                if isinstance(content, list):
                    # 提取所有文本内容并拼接
                    text_parts = [item['text'] for item in content if item['type'] == 'text']
                    last_user_content = ''.join(text_parts)
                elif isinstance(content, str):
                    last_user_content = content
                else:
                    last_user_content = str(content)

        # 动态检测商品相关查询
        if is_product_related_query(last_user_content):
            # 提取关键词
            keywords = extract_product_keywords(last_user_content)

            # 搜索相关商品
            relevant_products = search_products_by_keywords(keywords)

            # 如果有相关商品，添加系统消息提供商品信息
            if relevant_products:
                product_context = format_products_for_ai(relevant_products)

                # 添加系统提示
                system_prompt = (
                    "你是一个电商平台的AI助手，可以帮助用户解答商品相关问题。"
                    "请根据以下商品信息回答用户的问题，可以推荐商品、比较价格和功能等。"
                    "回答要友好、专业且有帮助。\n\n"
                    f"{product_context}"
                )

                validated_messages.append({
                    'role': 'system',
                    'content': system_prompt
                })

        # 添加用户消息
        for msg in payload['messages']:
            # 确保 content 字段存在且为字符串
            content = msg.get('content', '')
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