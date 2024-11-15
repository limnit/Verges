# main.py

from src.application import TradingApplication

def main():
    app = TradingApplication('config/config.yml')
    # The application will start and run indefinitely
    # Implement any necessary logic here

if __name__ == "__main__":
    main()

