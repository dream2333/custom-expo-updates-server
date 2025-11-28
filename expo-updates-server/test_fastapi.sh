#!/usr/bin/env bash
# Test script for FastAPI Expo Updates Server

set -e

echo "Starting FastAPI server..."
cd "$(dirname "$0")"
export HOSTNAME=http://localhost:8000
export PRIVATE_KEY_PATH=code-signing-keys/private-key.pem

# Start server in background
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Wait for server to start
sleep 3

echo "Running tests..."

# Test 1: Health check
echo "Test 1: Health check"
curl -s http://localhost:8000/health | grep -q "ok" && echo "✓ Health check passed" || echo "✗ Health check failed"

# Test 2: Root endpoint
echo "Test 2: Root endpoint"
curl -s http://localhost:8000/ | grep -q "Expo Updates Server" && echo "✓ Root endpoint passed" || echo "✗ Root endpoint failed"

# Test 3: Manifest endpoint (iOS)
echo "Test 3: Manifest endpoint (iOS)"
curl -s -H "expo-platform: ios" -H "expo-runtime-version: test" http://localhost:8000/api/manifest | grep -q "b15ed6d8-f39b-04ad-a248-fa3b95fd7e0e" && echo "✓ Manifest (iOS) passed" || echo "✗ Manifest (iOS) failed"

# Test 4: Manifest endpoint (Android)
echo "Test 4: Manifest endpoint (Android)"
curl -s -H "expo-platform: android" -H "expo-runtime-version: test" http://localhost:8000/api/manifest | grep -q "android-82adadb1fb6e489d04ad95fd79670deb.js" && echo "✓ Manifest (Android) passed" || echo "✗ Manifest (Android) failed"

# Test 5: Code signing
echo "Test 5: Code signing"
curl -s -H "expo-platform: ios" -H "expo-runtime-version: test" -H "expo-expect-signature: true" http://localhost:8000/api/manifest | grep -q "expo-signature" && echo "✓ Code signing passed" || echo "✗ Code signing failed"

# Test 6: Assets endpoint
echo "Test 6: Assets endpoint"
curl -s "http://localhost:8000/api/assets?asset=updates/test/1/bundles/ios-9d01842d6ee1224f7188971c5d397115.js&runtimeVersion=test&platform=ios" | grep -q "__BUNDLE_START_TIME__" && echo "✓ Assets endpoint passed" || echo "✗ Assets endpoint failed"

# Test 7: Rollback directive
echo "Test 7: Rollback directive"
curl -s -H "expo-platform: ios" -H "expo-runtime-version: testrollback" -H "expo-protocol-version: 1" -H "expo-embedded-update-id: 123" http://localhost:8000/api/manifest | grep -q "rollBackToEmbedded" && echo "✓ Rollback directive passed" || echo "✗ Rollback directive failed"

echo ""
echo "All tests completed!"

# Stop server
kill $SERVER_PID
wait $SERVER_PID 2>/dev/null || true

echo "Server stopped."
