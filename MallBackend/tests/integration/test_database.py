from app import db
from app.models import User, Product, CartItem


def test_database_operations(test_app, init_database):
    """测试数据库操作"""
    with test_app.app_context():
        # 测试用户查询
        user = User.query.filter_by(username='123456').first()
        assert user is not None
        assert user.username == '123456'

        # 测试商品查询
        products = Product.query.all()
        assert len(products) == 2
        assert products[0].name == '华为手机'

        # 测试添加购物车项
        cart_item = CartItem(user_id=user.id, product_id='1', quantity=1)
        db.session.add(cart_item)
        db.session.commit()

        # 验证购物车项已添加
        cart_items = CartItem.query.filter_by(user_id=user.id).all()
        assert len(cart_items) == 1
        assert cart_items[0].product.name == '华为手机'


def test_database_transaction_rollback(test_app, init_database):
    """测试数据库事务回滚"""
    with test_app.app_context():
        from app import db
        from app.models import User

        # 记录初始用户数量
        initial_count = User.query.count()

        try:
            # 开始事务
            user = User(username='test_transaction', password='test_pass')
            db.session.add(user)

            # 故意制造错误导致回滚
            raise Exception("Test exception")

            db.session.commit()
        except:
            db.session.rollback()

        # 验证用户没有被添加
        assert User.query.count() == initial_count