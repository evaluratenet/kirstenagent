import requests
import json
import os
from datetime import datetime

# Absolute path to your exchange_rates directory
output_dir = "/home5/evalurat/kirsten.evalurate.net/exchange_rates"
os.makedirs(output_dir, exist_ok=True)

# Currencies to convert relative to USD
base_currency = "USD"
target_currencies = ["SGD", "EUR", "CNY", "JPY", "HKD", "INR", "IDR", "THB", "VND", "AUD"]

# Use a reliable free API with no API key
url = f"https://open.er-api.com/v6/latest/{base_currency}"

try:
    response = requests.get(url, timeout=10)
    data = response.json()

    # Log full API response to debug.json
    with open(f"{output_dir}/debug.json", "w") as f:
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

    # Save to latest.json
    with open(f"{output_dir}/latest.json", "w") as f:
        json.dump(exchange_rates, f, indent=2)

    print("✅ Exchange rates updated successfully.")

except Exception as e:
    # Log errors to error.log
    with open(f"{output_dir}/error.log", "a") as f:
        f.write(f"{datetime.now()}: {str(e)}\n")
    print(f"❌ Failed to fetch exchange rates: {e}")
