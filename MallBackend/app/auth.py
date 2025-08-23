# app/auth.py
import re
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from . import db
from .models import User, TokenBlacklist

auth_api = Blueprint('auth_api', __name__)

def token_required(fn):
    @jwt_required()
    def decorated_function(*args, **kwargs):
        try:
            # 获取用户ID (兼容字符串和整数)
            user_id = get_jwt_identity()
            # 检查是否是字符串类型并转换
            if isinstance(user_id, str):
                try:
                    user_id = int(user_id)
                except (TypeError, ValueError):
                    current_app.logger.error(f"无效的用户标识格式: {user_id}")
                    return jsonify({'status': 'error', 'error': '无效的用户标识格式'}), 401

            # 检查令牌是否在黑名单中
            jti = get_jwt()['jti']
            token = TokenBlacklist.query.filter_by(jti=jti).first()
            if token:
                current_app.logger.warning(f"令牌已被加入黑名单: {jti}")
                return jsonify({'status': 'error', 'error': '令牌已失效'}), 401

            current_user = User.query.get(user_id)
            if not current_user:
                current_app.logger.error(f"用户不存在: ID={user_id}")
                return jsonify({'status': 'error', 'error': '无效的token'}), 401

            return fn(current_user, *args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"令牌验证失败: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': '令牌验证失败',
                'message': str(e),
                'jwt_identity': get_jwt_identity(),
                'request_headers': dict(request.headers)
            }), 401

    decorated_function.__name__ = fn.__name__
    return decorated_function

@auth_api.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # 验证用户名是否为6位数字
    if not username or not re.match(r'^\d{6}$', username):
        return jsonify({'status': 'error', 'error': '用户名必须是6位数字'}), 400

    # 验证密码长度
    if not password or len(password) > 20:
        return jsonify({'status': 'error', 'error': '密码长度需在1-20个字符之间'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'error': '用户名已存在'}), 400

    new_user = User(
        username=username,
        password=generate_password_hash(password)
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': '用户创建成功',
        'user_id': new_user.id
    }), 201

@auth_api.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({'status': 'error', 'error': '无效的用户名或密码'}), 401

    # 将用户ID转换为字符串作为identity
    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        'status': 'success',
        'access_token': access_token,
        'user_id': user.id,
        'username': user.username
    }), 200

@auth_api.route('/api/logout', methods=['POST'])
@token_required
def logout(current_user):
    try:
        # 获取当前令牌的JTI (JWT ID)
        jti = get_jwt()['jti']
        # 获取令牌的过期时间
        exp_timestamp = get_jwt()['exp']
        expires_at = datetime.utcfromtimestamp(exp_timestamp)

        # 将令牌加入黑名单
        blacklisted_token = TokenBlacklist(
            jti=jti,
            expires_at=expires_at
        )

        db.session.add(blacklisted_token)
        db.session.commit()

        return jsonify({'status': 'success', 'message': '退出成功'}), 200
    except Exception as e:
        current_app.logger.error(f"退出失败: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'status': 'error', 'error': '退出失败', 'details': str(e)}), 500

# 新增：验证token接口
@auth_api.route('/api/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    """验证token有效性并返回用户信息"""
    return jsonify({
        'status': 'success',
        'user_id': current_user.id,
        'username': current_user.username
    }), 200