from datetime import datetime, timedelta
from models import db, Order, OrderStatus
from web3_support import Web3Support


def check_orders(app):
    """检测订单是否已经收到资金"""
    with app.app_context():
        try:
            app.logger.info(f'Checking unpaid orders at {datetime.now()}')

            # 获取Web3实例
            w3 = Web3Support(app)

            # 查询过去2小时内的未支付订单
            two_hours_ago = datetime.utcnow() - timedelta(hours=2)
            unpaid_orders = Order.query.filter(
                Order.status == OrderStatus.UNPAID,
                Order.create_time >= two_hours_ago
            ).all()

            app.logger.info(f'Found {len(unpaid_orders)} unpaid orders')

            for order in unpaid_orders:
                try:
                    # 检查订单是否已过期
                    if order.expire_time < datetime.utcnow():
                        order.status = OrderStatus.EXPIRED
                        db.session.commit()
                        app.logger.info(f'Order {order.order_no} expired')
                        continue

                    app.logger.info(f'Checking order {order.order_no} - {order.address}')

                    # 检查USDT余额
                    usdt_balance = w3.get_usdt_balance(order.address)

                    if usdt_balance >= order.amount:
                        # 更新订单状态
                        order.status = OrderStatus.PAID
                        order.paid_amount = usdt_balance
                        order.paid_time = datetime.utcnow()
                        order.update_time = datetime.utcnow()
                        db.session.commit()

                        app.logger.info(
                            f'Order {order.order_no} paid: {usdt_balance} USDT'
                        )

                        # TODO: 在这里添加您的业务逻辑
                        # 例如：发送邮件通知、开通会员、发货等

                        # 尝试归集资金（如果配置了归集地址）
                        if w3.collect_address:
                            try:
                                collect_tx = w3.collect_usdt(
                                    order.address,
                                    order.private_key,
                                    usdt_balance
                                )
                                if collect_tx:
                                    order.collect_tx_hash = collect_tx
                                    db.session.commit()
                                    app.logger.info(
                                        f'Collected {usdt_balance} USDT from order {order.order_no}'
                                    )
                            except Exception as e:
                                app.logger.error(
                                    f'Failed to collect USDT from order {order.order_no}: {e}'
                                )
                    else:
                        app.logger.info(
                            f'Order {order.order_no} balance: {usdt_balance}/{order.amount} USDT'
                        )

                except Exception as e:
                    app.logger.error(f'Error checking order {order.order_no}: {e}')
                    continue

        except Exception as e:
            app.logger.exception(f'Error in check_orders: {e}')