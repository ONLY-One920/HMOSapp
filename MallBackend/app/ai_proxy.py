import time
import json
from flask import request, jsonify, Blueprint, current_app
from openai import OpenAI
from .models import AIMessage, Product
from .auth import token_required
import jieba  # 用于中文分词
from collections import Counter
from typing import List, Set, Dict
import re

ai_api = Blueprint("ai_api", __name__)

# 全局变量，用于缓存商品关键词
product_keywords_map: Dict[str, Set[str]] = {}  # 商品ID -> 关键词集合
all_product_keywords: Set[str] = set()  # 所有关键词
product_categories: Set[str] = set()  # 商品类别关键词

# 初始化jieba分词，添加商品相关词汇
jieba.initialize()

# 停用词表
STOP_WORDS = {
    "什么",
    "怎么",
    "如何",
    "请问",
    "可以",
    "想要",
    "推荐",
    "你好",
    "谢谢",
    "请问",
    "这个",
    "那个",
    "哪些",
    "有什么",
    "一下",
    "一下",
    "一点",
    "一些",
    "一种",
    "一款",
    "哪个",
    "哪款",
    "多少钱",
}

# 商品类别关键词
PRODUCT_CATEGORIES = {
    "手机",
    "华为",
    "小米",
    "苹果",
    "花朵",
    "卡片",
    "耳机",
    "手表",
    "智能",
    "无线",
    "蓝牙",
    "降噪",
    "健康",
    "运动",
    "防水",
    "电子",
    "数码",
    "配件",
    "礼品",
    "贺卡",
}

# 商城特定关键词
MALL_SPECIFIC_KEYWORDS = {
    "商城中",
    "商城里有",
    "你们有",
    "店铺里",
    "你们卖",
    "有没有",
    "能买到",
    "你们提供",
    "你们店",
    "商城",
}

GENERAL_PRODUCT_KEYWORDS = {
    "网络上",
    "一般",
    "市面上",
    "常见",
    "推荐一款",
    "哪种好",
    "哪个品牌好",
    "大家推荐",
    "流行",
}

# 添加商品类别词汇到jieba
for word in PRODUCT_CATEGORIES:
    jieba.add_word(word)
    product_categories.add(word)

# 添加商城特定关键词到jieba
for word in MALL_SPECIFIC_KEYWORDS:
    jieba.add_word(word)

for word in GENERAL_PRODUCT_KEYWORDS:
    jieba.add_word(word)


def load_all_product_keywords():
    """预加载所有商品的关键词"""
    try:
        products = Product.query.all()
        current_app.logger.info(f"正在加载 {len(products)} 个商品的关键词...")

        for product in products:
            keywords = set()

            # 从商品名称中提取关键词
            name_keywords = jieba.lcut(product.name)
            keywords.update(
                [kw for kw in name_keywords if len(kw) >= 2 and kw not in STOP_WORDS]
            )

            # 从商品描述中提取关键词
            if product.description:
                desc_keywords = jieba.lcut(product.description)
                keywords.update(
                    [
                        kw
                        for kw in desc_keywords
                        if len(kw) >= 2 and kw not in STOP_WORDS
                    ]
                )

            # 添加商品类别关键词
            for category in product_categories:
                if category in product.name or (
                    product.description and category in product.description
                ):
                    keywords.add(category)

            # 添加价格相关关键词
            if product.price:
                if product.price < 100:
                    keywords.add("低价")
                    keywords.add("实惠")
                elif product.price > 1000:
                    keywords.add("高端")
                    keywords.add("旗舰")

            product_keywords_map[product.id] = keywords
            all_product_keywords.update(keywords)

        current_app.logger.info(f"成功加载 {len(all_product_keywords)} 个商品关键词")
    except Exception as e:
        current_app.logger.error(f"加载商品关键词失败: {str(e)}")


def extract_product_keywords(message):
    """使用分词技术从用户消息中提取商品相关关键词"""
    # 使用jieba分词
    words = jieba.cut(message)

    # 过滤出可能的产品相关词汇
    product_related_words = []
    for word in words:
        # 长度至少为2，且不是停用词
        if len(word) >= 2 and word not in STOP_WORDS:
            # 检查是否是已知的商品关键词或类别
            if word in all_product_keywords or word in product_categories:
                product_related_words.append(word)

    # 统计词频并返回前5个最相关的词
    word_counts = Counter(product_related_words)
    return [word for word, count in word_counts.most_common(5)]


