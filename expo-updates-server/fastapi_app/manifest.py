import json
import pathlib
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, Header, Query
from fastapi.responses import StreamingResponse
import io

from .helpers import (
    get_latest_update_bundle_path_for_runtime_version_async,
    get_metadata_async,
    get_expo_config_async,
    get_asset_metadata_async,
    get_private_key_async,
    sign_rsa_sha256,
    convert_to_dictionary_items_representation,
    serialize_dictionary,
    convert_sha256_hash_to_uuid,
    create_rollback_directive_async,
    create_no_update_available_directive_async,
    NoUpdateAvailableError,
)

router = APIRouter()


class UpdateType:
    NORMAL_UPDATE = "normal"
    ROLLBACK = "rollback"


async def get_type_of_update_async(update_bundle_path: str) -> str:
    """Determine the type of update based on directory contents."""
    update_path = pathlib.Path(update_bundle_path)
    rollback_file = update_path / 'rollback'
    
    if rollback_file.exists():
        return UpdateType.ROLLBACK
    return UpdateType.NORMAL_UPDATE


def create_multipart_response(parts: list) -> bytes:
    """Create a multipart/mixed response."""
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    content = io.BytesIO()
    
    for part_name, part_data, part_headers in parts:
        content.write(f"--{boundary}\r\n".encode())
        content.write(f'Content-Disposition: form-data; name="{part_name}"\r\n'.encode())
        
        for header_name, header_value in part_headers.items():
            content.write(f"{header_name}: {header_value}\r\n".encode())
        
        content.write(b"\r\n")
        content.write(part_data.encode() if isinstance(part_data, str) else part_data)
        content.write(b"\r\n")
    
    content.write(f"--{boundary}--\r\n".encode())
    
    return content.getvalue(), boundary


async def put_update_in_response_async(
    request: Request,
    update_bundle_path: str,
    runtime_version: str,
    platform: str,
    protocol_version: int,
    expect_signature: Optional[str]
) -> Response:
    """Generate response for normal update."""
    current_update_id = request.headers.get('expo-current-update-id')
    
    metadata = await get_metadata_async(update_bundle_path, runtime_version)
    metadata_json = metadata['metadataJson']
    created_at = metadata['createdAt']
    update_id = metadata['id']
    
    # NoUpdateAvailable directive only supported on protocol version 1
    if current_update_id == convert_sha256_hash_to_uuid(update_id) and protocol_version == 1:
        raise NoUpdateAvailableError()
    
    expo_config = await get_expo_config_async(update_bundle_path, runtime_version)
    platform_specific_metadata = metadata_json['fileMetadata'][platform]
    
    # Build assets list
    assets = []
    for asset in platform_specific_metadata['assets']:
        asset_metadata = await get_asset_metadata_async(
            update_bundle_path=update_bundle_path,
            file_path=asset['path'],
            ext=asset['ext'],
            is_launch_asset=False,
            runtime_version=runtime_version,
            platform=platform
        )
        assets.append(asset_metadata)
    
    # Get launch asset
    launch_asset = await get_asset_metadata_async(
        update_bundle_path=update_bundle_path,
        file_path=platform_specific_metadata['bundle'],
        ext=None,
        is_launch_asset=True,
        runtime_version=runtime_version,
        platform=platform
    )
    
    manifest = {
        'id': convert_sha256_hash_to_uuid(update_id),
        'createdAt': created_at,
        'runtimeVersion': runtime_version,
        'assets': assets,
        'launchAsset': launch_asset,
        'metadata': {},
        'extra': {
            'expoClient': expo_config
        }
    }
    
    # Handle code signing
    signature = None
    if expect_signature:
        private_key = await get_private_key_async()
        if not private_key:
            raise HTTPException(
                status_code=400,
                detail='Code signing requested but no key supplied when starting server.'
            )
        
        manifest_string = json.dumps(manifest)
        hash_signature = sign_rsa_sha256(manifest_string, private_key)
        dictionary = convert_to_dictionary_items_representation({
            'sig': hash_signature,
            'keyid': 'main'
        })
        signature = serialize_dictionary(dictionary)
    
    # Create asset request headers
    asset_request_headers = {}
    for asset in [*manifest['assets'], manifest['launchAsset']]:
        asset_request_headers[asset['key']] = {
            'test-header': 'test-header-value'
        }
    
    # Build multipart response
    parts = []
    
    manifest_headers = {
        'content-type': 'application/json; charset=utf-8'
    }
    if signature:
        manifest_headers['expo-signature'] = signature
    
    parts.append(('manifest', json.dumps(manifest), manifest_headers))
    parts.append(('extensions', json.dumps({'assetRequestHeaders': asset_request_headers}), 
                  {'content-type': 'application/json'}))
    
    multipart_content, boundary = create_multipart_response(parts)
    
    return Response(
        content=multipart_content,
        media_type=f'multipart/mixed; boundary={boundary}',
        headers={
            'expo-protocol-version': str(protocol_version),
            'expo-sfv-version': '0',
            'cache-control': 'private, max-age=0'
        }
    )


