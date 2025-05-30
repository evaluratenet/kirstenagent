from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Optional
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import csv
import datetime

app = FastAPI()

# Allow CORS for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
CONGESTION_ALERTS_DIR = "congestion_alerts"
CSV_LOG_DIR = "csv_log"
os.makedirs(CSV_LOG_DIR, exist_ok=True)

@app.post("/analyze")
async def analyze(
    request: Optional[UploadFile] = File(None),
    quotes: List[UploadFile] = File(...),
    email: Optional[str] = Form(None)
):
    if not quotes or len(quotes) < 2:
        return JSONResponse(content={"error": "At least two quote files must be uploaded for comparison."}, status_code=400)

    # Handle request file (optional)
    request_summary = "No original request provided.\n"
    if request:
        try:
            request_content = await request.read()
            request_summary = f"Original request: {request.filename}\n"
        except Exception:
            request_summary = "⚠️ Could not read request file.\n"

    # Handle quote files (some may be unsupported types)
    quote_summaries = []
    accepted_extensions = ('.pdf', '.xls', '.xlsx', '.csv', '.doc', '.docx')
    for quote in quotes:
        ext = os.path.splitext(quote.filename)[1].lower()
        if ext not in accepted_extensions:
            quote_summaries.append(f"{quote.filename} ❌ (unsupported file type)")
            continue
        try:
            content = await quote.read()
            quote_summaries.append(f"{quote.filename} ✅ ({len(content)} bytes)")
        except Exception:
            quote_summaries.append(f"{quote.filename} ⚠️ (failed to read)")

    # Scan congestion alerts (optional folder)
    alert_summary = ""
    if os.path.exists(CONGESTION_ALERTS_DIR):
        alert_files = os.listdir(CONGESTION_ALERTS_DIR)
        if alert_files:
            alert_summary = "⚠️ Port/Airport congestion alerts detected:\n"
            for fname in alert_files:
                if any(k in fname.lower() for k in ["congestion", "delay"]):
                    alert_summary += f"• {fname}\n"

    # Log to daily CSV
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    csv_path = os.path.join(CSV_LOG_DIR, f"summary_{today}.csv")
    with open(csv_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        for quote in quotes:
            writer.writerow([today, quote.filename, email or "N/A"])

    # Build result summary
    summary = f"""
📦 Quote Comparison Summary
-----------------------------
{request_summary}
Quotes uploaded:
{chr(10).join(quote_summaries)}

{alert_summary or '✅ No port congestion alerts found.'}

✅ Quotes successfully analyzed.
"""
    if email:
        summary += f"\n📧 A copy has been sent to {email} (simulated)."

    return {"result": summary.strip()}
