from flask import Flask, render_template, jsonify, request, redirect, url_for
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import uuid
import os
import qrcode
from PIL import Image, ImageDraw
from io import BytesIO
import base64
import logging

from config import Config
from models import db, Order, OrderStatus
from web3_support import Web3Support
from scheduler import check_orders

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 创建Flask应用
app = Flask(__name__)
app.config.from_object(Config)

# 初始化扩展
db.init_app(app)
w3 = Web3Support(app)

# 初始化调度器
scheduler = APScheduler()

# 修改调度器配置，传入app实例
if app.config['JOBS']:
    app.config['JOBS'][0]['args'] = (app,)

scheduler.init_app(app)
scheduler.start()

# 创建数据库表
with app.app_context():
    db.create_all()


def generate_qr_with_logo(data: str, logo_path: str = None, logo_bg_shape: str = 'circle') -> str:
    """
    生成一个二维码，并在中间添加带白色背景的Logo
    :param data: 二维码内容
    :param logo_path: Logo图片文件路径
    :param logo_bg_shape: Logo背景形状, 'circle' 或 'square'
    :return: Base64编码的二维码图片
    """
    # 设置二维码参数，使用最高容错率
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # 创建二维码图片
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGBA')

    # 尝试添加Logo
    if logo_path and os.path.exists(logo_path):
        try:
            # 打开Logo图片
            logo = Image.open(logo_path).convert('RGBA')

            # 计算Logo大小（二维码的1/5）
            qr_width, qr_height = qr_img.size
            logo_size = min(qr_width, qr_height) // 5

            # 调整Logo大小
            logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
            logo_width, logo_height = logo.size

            # 创建白色背景
            bg_size = int(logo_size * 1.2)
            bg_img = Image.new('RGBA', (bg_size, bg_size), (255, 255, 255, 255))

            if logo_bg_shape == 'circle':
                # 创建圆形遮罩
                mask = Image.new('L', (bg_size, bg_size), 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, bg_size, bg_size), fill=255)
                bg_img.putalpha(mask)

            # 将Logo粘贴到白色背景中央
            logo_pos = ((bg_size - logo_width) // 2, (bg_size - logo_height) // 2)
            bg_img.paste(logo, logo_pos, logo)

            # 将带背景的Logo粘贴到二维码中央
            qr_pos = ((qr_width - bg_size) // 2, (qr_height - bg_size) // 2)
            qr_img.paste(bg_img, qr_pos, bg_img)

        except Exception as e:
            app.logger.warning(f"Failed to add logo to QR code: {e}")

    # 转换为Base64
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return img_str


@app.route('/')
def index():
    """首页"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>USDT Payment Demo</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 30px;
                text-align: center;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                color: #555;
                font-weight: 500;
            }
            input[type="number"] {
                width: 100%;
                padding: 12px 16px;
                font-size: 16px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                box-sizing: border-box;
                transition: border-color 0.3s;
            }
            input[type="number"]:focus {
                outline: none;
                border-color: #4CAF50;
            }
            button {
                width: 100%;
                background: #4CAF50;
                color: white;
                padding: 14px 20px;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.3s;
            }
            button:hover {
                background: #45a049;
            }
            button:active {
                background: #3d8b40;
            }
            .info {
                background: #e3f2fd;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                font-size: 14px;
                color: #1976d2;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>USDT Payment Demo</h1>
            <div class="info">
                <strong>测试说明：</strong><br>
                本系统支持BSC链上的USDT支付。每个订单将生成唯一的收款地址。
            </div>
            <form action="/create_order" method="post">
                <div class="form-group">
                    <label for="amount">支付金额 (USDT)</label>
                    <input type="number" 
                           id="amount" 
                           name="amount" 
                           step="0.01" 
                           min="0.01" 
                           placeholder="请输入金额" 
                           required>
                </div>
                <button type="submit">创建订单</button>
            </form>
        </div>
    </body>
    </html>
    '''


@app.route('/create_order', methods=['POST'])
def create_order():
    """创建订单"""
    try:
        # 获取金额
        amount = float(request.form.get('amount', 0))
        if amount <= 0:
            return "Invalid amount", 400

        # 创建新的收款地址
        account = w3.create_account()
        if not account:
            return "Failed to create payment address", 500

        # 生成二维码
        logo_path = os.path.join(app.root_path, 'static', 'img', 'usdt-bsc.png')
        qr_code = generate_qr_with_logo(account['address'], logo_path)

        # 创建订单
        order = Order(
            order_no=str(uuid.uuid4()),
            amount=amount,
            status=OrderStatus.UNPAID,
            address=account['address'],
            private_key=account['private_key'],
            qr_code=qr_code,
            expire_time=datetime.utcnow() + timedelta(hours=2)  # 2小时过期
        )

        db.session.add(order)
        db.session.commit()

        app.logger.info(f'Created order {order.order_no} for {amount} USDT')

        # 重定向到订单页面
        return redirect(url_for('order_detail', order_no=order.order_no))

    except Exception as e:
        app.logger.exception(f'Error creating order: {e}')
        return f"Error: {str(e)}", 500


@app.route('/order/<order_no>')
def order_detail(order_no):
    """订单详情页面"""
    order = Order.query.filter_by(order_no=order_no).first_or_404()
    return render_template('order.html', order=order)


@app.route('/order/<order_no>/check')
def check_order_status(order_no):
    """检查订单状态API"""
    order = Order.query.filter_by(order_no=order_no).first_or_404()

    # 检查是否过期
    if order.expire_time < datetime.utcnow() and order.status == OrderStatus.UNPAID:
        order.status = OrderStatus.EXPIRED
        db.session.commit()

    return jsonify({
        'status': order.status.value,
        'paid': order.status == OrderStatus.PAID,
        'expired': order.status == OrderStatus.EXPIRED
    })


@app.route('/order/<order_no>/collect', methods=['POST'])
def collect_order_funds(order_no):
    """手动归集订单资金"""
    order = Order.query.filter_by(order_no=order_no).first_or_404()

    # 只有已支付的订单才能归集
    if order.status != OrderStatus.PAID:
        return jsonify({
            'success': False,
            'message': 'Only paid orders can be collected'
        }), 400

    try:
        # 检查地址余额
        current_balance = w3.get_usdt_balance(order.address)

        if current_balance <= 0:
            return jsonify({
                'success': False,
                'message': 'No funds to collect (balance: 0 USDT)'
            })

        # 检查是否配置了归集地址
        if not w3.collect_address:
            return jsonify({
                'success': False,
                'message': 'Collection address not configured'
            })

        app.logger.info(f'Manual collection triggered for order {order.order_no}, balance: {current_balance} USDT')

        # 执行归集
        collect_tx = w3.collect_usdt(
            order.address,
            order.private_key,
            current_balance
        )

        if collect_tx:
            # 更新订单信息
            order.collect_tx_hash = collect_tx
            order.update_time = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Successfully collected {current_balance:.2f} USDT',
                'tx_hash': collect_tx,
                'amount': current_balance
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Collection failed, please check logs'
            })

    except Exception as e:
        app.logger.error(f'Error collecting funds for order {order.order_no}: {e}')
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# 健康检查端点
@app.route('/health')
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'time': datetime.utcnow().isoformat()
    })


# 手动触发订单检查（仅用于测试）
@app.route('/admin/check_orders')
def manual_check_orders():
    """手动触发订单检查"""
    check_orders(app)
    return 'Order check completed. <a href="/">Back to home</a>'


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return '''
    <h1>404 - Page Not Found</h1>
    <p>The requested page does not exist.</p>
    <a href="/">Back to home</a>
    ''', 404


@app.errorhandler(500)
def internal_error(error):
    return '''
    <h1>500 - Internal Server Error</h1>
    <p>Something went wrong. Please try again later.</p>
    <a href="/">Back to home</a>
    ''', 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)