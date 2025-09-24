import pytest
import os
import sys
from unittest.mock import MagicMock, patch
import time

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import User, Product, CartItem, AIMessage, TokenBlacklist
from werkzeug.security import generate_password_hash


@pytest.fixture(scope="module")
def test_app():
    """创建测试应用"""
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "JWT_SECRET_KEY": "test-secret-key",
            "ARK_API_KEY": "test-ark-key",
            "ARK_BASE_URL": "https://test-ark.example.com/api/v3",
        }
    )

    with app.app_context():
        db.create_all()
        yield app

        # 添加清理操作
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="module")
def test_client(test_app):
    """创建测试客户端"""
    return test_app.test_client()


@pytest.fixture(scope="function")  # 改为function级别，确保每个测试独立
def init_database(test_app):
    """初始化测试数据库"""
    with test_app.app_context():
        # 清除所有数据 - 按照正确的顺序删除，避免外键约束问题
        db.session.query(AIMessage).delete()
        db.session.query(CartItem).delete()
        db.session.query(TokenBlacklist).delete()
        db.session.query(User).delete()
        db.session.query(Product).delete()
        db.session.commit()

        # 添加测试用户 - 使用正确的密码哈希生成方式
        test_user = User(
            username="123456",
            password=generate_password_hash("password123"),  # 动态生成哈希
        )
        db.session.add(test_user)

        # 添加测试商品
        products = [
            Product(
                id="1",
                name="华为手机",
                price=1999.0,
                image="hw.png",
                description="高性能旗舰手机",
            ),
            Product(
                id="2",
                name="小米手机",
                price=4399.0,
                image="xm.png",
                description="性价比之王",
            ),
        ]

        for product in products:
            db.session.add(product)

        db.session.commit()
        yield db

        # 测试结束后清理 - 按照正确的顺序删除
        db.session.query(AIMessage).delete()
        db.session.query(CartItem).delete()
        db.session.query(TokenBlacklist).delete()
        db.session.query(User).delete()
        db.session.query(Product).delete()
        db.session.commit()


@pytest.fixture(scope="function")
def authenticated_client(test_client, init_database):
    """创建已认证的测试客户端"""
    # 登录获取token
    response = test_client.post(
        "/api/login", json={"username": "123456", "password": "password123"}
    )

    token = response.json["access_token"]

    # 设置认证头
    test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    yield test_client

    # 清理认证头
    if "HTTP_AUTHORIZATION" in test_client.environ_base:
        del test_client.environ_base["HTTP_AUTHORIZATION"]


@pytest.fixture(scope="function")
def mock_ai_response():
    """模拟AI响应"""
    with patch("app.ai_proxy.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "这是一个AI回复"

        mock_client.chat.completions.create.return_value = mock_response

        yield mock_client
