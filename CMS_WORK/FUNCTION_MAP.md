# Function Map — Daily Compound Harvester CMS

## Core flow

User
→ Frontend UI
→ FastAPI routes
→ CMS Engine / modules
→ Database
→ Response

## Backend modules

### main.py
- Application bootstrap
- Middleware
- Authentication flows
- API routing
- Market data orchestration
- Trading endpoints
- Strategy execution

### cms_core.py
- User model
- Plugin management
- CMS data layer

### bot.py
- HFT simulation lifecycle
- Start/stop control

### hft_brain.py
- Production HFT logic
- AI decision layer

### modules/strategy_manager.py
- Strategy loading
- Strategy configuration
- Execution routing

### market_history.py
- OHLCV loading
- Candle storage
- News loading
- Sentiment processing

### risk_management.py
- Risk parameters
- Position protection

## Main data flows

Market:
Exchange API → CCXT → market_history → strategy_manager → signal

Trading:
User/API → validation → risk_manager → bot → exchange adapter

Learning:
Results → learning_memory → AI analysis → strategy suggestions

## Audit status

This map is being expanded during code review.
