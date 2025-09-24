import pytest
from app.auth import token_required
from unittest.mock import patch, MagicMock
from flask import jsonify


def test_token_required_decorator(test_app):
    """测试token_required装饰器"""
    with test_app.app_context():
        # 创建一个模拟函数
        mock_function = MagicMock(return_value=jsonify({"success": True}))

        # 应用装饰器
        decorated_function = token_required(mock_function)

        # 模拟JWT身份
        with patch("app.auth.get_jwt_identity") as mock_identity, patch(
            "app.auth.get_jwt"
        ) as mock_jwt, patch("app.auth.current_app") as mock_app, patch(
            "app.auth.TokenBlacklist"
        ) as mock_blacklist:

            # 设置模拟返回值
            mock_identity.return_value = "1"
            mock_jwt.return_value = {"jti": "test-jti"}
            mock_blacklist.query.filter_by.return_value.first.return_value = None

            # 模拟用户查询
            mock_user = MagicMock()
            mock_user.id = 1
            mock_app.extensions = {"sqlalchemy": MagicMock()}
            mock_app.extensions["sqlalchemy"].db = MagicMock()
            mock_app.extensions[
                "sqlalchemy"
            ].db.session.query.return_value.get.return_value = mock_user

            # 调用装饰后的函数
            result = decorated_function()

            # 验证函数被调用
            assert mock_function.called
            assert result.json["success"] is True
