from . import db
from sqlalchemy import func


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200))  # 主图
    images = db.Column(db.Text, default="[]")  # 新增：多张图片URL列表（JSON格式）
    description = db.Column(db.Text)

    def __repr__(self):
        return f"<Product {self.name}>"


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.String(50), db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)

    # 允许空值作为临时解决方案
    updated_at = db.Column(
        db.DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=True,
    )

    # 关系定义
    product = db.relationship("Product", backref="cart_items", lazy="joined")
    user = db.relationship("User", backref="cart_items")

    def __repr__(self):
        return f"<CartItem {self.product_id} × {self.quantity}>"

    def to_dict(self):
        return {
            "id": self.id,
            "product": {
                "id": self.product.id,
                "name": self.product.name,
                "price": self.product.price,
                "image": self.product.image,
                "description": self.product.description,
            },
            "quantity": self.quantity,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AIMessage(db.Model):
    __tablename__ = "ai_messages"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.BigInteger, nullable=False)

    user = db.relationship("User", backref="ai_messages")

    def __repr__(self):
        return f"<AIMessage {self.role}: {self.content[:20]}>"


class TokenBlacklist(db.Model):
    __tablename__ = "token_blacklist"
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True)
    created_at = db.Column(
        db.DateTime, default=db.func.current_timestamp(), nullable=False
    )
    expires_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<TokenBlacklist jti={self.jti}>"