def search_products_by_keywords(keywords):
    """根据关键词动态搜索商品"""
    try:
        from sqlalchemy import or_

        # 如果没有关键词，返回空列表
        if not keywords:
            return []

        # 构建查询条件
        conditions = []
        for keyword in keywords:
            # 对每个关键词，搜索名称和描述
            conditions.append(Product.name.ilike(f"%{keyword}%"))
            conditions.append(Product.description.ilike(f"%{keyword}%"))

        # 执行查询
        products = Product.query.filter(or_(*conditions)).all()

        # 按关键词匹配度排序
        def match_score(product):
            score = 0
            for keyword in keywords:
                if keyword in product.name:
                    score += 2  # 名称匹配权重更高
                if product.description and keyword in product.description:
                    score += 1  # 描述匹配权重较低
            return score

        products.sort(key=match_score, reverse=True)
        return products[:10]  # 返回最多10个商品
    except Exception as e:
        current_app.logger.error(f"商品搜索错误: {str(e)}")
        return []


def get_all_products():
    """获取商城中的所有商品"""
    try:
        return Product.query.all()
    except Exception as e:
        current_app.logger.error(f"获取所有商品失败: {str(e)}")
        return []


def format_products_for_ai(products, is_mall_specific=True):
    """将商品信息格式化为AI可理解的文本"""
    if not products:
        if is_mall_specific:
            return "商城目前没有相关商品。"
        else:
            return ""

    if is_mall_specific:
        product_text = "商城中有以下商品：\n\n"
    else:
        product_text = ""

    for i, product in enumerate(products, 1):
        product_text += f"{i}. {product.name} - 价格: ¥{product.price}\n"
        if product.description:
            # 截断过长的描述
            desc = product.description
            if len(desc) > 100:
                desc = desc[:100] + "..."
            product_text += f"  描述: {desc}\n"
        product_text += "\n"

    return product_text


def is_product_related_query(message):
    """判断用户消息是否与商品相关"""
    # 检查是否包含商品类别关键词
    message_lower = message.lower()
    if any(keyword in message_lower for keyword in product_categories):
        return True

    # 检查是否包含购物相关词汇
    shopping_keywords = {
        "买",
        "购买",
        "价格",
        "多少钱",
        "推荐",
        "哪个好",
        "性价比",
        "优惠",
        "折扣",
        "购物",
    }
    if any(keyword in message_lower for keyword in shopping_keywords):
        return True

    # 检查是否包含已知的商品关键词
    words = jieba.lcut(message)
    for word in words:
        if word in all_product_keywords and len(word) >= 2:
            return True

    return False


def is_asking_about_mall_products(message):
    """判断用户是否在询问商城中的商品"""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in MALL_SPECIFIC_KEYWORDS)


def is_asking_about_general_products(message):
    """判断用户是否在询问一般网络商品信息"""
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in GENERAL_PRODUCT_KEYWORDS)


def is_asking_all_products(message):
    """判断用户是否在询问所有商品"""
    all_keywords = {
        "所有商品",
        "全部商品",
        "都有什么商品",
        "有哪些商品",
        "商品列表",
        "所有东西",
    }
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in all_keywords)


def build_mall_specific_prompt(products):
    """构建商城特定商品的提示词"""
    product_context = format_products_for_ai(products, is_mall_specific=True)

    return (
        "你是一个电商平台的AI助手，只能基于商城现有商品回答问题。\n"
        "请根据以下商品信息回答用户的问题，可以推荐商品、比较价格和功能等。\n"
        "回答要友好、专业且有帮助。\n\n"
        f"{product_context}"
        "注意：\n"
        "- 只能推荐商城已有的商品\n"
        "- 不要编造不存在的商品\n"
        "- 如果商城没有用户想要的商品，请如实告知\n"
        "- 在回答中明确说明这些是商城中的商品\n"
        "- 不要提供网络上的一般商品信息\n"
    )


def build_general_product_prompt():
    """构建一般商品推荐的提示词"""
    return (
        "你是一个购物助手，可以回答一般性的商品推荐和购物建议。\n"
        "请注意：\n"
        "- 你不是在推荐商城特定商品\n"
        "- 你可以提供一般性的购物建议、品牌推荐、功能比较等\n"
        "- 请明确说明你的推荐是基于一般市场情况，并非商城特有\n"
        '- 如果用户想了解商城是否有某商品，可以提示ta："您是想了解我们商城中是否有这类商品吗？"\n'
    )


