"""
FastAPI implementation of Expo Updates Server.

This server implements the Expo Updates protocol specification:
https://docs.expo.dev/technical-specs/expo-updates-0

It provides two main endpoints:
- /api/manifest: Returns update manifests and directives
- /api/assets: Serves asset files for updates
"""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .manifest import router as manifest_router
from .assets import router as assets_router

# Change working directory to the parent of fastapi_app (expo-updates-server root)
app_dir = Path(__file__).parent.parent
os.chdir(app_dir)

app = FastAPI(
    title="Expo Updates Server",
    description="Custom implementation of Expo Updates protocol",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix
app.include_router(manifest_router, prefix="/api", tags=["manifest"])
app.include_router(assets_router, prefix="/api", tags=["assets"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Expo Updates Server - FastAPI",
        "endpoints": {
            "manifest": "/api/manifest",
            "assets": "/api/assets"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
