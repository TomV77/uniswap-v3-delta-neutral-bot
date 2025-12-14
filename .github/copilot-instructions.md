# GitHub Copilot Instructions

This file provides guidance to GitHub Copilot coding agent for working effectively in this repository.

## Repository Overview

This is a Python-based delta-neutral hedging bot for Uniswap V3 and Aerodrome liquidity positions. The bot:
- Monitors LP positions across multiple protocols (Uniswap V3, Aerodrome, vfat.io sickle contracts)
- Calculates delta exposure and risk metrics
- Executes hedging trades on Hyperliquid to maintain delta neutrality
- Implements comprehensive risk management (IL tracking, VaR, gamma exposure)

## Code Standards

### Python Style
- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Use async/await for I/O operations (Web3, API calls)
- Keep functions focused and single-purpose
- Add docstrings to all classes and public methods

### Project Structure
```
/bot
  ├── __init__.py
  ├── config.py              # Configuration management
  ├── position_reader.py     # Fetches LP positions from protocols
  ├── hedging_executor.py    # Executes hedging trades on Hyperliquid
  ├── risk_management.py     # Risk calculations and metrics
  └── main.py               # Main bot orchestration
/tests                      # Unit tests matching bot structure
```

### Configuration
- Support both `.env` files (production) and `config.json` (development)
- All sensitive data (API keys, private keys) MUST use environment variables
- Never hardcode credentials or wallet addresses
- Use `.env.example` as template for required environment variables

### Error Handling
- Use try/except blocks for all external API calls
- Log errors with appropriate context using the logging module
- Handle network failures gracefully with retries where appropriate
- Fail safely - never leave partial hedge positions

### Dependencies
- Web3.py for blockchain interactions
- aiohttp for async HTTP requests
- pytest for testing
- python-dotenv for environment management
- Keep dependencies minimal and well-maintained

## Development Workflow

### Before Making Changes
1. Read and understand the relevant module's purpose
2. Check existing tests for similar functionality
3. Understand the bot's safety mechanisms (position limits, delta thresholds)
4. Review related configuration options in `config.json` and `.env.example`

### Testing Requirements
- Write unit tests for all new functionality
- Use pytest-asyncio for async test functions
- Mock external API calls (Web3, Hyperliquid, vfat.io)
- Test edge cases: network failures, invalid responses, zero positions
- Run tests before committing: `python -m pytest tests/`

### Code Changes
- Make minimal, focused changes
- Preserve existing safety checks and risk management logic
- Update documentation if public interfaces change
- Update `.env.example` if new configuration is added
- Maintain backward compatibility when possible

## Critical Safety Considerations

### Security
- **NEVER** commit private keys, API secrets, or wallet addresses
- All credentials MUST be in `.env` (not tracked by git)
- Validate all user inputs and configuration values
- Use secure randomness for any cryptographic operations
- Review Hyperliquid order parameters to prevent fat-finger trades

### Risk Management
- Respect configured limits: `max_position_size`, `max_daily_trades`, `slippage_tolerance`
- Always check delta threshold before executing trades
- Validate position sizes against available margin
- Log all trade decisions with full context
- Handle shutdown gracefully (`close_positions_on_shutdown` setting)

### Financial Safety
- Double-check order direction (long/short) in hedging logic
- Verify token decimals and units in delta calculations
- Ensure slippage protection is always active
- Test on Hyperliquid testnet before mainnet deployment
- Start with small position sizes in production

## Common Tasks

### Adding Support for New Protocol
1. Add new method in `PositionReader` class
2. Parse positions into standard format (dict with: id, protocol, token0, token1, liquidity, etc.)
3. Update delta calculation if needed
4. Add contract address to configuration
5. Write tests with mocked contract responses
6. Update README.md with new protocol details

### Modifying Risk Calculations
1. Work in `risk_management.py` module
2. Add new metrics to `RiskMetrics` dataclass
3. Update calculation methods
4. Add corresponding configuration thresholds
5. Update logging to include new metrics
6. Test with various market conditions (high volatility, IL scenarios)

### Changing Hedging Logic
1. Work in `hedging_executor.py` module
2. Validate changes don't bypass safety limits
3. Test order parameters carefully
4. Ensure proper error handling for failed trades
5. Log all order details before execution
6. Consider edge cases (low liquidity, extreme prices)

## Testing Approach

### Unit Tests
- Mock all external dependencies (Web3 providers, API clients)
- Test individual functions in isolation
- Cover success cases and failure modes
- Use realistic test data from actual protocols

### Integration Testing
- Use Hyperliquid testnet for end-to-end testing
- Test with small positions first
- Monitor for at least one full cycle before production
- Verify all logging and error handling

### Test Data
- Use example responses from vfat.io, Uniswap, Aerodrome
- Include edge cases: empty positions, extreme prices, zero liquidity
- Test configuration validation

## Documentation

### Code Comments
- Comment complex financial calculations
- Explain non-obvious risk management logic
- Document assumptions (e.g., concentrated liquidity formulas)
- Add references to Uniswap V3 whitepaper for delta calculations

### README Updates
- Keep feature list current
- Update configuration examples when adding new options
- Document new protocols or integrations
- Maintain troubleshooting section

### Changelog
- Document breaking changes
- Note new features and bug fixes
- Include migration instructions for config changes

## Common Pitfalls to Avoid

1. **Token Ordering**: Uniswap V3 uses token0/token1 ordering - verify this in calculations
2. **Decimals**: Different tokens have different decimals (USDC=6, ETH=18)
3. **Price Ranges**: Concentrated liquidity positions have defined tick ranges
4. **Async Context**: Ensure proper async/await usage with Web3 and aiohttp
5. **Configuration Precedence**: Environment variables override config.json
6. **Gas Estimation**: Account for gas costs in profitability calculations
7. **Testnet vs Mainnet**: Always verify which network is being used

## Resources

- Uniswap V3 Whitepaper: https://uniswap.org/whitepaper-v3.pdf
- Hyperliquid API Docs: https://hyperliquid.gitbook.io/
- Web3.py Docs: https://web3py.readthedocs.io/
- vfat.io: https://vfat.io/

## Questions?

When unsure about implementation details:
1. Check existing code patterns in the module
2. Review related tests for examples
3. Consult the README.md for architectural guidance
4. Verify against protocol documentation (Uniswap V3, Hyperliquid)
5. Start conservatively - add safety checks first, optimize later
