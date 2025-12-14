# Agents Documentation

This document provides additional context and coding standards for AI agents (including GitHub Copilot) working on this repository.

## Project Philosophy

This delta-neutral hedging bot prioritizes **safety, transparency, and reliability** above all else. When working on this codebase:

1. **Safety First**: Financial systems require extreme care. Double-check calculations, validate inputs, and maintain all safety limits.
2. **Fail Safely**: Errors should never result in unintended trades or positions. Log errors and halt rather than proceeding with uncertain state.
3. **Transparency**: All trading decisions should be logged with complete context for debugging and audit purposes.
4. **Simplicity**: Clear, maintainable code is more valuable than clever optimizations in financial systems.

## Core Principles

### Financial Accuracy
- Delta calculations must account for concentrated liquidity ranges (not simple 50/50 LP)
- Token amounts must respect proper decimal places (USDC=6, WETH=18, etc.)
- Price conversions must be verified against reliable oracles
- Impermanent loss calculations should consider fees earned
- All financial calculations should include unit tests with known correct answers

### Risk Management
- Never bypass configured safety limits (`max_position_size`, `delta_threshold`, etc.)
- Always validate available margin before placing orders
- Implement slippage protection on all trades
- Respect daily trade limits to prevent runaway behavior
- Log risk metrics (VaR, IL, gamma) with every position update

### Configuration Management
- Environment variables override JSON config (production security)
- All secrets MUST be in `.env` (never in code or JSON)
- Provide sensible defaults for non-sensitive configuration
- Validate configuration on startup (fail fast with clear error messages)
- Document all config options in `.env.example` with examples

### Error Handling Strategy
```python
# Good: Specific exception handling with context
try:
    position = await fetch_position(position_id)
except Web3Exception as e:
    logger.error(f"Failed to fetch position {position_id}: {e}")
    return None
except Exception as e:
    logger.critical(f"Unexpected error fetching position {position_id}: {e}")
    raise

# Bad: Silent failures or catching all exceptions without logging
try:
    position = await fetch_position(position_id)
except:
    pass
```

### Logging Standards
```python
# Use appropriate log levels:
logger.debug("Raw API response: {response}")      # Verbose debugging info
logger.info("Found 3 LP positions, total value: $10,000")  # Normal operation
logger.warning("Delta threshold exceeded: 0.15 > 0.10")    # Actionable warnings
logger.error("Failed to execute hedge: insufficient margin")  # Recoverable errors
logger.critical("Invalid private key configuration")  # Fatal errors requiring restart
```

## Code Quality Standards

### Type Safety
Always use type hints to make code self-documenting and catch errors early:

```python
from typing import List, Dict, Optional, Tuple
from decimal import Decimal

async def calculate_position_delta(
    position: Dict[str, any],
    current_price: Decimal
) -> Tuple[Decimal, Dict[str, Decimal]]:
    """
    Calculate delta exposure for a concentrated liquidity position.
    
    Args:
        position: Position data with liquidity, tick range, tokens
        current_price: Current price of token0 in terms of token1
        
    Returns:
        Tuple of (delta_value, breakdown_dict)
    """
    # Implementation
    pass
```

### Async Best Practices
- Use `async`/`await` for all I/O operations (RPC calls, API requests)
- Use `asyncio.gather()` for parallel operations when safe
- Handle task cancellation gracefully
- Close all sessions and connections properly

```python
# Good: Parallel fetching with proper error handling
positions = await asyncio.gather(
    fetch_uniswap_positions(),
    fetch_aerodrome_positions(),
    fetch_vfat_positions(),
    return_exceptions=True
)

# Process results and handle any exceptions
for i, result in enumerate(positions):
    if isinstance(result, Exception):
        logger.error(f"Failed to fetch from source {i}: {result}")
```

### Testing Standards
Every module should have corresponding tests:

```
bot/position_reader.py → tests/test_position_reader.py
bot/hedging_executor.py → tests/test_hedging_executor.py
```

Test structure:
```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

class TestPositionReader:
    @pytest.mark.asyncio
    async def test_fetch_uniswap_positions_success(self):
        """Test successful position fetching from Uniswap V3."""
        # Arrange: Set up mocks and test data
        mock_web3 = Mock()
        mock_contract = Mock()
        # ... setup
        
        # Act: Call the function
        positions = await position_reader.fetch_positions()
        
        # Assert: Verify results
        assert len(positions) == 2
        assert positions[0]['protocol'] == 'uniswap'
        
    @pytest.mark.asyncio
    async def test_fetch_positions_network_error(self):
        """Test handling of network errors during position fetch."""
        # Test error handling
        pass
```

## Architecture Patterns

### Module Responsibilities

**position_reader.py**: Read-only operations
- Fetch positions from various protocols
- Parse and normalize position data
- Calculate current position values
- NO trading or state modification

**hedging_executor.py**: Trading operations
- Execute hedge orders on Hyperliquid
- Manage open positions
- Handle order placement and cancellation
- Respect all safety limits

**risk_management.py**: Analytics and calculations
- Calculate risk metrics (IL, VaR, gamma)
- Assess position health
- Compute optimal hedge ratios
- NO trading execution

**main.py**: Orchestration
- Coordinate between modules
- Implement main event loop
- Handle shutdown gracefully
- Aggregate logging and reporting

