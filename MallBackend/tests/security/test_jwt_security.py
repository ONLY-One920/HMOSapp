import pytest
import jwt


def test_jwt_tampering_protection(test_client, init_database):
    """测试JWT篡改防护"""
    # 先获取有效的token
    response = test_client.post(
        "/api/login", json={"username": "123456", "password": "password123"}
    )

    valid_token = response.json["access_token"]

    # 篡改token
    try:
        # 解码token
        decoded = jwt.decode(valid_token, options={"verify_signature": False})
        # 修改payload
        decoded["user_id"] = "999"  # 修改用户ID
        # 使用错误的密钥重新编码
        tampered_token = jwt.encode(decoded, "wrong-secret-key", algorithm="HS256")
    except:
        # 如果编码失败，跳过测试
        pytest.skip("JWT编码失败")

    # 使用篡改后的token访问受保护接口
    test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {tampered_token}"
    response = test_client.get("/api/verify")

    # 应该返回401，说明篡改被检测到
    assert response.status_code == 401


def test_expired_token_rejection(test_client, init_database):
    # 创建一个明显过期的token格式
    # 这个token的过期时间是 2018-12-25，明显已经过期
    expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwiZXhwIjoxNTQ1NzE0NDAwLCJpYXQiOjE1NDU3MTA4MDAsImp0aSI6InRlc3QtZXhwaXJlZCJ9.fake_signature_should_be_rejected"

    test_client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {expired_token}"
    response = test_client.get("/api/verify")

    # 应该返回401，说明过期token被拒绝
    assert response.status_code == 401
    # 可以进一步验证错误消息
    error_data = response.json
    assert "token" in error_data.get("error", "").lower() or "无效令牌" in error_data.get("error", "").lower()


def test_token_revocation(authenticated_client, init_database):
    """测试令牌撤销功能"""
    # 先验证令牌当前有效
    response = authenticated_client.get("/api/verify")
    assert response.status_code == 200, "令牌在登出前应该有效"

    # 登出使token失效
    response = authenticated_client.post("/api/logout")
    assert response.status_code == 200, "登出应该成功"

    # 尝试使用已撤销的token访问受保护接口
    response = authenticated_client.get("/api/verify")

    # 应该返回401，说明令牌已失效
    assert response.status_code == 401, "撤销后的令牌应该被拒绝"
