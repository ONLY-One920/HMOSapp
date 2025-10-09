from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from . import db
from .models import Product, CartItem, AIMessage
from .auth import token_required
import json
import random

main_api = Blueprint("main_api", __name__)


@main_api.route("/api/health", methods=["GET"])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "healthy"}), 200


@main_api.route("/")
def home():
    return jsonify(
        {
            "status": "running",
            "message": "MallBackend API is running",
            "version": "1.0.0",
            "endpoints": {
                "products": "/api/products",
                "cart": "/api/cart",
                "ai_chat": "/api/ai/chat",
                "ai_messages": "/api/ai/messages",
                "register": "/api/register",
                "login": "/api/login",
                "logout": "/api/logout",
            },
        }
    )


# 添加全局变量存储上一次的商品组合
last_product_combination = []


@main_api.route("/api/products", methods=["GET"])
def get_products():
    # 获取所有商品
    all_products = Product.query.all()

    # 如果商品数量不足5个，直接返回所有商品
    if len(all_products) <= 5:
        return jsonify(
            [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "image": p.image,
                    "description": p.description,
                }
                for p in all_products
            ]
        )

    # 随机选择5个商品，确保与上一次不同
    global last_product_combination
    # 尝试最多10次找到不同的组合
    for _ in range(10):
        selected_products = random.sample(all_products, 5)
        selected_ids = sorted([p.id for p in selected_products])

        # 检查是否与上一次相同
        if selected_ids != last_product_combination:
            last_product_combination = selected_ids
            return jsonify(
                [
                    {
                        "id": p.id,
                        "name": p.name,
                        "price": p.price,
                        "image": p.image,
                        "description": p.description,
                    }
                    for p in selected_products
                ]
            )
    # 如果10次尝试后仍然相同，仍然返回随机选择的结果
    selected_products = random.sample(all_products, 5)
    return jsonify(
        [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "image": p.image,
                "description": p.description,
            }
            for p in selected_products
        ]
    )


@main_api.route("/api/products", methods=["POST"])
@token_required
def create_product():
    data = request.json
    required_fields = ["id", "name", "price"]
    if not all(field in data for field in required_fields):
        return jsonify({"status": "error", "error": "缺少必要参数"}), 400

    if Product.query.get(data["id"]):
        return jsonify({"status": "error", "error": "商品ID已存在"}), 400

    # 处理图片列表（默认为空列表）
    images = data.get("images", [])
    if not isinstance(images, list):
        images = []

    new_product = Product(
        id=data["id"],
        name=data["name"],
        price=data["price"],
        image=data.get("image", ""),
        images=json.dumps(images),  # 存储为JSON字符串
        description=data.get("description", ""),
    )
    db.session.add(new_product)
    db.session.commit()

    return jsonify({"message": "商品创建成功", "product_id": new_product.id}), 201


@main_api.route("/api/products/<product_id>", methods=["PUT"])
@token_required
def update_product( product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"status": "error", "error": "商品不存在"}), 404

    data = request.json
    if "name" in data:
        product.name = data["name"]
    if "price" in data:
        product.price = data["price"]
    if "image" in data:
        product.image = data["image"]
    if "description" in data:
        product.description = data["description"]
    if "images" in data and isinstance(data["images"], list):
        product.images = json.dumps(data["images"])  # 更新图片列表

    db.session.commit()
    return jsonify({"status": "success", "message": "商品更新成功"}), 200


@main_api.route("/api/products/<product_id>", methods=["DELETE"])
@token_required
def delete_product( product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"status": "error", "error": "商品不存在"}), 404

    # 删除购物车中相关项
    CartItem.query.filter_by(product_id=product_id).delete()
    db.session.delete(product)
    db.session.commit()
    return jsonify({"status": "success", "message": "商品已删除"}), 200


