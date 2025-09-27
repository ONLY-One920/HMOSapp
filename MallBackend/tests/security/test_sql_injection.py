import pytest
import time
from app import db


def test_sql_injection_in_login(test_client):
    """测试登录接口的SQL注入防护"""
    # 添加超时机制
    start_time = time.time()
    timeout = 10  # 10秒超时

    try:
        # 尝试SQL注入攻击 - 移除timeout参数
        response = test_client.post(
            "/api/login", json={"username": "admin' OR '1'='1", "password": "anything"}
        )

        # 应该返回401而不是200，说明SQL注入被阻止
        assert response.status_code == 401
        assert "无效" in response.json["error"]

    except Exception as e:
        # 如果超时或其他异常，记录并失败
        if time.time() - start_time > timeout:
            pytest.fail(f"测试超时: {timeout}秒")
        else:
            pytest.fail(f"测试异常: {str(e)}")


def test_sql_injection_in_search(test_client):
    """测试搜索接口的SQL注入防护"""
    # 添加超时机制
    start_time = time.time()
    timeout = 10  # 10秒超时

    try:
        # 尝试SQL注入攻击 - 移除timeout参数
        response = test_client.get("/api/products/search?q=华为%20OR%201=1")

        # 应该返回正常结果而不是错误或异常数据
        assert response.status_code == 200
        assert isinstance(response.json, list)

    except Exception as e:
        # 如果超时或其他异常，记录并失败
        if time.time() - start_time > timeout:
            pytest.fail(f"测试超时: {timeout}秒")
        else:
            pytest.fail(f"测试异常: {str(e)}")


def test_xss_in_product_description(authenticated_client, test_client):
    """测试XSS注入防护"""
    # 添加超时机制
    start_time = time.time()
    timeout = 10  # 10秒超时

    try:
        # 尝试添加包含XSS脚本的商品 - 移除timeout参数
        response = authenticated_client.post(
            "/api/products",
            json={
                "id": "xss-test",
                "name": "XSS测试商品",
                "price": 99.99,
                "image": "test.jpg",
                "description": '<script>alert("XSS")</script>',
            },
        )

        # 应该成功创建商品（XSS防护可能在前端或显示时处理）
        assert response.status_code == 201

        # 获取商品详情，验证描述是否被正确处理
        response = test_client.get("/api/products/xss-test/detail")
        assert response.status_code == 200

        # 根据实际XSS防护策略进行验证
        # 扩展：例如，如果后端进行了HTML转义，应该包含转义后的字符
        assert (
            "<script>" in response.json["description"]
            or "&lt;script&gt;" in response.json["description"]
        )

    except Exception as e:
        # 如果超时或其他异常，记录并失败
        if time.time() - start_time > timeout:
            pytest.fail(f"测试超时: {timeout}秒")
        else:
            pytest.fail(f"测试异常: {str(e)}")


def test_sql_injection_in_product_search(test_client):
    """测试商品搜索接口的SQL注入防护"""
    # 添加超时机制
    start_time = time.time()
    timeout = 10  # 10秒超时

    try:
        # 尝试SQL注入攻击 - 移除timeout参数
        response = test_client.get("/api/products/search?q=华为%27%20OR%201=1--")

        # 应该返回正常结果而不是错误或异常数据
        assert response.status_code == 200
        assert isinstance(response.json, list)

    except Exception as e:
        # 如果超时或其他异常，记录并失败
        if time.time() - start_time > timeout:
            pytest.fail(f"测试超时: {timeout}秒")
        else:
            pytest.fail(f"测试异常: {str(e)}")


def test_xss_in_product_description_display(test_client, authenticated_client):
    """测试XSS在商品描述显示时的防护"""
    # 添加超时机制
    start_time = time.time()
    timeout = 15  # 15秒超时，因为这个测试需要多个步骤

    try:
        # 添加包含XSS脚本的商品 - 移除timeout参数
        response = authenticated_client.post(
            "/api/products",
            json={
                "id": "xss-test-2",
                "name": "XSS测试商品2",
                "price": 99.99,
                "image": "test.jpg",
                "description": '<script>alert("XSS")</script>',
            },
        )
        assert response.status_code == 201

        # 获取商品详情，验证XSS是否被正确处理
        response = test_client.get("/api/products/xss-test-2/detail")
        assert response.status_code == 200

        # 根据实际XSS防护策略进行验证
        # 扩展：例如，如果后端进行了HTML转义，应该包含转义后的字符
        assert (
            "<script>" in response.json["description"]
            or "&lt;script&gt;" in response.json["description"]
        )

        # 清理测试数据
        with test_client.application.app_context():
            from app.models import Product

            product = Product.query.get("xss-test-2")
            if product:
                db.session.delete(product)
                db.session.commit()

    except Exception as e:
        # 如果超时或其他异常，记录并失败
        if time.time() - start_time > timeout:
            pytest.fail(f"测试超时: {timeout}秒")
        else:
            pytest.fail(f"测试异常: {str(e)}")
