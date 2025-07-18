import json
from web3 import Web3
from eth_account import Account
from decimal import Decimal


class Web3Support(object):
    """Web3交互支持类"""

    def __init__(self, app=None):
        self.app = app
        self.w3 = None
        # USDT在BSC上的地址
        # https://bscscan.com/token/0x55d398326f99059fF775485246999027B3197955
        self.usdt_address = Web3.to_checksum_address('0x55d398326f99059fF775485246999027B3197955')
        # USDT在BSC上的合约ABI, 只需要balanceOf和transfer函数
        self.usdt_abi = json.loads('''[
            {
                "constant": true,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": false,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]''')
        self.usdt_contract = None
        self.collect_address = None
        self.gas_address = None
        self.gas_address_private_key = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """初始化应用"""
        self.app = app
        bsc_endpoint = app.config.get('BSC_ENDPOINT')
        if bsc_endpoint:
            try:
                # 连接到BSC节点
                self.w3 = Web3(Web3.HTTPProvider(bsc_endpoint))
                if self.w3.is_connected():
                    app.logger.info(f'Connected to BSC node: {bsc_endpoint}')
                else:
                    app.logger.error('Failed to connect to BSC node')
                    return

                # 初始化USDT合约
                self.usdt_contract = self.w3.eth.contract(
                    address=self.usdt_address,
                    abi=self.usdt_abi
                )

                # 设置地址
                self.collect_address = app.config.get('BSC_COLLECT_ADDRESS')
                self.gas_address = app.config.get('BSC_GAS_ADDRESS')
                self.gas_address_private_key = app.config.get('BSC_GAS_ADDRESS_PRIVATE_KEY')

                # 验证配置
                if self.collect_address:
                    self.collect_address = Web3.to_checksum_address(self.collect_address)
                if self.gas_address:
                    self.gas_address = Web3.to_checksum_address(self.gas_address)

            except Exception as e:
                app.logger.error(f'Failed to initialize Web3: {e}')

    def create_account(self):
        """创建一个新的账户"""
        account = Account.create()
        return {
            'address': account.address,
            'private_key': account.key.hex()
        }

    def get_usdt_balance(self, address):
        """获取指定地址的USDT余额"""
        if not self.w3 or not self.usdt_contract:
            self.app.logger.error('Web3 not initialized')
            return 0

        try:
            address = Web3.to_checksum_address(address)
            balance_wei = self.usdt_contract.functions.balanceOf(address).call()
            balance = balance_wei / 10 ** 18  # USDT在BSC上是18位小数
            self.app.logger.info(f'USDT balance for {address}: {balance}')
            return float(balance)
        except Exception as e:
            self.app.logger.error(f'Error getting USDT balance for {address}: {e}')
            return 0

    def get_bnb_balance(self, address):
        """查询指定地址的BNB余额"""
        if not self.w3:
            self.app.logger.error('Web3 not initialized')
            return 0

        try:
            address = Web3.to_checksum_address(address)
            balance_wei = self.w3.eth.get_balance(address)
            balance = self.w3.from_wei(balance_wei, 'ether')
            self.app.logger.info(f'BNB balance for {address}: {balance}')
            return float(balance)
        except Exception as e:
            self.app.logger.error(f'Error getting BNB balance for {address}: {e}')
            return 0

    def estimate_gas(self, from_address, amount_usdt):
        """估算转账所需的Gas"""
        try:
            from_address = Web3.to_checksum_address(from_address)
            amount_wei = int(amount_usdt * 10 ** 18)

            # 估算gas用量
            gas_estimate = self.usdt_contract.functions.transfer(
                self.collect_address, amount_wei
            ).estimate_gas({'from': from_address})
        except Exception as e:
            self.app.logger.error(f'Error estimating gas: {e}')
            # 使用默认值
            gas_estimate = 65000

        # 获取当前gas价格
        try:
            gas_price = self.w3.eth.gas_price
        except:
            gas_price = self.w3.to_wei('5', 'gwei')  # 默认5 Gwei

        # 计算费用
        total_gas_cost_wei = gas_estimate * gas_price
        total_gas_cost_bnb = self.w3.from_wei(total_gas_cost_wei, 'ether')
        safe_gas_cost_bnb = float(total_gas_cost_bnb) * 1.2  # 增加20%缓冲

        self.app.logger.info(
            f'Gas estimate: {gas_estimate} units, '
            f'price: {gas_price} wei, '
            f'total: {safe_gas_cost_bnb} BNB'
        )

        return {
            'gas_limit': int(gas_estimate * 1.2),  # 增加20%缓冲
            'gas_price': gas_price,
            'total_cost_wei': total_gas_cost_wei,
            'total_cost_bnb': float(total_gas_cost_bnb),
            'safe_gas_cost_bnb': safe_gas_cost_bnb
        }

    def transfer_bnb_for_gas(self, to_address, amount_bnb):
        """转账BNB作为gas费用"""
        if not all([self.w3, self.gas_address, self.gas_address_private_key]):
            self.app.logger.error('Gas address not configured')
            return None

        try:
            to_address = Web3.to_checksum_address(to_address)
            nonce = self.w3.eth.get_transaction_count(self.gas_address)
            amount_wei = self.w3.to_wei(amount_bnb, 'ether')
            gas_price = self.w3.eth.gas_price

            # 构建交易
            transaction = {
                'nonce': nonce,
                'to': to_address,
                'value': amount_wei,
                'gas': 21000,
                'gasPrice': gas_price,
                'chainId': 56  # BSC主网
            }

            # 签名并发送交易
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction,
                private_key=self.gas_address_private_key
            )

            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # 等待交易确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            tx_hash_hex = tx_hash.hex()

            if receipt.status == 1:
                self.app.logger.info(
                    f'BNB transfer successful: {amount_bnb} BNB to {to_address}, '
                    f'tx: {tx_hash_hex}'
                )
                return tx_hash_hex
            else:
                self.app.logger.error(f'BNB transfer failed: {tx_hash_hex}')
                return None

        except Exception as e:
            self.app.logger.error(f'Error transferring BNB: {e}')
            return None

    def collect_usdt(self, from_address, from_private_key, amount_usdt):
        """归集USDT到指定地址"""
        if not all([self.w3, self.usdt_contract, self.collect_address]):
            self.app.logger.error('Collection address not configured')
            return None

        try:
            from_address = Web3.to_checksum_address(from_address)

            # 检查BNB余额是否足够支付gas
            current_bnb_balance = self.get_bnb_balance(from_address)
            gas_info = self.estimate_gas(from_address, amount_usdt)
            required_bnb = gas_info['safe_gas_cost_bnb']

            if current_bnb_balance < required_bnb:
                # 转账BNB作为gas费
                bnb_to_transfer = required_bnb - current_bnb_balance
                self.app.logger.info(
                    f'Transferring {bnb_to_transfer} BNB for gas to {from_address}'
                )
                gas_tx = self.transfer_bnb_for_gas(from_address, bnb_to_transfer)
                if not gas_tx:
                    return None
                # 等待一下确保到账
                import time
                time.sleep(5)

            # 执行USDT转账
            nonce = self.w3.eth.get_transaction_count(from_address)
            amount_wei = int(amount_usdt * 10 ** 18)

            # 构建交易
            transaction = self.usdt_contract.functions.transfer(
                self.collect_address, amount_wei
            ).build_transaction({
                'chainId': 56,
                'gas': gas_info['gas_limit'],
                'gasPrice': gas_info['gas_price'],
                'nonce': nonce,
            })

            # 签名并发送交易
            signed_txn = self.w3.eth.account.sign_transaction(
                transaction,
                private_key=from_private_key
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # 等待交易确认
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            tx_hash_hex = tx_hash.hex()

            if receipt.status == 1:
                self.app.logger.info(
                    f'USDT collection successful: {amount_usdt} USDT from {from_address}, '
                    f'tx: {tx_hash_hex}'
                )
                return tx_hash_hex
            else:
                self.app.logger.error(f'USDT collection failed: {tx_hash_hex}')
                return None

        except Exception as e:
            self.app.logger.error(f'Error collecting USDT: {e}')
            return None