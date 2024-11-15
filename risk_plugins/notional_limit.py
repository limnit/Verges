# risk_plugins/notional_limit.py

from .base import RiskPlugin
import logging

class NotionalLimitCheck(RiskPlugin):
    def __init__(self, database, market_data):
        super().__init__(database, market_data)

    def check(self, order, account, session_id, risk_settings):
        try:
            asset_class = order.get('asset_class', 'EQUITY')  # Default to 'EQUITY'
            # Fetch notional limits from the database
            notional_limits = self.get_notional_limits(session_id, asset_class)
            if not notional_limits:
                return False, f"Notional limits not set for asset class {asset_class}"

            max_order_notional = notional_limits.get('max_order_notional')
            max_total_notional = notional_limits.get('max_total_notional')

            # Calculate order notional value
            if order.get('order_type') == 'SPREAD':
                order_notional = self.calculate_spread_notional(order)
            else:
                order_notional = self.calculate_order_notional(order)

            if order_notional is None:
                return False, "Failed to calculate order notional value"

            # Check against max_order_notional
            if max_order_notional is not None and order_notional > max_order_notional:
                return False, f"Order notional value {order_notional} exceeds maximum allowed {max_order_notional}"

            # Calculate total notional value of open positions including the new order
            total_notional = self.calculate_total_notional(account['account_id'], order, order_notional)

            # Check against max_total_notional
            if max_total_notional is not None and total_notional > max_total_notional:
                return False, f"Total notional value {total_notional} exceeds maximum allowed {max_total_notional}"

            return True, ""
        except Exception as e:
            logging.error(f"NotionalLimitCheck error: {e}")
            return False, "Error in notional limit check"

    def get_notional_limits(self, session_id, asset_class):
        try:
            cur = self.database.conn.cursor()
            cur.execute("""
                SELECT max_order_notional, max_total_notional
                FROM notional_limits
                WHERE session_id = %s AND asset_class = %s;
            """, (session_id, asset_class))
            result = cur.fetchone()
            cur.close()
            if result:
                return {
                    'max_order_notional': float(result[0]) if result[0] is not None else None,
                    'max_total_notional': float(result[1]) if result[1] is not None else None
                }
            else:
                return None
        except Exception as e:
            logging.error(f"Failed to fetch notional limits: {e}")
            return None

    def calculate_order_notional(self, order):
        try:
            price = order.get('price')
            quantity = order.get('quantity')
            asset_class = order.get('asset_class', 'EQUITY')

            if price is None or quantity is None:
                return None

            if asset_class in ['OPTION', 'FUTURE']:
                # Fetch contract size
                contract_size = self.get_contract_size(order['ticker'])
                if contract_size is None:
                    return None
                order_notional = price * quantity * contract_size
            else:
                # For equities
                order_notional = price * quantity

            return order_notional
        except Exception as e:
            logging.error(f"Failed to calculate order notional: {e}")
            return None

    def get_contract_size(self, ticker):
        try:
            cur = self.database.conn.cursor()
            cur.execute("""
                SELECT contract_size FROM instruments WHERE ticker = %s;
            """, (ticker,))
            result = cur.fetchone()
            cur.close()
            if result:
                return int(result[0])
            else:
                return None
        except Exception as e:
            logging.error(f"Failed to fetch contract size for {ticker}: {e}")
            return None

    def calculate_spread_notional(self, order):
        try:
            legs = order.get('legs', [])
            if not legs or len(legs) < 2:
                return None

            total_notional = 0.0

            for leg in legs:
                leg_notional = self.calculate_order_notional(leg)
                if leg_notional is None:
                    return None
                total_notional += leg_notional

            return total_notional
        except Exception as e:
            logging.error(f"Failed to calculate spread notional: {e}")
            return None

    def calculate_total_notional(self, account_id, order, order_notional):
        try:
            # Fetch current positions for the account
            positions = self.database.get_positions(account_id)
            total_notional = 0.0

            for position in positions:
                # For each position, calculate its notional value
                position_quantity = position['quantity']
                if position_quantity == 0:
                    continue
                ticker = position['ticker']
                asset_class = position.get('asset_class', 'EQUITY')
                price = self.get_market_price(ticker)
                if price is None:
                    continue

                if asset_class in ['OPTION', 'FUTURE']:
                    contract_size = self.get_contract_size(ticker)
                    if contract_size is None:
                        continue
                    position_notional = abs(position_quantity) * price * contract_size
                else:
                    position_notional = abs(position_quantity) * price

                total_notional += position_notional

            # Add the notional value of the new order
            total_notional += order_notional

            return total_notional
        except Exception as e:
            logging.error(f"Failed to calculate total notional: {e}")
            return None

    def get_market_price(self, ticker):
        try:
            price = self.market_data.get_last_trade(ticker)
            return price
        except Exception as e:
            logging.error(f"Failed to fetch market price for {ticker}: {e}")
            return None

