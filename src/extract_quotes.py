import argparse
import os
import json
import uuid
import importlib
from pathlib import Path
from datetime import datetime
import pandas as pd
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import tempfile

# Get the script's directory
SCRIPT_DIR = Path(__file__).parent.absolute()
BASE_DIR = SCRIPT_DIR.parent

# Setup logging
def setup_logging():
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir / "extract_quotes_start.log"

with open(setup_logging(), "a") as log:
    log.write(f"{datetime.now()}: extract_quotes.py started\n")

def get_client_secrets():
    # Render Secret File path
    render_secret_path = '/etc/secrets/CLIENT_SECRETS_JSON'
    # Local file path
    local_secret_path = 'client_secrets.json'

    if os.path.exists(render_secret_path):
        with open(render_secret_path, 'r') as f:
            return f.read()
    elif os.path.exists(local_secret_path):
        with open(local_secret_path, 'r') as f:
            return f.read()
    else:
        client_secrets = os.getenv('CLIENT_SECRETS_JSON')
        if client_secrets:
            return client_secrets
        else:
            raise FileNotFoundError(
                "No client secrets found. "
                "Checked /etc/secrets/CLIENT_SECRETS_JSON, client_secrets.json, and CLIENT_SECRETS_JSON env var."
            )

def gdrive_auth():
    gauth = GoogleAuth()
    
    # Get client secrets from environment variable
    client_secrets = get_client_secrets()
    
    # Create a temporary file with the client secrets
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write(client_secrets)
        temp_file_path = temp_file.name
    
    try:
        # Load client secrets from temporary file
        gauth.LoadClientConfigFile(temp_file_path)
        
        # Try to load existing credentials
        if os.path.exists("mycreds.txt"):
            gauth.LoadCredentialsFile("mycreds.txt")
        
        # If no credentials or they're expired, authenticate
        if gauth.credentials is None or gauth.access_token_expired:
            # Set access_type to offline to get refresh token
            gauth.GetFlow()
            gauth.flow.params['access_type'] = 'offline'
            gauth.flow.params['approval_prompt'] = 'force'
            gauth.LocalWebserverAuth()
            gauth.SaveCredentialsFile("mycreds.txt")
        else:
            gauth.Authorize()
        
        return GoogleDrive(gauth)
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

def get_folder_id(drive, folder_name):
    file_list = drive.ListFile({
        'q': f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    }).GetList()
    if file_list:
        return file_list[0]['id']
    return None

# Load exchange rates from Google Drive
def load_exchange_rates():
    try:
        drive = gdrive_auth()
        folder_id = get_folder_id(drive, "exchange_rates")
        if not folder_id:
            raise Exception("Exchange rates folder not found in Google Drive")

        # Get the latest.json file
        file_list = drive.ListFile({
            'q': f"title='latest.json' and '{folder_id}' in parents and trashed=false"
        }).GetList()

        if not file_list:
            raise Exception("latest.json not found in exchange_rates folder")

        # Download and parse the file
        file1 = drive.CreateFile({'id': file_list[0]['id']})
        content = file1.GetContentString()
        return json.loads(content)
    except Exception as e:
        with open(BASE_DIR / "logs" / "error.log", "a") as log:
            log.write(f"{datetime.now()}: Error loading exchange rates: {str(e)}\n")
        return {}

# Determine parser by file extension
def get_parser(file_path):
    ext = file_path.suffix.lower()
    log_path = BASE_DIR / "logs" / "parser_debug.log"
    with open(log_path, "a") as log:
        log.write(f"{datetime.now()}: Checking file: {file_path.name} with ext: {ext}\n")
    if ext == ".xlsx":
        return "parse_excel"
    elif ext == ".pdf":
        return "parse_pdf"
    elif ext == ".docx":
        return "parse_docx"
    return None

# Combine all parsed quotes into one vertical format DataFrame
def combine_quotes(parsed_quotes):
    all_fields = set()
    for quote in parsed_quotes:
        all_fields.update(quote.keys())

    all_fields = sorted(list(all_fields))
    data = {"Field": all_fields}

    for i, quote in enumerate(parsed_quotes):
        col = []
        for field in all_fields:
            col.append(quote.get(field, ""))
        data[f"Quote {i+1}"] = col

    return pd.DataFrame(data)

# Parse all files using respective modules
def extract_all(files, currency_requested):
    parsed_quotes = []
    exchange_rates = load_exchange_rates()

    for file_path in files:
        file_path = Path(file_path)
        parser_name = get_parser(file_path)
        if not parser_name:
            continue

        try:
            parser_module = importlib.import_module(f"src.parsers.{parser_name}")
            extracted = parser_module.parse(file_path, currency_requested, exchange_rates)

            # Append metadata
            for quote in extracted:
                quote['filename'] = file_path.name
                quote['currency_requested'] = currency_requested
                quote['exchange_rates_used'] = json.dumps(exchange_rates)
                parsed_quotes.append(quote)
        except Exception as e:
            with open(BASE_DIR / "logs" / "error.log", "a") as log:
                log.write(f"{datetime.now()}: Error processing {file_path}: {str(e)}\n")

    return parsed_quotes

# Main entry point
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--comparison_id', required=True)
    parser.add_argument('--currency', required=True)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args()

    result_dir = BASE_DIR / "results" / args.comparison_id
    result_dir.mkdir(parents=True, exist_ok=True)

    quotes = extract_all(args.files, args.currency)

    with open(result_dir / "debug.log", "w") as f:
        f.write(f"Parsed quotes count: {len(quotes)}\n")
        for q in quotes:
            f.write(json.dumps(q, indent=2) + "\n\n")

    if len(quotes) < 2:
        with open(result_dir / "summary.txt", "w") as f:
            f.write("❗ Insufficient quotes for comparison.")
        return

    df = combine_quotes(quotes)
    df.to_excel(result_dir / f"{args.comparison_id}_comparison.xlsx", index=False)

if __name__ == "__main__":
    main()
