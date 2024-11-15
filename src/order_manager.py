# src/order_manager.py

import logging

# src/order_manager.py

import logging
import threading

class OrderManager:
    def __init__(self, database, fix_engine):
        self.database = database
        self.fix_engine = fix_engine

    def process_order(self, order, session_id, price):
        account = self.database.get_account(order['account_id'])
        if account.get('internalization_enabled', False):
            internalized = self.attempt_internalization(order, account, session_id)
            if internalized:
                return  # Order has been internalized

        # If not internalized, send the order to the market
        self.send_order_to_market(order, session_id)

    def attempt_internalization(self, order, account, session_id):
        # Check for matching open orders
        matching_order = self.find_matching_order(order)
        if matching_order:
            # Cancel the existing order in the market
            self.cancel_order_in_market(matching_order)
            # Wait for cancellation confirmation
            cancellation_confirmed = self.wait_for_cancellation(matching_order)
            if cancellation_confirmed:
                # Internalize the trade
                self.internalize_trade(order, matching_order, session_id)
                return True
        return False

    def find_matching_order(self, order):
        # Find open orders in the same account, opposite side, same ticker, same price
        matching_orders = self.database.get_open_orders(
            account_id=order['account_id'],
            ticker=order['ticker'],
            side='BUY' if order['side'] == 'SELL' else 'SELL',
            price=order['price']
        )
        if matching_orders:
            return matching_orders[0]  # Return the first matching order
        return None

    def cancel_order_in_market(self, order):
        # Send cancel request to the market via FIX
        self.fix_engine.send_order_cancel_request(order)

    def wait_for_cancellation(self, order):
        # Wait for cancellation confirmation (implement timeout if necessary)
        # This is a simplified example; in a real application, you'd handle this asynchronously
        for _ in range(10):
            updated_order = self.database.get_order(order['order_id'])
            if updated_order['status'] == 'CANCELED':
                return True
            time.sleep(0.5)  # Wait 0.5 seconds before checking again
        return False

    def internalize_trade(self, incoming_order, existing_order, session_id):
        # Determine the execution quantity (handle partial fills)
        execution_quantity = min(incoming_order['quantity'], existing_order['quantity'])

        # Update orders in the database
        self.database.update_order_status(
            order_id=incoming_order['order_id'],
            status='FILLED',
            filled_quantity=execution_quantity,
            liquidity_tag='INTERNALIZED'
        )
        self.database.update_order_status(
            order_id=existing_order['order_id'],
            status='FILLED',
            filled_quantity=execution_quantity,
            liquidity_tag='INTERNALIZED'
        )

        # Update positions
        self.database.update_position(
            account_id=incoming_order['account_id'],
            session_id=session_id,
            ticker=incoming_order['ticker'],
            quantity=execution_quantity if incoming_order['side'] == 'BUY' else -execution_quantity,
            average_price=incoming_order['price']
        )
        self.database.update_position(
            account_id=existing_order['account_id'],
            session_id=existing_order['session_id'],
            ticker=existing_order['ticker'],
            quantity=execution_quantity if existing_order['side'] == 'BUY' else -execution_quantity,
            average_price=existing_order['price']
        )

        # Send execution reports via FIX
        self.fix_engine.send_execution_report(
            order=incoming_order,
            session_id=session_id,
            price=incoming_order['price'],
            quantity=execution_quantity,
            liquidity_tag='INTERNALIZED'
        )
        self.fix_engine.send_execution_report(
            order=existing_order,
            session_id=existing_order['session_id'],
            price=existing_order['price'],
            quantity=execution_quantity,
            liquidity_tag='INTERNALIZED'
        )

        # Handle remaining quantities if partial fills occurred
        self.handle_partial_fills(incoming_order, existing_order, execution_quantity)

    def handle_partial_fills(self, incoming_order, existing_order, execution_quantity):
        # Check if there are remaining quantities
        incoming_remaining = incoming_order['quantity'] - execution_quantity
        existing_remaining = existing_order['quantity'] - execution_quantity

        if incoming_remaining > 0:
            # Update incoming order with remaining quantity
            self.database.update_order_quantity(
                order_id=incoming_order['order_id'],
                quantity=incoming_remaining
            )
            # Continue processing the remaining order
            self.send_order_to_market(incoming_order, incoming_order['session_id'])
        if existing_remaining > 0:
            # Update existing order with remaining quantity
            self.database.update_order_quantity(
                order_id=existing_order['order_id'],
                quantity=existing_remaining
            )
            # Resubmit the existing order to the market
            self.send_order_to_market(existing_order, existing_order['session_id'])

    def send_order_to_market(self, order, session_id):
        # Implement sending the order to the external market via FIX
        self.fix_engine.send_new_order(order, session_id)
        # Update order status in the database
        self.database.update_order_status(
            order_id=order['order_id'],
            status='SENT_TO_MARKET'
        )

