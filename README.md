# Exchange Rates Service

This service fetches exchange rates from the Open Exchange Rates API and stores them in JSON format.

## Features

- Fetches exchange rates for multiple currencies relative to USD
- Stores rates in JSON format
- Includes error logging
- Deployed on Render

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (if needed)

## Usage

The service can be run as a scheduled task on Render. It will:
- Fetch current exchange rates
- Store them in JSON format
- Log any errors that occur

## Environment Variables

No environment variables are required for basic operation.

## API Endpoints

This service uses the free Open Exchange Rates API (https://open.er-api.com/). 