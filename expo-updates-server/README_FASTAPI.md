# FastAPI Expo Updates Server

This is a FastAPI implementation of the Expo Updates Server protocol.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

The server uses environment variables for configuration. You can set them in `.env.local`:

```
HOSTNAME=http://localhost:8000
PRIVATE_KEY_PATH=code-signing-keys/private-key.pem
```

### 3. Run the Server

```bash
./run_fastapi.sh
```

Or directly with uvicorn:

```bash
export HOSTNAME=http://localhost:8000
export PRIVATE_KEY_PATH=code-signing-keys/private-key.pem
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`

### 4. API Endpoints

- **GET /api/manifest** - Returns update manifests and directives
  - Headers:
    - `expo-protocol-version` (optional, default: "0")
    - `expo-platform` (required: "ios" or "android")
    - `expo-runtime-version` (required)
    - `expo-expect-signature` (optional)
    - `expo-current-update-id` (optional)
    - `expo-embedded-update-id` (required for rollback)
  - Query params (alternative to headers):
    - `platform`
    - `runtime-version`

- **GET /api/assets** - Serves asset files
  - Query params:
    - `asset` (required): Asset file path
    - `runtimeVersion` (required)
    - `platform` (required: "ios" or "android")

- **GET /** - Server info
- **GET /health** - Health check

## API Documentation

Once the server is running, you can access:
- Interactive API docs: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

## Directory Structure

```
expo-updates-server/
├── fastapi_app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── manifest.py      # Manifest endpoint
│   ├── assets.py        # Assets endpoint
│   └── helpers.py       # Helper functions
├── updates/             # Update bundles directory
├── code-signing-keys/   # Code signing keys
├── requirements.txt     # Python dependencies
├── run_fastapi.sh       # Run script
└── README_FASTAPI.md    # This file
```

## Publishing Updates

The update publishing process remains the same as the Next.js version:

1. Make changes in the `/expo-updates-client` directory
2. Run `yarn expo-publish` from the `/expo-updates-server` directory
3. The updates will be copied to the `updates/` directory
4. The FastAPI server will serve them automatically

## Code Signing

The server supports code signing using RSA-SHA256. Set the `PRIVATE_KEY_PATH` environment variable to point to your private key file.

## Differences from Next.js Version

- Port changed from 3000 to 8000 (default FastAPI/Uvicorn port)
- Environment variables are loaded from `.env.local` via the run script
- Built-in interactive API documentation at `/docs`
- Simpler deployment options (can use standard ASGI servers)

## Testing

You can test the server with curl:

```bash
# Get manifest
curl -H "expo-platform: ios" \
     -H "expo-runtime-version: test" \
     http://localhost:8000/api/manifest

# Get asset
curl "http://localhost:8000/api/assets?asset=updates/test/1/bundles/ios-xxx.js&runtimeVersion=test&platform=ios"
```

## Production Deployment

For production, use a production ASGI server configuration:

### Option 1: Gunicorn with Uvicorn workers (Recommended)

```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn fastapi_app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Option 2: Uvicorn alone

```bash
# Run with multiple workers
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Option 3: Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fastapi_app fastapi_app/
COPY updates updates/
COPY code-signing-keys code-signing-keys/
COPY .env.fastapi .env.fastapi

ENV HOSTNAME=http://localhost:8000
ENV PRIVATE_KEY_PATH=code-signing-keys/private-key.pem

EXPOSE 8000

CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t expo-updates-server .
docker run -p 8000:8000 expo-updates-server
```

### Environment Variables for Production

Make sure to set these environment variables:

- `HOSTNAME`: Your server's public URL (e.g., `https://updates.example.com`)
- `PRIVATE_KEY_PATH`: Path to your RSA private key for code signing

### Using Nginx as Reverse Proxy

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name updates.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Testing

Run the test suite:

```bash
./test_fastapi.sh
```

This will validate all endpoints including:
- Health check
- Root endpoint
- Manifest endpoint (iOS and Android)
- Code signing
- Assets endpoint
- Rollback directive

## Troubleshooting

- Make sure Python 3.8+ is installed
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that the `updates/` directory exists and contains update bundles
- Verify environment variables are set correctly
- Check logs for detailed error messages
