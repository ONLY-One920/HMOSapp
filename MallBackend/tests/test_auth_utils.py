import pytest
from werkzeug.security import generate_password_hash, check_password_hash


# 这是一个简单的单元测试示例，测试密码加密和验证功能
class TestPasswordHashing:
    """测试密码加密工具函数"""

    def test_password_hashing_and_verification(self):
        """
        测试步骤：
        1. 对一个明文密码进行加密
        2. 验证另一个明文密码是否与加密后的密码匹配
        3. 验证正确的明文密码是否与加密后的密码匹配
        """
        # 测试数据
        plain_password = "mySecurePassword123"
        wrong_password = "wrongPassword"

        # 执行加密
        hashed_password = generate_password_hash(plain_password)

        # 断言：加密后的密码不应与原密码相同
        assert hashed_password != plain_password, "加密后的密码不应是明文"

        # 断言：错误的密码验证应返回 False
        assert not check_password_hash(
            hashed_password, wrong_password
        ), "错误密码验证应失败"

        # 断言：正确的密码验证应返回 True
        assert check_password_hash(
            hashed_password, plain_password
        ), "正确密码验证应成功"

    def test_different_salts_produce_different_hashes(self):
        """
        测试即使密码相同，每次加密也会因为随机盐值而产生不同的哈希值
        """
        password = "testPassword"
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)

        # 两次加密结果应该不同
        assert hash1 != hash2, "相同密码的两次加密应产生不同的哈希值"

        # 但两者都应该能验证通过
        assert check_password_hash(hash1, password)
        assert check_password_hash(hash2, password)


# 运行这个测试的命令: python -m pytest tests/test_auth_utils.py -v
