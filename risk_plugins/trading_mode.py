# risk_plugins/trading_mode.py

from .base import RiskPlugin
import logging

class TradingModeCheck(RiskPlugin):
    def check(self, order, account, session_id, risk_settings):
        try:
            trading_mode = account.get('trading_mode', 'NORMAL')
            asset_class = order.get('asset_class', 'EQUITY')
            order_type = order.get('order_type', 'LIMIT')
            side = order.get('side', 'BUY')

            # Fetch trading permissions from the database
            permissions = self.get_trading_permissions(trading_mode, asset_class)
            if not permissions:
                return False, f"Trading permissions not defined for mode {trading_mode} and asset class {asset_class}"

            # Check if trading is allowed
            if not self.is_trading_allowed(order, permissions):
                return False, f"Trading not allowed for {asset_class} in mode {trading_mode} with side {side}"

            return True, ""
        except Exception as e:
            logging.error(f"TradingModeCheck error: {e}")
            return False, "Error in trading mode check"

    def get_trading_permissions(self, trading_mode, asset_class):
        try:
            cur = self.database.conn.cursor()
            cur.execute("""
                SELECT allow_buy, allow_sell, allow_short, allow_options, allow_spreads
                FROM trading_permissions
                WHERE trading_mode = %s AND asset_class = %s;
            """, (trading_mode, asset_class))
            result = cur.fetchone()
            cur.close()
            if result:
                return {
                    'allow_buy': result[0],
                    'allow_sell': result[1],
                    'allow_short': result[2],
                    'allow_options': result[3],
                    'allow_spreads': result[4]
                }
            else:
                return None
        except Exception as e:
            logging.error(f"Failed to fetch trading permissions: {e}")
            return None

    def is_trading_allowed(self, order, permissions):
        side = order.get('side', 'BUY')
        order_type = order.get('order_type', 'LIMIT')
        asset_class = order.get('asset_class', 'EQUITY')

        # Check for spread orders
        if order_type == 'SPREAD' and not permissions.get('allow_spreads', False):
            return False

        # Check for options trading
        if asset_class == 'OPTION' and not permissions.get('allow_options', False):
            return False

        # Check for buying and selling permissions
        if side == 'BUY' and not permissions.get('allow_buy', True):
            return False
        if side == 'SELL' and not permissions.get('allow_sell', True):
            return False

        # Check for short selling
        if side == 'SELL' and not self.is_position_available(order):
            # If no position available to sell, it's a short sale
            if not permissions.get('allow_short', False):
                return False

        return True

    def is_position_available(self, order):
        try:
            account_id = order['account_id']
            ticker = order['ticker']
            quantity = order['quantity']

            # Fetch current position for the ticker
            positions = self.database.get_positions(account_id)
            for position in positions:
                if position['ticker'] == ticker:
                    if position['quantity'] >= quantity:
                        return True  # Sufficient position available
                    else:
                        return False  # Insufficient position
            return False  # No position available
        except Exception as e:
            logging.error(f"Failed to check position availability: {e}")
            return False

