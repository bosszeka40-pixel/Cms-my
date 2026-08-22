# System Connection Map

## Architecture

Frontend
↓
FastAPI application
↓
CMS Core
↓
Modules
↓
Storage / External APIs

## External connections

CCXT
- Market exchange communication
- Public OHLCV data
- Trading adapter layer

Social OAuth
- Google login
- GitHub login
- Telegram login

Deployment
- Docker configuration
- Cloud deployment targets

## Security checkpoints

- Production SECRET_KEY required
- Exchange keys should not be persisted
- Live trading requires explicit confirmation
- Sandbox testing before real orders

## Pending audit

- Verify every dependency
- Verify database boundaries
- Verify error handling
- Verify permissions
