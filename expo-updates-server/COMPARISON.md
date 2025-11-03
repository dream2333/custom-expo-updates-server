# FastAPI vs Next.js Implementation Comparison

## Overview

This document compares the FastAPI (Python) and Next.js (TypeScript) implementations of the Expo Updates Server.

## Similarities

Both implementations:
- ✅ Implement the Expo Updates protocol specification
- ✅ Support manifest endpoint (`/api/manifest`)
- ✅ Support assets endpoint (`/api/assets`)
- ✅ Support code signing with RSA-SHA256
- ✅ Support rollback directives
- ✅ Support NoUpdateAvailable directives
- ✅ Use multipart/mixed responses for manifests
- ✅ Support both iOS and Android platforms
- ✅ Support protocol versions 0 and 1
- ✅ Share the same `updates/` directory structure
- ✅ Use the same code signing keys

## Differences

| Feature | Next.js | FastAPI |
|---------|---------|---------|
| **Language** | TypeScript | Python |
| **Default Port** | 3000 | 8000 |
| **Runtime** | Node.js | Python 3.8+ |
| **Framework** | Next.js 15.5.3 | FastAPI 0.115.6 |
| **Server** | Next.js dev server | Uvicorn |
| **Auto Docs** | ❌ | ✅ (Swagger UI at /docs) |
| **Dependencies** | npm/yarn | pip |
| **Config File** | `.env.local` | `.env.fastapi` |
| **Start Script** | `yarn dev` | `./run_fastapi.sh` or `yarn dev:fastapi` |
| **Test Suite** | Jest | Custom bash script |

## Performance Considerations

### Next.js
- Better for JavaScript/TypeScript teams
- Integrates well with React-based admin panels
- Hot module reloading in development
- Can leverage Next.js features (SSR, API routes, etc.)

### FastAPI
- Generally faster for pure API workloads
- Lower memory footprint
- Easier to deploy on Linux servers
- Built-in async support
- Auto-generated OpenAPI documentation
- Simpler to containerize

## File Structure Comparison

### Next.js
```
expo-updates-server/
├── pages/
│   └── api/
│       ├── manifest.ts
│       └── assets.ts
├── common/
│   └── helpers.ts
└── package.json
```

### FastAPI
```
expo-updates-server/
├── fastapi_app/
│   ├── __init__.py
│   ├── main.py
│   ├── manifest.py
│   ├── assets.py
│   └── helpers.py
└── requirements.txt
```

## API Endpoint Compatibility

Both implementations are 100% compatible with the Expo Updates protocol. You can:
- Switch between implementations without changing the client
- Use the same update bundles
- Use the same code signing keys
- Use the same configuration (with port adjustment)

## Deployment Options

### Next.js
- Vercel (native platform)
- Node.js hosting (AWS, GCP, Azure)
- Docker containers
- PM2 for process management

### FastAPI
- Any ASGI server (Uvicorn, Gunicorn + Uvicorn)
- Docker containers (smaller images)
- Systemd services
- Kubernetes deployments
- AWS Lambda (with Mangum)

## When to Use Which?

### Use Next.js if:
- You're already using Next.js or React
- Your team is more comfortable with TypeScript/JavaScript
- You want to add a web UI for managing updates
- You're deploying to Vercel

### Use FastAPI if:
- You prefer Python
- You want built-in API documentation
- You need maximum performance
- You're deploying to Linux servers
- You want simpler deployment options
- You're building other Python-based tools

## Migration Between Implementations

To switch from one implementation to the other:

1. Keep the `updates/` directory (shared between both)
2. Keep the `code-signing-keys/` directory (shared between both)
3. Update the port in your Expo client's `app.json` if needed
4. Start the new server implementation

No changes to the client app are needed!
