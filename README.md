# USDT Payment Demo

一个基于Flask的USDT(BSC链)收款演示系统，支持自动监控链上支付状态。使用了web3库访问BSC节点，因此EVM兼容链都可以支持。

本文的设计文档请查看《[使用稳定币收付款](https://medium.com/p/712a5cab4173)》第四章。

## 功能特性

- 为每个订单生成唯一的BSC收款地址
- 生成带Logo的收款二维码
- 实时监控链上USDT到账状态
- 自动更新订单状态
- 支持资金自动归集
- 订单过期管理

## 快速开始

### 1. 环境要求

- Python 3.8+
- pip

### 2. 安装依赖

```bash
# 克隆项目
git clone https://github.com/javisgally/simple-usdt-payment.git
cd simple-usdt-payment

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```
### 3. 配置环境变量

复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置以下参数：

```env
# Flask密钥（生产环境请使用强密码）
# https://flask.palletsprojects.com/en/stable/config/#SECRET_KEY
SECRET_KEY=your-secret-key-here

# BSC节点（可选，使用公共节点）
BSC_ENDPOINT=https://bsc-dataseed.bnbchain.org

# 归集地址（收款最终汇总地址）
BSC_COLLECT_ADDRESS=0x...

# Gas费用地址（用于支付归集手续费）
BSC_GAS_ADDRESS=0x...
BSC_GAS_ADDRESS_PRIVATE_KEY=0x...
```

### 4. 运行应用

```bash
python app.py
```

访问 http://localhost:5000

## 使用流程

1. **创建订单**
   - 访问首页
   - 输入支付金额
   - 点击创建订单

2. **支付**
   - 扫描二维码或复制地址
   - 使用任意BSC钱包发送USDT(BEP-20)
   - 等待系统确认

3. **确认**
   - 系统每30秒检查一次链上状态
   - 页面每10秒查询一次订单状态
   - 支付成功后自动显示成功页面

## 项目结构

```
flask-usdt-payment/
├── app.py              # 主应用入口
├── models.py           # 数据库模型
├── web3_support.py     # Web3交互封装
├── scheduler.py        # 后台任务
├── config.py           # 配置管理
├── requirements.txt    # 依赖列表
├── templates/          # HTML模板
│   └── order.html      # 订单页面
└── static/             # 静态资源
    └── img/
        └── usdt-bsc.png  # USDT logo
```

## API 端点

- `GET /` - 首页
- `POST /create_order` - 创建订单
- `GET /order/<order_no>` - 订单详情
- `GET /order/<order_no>/check` - 检查订单状态
- `GET /health` - 健康检查
- `GET /admin/check_orders` - 手动触发检查（测试用）

## 许可证

MIT License