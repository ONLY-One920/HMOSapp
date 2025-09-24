from flask import Blueprint, jsonify, current_app
import os
import json

swagger_bp = Blueprint("swagger", __name__)


@swagger_bp.route("/static/swagger.json")
def swagger_json():
    """返回 OpenAPI 规范文档"""
    swagger_path = os.path.join(current_app.root_path, "static", "swagger.json")
    try:
        with open(swagger_path, "r", encoding="utf-8") as f:
            swagger_data = json.load(f)
            return jsonify(swagger_data)
    except Exception as e:
        return jsonify({"error": f"无法加载 Swagger 文件: {str(e)}"}), 500
