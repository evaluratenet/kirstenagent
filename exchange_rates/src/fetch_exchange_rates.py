import requests
import json
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

def gdrive_auth():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDrive(gauth)

def get_or_create_folder(drive, folder_name):
    file_list = drive.ListFile({
        'q': f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()
    if file_list:
        return file_list[0]['id']
    folder_metadata = {'title': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
    folder = drive.CreateFile(folder_metadata)
    folder.Upload()
    return folder['id']

def upload_to_gdrive(drive, content, gdrive_filename, folder_id):
    file1 = drive.CreateFile({'title': gdrive_filename, 'parents': [{'id': folder_id}]})
    file1.SetContentString(content)
    file1.Upload()
    print(f"Uploaded {gdrive_filename} to Google Drive in folder ID {folder_id}")

base_currency = "USD"
target_currencies = ["SGD", "EUR", "CNY", "JPY", "HKD", "INR", "IDR", "THB", "VND", "AUD"]
url = f"https://open.er-api.com/v6/latest/{base_currency}"

def fetch_exchange_rates():
    drive = gdrive_auth()
    folder_id = get_or_create_folder(drive, "exchange_rates")
    try:
        response = requests.get(url, timeout=10)
        print("API status code:", response.status_code)
        print("API response text:", response.text[:200])  # Print first 200 chars for debugging

        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        data = response.json()

        # Upload full API response to debug.json
        upload_to_gdrive(drive, json.dumps(data, indent=2), "debug.json", folder_id)

        if "rates" not in data:
            raise KeyError("Missing 'rates' in API response.")

        # Build exchange rate mapping
        exchange_rates = {}
        for currency in target_currencies:
            rate = data["rates"].get(currency)
            if rate:
                exchange_rates[f"USD→{currency}"] = round(rate, 6)
                exchange_rates[f"{currency}→USD"] = round(1 / rate, 6)

        # Upload latest.json
        upload_to_gdrive(drive, json.dumps(exchange_rates, indent=2), "latest.json", folder_id)

        print("✅ Exchange rates updated and uploaded to Google Drive successfully.")
        return True

    except Exception as e:
        # Upload error log to Google Drive
        error_content = f"{datetime.now()}: {str(e)}\n"
        upload_to_gdrive(drive, error_content, "error.log", folder_id)
        print(f"❌ Failed to fetch exchange rates: {e}")
        return False

if __name__ == "__main__":
    fetch_exchange_rates()