async def put_rollback_in_response_async(
    request: Request,
    update_bundle_path: str,
    protocol_version: int,
    expect_signature: Optional[str]
) -> Response:
    """Generate response for rollback."""
    if protocol_version == 0:
        raise HTTPException(status_code=400, detail='Rollbacks not supported on protocol version 0')
    
    embedded_update_id = request.headers.get('expo-embedded-update-id')
    if not embedded_update_id:
        raise HTTPException(status_code=400, detail='Invalid Expo-Embedded-Update-ID request header specified.')
    
    current_update_id = request.headers.get('expo-current-update-id')
    if current_update_id == embedded_update_id:
        raise NoUpdateAvailableError()
    
    directive = await create_rollback_directive_async(update_bundle_path)
    
    # Handle code signing
    signature = None
    if expect_signature:
        private_key = await get_private_key_async()
        if not private_key:
            raise HTTPException(
                status_code=400,
                detail='Code signing requested but no key supplied when starting server.'
            )
        
        directive_string = json.dumps(directive)
        hash_signature = sign_rsa_sha256(directive_string, private_key)
        dictionary = convert_to_dictionary_items_representation({
            'sig': hash_signature,
            'keyid': 'main'
        })
        signature = serialize_dictionary(dictionary)
    
    # Build multipart response
    parts = []
    directive_headers = {
        'content-type': 'application/json; charset=utf-8'
    }
    if signature:
        directive_headers['expo-signature'] = signature
    
    parts.append(('directive', json.dumps(directive), directive_headers))
    
    multipart_content, boundary = create_multipart_response(parts)
    
    return Response(
        content=multipart_content,
        media_type=f'multipart/mixed; boundary={boundary}',
        headers={
            'expo-protocol-version': '1',
            'expo-sfv-version': '0',
            'cache-control': 'private, max-age=0'
        }
    )


async def put_no_update_available_in_response_async(
    request: Request,
    protocol_version: int,
    expect_signature: Optional[str]
) -> Response:
    """Generate response for no update available."""
    if protocol_version == 0:
        raise HTTPException(
            status_code=400, 
            detail='NoUpdateAvailable directive not available in protocol version 0'
        )
    
    directive = await create_no_update_available_directive_async()
    
    # Handle code signing
    signature = None
    if expect_signature:
        private_key = await get_private_key_async()
        if not private_key:
            raise HTTPException(
                status_code=400,
                detail='Code signing requested but no key supplied when starting server.'
            )
        
        directive_string = json.dumps(directive)
        hash_signature = sign_rsa_sha256(directive_string, private_key)
        dictionary = convert_to_dictionary_items_representation({
            'sig': hash_signature,
            'keyid': 'main'
        })
        signature = serialize_dictionary(dictionary)
    
    # Build multipart response
    parts = []
    directive_headers = {
        'content-type': 'application/json; charset=utf-8'
    }
    if signature:
        directive_headers['expo-signature'] = signature
    
    parts.append(('directive', json.dumps(directive), directive_headers))
    
    multipart_content, boundary = create_multipart_response(parts)
    
    return Response(
        content=multipart_content,
        media_type=f'multipart/mixed; boundary={boundary}',
        headers={
            'expo-protocol-version': '1',
            'expo-sfv-version': '0',
            'cache-control': 'private, max-age=0'
        }
    )


@router.get("/manifest")
async def manifest_endpoint(
    request: Request,
    expo_protocol_version: Optional[str] = Header(None, alias="expo-protocol-version"),
    expo_platform: Optional[str] = Header(None, alias="expo-platform"),
    expo_runtime_version: Optional[str] = Header(None, alias="expo-runtime-version"),
    expo_expect_signature: Optional[str] = Header(None, alias="expo-expect-signature"),
    platform: Optional[str] = Query(None),
    runtime_version: Optional[str] = Query(None, alias="runtime-version")
):
    """Manifest endpoint - returns update manifests and directives."""
    
    # Parse protocol version
    protocol_version = int(expo_protocol_version or '0')
    
    # Get platform from header or query param
    platform_value = expo_platform or platform
    if platform_value not in ['ios', 'android']:
        raise HTTPException(
            status_code=400,
            detail='Unsupported platform. Expected either ios or android.'
        )
    
    # Get runtime version from header or query param
    runtime_version_value = expo_runtime_version or runtime_version
    if not runtime_version_value:
        raise HTTPException(
            status_code=400,
            detail='No runtimeVersion provided.'
        )
    
    # Get update bundle path
    try:
        update_bundle_path = await get_latest_update_bundle_path_for_runtime_version_async(runtime_version_value)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # Determine update type
    update_type = await get_type_of_update_async(update_bundle_path)
    
    # Generate appropriate response
    try:
        if update_type == UpdateType.NORMAL_UPDATE:
            return await put_update_in_response_async(
                request,
                update_bundle_path,
                runtime_version_value,
                platform_value,
                protocol_version,
                expo_expect_signature
            )
        elif update_type == UpdateType.ROLLBACK:
            return await put_rollback_in_response_async(
                request,
                update_bundle_path,
                protocol_version,
                expo_expect_signature
            )
    except NoUpdateAvailableError:
        return await put_no_update_available_in_response_async(
            request,
            protocol_version,
            expo_expect_signature
        )
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
