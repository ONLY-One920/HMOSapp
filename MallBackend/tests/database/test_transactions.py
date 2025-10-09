import pytest
from app import db
from app.models import User, Product


def test_transaction_rollback(test_app, init_database):
    """测试事务回滚"""
    with test_app.app_context():
        # 记录初始用户数量
        initial_user_count = User.query.count()

        try:
            # 开始一个会失败的事务
            new_user = User(username="testuser", password="testpass")
            db.session.add(new_user)

            # 故意创建一个会失败的操作
            # 尝试添加一个重复主键的商品
            duplicate_product = Product(id="1", name="Duplicate", price=99.99)
            db.session.add(duplicate_product)

            db.session.commit()
            pytest.fail("Expected an exception but none was raised")

        except:
            # 发生异常，事务应该已回滚
            db.session.rollback()

            # 验证用户没有被添加
            assert User.query.count() == initial_user_count


def test_transaction_isolation(test_app, init_database):
    """测试事务隔离"""
    with test_app.app_context():
        # 在第一个事务中添加用户
        user1 = User(username="user1", password="pass1")
        db.session.add(user1)
        db.session.commit()

        # 开始一个新事务
        db.session.begin_nested()

        # 在新事务中添加另一个用户
        user2 = User(username="user2", password="pass2")
        db.session.add(user2)

        # 提交嵌套事务
        db.session.commit()

        # 现在能看到用户2
        all_users = User.query.all()
        user2_found = any(u.username == "user2" for u in all_users)
        assert user2_found, "User2 should be visible after commit"
