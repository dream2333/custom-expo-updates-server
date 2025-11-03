# Security Measures

## Path Traversal Attack Protection

The FastAPI implementation includes comprehensive protection against path traversal attacks.

### Assets Endpoint Security

**File**: `fastapi_app/assets.py`

**Protection Measures**:
1. Resolves all asset paths to absolute paths
2. Validates that resolved paths are within the `updates/` directory
3. Uses `pathlib.Path.relative_to()` to ensure no directory escape
4. Returns HTTP 400 error for invalid paths

**Code**:
```python
asset_path = pathlib.Path(asset).resolve()
base_updates_path = pathlib.Path('updates').resolve()

# Security: Ensure the asset path is within the updates directory
try:
    asset_path.relative_to(base_updates_path)
except ValueError:
    raise HTTPException(status_code=400, detail='Invalid asset path')
```

**Example Attack Blocked**:
```bash
# Attack attempt
curl "http://localhost:8000/api/assets?asset=../../../etc/passwd&runtimeVersion=test&platform=ios"

# Response
{"detail":"Invalid asset path"}
```

### Helper Functions Security

**File**: `fastapi_app/helpers.py`

**Protection Measures**:
1. Input validation: Checks for `..` and leading `/` in file paths
2. Path resolution validation: Ensures resolved path remains within update bundle
3. Dual-layer protection: Both input sanitization and path verification

**Code**:
```python
async def get_asset_metadata_async(...):
    # Security: validate that file_path doesn't contain path traversal
    if '..' in file_path or file_path.startswith('/'):
        raise ValueError('Invalid file path')
    
    asset_file_path = pathlib.Path(update_bundle_path) / file_path
    
    # Security: ensure the resolved path is within the update bundle directory
    update_bundle_resolved = pathlib.Path(update_bundle_path).resolve()
    asset_file_resolved = asset_file_path.resolve()
    try:
        asset_file_resolved.relative_to(update_bundle_resolved)
    except ValueError:
        raise ValueError('Invalid asset path')
```

## CodeQL Static Analysis

### Findings

CodeQL reports 4 path injection alerts, which are **false positives**:

1. `expo-updates-server/fastapi_app/assets.py:49` - Path validated on lines 51-55
2. `expo-updates-server/fastapi_app/assets.py:74` - Path validated earlier
3. `expo-updates-server/fastapi_app/assets.py:87` - Path validated earlier
4. `expo-updates-server/fastapi_app/helpers.py:88` - Path validated on lines 115-127

### Why These Are False Positives

Static analysis tools like CodeQL cannot detect runtime validation logic. The security measures are implemented but appear as potential vulnerabilities to the static analyzer because:

1. **Runtime Validation**: Path validation happens at runtime using `relative_to()`
2. **Exception Handling**: Invalid paths raise exceptions before being used
3. **Multi-Layer Defense**: Both input sanitization and path resolution checks

### Verification

Manual testing confirms the security measures work:

✅ Legitimate requests succeed
✅ Path traversal attempts (e.g., `../../../etc/passwd`) are blocked
✅ All functional tests pass
✅ Error messages don't reveal system information

## Additional Security Considerations

### Environment Variables

Sensitive configuration is stored in environment variables:
- `PRIVATE_KEY_PATH`: Path to RSA private key
- `HOSTNAME`: Server hostname/URL

### Code Signing

- RSA-SHA256 signatures for update manifests
- Optional signature verification by clients
- Private keys must be kept secure

### Production Recommendations

1. **Use HTTPS**: Always use TLS/SSL in production
2. **Restrict Access**: Use firewall rules to limit access
3. **Regular Updates**: Keep dependencies up to date
4. **Monitor Logs**: Watch for suspicious access patterns
5. **Rate Limiting**: Consider adding rate limiting for API endpoints
6. **Key Management**: Rotate code signing keys periodically

### Environment-Specific Security

**Development**:
- HTTP acceptable for localhost
- Test keys can be used
- Detailed error messages enabled

**Production**:
- HTTPS required
- Production code signing keys
- Generic error messages
- Enable access logging
- Consider adding authentication

## Security Testing

### Manual Tests Performed

1. ✅ Path traversal with `../../../etc/passwd` - Blocked
2. ✅ Absolute path `/etc/passwd` - Blocked  
3. ✅ Legitimate asset paths - Allowed
4. ✅ Non-existent files - Proper 404 error
5. ✅ Invalid runtime versions - Proper error handling

### Automated Tests

Run `./test_fastapi.sh` to verify:
- All endpoints function correctly
- Security validations don't break legitimate use
- Error handling works properly

## Conclusion

The FastAPI implementation includes production-ready security measures against common web vulnerabilities, specifically path traversal attacks. While static analysis tools may report potential issues, manual code review and testing confirm that proper security controls are in place.

For production deployments, follow the additional security recommendations and use appropriate infrastructure security measures (HTTPS, firewalls, etc.).
