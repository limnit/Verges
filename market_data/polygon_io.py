# market_data/polygon_io.py

import requests
import logging

class PolygonIO:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'https://api.polygon.io'

    def get_last_trade(self, ticker):
        url = f"{self.base_url}/v2/last/trade/{ticker}"
        params = {'apiKey': self.api_key}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            return data['results']['price']
        else:
            logging.error(f"Polygon.io API error: {response.text}")
            return None
