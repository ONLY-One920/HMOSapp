import pytest
import os
import tempfile
from flask_migrate import upgrade, downgrade, init
from app import create_app, db


def test_migrations():
    """测试数据库迁移"""
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        # 创建测试应用
        app = create_app()
        app.config.update(
            {
                "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            }
        )

        with app.app_context():
            # 初始化迁移仓库
            migrations_dir = os.path.join(os.path.dirname(__file__), "../../migrations")

            # 如果迁移目录已存在，直接应用迁移
            if os.path.exists(migrations_dir):
                upgrade(directory=migrations_dir)
            else:
                init(directory=migrations_dir)
                upgrade(directory=migrations_dir)

            # 验证表结构
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            assert "users" in tables
            assert "products" in tables
            assert "cart_items" in tables
            assert "ai_messages" in tables
            assert "token_blacklist" in tables

            # 回滚迁移
            downgrade(directory=migrations_dir, revision="base")

    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)