@main_api.route("/api/products/search", methods=["GET"])
def search_products():
    """搜索商品"""
    keyword = request.args.get("q", "")
    if not keyword:
        return jsonify({"status": "error", "error": "缺少搜索关键词"}), 400

    # 构建查询条件
    from sqlalchemy import or_

    products = Product.query.filter(
        or_(
            Product.name.ilike(f"%{keyword}%"),
            Product.description.ilike(f"%{keyword}%"),
        )
    ).all()

    return jsonify(
        [
            {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "image": p.image,
                "description": p.description,
            }
            for p in products
        ]
    )


@main_api.route("/api/products/<product_id>/detail", methods=["GET"])
def get_product_detail(product_id):
    """获取商品详情(包含多张图片)"""
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"status": "error", "error": "商品不存在"}), 404

    try:
        # 解析图片列表
        images = json.loads(product.images) if product.images else []
    except:
        images = []

        # 确保至少有一张主图
    if not images and product.image:
        images = [product.image]

    return jsonify(
        {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "image": product.image,
            "images": images,  # 返回多张图片列表
            "description": product.description,
        }
    )


@main_api.route("/api/cart", methods=["GET"])
@token_required
def get_cart(current_user):
    # 使用join优化查询性能
    items = (
        CartItem.query.filter_by(user_id=current_user.id)
        .join(Product, CartItem.product_id == Product.id)
        .all()
    )

    cart_data = [
        {
            "id": item.id,
            "product": {
                "id": item.product.id,
                "name": item.product.name,
                "price": item.product.price,
                "image": item.product.image,
                "description": item.product.description,
            },
            "quantity": item.quantity,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in items
    ]

    return jsonify(cart_data)


@main_api.route("/api/cart", methods=["POST"])
@token_required
def add_to_cart(current_user):
    data = request.json
    product_id = data.get("product_id")
    if not product_id:
        return jsonify({"status": "error", "error": "缺少商品ID"}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"status": "error", "error": "商品不存在"}), 404

    # 使用更健壮的方式查询购物车项
    cart_item = CartItem.query.filter(
        CartItem.user_id == current_user.id, CartItem.product_id == product_id
    ).first()

    try:
        if cart_item:
            cart_item.quantity += 1
            # 如果updated_at字段存在则更新
            if hasattr(cart_item, "updated_at"):
                cart_item.updated_at = datetime.utcnow()
        else:
            cart_item = CartItem(
                user_id=current_user.id, product_id=product_id, quantity=1
            )
            db.session.add(cart_item)

        db.session.commit()

        # 返回完整的购物车状态
        items = CartItem.query.filter_by(user_id=current_user.id).all()
        cart_data = [
            {
                "id": item.id,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "price": item.product.price,
                    "image": item.product.image,
                },
                "quantity": item.quantity,
            }
            for item in items
        ]

        return (
            jsonify(
                {"status": "success", "message": "已添加到购物车", "cart": cart_data}
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"添加到购物车失败: {str(e)}")
        return (
            jsonify(
                {"status": "error", "error": "添加到购物车失败", "message": str(e)}
            ),
            500,
        )


@main_api.route("/api/cart", methods=["PUT"])
@token_required
def update_cart_quantity(current_user):
    data = request.json
    item_id = data.get("item_id")
    quantity = data.get("quantity")

    if not item_id or quantity is None:
        return jsonify({"status": "error", "error": "缺少参数"}), 400

    # 当数量 <= 0 时执行删除
    if quantity <= 0:
        # 直接调用删除逻辑，而不是重定向到另一个路由
        return remove_cart_item_directly(current_user, item_id)

    # 使用更健壮的查询方式
    cart_item = CartItem.query.filter(
        CartItem.id == item_id, CartItem.user_id == current_user.id
    ).first()

    if not cart_item:
        current_app.logger.error(
            f"购物车项未找到: item_id={item_id} user_id={current_user.id}"
        )
        return jsonify({"status": "error", "error": "购物车项不存在"}), 404

    cart_item.quantity = quantity

    # 如果updated_at字段存在则更新
    if hasattr(cart_item, "updated_at"):
        cart_item.updated_at = datetime.utcnow()

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新购物车数量失败: {str(e)}")
        return (
            jsonify(
                {"status": "error", "error": "更新购物车数量失败", "message": str(e)}
            ),
            500,
        )

    # 返回完整的购物车状态
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    cart_data = [
        {
            "id": item.id,
            "product": {
                "id": item.product.id,
                "name": item.product.name,
                "price": item.product.price,
                "image": item.product.image,
            },
            "quantity": item.quantity,
        }
        for item in items
    ]

    return (
        jsonify({"status": "success", "message": "购物车已更新", "cart": cart_data}),
        200,
    )


def remove_cart_item_directly(current_user, item_id):
    """直接删除购物车项的内部函数"""
    # 使用更健壮的查询方式
    cart_item = CartItem.query.filter(
        CartItem.id == item_id, CartItem.user_id == current_user.id
    ).first()

    if not cart_item:
        return jsonify({"status": "error", "error": "购物车项不存在"}), 404

    try:
        db.session.delete(cart_item)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"移除购物车项失败: {str(e)}")
        return (
            jsonify({"status": "error", "error": "移除商品失败", "message": str(e)}),
            500,
        )

    # 返回剩余的购物车状态
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    cart_data = [
        {
            "id": item.id,
            "product": {
                "id": item.product.id,
                "name": item.product.name,
                "price": item.product.price,
                "image": item.product.image,
            },
            "quantity": item.quantity,
        }
        for item in items
    ]

    return (
        jsonify({"status": "success", "message": "已从购物车移除", "cart": cart_data}),
        200,
    )


