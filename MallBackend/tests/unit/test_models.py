import pytest
from app.models import User, Product, CartItem, AIMessage, TokenBlacklist
from datetime import datetime


def test_user_model():
    """测试用户模型"""
    user = User(username="testuser", password="testpass")
    assert user.username == "testuser"
    assert user.password == "testpass"
    assert str(user) == "<User testuser>"


def test_product_model():
    """测试商品模型"""
    product = Product(
        id="test-id",
        name="Test Product",
        price=99.99,
        image="test.jpg",
        description="Test description",
    )
    assert product.id == "test-id"
    assert product.name == "Test Product"
    assert product.price == 99.99
    assert str(product) == "<Product Test Product>"


def test_cart_item_model():
    """测试购物车项模型"""
    product = Product(id="test-id", name="Test Product", price=99.99)
    user = User(username="testuser", password="testpass")

    cart_item = CartItem(user=user, product=product, quantity=2)
    assert cart_item.quantity == 2
    assert cart_item.product.name == "Test Product"
    assert cart_item.user.username == "testuser"

    # 测试to_dict方法
    cart_dict = cart_item.to_dict()
    assert cart_dict["quantity"] == 2
    assert cart_dict["product"]["name"] == "Test Product"


def test_ai_message_model():
    """测试AI消息模型"""
    user = User(username="testuser", password="testpass")
    message = AIMessage(
        user=user, role="user", content="Hello, AI", timestamp=1234567890
    )
    assert message.role == "user"
    assert message.content == "Hello, AI"
    assert str(message).startswith("<AIMessage user:")


def test_token_blacklist_model():
    """测试令牌黑名单模型"""
    token = TokenBlacklist(jti="test-jti", expires_at=datetime.now())
    assert token.jti == "test-jti"
    assert str(token) == "<TokenBlacklist jti=test-jti>"