### Data Flow
```
1. position_reader → Fetch positions from protocols
2. risk_management → Calculate delta, IL, risk metrics
3. main → Decide if hedging needed based on thresholds
4. hedging_executor → Execute hedge if needed
5. main → Log results and wait for next cycle
```

## Common Integration Points

### Web3 Provider Setup
```python
from web3 import Web3
from web3.middleware import geth_poa_middleware

w3 = Web3(Web3.HTTPProvider(rpc_url))
# Base chain and other L2s may need PoA middleware
w3.middleware_onion.inject(geth_poa_middleware, layer=0)
```

### Hyperliquid API Authentication
- Uses private key for signing (not API key/secret pattern)
- Requires specific message formatting and signing
- Testnet and mainnet use different endpoints
- Always verify testnet flag before trading

### Position Data Format
Standardized format across all protocols:
```python
{
    'id': 'protocol-tokenId',
    'protocol': 'uniswap|aerodrome|vfat',
    'token0': 'WETH',
    'token1': 'USDC',
    'token0_address': '0x...',
    'token1_address': '0x...',
    'liquidity': Decimal('1000000'),
    'tick_lower': -887220,
    'tick_upper': 887220,
    'fee_tier': 3000,  # 0.3%
    'token0_amount': Decimal('1.5'),
    'token1_amount': Decimal('3000'),
    'uncollected_fees_token0': Decimal('0.001'),
    'uncollected_fees_token1': Decimal('2.5'),
}
```

## Security Checklist

Before committing code that handles:

**Private Keys / Secrets**
- [ ] Uses environment variables only
- [ ] No hardcoded values
- [ ] Not logged (even at DEBUG level)
- [ ] Proper key validation on startup

**Trading Operations**
- [ ] Validates order direction (long vs short)
- [ ] Checks position size limits
- [ ] Implements slippage protection
- [ ] Logs order details before execution
- [ ] Handles execution failures gracefully

**Configuration**
- [ ] Validates all numeric limits (no negative values where inappropriate)
- [ ] Checks wallet addresses are valid
- [ ] Verifies RPC URLs are accessible
- [ ] Tests with both testnet and mainnet configs

## Performance Considerations

### Async Operations
- Fetch positions from multiple protocols in parallel
- Cache token prices for short periods (60s)
- Reuse Web3 connections
- Use connection pooling for HTTP clients

### Rate Limiting
- Respect RPC provider rate limits (especially Infura free tier)
- Implement exponential backoff for retries
- Cache immutable data (contract addresses, ABIs)

### Resource Usage
- Close all aiohttp sessions properly
- Limit concurrent API calls
- Avoid memory leaks in long-running process
- Log memory usage periodically

## Deployment Considerations

### AWS Environment
- Runs on t3.small instance (2 vCPU, 2GB RAM)
- Uses systemd service for process management
- Logs to both file and systemd journal
- Environment variables from `/etc/environment` or service file

### Monitoring
- Should run continuously with minimal intervention
- Key metrics: position count, delta, hedge size, PnL
- Alerts on: critical errors, high IL, failed trades
- Daily performance summary in logs

### Updates
- Test on testnet before deploying to production
- Use blue-green deployment approach
- Back up configuration before changes
- Monitor closely after deployment

## Development Tips

### Quick Start for Changes
```bash
# 1. Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure for testnet
cp .env.example .env
# Edit .env: set HYPERLIQUID_TESTNET=true

# 3. Run tests
python -m pytest tests/ -v

# 4. Test your changes
python -m bot.main
```

### Debugging
```python
# Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use python debugger
import pdb; pdb.set_trace()

# Or use breakpoint() in Python 3.7+
breakpoint()
```

### Common Issues
1. **"Web3 connection failed"**: Check RPC_URL in .env
2. **"Invalid private key"**: Verify HYPERLIQUID_PRIVATE_KEY format (0x + 64 hex chars)
3. **"No positions found"**: Verify wallet address has LP positions on correct network
4. **"Insufficient margin"**: Check Hyperliquid account has funds

## Resources for Contributors

### Protocol Documentation
- [Uniswap V3 Docs](https://docs.uniswap.org/protocol/concepts/V3-overview/concentrated-liquidity)
- [Hyperliquid Docs](https://hyperliquid.gitbook.io/)
- [Web3.py Docs](https://web3py.readthedocs.io/)

### Financial Concepts
- Concentrated Liquidity: Provides liquidity in specific price ranges
- Impermanent Loss: Loss vs holding tokens due to price changes
- Delta: Directional exposure (positive = long, negative = short)
- Gamma: Rate of change of delta (convexity risk)
- VaR: Value at Risk - potential loss at confidence level

### Testing Tools
- pytest: Unit testing framework
- pytest-asyncio: Async test support
- unittest.mock: Mocking for tests
- Hyperliquid testnet: Safe environment for testing trades

## Questions or Clarifications?

When implementing changes:
1. **Read the relevant module first** - understand existing patterns
2. **Check tests for examples** - see how similar functionality is tested
3. **Respect safety limits** - financial systems require conservative defaults
4. **Log extensively** - debugging production issues requires good logs
5. **Test on testnet** - always verify trading logic safely first

Remember: This bot handles real financial positions. When in doubt, choose the safer, more conservative approach.
