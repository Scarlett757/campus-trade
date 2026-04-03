from exts import db
from sqlalchemy.orm import Mapped,mapped_column,relationship
from sqlalchemy import Integer, String,Text,Float,DateTime,ForeignKey,Enum
from typing import List
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum




class User(db.Model):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(100), unique=True)  # String → str
    username: Mapped[str] = mapped_column(String(50))  # String → str
    password_hashed: Mapped[str] = mapped_column(String(200))  # String → str
    mobile: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)  # 手机号
    avatar: Mapped[str | None] = mapped_column(String(200), nullable=True, default="default_avatar.png")  # 头像
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)  # 个性签名
    # 关联收货地址表（一对多）
    # addresses 定义的属性名 目的是通过user.addresses 读取到所有的地址信息
    addresses: Mapped[List["Address"]] = relationship(
        "Address",
        cascade="all, delete-orphan"  # 删除用户自动删地址
    )

    products: Mapped[List["Product"]] = relationship("Product", back_populates="publisher")

    def __init__(self, *args, **kwargs):
        password = kwargs.get('password')
        if password:
            kwargs.pop('password')
        # 其余的参数该怎么处理怎么处理，返回父类
        super().__init__(*args, **kwargs)
        self.password = password

    @property
    def password(self):
        return self.password_hashed

    @password.setter
    def password(self, password):
        self.password_hashed = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hashed, password)


class Address(db.Model):
    __tablename__ = 'address'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    receiver: Mapped[str] = mapped_column(String(50), nullable=False)  # 收件人
    phone: Mapped[str] = mapped_column(String(20), nullable=False)  # 收件人电话
    province: Mapped[str] = mapped_column(String(50), nullable=False)  # 省份
    city: Mapped[str] = mapped_column(String(50), nullable=False)  # 城市
    district: Mapped[str] = mapped_column(String(50), nullable=False)  # 区县
    detail: Mapped[str] = mapped_column(Text, nullable=False)  # 详细地址（校园场景适配）
    is_default: Mapped[bool] = mapped_column(default=False)  # 是否默认地址
    # 外键关联用户表
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False)


    
class ProductCategory(db.Model):
    __tablename__ = 'product_category'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))  # String → str

    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")


class Product(db.Model):
    __tablename__ = 'product'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    content: Mapped[str] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Float)
    num: Mapped[int] = mapped_column(Integer, nullable=False)   # 余量
    picture: Mapped[str] = mapped_column(String(200))
    origin_place: Mapped[str] = mapped_column(String(100))  # 发货地点
    ship_name: Mapped[str] = mapped_column(String(100)) # 发货方式
    pub_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  # 不需要手动输入当前时间 有默认值

    category_id: Mapped[int] = mapped_column(Integer, ForeignKey('product_category.id'))
    category: Mapped[ProductCategory] = relationship('ProductCategory', back_populates='products')

    publisher_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    publisher: Mapped[User] = relationship('User', back_populates='products')

class EmailCode(db.Model):
    __tablename__ = 'email_code'
    id:Mapped[int]=mapped_column(Integer, primary_key=True, autoincrement=True)
    code:Mapped[str]=mapped_column(String(10))
    email: Mapped[str] = mapped_column(String(100))
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 防止重复收藏 (同一个用户不能收藏同一个商品两次)
    __table_args__ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product'),)

    def __repr__(self):
        return f'<Favorite {self.user_id}-{self.product_id}>'


# 定义订单状态枚举
class OrderStatus(enum.Enum):
    PENDING = 'pending'  # 待付款 (简化流程，下单即视为锁定，这里我们直接设为待发货)
    PAID = 'paid'  # 已付款/待发货 (校园二手通常直接线下交易或先确认，这里简化为：下单=待发货)
    SHIPPED = 'shipped'  # 已发货 (商家操作)
    COMPLETED = 'completed'  # 已完成 (用户确认收货)
    CANCELLED = 'cancelled'  # 已取消


class Order(db.Model):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # 订单号

    # 关联用户
    buyer_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'), nullable=False)
    seller_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'), nullable=False)

    # 关联商品 
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey('product.id'), nullable=False)

    # 价格快照 (防止商品后续改价影响订单)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    # 关联地址 (快照或关联ID，建议存快照或关联ID，这里关联ID)
    address_id: Mapped[int] = mapped_column(Integer, ForeignKey('address.id'), nullable=False)

    # 状态
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PAID)

    # 时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now,
                                                          onupdate=datetime.now)

    # 关系
    buyer = relationship('User', foreign_keys=[buyer_id], backref='bought_orders')
    seller = relationship('User', foreign_keys=[seller_id], backref='sold_orders')
    product = relationship('Product', backref='orders')
    address = relationship('Address', backref='orders')

    # 订单内的消息 (砍价/物流通知)
    messages = relationship('OrderMessage', backref='order', cascade='all, delete-orphan')


class OrderMessage(db.Model):
    __tablename__ = 'order_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey('orders.id'), nullable=False)

    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey('user.id'), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 消息类型：text(普通文本), system(系统通知：如"商家已发货")
    msg_type: Mapped[str] = mapped_column(String(20), default='text')

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    sender = relationship('User', backref='order_messages')