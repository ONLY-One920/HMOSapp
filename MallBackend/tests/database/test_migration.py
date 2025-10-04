import os
import pytest
import random
from app import create_app, db
from sqlalchemy import text, inspect, create_engine


def test_basic_database_operations():
    """测试基本数据库操作"""

    # 创建临时数据库配置
    db_config = {
        "DB_HOST": os.getenv("DB_HOST", "localhost"),
        "DB_PORT": os.getenv("DB_PORT", "3306"),
        "DB_USER": os.getenv("DB_USER", "root"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", "123456"),
    }

    test_db_name = f"test_basic_{random.randint(1000, 9999)}"

    try:
        app = create_app()
        app.config.update(
            {
                "SQLALCHEMY_DATABASE_URI": (
                    f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASSWORD']}"
                    f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/{test_db_name}"
                ),
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "TESTING": True,
            }
        )

        with app.app_context():
            # 创建测试数据库
            temp_conn_uri = (
                f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASSWORD']}"
                f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/mysql"
            )
            temp_engine = create_engine(temp_conn_uri)
            with temp_engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {test_db_name}"))
            temp_engine.dispose()

            # 直接使用 db.create_all() 创建表
            db.create_all()

            # 验证基本表结构
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            required_tables = [
                "users",
                "products",
                "cart_items",
                "ai_messages",
                "token_blacklist",
            ]
            for table in required_tables:
                assert table in tables, f"缺少表: {table}"

            # 验证 users 表结构
            user_columns = [col["name"] for col in inspector.get_columns("users")]
            expected_user_columns = ["id", "username", "password"]
            for col in expected_user_columns:
                assert col in user_columns, f"users 表缺少列: {col}"

            # 验证 products 表结构
            product_columns = [col["name"] for col in inspector.get_columns("products")]
            expected_product_columns = [
                "id",
                "name",
                "price",
                "image",
                "images",
                "description",
            ]
            for col in expected_product_columns:
                assert col in product_columns, f"products 表缺少列: {col}"

            print("基础数据库操作测试完成")

    except Exception as e:
        print(f"基础数据库操作测试失败: {str(e)}")
        pytest.fail(f"基础数据库操作测试失败: {str(e)}")

    finally:
        # 清理
        try:
            temp_engine = create_engine(temp_conn_uri)
            with temp_engine.connect() as conn:
                conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
            temp_engine.dispose()
        except Exception as e:
            print(f"清理测试数据库失败: {str(e)}")


def test_table_relationships():
    """测试表关系"""

    db_config = {
        "DB_HOST": os.getenv("DB_HOST", "localhost"),
        "DB_PORT": os.getenv("DB_PORT", "3306"),
        "DB_USER": os.getenv("DB_USER", "root"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", "123456"),
    }

    test_db_name = f"test_relations_{random.randint(1000, 9999)}"

    try:
        app = create_app()
        app.config.update(
            {
                "SQLALCHEMY_DATABASE_URI": (
                    f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASSWORD']}"
                    f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/{test_db_name}"
                ),
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "TESTING": True,
            }
        )

        with app.app_context():
            # 创建测试数据库
            temp_conn_uri = (
                f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASSWORD']}"
                f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/mysql"
            )
            temp_engine = create_engine(temp_conn_uri)
            with temp_engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {test_db_name}"))
            temp_engine.dispose()

            # 创建表
            db.create_all()

            # 测试外键关系
            from app.models import User, Product, CartItem

            # 创建测试用户
            user = User(username="testuser", password="testpass")
            db.session.add(user)
            db.session.commit()

            # 创建测试商品
            product = Product(id="test-product", name="Test Product", price=99.99)
            db.session.add(product)
            db.session.commit()

            # 测试购物车项关系
            cart_item = CartItem(user_id=user.id, product_id=product.id, quantity=2)
            db.session.add(cart_item)
            db.session.commit()

            # 验证关系
            assert cart_item.user_id == user.id
            assert cart_item.product_id == product.id
            assert cart_item.quantity == 2

            print("表关系测试完成")

    except Exception as e:
        print(f"表关系测试失败: {str(e)}")
        pytest.fail(f"表关系测试失败: {str(e)}")

    finally:
        # 清理
        try:
            temp_engine = create_engine(temp_conn_uri)
            with temp_engine.connect() as conn:
                conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
            temp_engine.dispose()
        except Exception as e:
            print(f"清理测试数据库失败: {str(e)}")


def test_database_constraints():
    """测试数据库约束"""

    db_config = {
        "DB_HOST": os.getenv("DB_HOST", "localhost"),
        "DB_PORT": os.getenv("DB_PORT", "3306"),
        "DB_USER": os.getenv("DB_USER", "root"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", "123456"),
    }

    test_db_name = f"test_constraints_{random.randint(1000, 9999)}"

    try:
        app = create_app()
        app.config.update(
            {
                "SQLALCHEMY_DATABASE_URI": (
                    f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASSWORD']}"
                    f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/{test_db_name}"
                ),
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "TESTING": True,
            }
        )

        with app.app_context():
            # 创建测试数据库
            temp_conn_uri = (
                f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASSWORD']}"
                f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/mysql"
            )
            temp_engine = create_engine(temp_conn_uri)
            with temp_engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {test_db_name}"))
            temp_engine.dispose()

            # 创建表
            db.create_all()

            from app.models import User

            # 测试唯一约束
            user1 = User(username="uniqueuser", password="pass1")
            db.session.add(user1)
            db.session.commit()

            # 尝试创建相同用户名的用户
            user2 = User(username="uniqueuser", password="pass2")
            db.session.add(user2)

            try:
                db.session.commit()
                pytest.fail("应该触发唯一约束错误")
            except Exception as e:
                db.session.rollback()
                # 期望出现完整性错误
                assert "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e)

            print("数据库约束测试完成")

    except Exception as e:
        print(f"数据库约束测试失败: {str(e)}")
        pytest.fail(f"数据库约束测试失败: {str(e)}")

    finally:
        # 清理
        try:
            temp_engine = create_engine(temp_conn_uri)
            with temp_engine.connect() as conn:
                conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
            temp_engine.dispose()
        except Exception as e:
            print(f"清理测试数据库失败: {str(e)}")


def test_database_transactions():
    """测试数据库事务"""

    db_config = {
        "DB_HOST": os.getenv("DB_HOST", "localhost"),
        "DB_PORT": os.getenv("DB_PORT", "3306"),
        "DB_USER": os.getenv("DB_USER", "root"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", "123456"),
    }

    test_db_name = f"test_transactions_{random.randint(1000, 9999)}"

    try:
        app = create_app()
        app.config.update(
            {
                "SQLALCHEMY_DATABASE_URI": (
                    f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASSWORD']}"
                    f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/{test_db_name}"
                ),
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "TESTING": True,
            }
        )

        with app.app_context():
            # 创建测试数据库
            temp_conn_uri = (
                f"mysql+pymysql://{db_config['DB_USER']}:{db_config['DB_PASSWORD']}"
                f"@{db_config['DB_HOST']}:{db_config['DB_PORT']}/mysql"
            )
            temp_engine = create_engine(temp_conn_uri)
            with temp_engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {test_db_name}"))
            temp_engine.dispose()

            # 创建表
            db.create_all()

            from app.models import User

            # 记录初始用户数量
            initial_count = User.query.count()

            try:
                # 开始事务
                user = User(username="transaction_test", password="test_pass")
                db.session.add(user)

                # 故意制造错误导致回滚
                raise Exception("Test exception for rollback")

                db.session.commit()
            except:
                db.session.rollback()

            # 验证用户没有被添加
            final_count = User.query.count()
            assert final_count == initial_count, "事务回滚失败"

            print("数据库事务测试完成")

    except Exception as e:
        print(f"数据库事务测试失败: {str(e)}")
        pytest.fail(f"数据库事务测试失败: {str(e)}")

    finally:
        # 清理
        try:
            temp_engine = create_engine(temp_conn_uri)
            with temp_engine.connect() as conn:
                conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
            temp_engine.dispose()
        except Exception as e:
            print(f"清理测试数据库失败: {str(e)}")


if __name__ == "__main__":
    test_basic_database_operations()
    test_table_relationships()
    test_database_constraints()
    test_database_transactions()
    print("所有数据库测试完成!")
