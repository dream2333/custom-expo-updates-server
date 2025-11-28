#!/usr/bin/env bash
# Run the FastAPI Expo Updates Server

# Set default values
export HOSTNAME=${HOSTNAME:-http://localhost:8000}
export PRIVATE_KEY_PATH=${PRIVATE_KEY_PATH:-code-signing-keys/private-key.pem}

# Load .env.fastapi if it exists
if [ -f .env.fastapi ]; then
    export $(grep -v '^#' .env.fastapi | xargs)
fi

# Run uvicorn
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000 --reload
