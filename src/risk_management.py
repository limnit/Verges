# src/risk_management.py

import importlib
import logging

class RiskManagement:
    def __init__(self, database):
        self.database = database
        self.plugins = {}
        self.load_plugins()
    
    def load_plugins(self):
        plugin_names = [
            'credit_limit',
            'margin_check',
            'notional_limit',
            'volume_limit',
            'trading_mode',
            'portfolio_margin',
            'equity_option_spread',
            'message_throttling',
	    'wash_trade'
        ]
        for name in plugin_names:
            try:
                module = importlib.import_module(f"risk_plugins.{name}")
                plugin_class_name = ''.join([part.title() for part in name.split('_')]) + "Check"
                plugin_class = getattr(module, plugin_class_name)
                self.plugins[name] = plugin_class(self.database)
                logging.info(f"Loaded risk plugin: {name}")
            except Exception as e:
                logging.error(f"Failed to load plugin {name}: {e}")
    
    def check_order(self, order, account, session_id):
        risk_settings = self.database.get_risk_settings(session_id)
        if not risk_settings:
            return False, "Risk settings not found for session."
        
        for plugin in self.plugins.values():
            result, message = plugin.check(order, account, session_id, risk_settings)
            if not result:
                return False, message
        return True, ""

