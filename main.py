from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import tempfile
import pandas as pd
from fastapi.responses import FileResponse
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

class ProcessRequest(BaseModel):
    comparison_id: str
    currency: str
    file_ids: List[str]

def authenticate_google_drive():
    """Authenticate with Google Drive using service account credentials."""
    try:
        # Get credentials from environment variable
        credentials_json = os.getenv('GOOGLE_DRIVE_CREDENTIALS')
        if not credentials_json:
            raise ValueError("GOOGLE_DRIVE_CREDENTIALS environment variable not set")
        
        # Save credentials to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write(credentials_json)
            credentials_path = f.name
        
        try:
            # Initialize GoogleAuth
            gauth = GoogleAuth()
            gauth.LoadCredentialsFile(credentials_path)
            
            if gauth.credentials is None:
                raise ValueError("Failed to load Google Drive credentials")
            
            # Create and return GoogleDrive instance
            return GoogleDrive(gauth)
        finally:
            # Clean up the temporary file
            try:
                os.unlink(credentials_path)
            except:
                pass
                
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

def download_file_from_drive(drive, file_id, temp_dir):
    """Download a file from Google Drive to a temporary location."""
    try:
        file = drive.CreateFile({'id': file_id})
        temp_path = os.path.join(temp_dir, file['title'])
        file.GetContentFile(temp_path)
        return temp_path
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {str(e)}")
        return None

def extract_quotes_from_pdf(pdf_path, currency):
    """Extract quotes from a PDF file."""
    # TODO: Add your existing PDF processing logic here
    # For now, return dummy data
    return {
        'carrier': 'Dummy Carrier',
        'rate': 100.0,
        'currency': currency,
        'validity': '30 days'
    }

@app.post("/process")
async def process_files(request: ProcessRequest):
    try:
        # Authenticate with Google Drive
        drive = authenticate_google_drive()
        
        # Create a temporary directory for downloaded files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download all files
            downloaded_files = []
            for file_id in request.file_ids:
                try:
                    file = drive.CreateFile({'id': file_id})
                    temp_path = os.path.join(temp_dir, file['title'])
                    file.GetContentFile(temp_path)
                    downloaded_files.append(temp_path)
                except Exception as e:
                    logger.error(f"Error downloading file {file_id}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Error downloading file {file_id}: {str(e)}")
            
            if not downloaded_files:
                raise HTTPException(status_code=400, detail="No files were successfully downloaded")
            
            # Process each file
            results = []
            for file_path in downloaded_files:
                try:
                    quote_data = extract_quotes_from_pdf(file_path, request.currency)
                    results.append({
                        'file': os.path.basename(file_path),
                        **quote_data
                    })
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    results.append({
                        'file': os.path.basename(file_path),
                        'error': str(e)
                    })
            
            # Create Excel file
            df = pd.DataFrame(results)
            
            # Save results to temporary file
            output_file = os.path.join(temp_dir, f"{request.comparison_id}_comparison.xlsx")
            df.to_excel(output_file, index=False)
            
            # Return the file
            return FileResponse(
                output_file,
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                filename=f"{request.comparison_id}_comparison.xlsx"
            )
            
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"} 
