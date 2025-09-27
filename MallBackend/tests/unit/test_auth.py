import pytest
from app.auth import token_required
from unittest.mock import patch, MagicMock
from flask import jsonify
def test_token_required_decorator(test_app):
    """测试token_required装饰器"""
    with test_app.app_context():
        # 创建一个模拟函数
        @token_required
        def mock_function(current_user):
            return jsonify({'success': True, 'user_id': current_user.id})

        # 模拟JWT身份
        with patch('app.auth.get_jwt_identity') as mock_identity, \
                patch('app.auth.get_jwt') as mock_jwt, \
                patch('app.auth.current_app') as mock_app:
            # 设置模拟返回值
            mock_identity.return_value = '1'
            mock_jwt.return_value = {'jti': 'test-jti'}

            # 模拟用户查询
            mock_user = MagicMock()
            mock_user.id = 1

            # 模拟数据库查询
            with patch('app.auth.TokenBlacklist') as mock_blacklist, \
                    patch('app.auth.User') as mock_user_model:
                mock_blacklist.query.filter_by.return_value.first.return_value = None
                mock_user_model.query.get.return_value = mock_user

                # 模拟请求上下文
                with test_app.test_request_context():
                    # 调用装饰后的函数
                    result = mock_function()

                    # 验证函数被调用
                    assert result.json['success'] is True
                    assert result.json['user_id'] == 1