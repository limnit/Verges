# risk_plugins/base.py

class RiskPlugin:
    def __init__(self, database, market_data=None):
        self.database = database
        self.market_data = market_data

    def check(self, order, account, session_id, risk_settings):
        raise NotImplementedError("Risk plugins must implement the 'check' method.")

