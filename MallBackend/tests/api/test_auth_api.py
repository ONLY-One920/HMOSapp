def test_register_api(test_client, init_database):
    """测试注册API"""
    # 测试成功注册
    response = test_client.post(
        "/api/register", json={"username": "654321", "password": "newpassword"}
    )

    assert response.status_code == 201
    assert "user_id" in response.json

    # 测试用户名已存在
    response = test_client.post(
        "/api/register", json={"username": "123456", "password": "password123"}
    )

    assert response.status_code == 400
    assert "已存在" in response.json["error"]

    # 测试用户名格式错误
    response = test_client.post(
        "/api/register", json={"username": "123", "password": "password123"}
    )

    assert response.status_code == 400
    assert "6位数字" in response.json["error"]


def test_login_api(test_client, init_database):
    """测试登录API"""
    # 测试成功登录
    response = test_client.post(
        "/api/login", json={"username": "123456", "password": "password123"}
    )

    assert response.status_code == 200
    assert "access_token" in response.json

    # 测试错误密码
    response = test_client.post(
        "/api/login", json={"username": "123456", "password": "wrongpassword"}
    )

    assert response.status_code == 401
    assert "无效" in response.json["error"]

    # 测试用户不存在
    response = test_client.post(
        "/api/login", json={"username": "nonexistent", "password": "password123"}
    )

    assert response.status_code == 401
    assert "无效" in response.json["error"]


def test_logout_api(authenticated_client):
    """测试登出API"""
    response = authenticated_client.post("/api/logout")

    assert response.status_code == 200
    assert "退出成功" in response.json["message"]


def test_verify_token_api(authenticated_client):
    """测试验证令牌API"""
    response = authenticated_client.get("/api/verify")

    assert response.status_code == 200
    assert response.json["status"] == "success"
    assert "user_id" in response.json


def test_verify_token_with_invalid_token(test_client):
    """测试使用无效token验证"""
    test_client.environ_base["HTTP_AUTHORIZATION"] = "Bearer invalid_token"
    response = test_client.get("/api/verify")
    assert response.status_code == 401


def test_logout_without_token(test_client):
    """测试无token登出"""
    response = test_client.post("/api/logout")
    assert response.status_code == 401


def test_register_with_invalid_password(test_client):
    """测试注册时密码过长"""
    response = test_client.post(
        "/api/register",
        json={"username": "999999", "password": "a" * 21},  # 超过20个字符
    )
    assert response.status_code == 400
    assert "密码长度" in response.json["error"]
