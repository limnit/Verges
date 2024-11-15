# src/application.py

import logging
import yaml
from dotenv import load_dotenv
from src.database import Database
from src.fix_engine import FIXEngine
from src.risk_management import RiskManagement
from src.order_manager import OrderManager
from market_data.polygon_io import PolygonIO
from src.utils import setup_logging

class TradingApplication:
    def __init__(self, config_file):
        load_dotenv()
        setup_logging()
        logging.info("Starting Trading Application...")
        
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.database = Database(self.config['database'])
        self.market_data = PolygonIO(self.config['market_data']['api_key'])
        self.risk_management = RiskManagement(self.database)
        self.order_manager = OrderManager(self.database)
        self.fix_engine = FIXEngine('config/quickfix.cfg', self)
        self.fix_engine.start()
    
    def process_order(self, order, session_id):
        account = self.database.get_account(order['account_id'])
        if not account:
            logging.error(f"Account ID {order['account_id']} not found.")
            return
        
        risk_passed, message = self.risk_management.check_order(order, account, session_id)
        if not risk_passed:
            logging.warning(f"Order rejected: {message}")
            self.fix_engine.send_reject(order, session_id, message)
            return
        
        price = self.market_data.get_last_trade(order['ticker'])
        if not price:
            logging.error("Failed to fetch market price.")
            return
        
        self.order_manager.process_order(order, session_id, price)
        self.fix_engine.send_execution_report(order, session_id, price)
    
    def shutdown(self):
        self.fix_engine.stop()
        logging.info("Trading Application stopped.")