def build_hybrid_prompt(products):
    """构建混合提示词（当用户意图不明确时使用）"""
    product_context = format_products_for_ai(products, is_mall_specific=True)

    return (
        "你是一个电商平台的AI助手，可以回答关于商城商品和一般商品的问题。\n"
        "请根据用户的问题意图提供相应的回答：\n\n"
        "如果用户询问商城中的商品，请基于以下商品信息回答：\n"
        f"{product_context}\n\n"
        "如果用户询问一般性的商品推荐，可以提供市场常见品牌的建议。\n\n"
        "注意：\n"
        "- 回答时要明确区分商城商品和一般市场商品\n"
        "- 如果用户意图不明确，可以主动询问\n"
        "- 不要混淆商城商品和网络商品信息\n"
    )


def build_all_products_prompt(products):
    """构建展示所有商品的提示词"""
    product_context = format_products_for_ai(products, is_mall_specific=True)

    return (
        "你是一个电商平台的AI助手，用户询问商城中的所有商品。\n"
        "请基于以下商品信息回答用户的问题：\n\n"
        f"{product_context}\n\n"
        "注意：\n"
        "- 只能推荐商城已有的商品\n"
        "- 不要编造不存在的商品\n"
        "- 在回答中明确说明这些是商城中的商品\n"
        "- 可以按类别组织商品信息，使回答更有条理\n"
    )


@ai_api.route("/chat", methods=["POST"])
@token_required
def ai_chat_proxy(current_user):
    # 确保商品关键词已加载
    if not all_product_keywords:
        load_all_product_keywords()

        # 获取请求数据
    payload = request.json
    if not payload or "messages" not in payload:
        return jsonify({"error": "无效的请求数据"}), 400

    model = payload.get("model", current_app.config["ARK_DEFAULT_MODEL"])

    # 检查消息是否为空
    messages = payload.get("messages", [])
    if not messages:
        return jsonify({"error": "消息不能为空"}), 400

    # 检查最后一条用户消息是否为空
    user_messages = [msg for msg in messages if msg.get("role") == "user"]
    if not user_messages:
        return jsonify({"error": "没有用户消息"}), 400

    last_user_message = user_messages[-1]
    content = last_user_message.get("content", "")

    # 处理空内容的情况
    if not content or (isinstance(content, str) and content.strip() == ""):
        # 返回友好的提示而不是错误
<<<<<<< HEAD
        return (
            jsonify(
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "您好！我注意到您发送了空消息。请问有什么可以帮助您的吗？",
                            }
                        }
                    ],
                    "products": [],
                }
            ),
            200,
        )
=======
        return jsonify({
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "您好！我注意到您发送了空消息。请问有什么可以帮助您的吗？"
                }
            }],
            "products": []
        }), 200
