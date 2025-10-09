from app import db
from app.models import User, TokenBlacklist
from flask_jwt_extended import create_access_token, decode_token
from datetime import datetime, timedelta


def test_jwt_token_creation_and_verification(test_app):
    """测试JWT令牌创建和验证"""
    with test_app.app_context():
        # 创建测试用户
        user = User(username="testjwt", password="testpass")
        db.session.add(user)
        db.session.commit()

        # 创建访问令牌
        token = create_access_token(identity=str(user.id))

        # 验证令牌
        decoded = decode_token(token)
        assert decoded["sub"] == str(user.id)

        # 测试令牌加入黑名单
        jti = decoded["jti"]
        expires_at = datetime.utcfromtimestamp(decoded["exp"])

        blacklisted_token = TokenBlacklist(jti=jti, expires_at=expires_at)
        db.session.add(blacklisted_token)
        db.session.commit()

        # 验证令牌已在黑名单中
        token_in_blacklist = TokenBlacklist.query.filter_by(jti=jti).first()
        assert token_in_blacklist is not None


def test_token_blacklist_functionality(test_app, init_database):
    """测试令牌黑名单功能"""
    with test_app.app_context():
        from app import db
        from app.models import User, TokenBlacklist
        from flask_jwt_extended import create_access_token, decode_token

        # 创建测试用户
        user = User(username="test_blacklist", password="test_pass")
        db.session.add(user)
        db.session.commit()

        # 创建访问令牌
        token = create_access_token(identity=str(user.id))
        decoded = decode_token(token)
        jti = decoded["jti"]

        # 将令牌加入黑名单
        blacklisted_token = TokenBlacklist(
            jti=jti, expires_at=datetime.utcfromtimestamp(decoded["exp"])
        )
        db.session.add(blacklisted_token)
        db.session.commit()

        # 验证令牌已在黑名单中
        token_in_blacklist = TokenBlacklist.query.filter_by(jti=jti).first()
        assert token_in_blacklist is not None
