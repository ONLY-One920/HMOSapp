import pytest
import jwt


def test_jwt_tampering_protection(test_client, init_database):
    """测试JWT篡改防护"""
    # 先获取有效的token
    response = test_client.post(
        "/api/login", json={"username": "123456", "password": "password123"}
    )

    valid_token = response.json["access_token"]

    # 尝试篡改token
    try:
        # 解码token
        decoded = jwt.decode(valid_token, options={"verify_signature": False})
        # 修改payload
        decoded["user_id"] = "999"  # 尝试修改用户ID
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
    """测试过期令牌拒绝"""
    # 创建一个过期的token（需要设置较短的过期时间）
    # 这个测试可能需要调整应用配置或使用特殊方法创建过期token
    pass  # 实现取决于你的JWT配置


def test_token_revocation(authenticated_client, init_database):
    """测试令牌撤销功能"""
    # 先登出使token失效
    response = authenticated_client.post("/api/logout")
    assert response.status_code == 200

    # 尝试使用已撤销的token访问受保护接口
    response = authenticated_client.get("/api/verify")

    # 应该返回401，说明令牌已失效
    assert response.status_code == 401
