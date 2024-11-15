# src/risk_management.py

import importlib
import logging

class RiskManagement:
    def __init__(self, database, market_data):
        self.database = database
        self.market_data = market_data
        self.plugins = {}
        self.load_plugins()

    def load_plugins(self):
        plugin_names = [
            'credit_limit',
            'margin_check',
            'notional_limit',
            'volume_limit',  # Include the volume_limit plugin
            'trading_mode',
            'portfolio_margin',
            'equity_option_spread',
            'message_throttling'
        ]
        for name in plugin_names:
            try:
                module = importlib.import_module(f"risk_plugins.{name}")
                plugin_class_name = ''.join([part.title() for part in name.split('_')]) + "Check"
                plugin_class = getattr(module, plugin_class_name)
                self.plugins[name] = plugin_class(self.database, self.market_data)
                logging.info(f"Loaded risk plugin: {name}")
            except Exception as e:
                logging.error(f"Failed to load plugin {name}: {e}")

    # Rest of the class remains the same...

