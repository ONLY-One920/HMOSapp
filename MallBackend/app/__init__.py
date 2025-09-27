from flask import Flask, send_from_directory, jsonify, request, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import logging

# 加载环境变量
load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def create_app():
    # 使用绝对路径指定静态文件夹
    base_dir = os.path.abspath(os.path.dirname(__file__))
    static_path = os.path.join(base_dir, "..", "static")
    app = Flask(__name__, static_folder=static_path)

    # 配置详细的SQL日志
    if app.config.get("FLASK_ENV") == "development":
        logging.basicConfig()
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        app.logger.setLevel(logging.DEBUG)

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": "*",
                "supports_credentials": True,
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )

    # 配置 - 确保所有配置项正确设置
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fallback_secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # JWT配置 - 修复 proxies 参数问题
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwt_fallback_secret")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 604800  # 设置7天有效期
    app.config["JWT_HEADER_TYPE"] = "Bearer"
    app.config["JWT_HEADER_NAME"] = "Authorization"  # 明确指定头部名称
    app.config["JWT_TOKEN_LOCATION"] = ["headers"]  # 明确指定从头部获取token
    app.config["JWT_ALGORITHM"] = "HS256"  # 明确指定算法
    app.config["JWT_DECODE_ALGORITHMS"] = ["HS256"]  # 指定可接受的算法列表
    # 修复：避免传递不必要的参数
    app.config["JWT_ADDITIONAL_HEADERS"] = {}  # 明确设置为空

    # 火山方舟API配置
    app.config["ARK_API_KEY"] = os.getenv("ARK_API_KEY")
    app.config["ARK_BASE_URL"] = os.getenv(
        "ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"
    )
    app.config["ARK_DEFAULT_MODEL"] = os.getenv(
        "ARK_DEFAULT_MODEL", "doubao-seed-1-6-250615"
    )

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # 配置 Swagger UI
    SWAGGER_URL = "/api/docs"
    API_URL = "/static/swagger.json"

    # 修复Swagger UI配置
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            "app_name": "MallBackend API",
            "docExpansion": "none",
            "supportedSubmitMethods": ["get", "post", "put", "delete"],
            "securityDefinitions": {
                "Bearer": {
                    "type": "apiKey",
                    "name": "Authorization",  # 确保与JWT配置一致
                    "in": "header",
                    "description": "输入格式: Bearer <你的令牌>",
                }
            },
            "security": [{"Bearer": []}],  # 确保所有端点都需要认证
            "validatorUrl": None,
            "displayRequestDuration": True,
            "showCommonExtensions": True,
        },
    )

    # 注册蓝图 - 使用延迟导入
    from .routes import main_api
    from .auth import auth_api
    from .ai_proxy import ai_api

    app.register_blueprint(main_api)
    app.register_blueprint(auth_api)
    app.register_blueprint(ai_api, url_prefix="/api/ai")
    app.register_blueprint(swaggerui_blueprint)

    # 添加黑名单检查回调
    from .models import TokenBlacklist

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """检查令牌是否在黑名单中"""
        jti = jwt_payload["jti"]
        # 使用应用上下文中的db对象
        token = TokenBlacklist.query.filter_by(jti=jti).first()
        return token is not None

    # 添加自定义错误处理器
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        # 获取当前请求的Authorization头
        auth_header = request.headers.get("Authorization", "未提供")

        # 修正空格问题：将多个空格替换为单个空格
        if auth_header and "Bearer" in auth_header:
            corrected_header = "Bearer " + auth_header.split("Bearer")[-1].strip()
        else:
            corrected_header = auth_header

        return (
            jsonify(
                {
                    "error": "无效令牌",
                    "message": str(error),
                    "expected_format": "Authorization: Bearer <token>",
                    "received_header": auth_header,
                    "corrected_header": corrected_header,
                    "debug_info": {
                        "jwt_secret_key": app.config["JWT_SECRET_KEY"],
                        "jwt_header_type": app.config["JWT_HEADER_TYPE"],
                        "jwt_token_location": app.config["JWT_TOKEN_LOCATION"],
                        "hint": "请确保令牌未过期且格式正确(Bearer+空格+token)",
                    },
                }
            ),
            401,
        )

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return (
            jsonify(
                {
                    "error": "缺少认证令牌",
                    "message": str(error),
                    "expected_format": "Authorization: Bearer <token>",
                    "request_headers": dict(request.headers),
                }
            ),
            401,
        )

    # 添加JWT解码错误处理器
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "令牌已过期", "message": "请重新登录获取新令牌"}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return (
            jsonify({"error": "令牌已被撤销", "message": "此令牌已被加入黑名单"}),
            401,
        )

    # 显式添加静态文件路由
    @app.route("/static/<path:filename>")
    def serve_static(filename):
        return send_from_directory(static_path, filename)

    # 添加请求钩子调试Authorization头（仅在开发环境启用）
    if app.config.get("FLASK_ENV") == "development":

        @app.before_request
        def log_headers():
            auth_header = request.headers.get("Authorization")
            if auth_header:
                # 修正空格问题
                if "Bearer" in auth_header:
                    corrected = "Bearer " + auth_header.split("Bearer")[-1].strip()
                else:
                    corrected = auth_header
                app.logger.debug(f"原始Authorization头: {auth_header}")
                app.logger.debug(f"修正后Authorization头: {corrected}")
            return None

    # 添加请求日志中间件
    @app.before_request
    def log_request_info():
        if app.config.get("FLASK_ENV") == "development":
            current_app.logger.debug(f"Request: {request.method} {request.path}")
            current_app.logger.debug(f"Headers: {dict(request.headers)}")
            if request.json:
                current_app.logger.debug(f"Body: {request.json}")

    return app
