# risk_plugins/margin_check.py

from .base import RiskPlugin
import logging

class MarginCheck(RiskPlugin):
    def check(self, order, account, session_id, risk_settings):
        try:
            account_type = account['account_type']
            asset_class = order.get('asset_class', 'EQUITY')  # Default to 'EQUITY' if not specified

            # Fetch margin rates from the database
            instrument_id = order.get('ticker')
            margin_rates = self.get_margin_rates(asset_class, account_type, instrument_id)

            if not margin_rates:
                return False, f"Margin rates not defined for asset class {asset_class} and account type {account_type}"

            initial_margin_rate = margin_rates['initial_margin_rate']
            maintenance_margin_rate = margin_rates['maintenance_margin_rate']

            # Calculate required margin
            order_value = self.calculate_order_value(order)

            if order_value is None:
                return False, "Failed to calculate order value"

            required_margin = order_value * initial_margin_rate

            # Get current balances
            margin_balance = account.get('margin_balance', 0.0)
            cash_balance = account.get('cash_balance', 0.0)
            portfolio_margin_available = account.get('portfolio_margin_available', 0.0)

            if account_type == 'CASH':
                if required_margin > cash_balance:
                    return False, "Insufficient cash balance for the order"
            elif account_type == 'MARGIN' or account_type == 'DAY_TRADING_MARGIN':
                total_available = cash_balance + margin_balance
                if required_margin > total_available:
                    return False, "Insufficient margin balance for the order"
            elif account_type == 'PORTFOLIO_MARGIN':
                if required_margin > portfolio_margin_available:
                    return False, "Insufficient portfolio margin available"
            else:
                return False, f"Unknown account type: {account_type}"

            # For spread trades, apply margin offsets
            if order.get('order_type') == 'SPREAD':
                spread_check_passed, message = self.check_spread_margin(order, account)
                if not spread_check_passed:
                    return False, message

            return True, ""
        except Exception as e:
            logging.error(f"MarginCheck error: {e}")
            return False, "Error in margin check"

    def get_margin_rates(self, asset_class, account_type, instrument_id=None):
        try:
            if instrument_id:
                # Check for instrument-specific overrides
                cur = self.database.conn.cursor()
                cur.execute("""
                    SELECT initial_margin_rate, maintenance_margin_rate
                    FROM instrument_margin_overrides
                    WHERE instrument_id = %s;
                """, (instrument_id,))
                result = cur.fetchone()
                cur.close()
                if result:
                    return {
                        'initial_margin_rate': float(result[0]),
                        'maintenance_margin_rate': float(result[1])
                    }

            # Fetch default margin rates
            cur = self.database.conn.cursor()
            cur.execute("""
                SELECT initial_margin_rate, maintenance_margin_rate
                FROM margin_requirements
                WHERE asset_class = %s AND account_type = %s;
            """, (asset_class, account_type))
            result = cur.fetchone()
            cur.close()
            if result:
                return {
                    'initial_margin_rate': float(result[0]),
                    'maintenance_margin_rate': float(result[1])
                }
            else:
                return None
        except Exception as e:
            logging.error(f"Failed to fetch margin rates: {e}")
            return None

    def calculate_order_value(self, order):
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
                order_value = price * quantity * contract_size
            else:
                # For equities
                order_value = price * quantity

            return order_value
        except Exception as e:
            logging.error(f"Failed to calculate order value: {e}")
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

    def check_spread_margin(self, order, account):
        try:
            legs = order.get('legs', [])
            if not legs or len(legs) < 2:
                return False, "Invalid spread order: Less than two legs"

            net_required_margin = 0.0
            total_offset = 0.0

            for leg in legs:
                leg_asset_class = leg.get('asset_class', 'OPTION')
                leg_instrument_id = leg.get('ticker')

                # Fetch margin rates for the leg
                margin_rates = self.get_margin_rates(
                    leg_asset_class, account['account_type'], leg_instrument_id
                )
                if not margin_rates:
                    return False, f"Margin rates not defined for leg {leg_instrument_id}"

                initial_margin_rate = margin_rates['initial_margin_rate']
                leg_value = self.calculate_order_value(leg)
                if leg_value is None:
                    return False, f"Failed to calculate order value for leg {leg_instrument_id}"

                leg_required_margin = leg_value * initial_margin_rate
                net_required_margin += leg_required_margin

            # Calculate margin offset for the spread
            spread_margin_offset = self.calculate_spread_margin_offset(order)
            total_required_margin = net_required_margin - spread_margin_offset

            # Ensure margin requirement is not negative
            if total_required_margin < 0:
                total_required_margin = 0.0

            # Check if account has sufficient margin
            margin_balance = account.get('margin_balance', 0.0)
            cash_balance = account.get('cash_balance', 0.0)
            total_available = cash_balance + margin_balance

            if total_required_margin > total_available:
                return False, "Insufficient margin balance for the spread order"

            return True, ""
        except Exception as e:
            logging.error(f"Spread margin check error: {e}")
            return False, "Error in spread margin check"

    def calculate_spread_margin_offset(self, order):
        try:
            legs = order.get('legs', [])
            if len(legs) < 2:
                return 0.0

            # For vertical spreads, offset is the difference in strike prices times contract size times quantity
            leg1 = legs[0]
            leg2 = legs[1]

            strike1 = self.get_option_strike_price(leg1['ticker'])
            strike2 = self.get_option_strike_price(leg2['ticker'])

            if strike1 is None or strike2 is None:
                return 0.0

            contract_size = self.get_contract_size(leg1['ticker'])
            if contract_size is None:
                return 0.0

            spread_width = abs(strike1 - strike2)
            quantity = min(leg1['quantity'], leg2['quantity'])

            spread_margin_offset = spread_width * contract_size * quantity

            return spread_margin_offset
        except Exception as e:
            logging.error(f"Failed to calculate spread margin offset: {e}")
            return 0.0

    def get_option_strike_price(self, ticker):
        try:
            cur = self.database.conn.cursor()
            cur.execute("""
                SELECT strike_price FROM instruments WHERE ticker = %s;
            """, (ticker,))
            result = cur.fetchone()
            cur.close()
            if result:
                return float(result[0])
            else:
                return None
        except Exception as e:
            logging.error(f"Failed to fetch strike price for {ticker}: {e}")
            return None

