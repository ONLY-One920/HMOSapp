import logging
import re
from datetime import datetime
from sqlalchemy import inspect, text
from flask import current_app
from werkzeug.security import generate_password_hash
import json  # 新增导入

logger = logging.getLogger(__name__)


def validate_credentials(username, password):
    if not re.match(r'^\d{6}$', username):
        return False, '用户名必须是6位数字'
    if len(password) == 0 or len(password) > 20:
        return False, '密码长度需在1-20个字符之间'
    return True, ""


def check_database_schema():
    """检查并修复数据库表结构"""
    try:
        db = current_app.extensions['sqlalchemy']
        inspector = inspect(db.engine)
        required_columns = {
            'cart_items': ['updated_at'],
            'products': ['images']  # 新增：检查products表的images字段
        }

        fixed_count = 0
        for table, columns in required_columns.items():
            if table in inspector.get_table_names():
                existing_columns = [col['name'] for col in inspector.get_columns(table)]
                for col in columns:
                    if col not in existing_columns:
                        logger.info(f"添加缺失字段 {col} 到表 {table}")
                        try:
                            # 尝试添加带默认值的列
                            if col == 'images':
                                db.session.execute(text(
                                    f"ALTER TABLE {table} "
                                    f"ADD COLUMN {col} TEXT DEFAULT '[]'"
                                ))
                            else:
                                db.session.execute(text(
                                    f"ALTER TABLE {table} "
                                    f"ADD COLUMN {col} DATETIME DEFAULT CURRENT_TIMESTAMP "
                                    "ON UPDATE CURRENT_TIMESTAMP"
                                ))
                            fixed_count += 1
                        except Exception as alter_err:
                            logger.error(f"添加字段失败: {str(alter_err)}")
                            try:
                                # 尝试更简单的添加方式
                                db.session.execute(text(
                                    f"ALTER TABLE {table} "
                                    f"ADD COLUMN {col} TEXT"
                                ))
                                fixed_count += 1
                                logger.info(f"成功添加字段 {col} (无默认值)")
                            except Exception as simple_err:
                                logger.error(f"简单添加字段失败: {str(simple_err)}")

        if fixed_count > 0:
            db.session.commit()
            logger.info(f"修复了 {fixed_count} 个数据库字段问题")
            return True
        return False
    except Exception as e:
        logger.error(f"数据库结构检查失败: {str(e)}")
        if 'db' in locals() and hasattr(db, 'session'):
            db.session.rollback()
        return False


def seed_initial_data():
    """初始化数据库数据"""
    # 先检查并修复数据库结构
    check_database_schema()
    try:
        db = current_app.extensions['sqlalchemy']
        from .models import Product, User

        # 添加示例商品（带多张图片）
        if not Product.query.first():
            products = [
                Product(
                    id='1',
                    name='华为手机',
                    price=1999.0,
                    image='hw.png',
                    images=json.dumps([
                        'hw.png',
                        'hw_detail1.png',
                        'hw_detail2.png'
                    ]),
                    description='高性能旗舰手机'
                ),
                Product(
                    id='2',
                    name='小米手机',
                    price=4399.0,
                    image='xm.png',
                    images=json.dumps([
                        'xm.png',
                        'xm_detail1.png',
                        'xm_detail2.png'
                    ]),
                    description='性价比之王'
                ),
                Product(
                    id='3',
                    name='苹果手机',
                    price=5999.0,
                    image='pg.png',
                    images=json.dumps([
                        'pg.png',
                        'pg_detail1.png',
                        'pg_detail2.png'
                    ]),
                    description='iOS生态系统'
                ),
                Product(
                    id='4',
                    name='花朵卡片',
                    price=9.9,
                    image='flower.png',
                    images=json.dumps([
                        'flower.png',
                        'flower_detail1.png'
                    ]),
                    description='六一电子贺卡'
                ),
            ]
            db.session.bulk_save_objects(products)
            db.session.commit()
            print("添加了初始商品数据")

        # 添加测试用户
        if not User.query.first():
            test_user = User(
                username='123456',
                password=generate_password_hash('password123')
            )
            db.session.add(test_user)
            db.session.commit()
            print("创建了测试用户: 123456/password123")
    except Exception as e:
        logger.error(f"初始化数据时出错: {str(e)}")
        if 'db' in locals() and hasattr(db, 'session'):
            db.session.rollback()
        print(f"初始化数据时出错: {str(e)}")


def cleanup_expired_tokens():
    """定期清理过期令牌"""
    try:
        # 确保有当前应用上下文
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        from .models import TokenBlacklist

        now = datetime.utcnow()
        expired_tokens = TokenBlacklist.query.filter(
            TokenBlacklist.expires_at < now
        ).all()

        for token in expired_tokens:
            db.session.delete(token)

        db.session.commit()
        logger.info(f"清理了 {len(expired_tokens)} 个过期令牌")
        print(f"清理了 {len(expired_tokens)} 个过期令牌")

    except Exception as e:
        logger.error(f"清理令牌错误: {str(e)}")
        if 'db' in locals() and hasattr(db, 'session'):
            db.session.rollback()