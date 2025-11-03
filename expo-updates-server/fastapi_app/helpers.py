import hashlib
import json
import os
import pathlib
from base64 import b64encode, b64decode
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import mimetypes


class NoUpdateAvailableError(Exception):
    pass


def create_hash(data: bytes, algorithm: str, encoding: str) -> str:
    """Create hash of data using specified algorithm and encoding."""
    if algorithm == 'sha256':
        hash_obj = hashlib.sha256(data)
    elif algorithm == 'md5':
        hash_obj = hashlib.md5(data)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    if encoding == 'hex':
        return hash_obj.hexdigest()
    elif encoding == 'base64':
        return b64encode(hash_obj.digest()).decode('utf-8')
    else:
        raise ValueError(f"Unsupported encoding: {encoding}")


def get_base64_url_encoding(base64_encoded_string: str) -> str:
    """Convert base64 to base64url encoding."""
    return base64_encoded_string.replace('+', '-').replace('/', '_').rstrip('=')


def convert_to_dictionary_items_representation(obj: Dict[str, str]) -> Dict[str, Tuple[str, Dict]]:
    """Convert object to dictionary items representation for structured headers."""
    return {k: (v, {}) for k, v in obj.items()}


def sign_rsa_sha256(data: str, private_key_pem: str) -> str:
    """Sign data using RSA-SHA256."""
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'),
        password=None,
        backend=default_backend()
    )
    
    signature = private_key.sign(
        data.encode('utf-8'),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    return b64encode(signature).decode('utf-8')


def serialize_dictionary(dictionary: Dict[str, Tuple[str, Dict]]) -> str:
    """Serialize dictionary to structured header format."""
    # Simplified implementation - for full compatibility, use structured-headers library
    items = []
    for key, (value, params) in dictionary.items():
        items.append(f'{key}=:{value}:')
    return ', '.join(items)


async def get_private_key_async() -> Optional[str]:
    """Get private key from path specified in environment."""
    private_key_path = os.getenv('PRIVATE_KEY_PATH')
    if not private_key_path:
        return None
    
    try:
        with open(pathlib.Path(private_key_path).resolve(), 'r') as f:
            return f.read()
    except FileNotFoundError:
        return None


async def get_latest_update_bundle_path_for_runtime_version_async(runtime_version: str) -> str:
    """Get the latest update bundle path for a runtime version."""
    updates_directory = pathlib.Path('updates') / runtime_version
    
    if not updates_directory.exists():
        raise ValueError('Unsupported runtime version')
    
    # Get all directories in the runtime version folder
    directories = [
        d for d in updates_directory.iterdir() 
        if d.is_dir() and d.name.isdigit()
    ]
    
    if not directories:
        raise ValueError('No updates found for runtime version')
    
    # Sort by directory name (timestamp) in descending order
    directories.sort(key=lambda x: int(x.name), reverse=True)
    
    return str(directories[0])


async def get_asset_metadata_async(
    update_bundle_path: str,
    file_path: str,
    ext: Optional[str],
    is_launch_asset: bool,
    runtime_version: str,
    platform: str
) -> Dict[str, Any]:
    """Get metadata for an asset."""
    asset_file_path = pathlib.Path(update_bundle_path) / file_path
    
    with open(asset_file_path, 'rb') as f:
        asset_data = f.read()
    
    asset_hash = get_base64_url_encoding(create_hash(asset_data, 'sha256', 'base64'))
    key = create_hash(asset_data, 'md5', 'hex')
    
    if is_launch_asset:
        key_extension_suffix = 'bundle'
        content_type = 'application/javascript'
    else:
        key_extension_suffix = ext
        content_type = mimetypes.guess_type(f'file.{ext}')[0] or 'application/octet-stream'
    
    hostname = os.getenv('HOSTNAME', 'http://localhost:8000')
    
    return {
        'hash': asset_hash,
        'key': key,
        'fileExtension': f'.{key_extension_suffix}',
        'contentType': content_type,
        'url': f"{hostname}/api/assets?asset={asset_file_path}&runtimeVersion={runtime_version}&platform={platform}"
    }


async def create_rollback_directive_async(update_bundle_path: str) -> Dict[str, Any]:
    """Create a rollback directive."""
    rollback_file_path = pathlib.Path(update_bundle_path) / 'rollback'
    
    if not rollback_file_path.exists():
        raise ValueError('No rollback found')
    
    stat = rollback_file_path.stat()
    commit_time = datetime.fromtimestamp(stat.st_birthtime if hasattr(stat, 'st_birthtime') else stat.st_ctime)
    
    return {
        'type': 'rollBackToEmbedded',
        'parameters': {
            'commitTime': commit_time.isoformat() + 'Z'
        }
    }


async def create_no_update_available_directive_async() -> Dict[str, Any]:
    """Create a no update available directive."""
    return {
        'type': 'noUpdateAvailable'
    }


async def get_metadata_async(update_bundle_path: str, runtime_version: str) -> Dict[str, Any]:
    """Get metadata for an update bundle."""
    metadata_path = pathlib.Path(update_bundle_path) / 'metadata.json'
    
    if not metadata_path.exists():
        raise ValueError(f'No update found with runtime version: {runtime_version}')
    
    with open(metadata_path, 'rb') as f:
        metadata_buffer = f.read()
    
    metadata_json = json.loads(metadata_buffer.decode('utf-8'))
    stat = metadata_path.stat()
    created_at = datetime.fromtimestamp(stat.st_birthtime if hasattr(stat, 'st_birthtime') else stat.st_ctime)
    update_id = create_hash(metadata_buffer, 'sha256', 'hex')
    
    return {
        'metadataJson': metadata_json,
        'createdAt': created_at.isoformat() + 'Z',
        'id': update_id
    }


async def get_expo_config_async(update_bundle_path: str, runtime_version: str) -> Any:
    """Get Expo config for an update bundle."""
    expo_config_path = pathlib.Path(update_bundle_path) / 'expoConfig.json'
    
    if not expo_config_path.exists():
        raise ValueError(f'No expo config json found with runtime version: {runtime_version}')
    
    with open(expo_config_path, 'r') as f:
        return json.load(f)


def convert_sha256_hash_to_uuid(value: str) -> str:
    """Convert SHA256 hash to UUID format."""
    return f"{value[0:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:32]}"
