from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum

db = SQLAlchemy()


class OrderStatus(Enum):
    UNPAID = 'unpaid'
    PAID = 'paid'
    EXPIRED = 'expired'


class Order(db.Model):
    """订单数据模型"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(64), unique=True, nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.UNPAID, nullable=False, index=True)

    # BSC相关字段
    address = db.Column(db.String(42), nullable=False, unique=True)  # 收款地址
    private_key = db.Column(db.String(66), nullable=False)  # 地址私钥（加密存储）
    qr_code = db.Column(db.Text, nullable=False)  # Base64编码的二维码图片

    # 支付信息
    tx_hash = db.Column(db.String(66))  # 支付交易哈希
    paid_amount = db.Column(db.Float)  # 实际支付金额
    collect_tx_hash = db.Column(db.String(66))  # 归集交易哈希

    # 时间戳
    create_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expire_time = db.Column(db.DateTime, nullable=False)
    paid_time = db.Column(db.DateTime)  # 支付时间

    def __repr__(self):
        return f'<Order {self.order_no}: {self.amount} USDT - {self.status.value}>'

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'order_no': self.order_no,
            'amount': self.amount,
            'status': self.status.value,
            'address': self.address,
            'qr_code': self.qr_code,
            'tx_hash': self.tx_hash,
            'paid_amount': self.paid_amount,
            'create_time': self.create_time.isoformat() if self.create_time else None,
            'update_time': self.update_time.isoformat() if self.update_time else None,
            'expire_time': self.expire_time.isoformat() if self.expire_time else None,
            'paid_time': self.paid_time.isoformat() if self.paid_time else None
        }