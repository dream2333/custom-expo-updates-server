import pathlib
import mimetypes
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from .helpers import (
    get_latest_update_bundle_path_for_runtime_version_async,
    get_metadata_async,
)

router = APIRouter()


@router.get("/assets")
async def assets_endpoint(
    asset: str = Query(...),
    runtimeVersion: str = Query(...),
    platform: str = Query(...)
):
    """Assets endpoint - serves asset files for updates."""
    
    # Validate asset name
    if not asset:
        raise HTTPException(status_code=400, detail='No asset name provided.')
    
    # Validate platform
    if platform not in ['ios', 'android']:
        raise HTTPException(
            status_code=400,
            detail='No platform provided. Expected "ios" or "android".'
        )
    
    # Validate runtime version
    if not runtimeVersion:
        raise HTTPException(status_code=400, detail='No runtimeVersion provided.')
    
    # Get update bundle path
    try:
        update_bundle_path = await get_latest_update_bundle_path_for_runtime_version_async(runtimeVersion)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Get metadata
    metadata = await get_metadata_async(update_bundle_path, runtimeVersion)
    metadata_json = metadata['metadataJson']
    
    # Resolve asset path
    asset_path = pathlib.Path(asset).resolve()
    
    # Check if it's a launch asset
    is_launch_asset = (
        metadata_json['fileMetadata'][platform]['bundle'] == 
        asset.replace(f"{update_bundle_path}/", '')
    )
    
    # Find asset metadata
    asset_metadata = None
    asset_name_relative = asset.replace(f"{update_bundle_path}/", '')
    
    for asset_item in metadata_json['fileMetadata'][platform]['assets']:
        if asset_item['path'] == asset_name_relative:
            asset_metadata = asset_item
            break
    
    # Check if asset exists
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail=f'Asset "{asset}" does not exist.')
    
    # Determine content type
    if is_launch_asset:
        content_type = 'application/javascript'
    elif asset_metadata and 'ext' in asset_metadata:
        content_type = mimetypes.guess_type(f'file.{asset_metadata["ext"]}')[0] or 'application/octet-stream'
    else:
        content_type = mimetypes.guess_type(str(asset_path))[0] or 'application/octet-stream'
    
    # Return file
    return FileResponse(
        path=asset_path,
        media_type=content_type
    )