@main_api.route("/api/cart/<int:item_id>", methods=["DELETE"])
@token_required
def remove_from_cart(current_user, item_id):
    # 使用更健壮的查询方式
    cart_item = CartItem.query.filter(
        CartItem.id == item_id, CartItem.user_id == current_user.id
    ).first()

    if not cart_item:
        return jsonify({"status": "error", "error": "购物车项不存在"}), 404

    try:
        db.session.delete(cart_item)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"移除购物车项失败: {str(e)}")
        return (
            jsonify({"status": "error", "error": "移除商品失败", "message": str(e)}),
            500,
        )

    # 返回剩余的购物车状态
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    cart_data = [
        {
            "id": item.id,
            "product": {
                "id": item.product.id,
                "name": item.product.name,
                "price": item.product.price,
                "image": item.product.image,
            },
            "quantity": item.quantity,
        }
        for item in items
    ]

    return (
        jsonify({"status": "success", "message": "已从购物车移除", "cart": cart_data}),
        200,
    )


@main_api.route("/api/ai/messages", methods=["GET"])
@token_required
def get_ai_messages(current_user):
    messages = (
        AIMessage.query.filter_by(user_id=current_user.id)
        .order_by(AIMessage.timestamp)
        .all()
    )
    return jsonify(
        [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
            }
            for msg in messages
        ]
    )


@main_api.route("/api/ai/messages/<int:message_id>", methods=["DELETE"])
@token_required
def delete_ai_message(current_user, message_id):
    """删除指定的AI消息"""
    try:
        message = AIMessage.query.get(message_id)
        if not message:
            return jsonify({"status": "error", "error": "消息不存在"}), 404

        if message.user_id != current_user.id:
            return jsonify({"status": "error", "error": "无权删除该消息"}), 403

        db.session.delete(message)
        db.session.commit()
        return jsonify({"status": "success", "message": "消息已删除"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"删除AI消息失败: {str(e)}")
        return (
            jsonify({"status": "error", "error": "删除消息失败", "message": str(e)}),
            500,
        )


@main_api.route("/api/ai/messages", methods=["POST"])
@token_required
def save_ai_message(current_user):
    data = request.json
    role = data.get("role", "user")
    content = data.get("content")
    timestamp = data.get("timestamp")

    if not content or not timestamp:
        return jsonify({"status": "error", "error": "缺少必要参数"}), 400

    user_msg = AIMessage(
        user_id=current_user.id, role=role, content=content, timestamp=timestamp
    )
    db.session.add(user_msg)
    db.session.commit()

    return jsonify({"status": "success", "message": "消息已保存"}), 201
