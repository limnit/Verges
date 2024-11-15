# src/database.py

# src/database.py

import psycopg2
import logging
from psycopg2.extras import RealDictCursor

class Database:
    # Existing methods...

    def get_open_orders(self, account_id, ticker, side, price):
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM orders
                WHERE account_id = %s AND ticker = %s AND side = %s AND price = %s AND status = 'OPEN';
            """, (account_id, ticker, side, price))
            orders = cur.fetchall()
            cur.close()
            return orders
        except Exception as e:
            logging.error(f"Failed to fetch open orders: {e}")
            return []

    def get_order(self, order_id):
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM orders WHERE order_id = %s;
            """, (order_id,))
            order = cur.fetchone()
            cur.close()
            return order
        except Exception as e:
            logging.error(f"Failed to fetch order: {e}")
            return None

    def update_order_status(self, order_id, status, filled_quantity=None, liquidity_tag=None):
        try:
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE orders
                SET status = %s,
                    filled_quantity = COALESCE(filled_quantity, 0) + COALESCE(%s, 0),
                    liquidity_tag = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_id = %s;
            """, (status, filled_quantity, liquidity_tag, order_id))
            self.conn.commit()
            cur.close()
        except Exception as e:
            logging.error(f"Failed to update order status: {e}")

    def update_order_quantity(self, order_id, quantity):
        try:
            cur = self.conn.cursor()
            cur.execute("""
                UPDATE orders
                SET quantity = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE order_id = %s;
            """, (quantity, order_id))
            self.conn.commit()
            cur.close()
        except Exception as e:
            logging.error(f"Failed to update order quantity: {e}")

