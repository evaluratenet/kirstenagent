import requests
import json
from datetime import datetime
import os

print("Running script from:", os.path.abspath(__file__))
print("EXCHANGE_RATES_DIR will be:", "/opt/render/project/src/exchange_rates")

base_currency = "USD"
target_currencies = ["SGD", "EUR", "CNY", "JPY", "HKD", "INR", "IDR", "THB", "VND", "AUD"]
url = f"https://open.er-api.com/v6/latest/{base_currency}"

# Use an absolute path for exchange rates storage on Render
EXCHANGE_RATES_DIR = "/opt/render/project/src/exchange_rates"

def fetch_exchange_rates():
    try:
        print("EXCHANGE_RATES_DIR will be:", EXCHANGE_RATES_DIR)
        os.makedirs(EXCHANGE_RATES_DIR, exist_ok=True)
        
        response = requests.get(url, timeout=10)
        print("API status code:", response.status_code)
        print("API response text:", response.text[:200])  # Print first 200 chars for debugging

        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        data = response.json()

        # Save full API response to debug.json
        with open(os.path.join(EXCHANGE_RATES_DIR, "debug.json"), "w") as f:
            json.dump(data, f, indent=2)

        if "rates" not in data:
            raise KeyError("Missing 'rates' in API response.")

        # Build exchange rate mapping
        exchange_rates = {}
        for currency in target_currencies:
            rate = data["rates"].get(currency)
            if rate:
                exchange_rates[f"USD→{currency}"] = round(rate, 6)
                exchange_rates[f"{currency}→USD"] = round(1 / rate, 6)

        # Save latest.json
        with open(os.path.join(EXCHANGE_RATES_DIR, "latest.json"), "w") as f:
            json.dump(exchange_rates, f, indent=2)

        print("✅ Exchange rates updated and saved locally successfully.")
        return True

    except Exception as e:
        # Save error log locally
        error_content = f"{datetime.now()}: {str(e)}\n"
        # Ensure the directory exists before writing the error log
        try:
            os.makedirs(EXCHANGE_RATES_DIR, exist_ok=True)
            with open(os.path.join(EXCHANGE_RATES_DIR, "error.log"), "a") as f:
                f.write(error_content)
        except Exception as log_error:
            print(f"Could not write error log: {log_error}")
        print(f"❌ Failed to fetch exchange rates: {e}")
        return False

if __name__ == "__main__":
    fetch_exchange_rates()
