#!/usr/bin/env python3
import argparse
import os
import sys
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import pandas as pd
import tempfile

def authenticate_google_drive():
    """Authenticate with Google Drive using service account credentials."""
    try:
        # Get the path to the credentials file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(script_dir, '..', 'private', 'client_secrets.json')
        
        # Initialize GoogleAuth
        gauth = GoogleAuth()
        gauth.LoadCredentialsFile(credentials_path)
        
        if gauth.credentials is None:
            # Authenticate if credentials don't exist
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            # Refresh token if expired
            gauth.Refresh()
        else:
            # Initialize with existing credentials
            gauth.Authorize()
            
        # Save credentials for future use
        gauth.SaveCredentialsFile(credentials_path)
        
        # Create and return GoogleDrive instance
        return GoogleDrive(gauth)
    except Exception as e:
        print(f"Authentication error: {str(e)}", file=sys.stderr)
        sys.exit(1)

def download_file_from_drive(drive, file_id, temp_dir):
    """Download a file from Google Drive to a temporary location."""
    try:
        file = drive.CreateFile({'id': file_id})
        temp_path = os.path.join(temp_dir, file['title'])
        file.GetContentFile(temp_path)
        return temp_path
    except Exception as e:
        print(f"Error downloading file {file_id}: {str(e)}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description='Extract and compare freight quotes from PDF files.')
    parser.add_argument('--comparison_id', required=True, help='Unique identifier for this comparison')
    parser.add_argument('--currency', required=True, help='Target currency for comparison')
    parser.add_argument('files', nargs='+', help='Google Drive file IDs to process')
    args = parser.parse_args()

    # Create a temporary directory for downloaded files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Authenticate with Google Drive
        drive = authenticate_google_drive()
        
        # Download all files
        downloaded_files = []
        for file_id in args.files:
            file_path = download_file_from_drive(drive, file_id, temp_dir)
            if file_path:
                downloaded_files.append(file_path)
        
        if not downloaded_files:
            print("No files were successfully downloaded", file=sys.stderr)
            sys.exit(1)
            
        # TODO: Add your existing quote extraction and comparison logic here
        # For now, just create a dummy Excel file to test the flow
        df = pd.DataFrame({
            'File': [os.path.basename(f) for f in downloaded_files],
            'Status': ['Processed'] * len(downloaded_files)
        })
        
        # Save results
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                'results', args.comparison_id)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{args.comparison_id}_comparison.xlsx")
        df.to_excel(output_file, index=False)
        print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main() 