>>>>>>> 407e1bf385e8c191cda329ecf379a92fa292e5ea

    # 使用应用上下文中的 db 对象
    db = current_app.extensions["sqlalchemy"]

    # 配置火山方舟客户端
    client = OpenAI(
        base_url=current_app.config["ARK_BASE_URL"],
        api_key=current_app.config["ARK_API_KEY"],
    )

    # 获取请求数据
    payload = request.json
    model = payload.get("model", current_app.config["ARK_DEFAULT_MODEL"])

    # 提取并保存用户消息
    user_messages = [msg for msg in payload["messages"] if msg["role"] == "user"]
    if user_messages:
        last_user_message = user_messages[-1]

        # 处理多模态消息内容
        content = last_user_message.get("content")
        if isinstance(content, list):
            # 将多模态内容转换为可存储的 JSON 字符串
            content_data = []
            for item in content:
                if item["type"] == "text":
                    content_data.append({"type": "text", "value": item["text"]})
                elif item["type"] == "image_url":
                    content_data.append(
                        {"type": "image_url", "value": item["image_url"]["url"]}
                    )
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
            AIMessage.timestamp >= int(time.time() * 1000) - duplicate_window,
        ).first()

        # 保存消息到数据库（仅当无重复时）
        if not duplicate:
            user_msg = AIMessage(
                user_id=current_user.id,
                role="user",
                content=content_str,
                timestamp=int(time.time() * 1000),
            )
            db.session.add(user_msg)
            db.session.commit()

    try:
        # 确保消息格式符合火山方舟 API 要求
        validated_messages = []

        # 检查用户最后一条消息是否与商品相关
        last_user_content = ""
        for msg in payload["messages"]:
            if msg["role"] == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    # 提取所有文本内容并拼接
                    text_parts = [
                        item["text"] for item in content if item["type"] == "text"
                    ]
                    last_user_content = "".join(text_parts)
                elif isinstance(content, str):
                    last_user_content = content
                else:
                    last_user_content = str(content)

        # 判断用户意图
        is_asking_mall = is_asking_about_mall_products(last_user_content)
        is_asking_general = is_asking_about_general_products(last_user_content)
        is_asking_all = is_asking_all_products(last_user_content)

        # 根据用户意图获取相关商品
        if is_asking_all:
            # 用户询问所有商品
            relevant_products = get_all_products()
        else:
            # 提取关键词
            keywords = extract_product_keywords(last_user_content)
            current_app.logger.info(f"提取的关键词: {keywords}")

            # 搜索相关商品
            relevant_products = search_products_by_keywords(keywords)
            current_app.logger.info(f"找到 {len(relevant_products)} 个相关商品")

        # 根据用户意图构建不同的系统提示
        if is_asking_mall or is_asking_all:
            # 用户明确询问商城商品或所有商品
            system_prompt = build_mall_specific_prompt(relevant_products)
        elif is_asking_general:
            # 用户明确询问一般网络商品
            system_prompt = build_general_product_prompt()
        else:
            # 用户意图不明确，使用混合提示
            system_prompt = build_hybrid_prompt(relevant_products)

        # 添加系统提示
        validated_messages.append({"role": "system", "content": system_prompt})

        # 添加用户消息
        for msg in payload["messages"]:
            # 确保 content 字段存在且为字符串
            content = msg.get("content", "")
            if isinstance(content, list):
                # 提取所有文本内容并拼接
                text_parts = [
                    item["text"] for item in content if item["type"] == "text"
                ]
                content = "".join(text_parts)
            elif not isinstance(content, str):
                content = str(content)

            validated_messages.append({"role": msg["role"], "content": content})

        # 调用火山方舟 API
        response = client.chat.completions.create(
            model=model, messages=validated_messages  # 使用验证后的消息
        )

        # 提取 AI 回复内容
        ai_content = response.choices[0].message.content

        # 构建响应，包含AI回复和商品信息
        chat_response = {
            "choices": [{"message": {"role": "assistant", "content": ai_content}}],
            # 添加商品信息到响应中（仅当用户询问商城商品时）
            "products": (
                [
                    {
                        "id": product.id,
                        "name": product.name,
                        "price": product.price,
                        "image": product.image,
                        "description": product.description,
                    }
                    for product in relevant_products
                ]
                if (is_asking_mall or is_asking_all) and relevant_products
                else []
            ),
        }

        # 保存 AI 回复 - 添加去重检查
        ai_duplicate_window = 3000  # 3秒时间窗口
        ai_duplicate = AIMessage.query.filter(
            AIMessage.user_id == current_user.id,
            AIMessage.content == ai_content,
            AIMessage.timestamp >= int(time.time() * 1000) - ai_duplicate_window,
        ).first()

        if not ai_duplicate:
            ai_msg = AIMessage(
                user_id=current_user.id,
                role="assistant",
                content=ai_content,
                timestamp=int(time.time() * 1000),
            )
            db.session.add(ai_msg)
            db.session.commit()

        return jsonify(chat_response), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"AI 代理错误: {str(e)}")
        return jsonify({"error": "内部服务器错误", "message": str(e)}), 500


# 添加一个路由用于手动重新加载商品关键词
@ai_api.route("/reload-keywords", methods=["POST"])
@token_required
def reload_keywords(current_user):
    try:
        load_all_product_keywords()
        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"成功加载 {len(all_product_keywords)} 个商品关键词",
                    "keywords_count": len(all_product_keywords),
                }
            ),
            200,
        )
    except Exception as e:
        current_app.logger.error(f"重新加载关键词失败: {str(e)}")
        return (
            jsonify({"status": "error", "message": f"重新加载关键词失败: {str(e)}"}),
            500,
        )
