# Uniswap V3 Delta-Neutral Hedging Bot

A sophisticated Python bot that implements delta-neutral hedging strategies for concentrated liquidity positions in Uniswap V3 and Aerodrome, with dynamic hedging execution via Hyperliquid.

## Overview

This bot monitors liquidity positions across Uniswap V3 and Aerodrome (via vfat.io sickle contracts), calculates delta exposure, and automatically executes hedging trades on Hyperliquid to maintain a delta-neutral portfolio. It includes comprehensive risk management features including impermanent loss tracking, fee analysis, and downside risk calculations.

## Features

- **Multi-Protocol Position Reading**: Fetches positions from Uniswap V3, Aerodrome, and vfat.io sickle contracts
- **Dynamic Delta Calculation**: Real-time delta calculation for concentrated liquidity positions
- **Automated Hedging**: Executes hedging trades on Hyperliquid to maintain delta neutrality
- **Risk Management**: 
  - Impermanent loss calculation and monitoring
  - Fee tracking and PnL analysis
  - Value at Risk (VaR) calculations
  - Downside risk assessment
  - Gamma exposure tracking
- **Safety Features**:
  - Configurable delta thresholds
  - Position size limits
  - Daily trade limits
  - Slippage protection
  - Emergency position closing
- **Comprehensive Logging**: Detailed logging of all operations and risk metrics

## Architecture

```
/delta-neutral-bot
├── /bot
│   ├── __init__.py
│   ├── position_reader.py      # Fetches positions from vfat.io, Uniswap, and Aerodrome
│   ├── hedging_executor.py     # Executes hedging trades on Hyperliquid
│   ├── risk_management.py      # Risk calculations and metrics
│   └── main.py                 # Main bot orchestration and entry point
├── /tests                      # Unit tests
├── requirements.txt            # Python dependencies
├── config.json                 # Configuration file
├── README.md                   # This file
└── LICENSE                     # MIT License
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Ethereum node access (Infura, Alchemy, or local node)
- Hyperliquid account and API credentials
- Wallet with LP positions in Uniswap V3 or Aerodrome

### Setup

1. Clone the repository:
```bash
git clone https://github.com/TomV77/uniswap-v3-delta-neutral-bot.git
cd uniswap-v3-delta-neutral-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the bot:
```bash
cp config.json config.json.local
# Edit config.json.local with your settings
```

## Configuration

Edit `config.json` with your settings:

### Essential Settings

```json
{
  "wallet_address": "0xYourWalletAddress",
  "rpc_url": "https://mainnet.infura.io/v3/YOUR_KEY",
  "hyperliquid_api_key": "your_api_key",
  "hyperliquid_api_secret": "your_api_secret",
  "hyperliquid_testnet": true
}
```

### Contract Addresses

```json
{
  "uniswap_v3_nft_address": "0xC36442b4a4522E871399CD717aBDD847Ab11FE88",
  "aerodrome_nft_address": "0xAerodromeNFTPositionManager",
  "sickle_contract_address": "0xSickleContractAddress"
}
```

### Risk Parameters

```json
{
  "delta_threshold": 0.1,           // Maximum delta before rebalancing
  "rebalance_threshold": 0.05,      // Delta change triggering rebalance
  "max_impermanent_loss": 0.05,     // 5% maximum IL tolerance
  "min_fee_coverage": 1.5,          // Fees should cover IL by 1.5x
  "slippage_tolerance": 0.005       // 0.5% slippage tolerance
}
```

### Trading Limits

```json
{
  "max_position_size": 10.0,        // Maximum single position size
  "min_order_size": 0.01,           // Minimum order size
  "max_daily_trades": 100,          // Daily trade limit
  "update_interval_seconds": 60     // Update frequency
}
```

See `config.json` for complete configuration options with detailed descriptions.

## Usage

### Running the Bot

Basic usage:
```bash
python -m bot.main
```

With custom config file:
```bash
python -m bot.main /path/to/config.json
```

### Bot Workflow

1. **Position Reading**: Fetches all LP positions from configured sources
2. **Delta Calculation**: Calculates net directional exposure
3. **Risk Assessment**: Evaluates IL, fees, VaR, and other risk metrics
4. **Hedge Decision**: Determines if hedging is needed based on thresholds
5. **Execution**: Places hedge orders on Hyperliquid if required
6. **Monitoring**: Logs performance and waits for next cycle

### Example Output

```
================================================================================
Starting new bot cycle
================================================================================
Fetching positions...
Found 3 positions

Position: uniswap-12345
  Protocol: uniswap
  Pair: ETH/USDC
  Value: $10000
  Delta: 0.15
  IL: 2.34%
  Fees: $234.56
  Net PnL: $180.22
  Risk Level: MEDIUM

Total LP Delta: 0.15
Current Hedge: -0.12
Net Delta: 0.03

Position is within delta threshold, no hedging needed

================================================================================
PERFORMANCE REPORT
================================================================================
Total Position Value: $30000
Total Impermanent Loss: $701.20
Total Fees Earned: $1023.45
Total Net PnL: $322.25
Total Hedges Executed: 15
================================================================================
```

## Integration Details

### vfat.io Sickle Contracts

The bot integrates with vfat.io's sickle contracts to fetch position data:

- API endpoint: `https://api.vfat.io/positions/{wallet_address}`
- Provides aggregated position data across multiple protocols
- Includes liquidity, token amounts, fees, and price information

### Uniswap V3

Direct integration with Uniswap V3 NFT Position Manager:

- Contract: `0xC36442b4a4522E871399CD717aBDD847Ab11FE88` (Ethereum mainnet)
- Fetches positions via `positions()` function
- Calculates amounts from liquidity and tick ranges

### Aerodrome

Integration with Aerodrome's concentrated liquidity positions:

- Uses similar NFT position manager interface
- Supports Base network deployment
- Compatible with Uniswap V3-style positions

### Hyperliquid

Hedging execution via Hyperliquid's perpetual futures:

- REST API for order placement
- WebSocket support for real-time updates (future enhancement)
- Supports both testnet and mainnet
- Limit orders with slippage protection

## Risk Management

### Delta Neutrality

The bot maintains delta neutrality by:

1. Calculating total delta across all LP positions
2. Monitoring existing hedge positions on Hyperliquid
3. Adjusting hedges when net delta exceeds configured threshold
4. Using limit orders to minimize slippage

### Impermanent Loss

IL calculation considers:

- Concentrated liquidity range effects
- Price movements relative to entry
- Current position in relation to range bounds
- Fee generation to offset IL

### Value at Risk (VaR)

Calculates downside risk using:

- Historical volatility estimates
- Configurable confidence levels (95%, 99%)
- Time horizon adjustments
- Position value exposure

## Safety Features

### Trading Limits

- Maximum position size per trade
- Daily trade count limits
- Minimum order size requirements
- Slippage tolerance controls

### Emergency Controls

- Graceful shutdown with signal handling
- Optional position closing on shutdown
- Emergency close all positions function
- Comprehensive error handling and logging

### Monitoring

- Real-time logging to console and file
- Performance tracking and reporting
- Risk level assessment (LOW/MEDIUM/HIGH)
- PnL tracking across all positions

## Testing

Run unit tests:
```bash
python -m pytest tests/
```

Run specific test modules:
```bash
python -m pytest tests/test_position_reader.py
python -m pytest tests/test_hedging_executor.py
python -m pytest tests/test_risk_management.py
```

## Development

### Adding New Protocols

To add support for new protocols:

1. Extend `PositionReader._fetch_[protocol]_positions()`
2. Implement position parsing logic
3. Add contract addresses to config
4. Update documentation

### Custom Risk Metrics

To add custom risk calculations:

1. Extend `RiskManagement` class
2. Add new metrics to `RiskMetrics` dataclass
3. Update risk assessment logic
4. Modify thresholds in config

## Troubleshooting

### Common Issues

**Bot not finding positions**
- Verify wallet address in config
- Check RPC URL is accessible
- Ensure contracts are deployed on correct network

**Hedge execution failing**
- Verify Hyperliquid API credentials
- Check position size limits
- Ensure sufficient margin on Hyperliquid
- Review slippage tolerance settings

**High impermanent loss**
- Consider wider position ranges
- Increase hedging frequency
- Adjust delta threshold
- Review fee coverage ratio

## Best Practices

1. **Start with Testnet**: Always test on Hyperliquid testnet first
2. **Small Positions**: Start with small position sizes to test behavior
3. **Monitor Closely**: Watch the bot for first few hours/days
4. **Regular Backups**: Keep backups of config and logs
5. **Review Limits**: Regularly review and adjust safety limits
6. **Fee Awareness**: Consider gas fees and Hyperliquid trading fees
7. **Diversification**: Don't put all capital in one strategy

## Security Considerations

- **Never commit API keys**: Use environment variables or separate config files
- **Secure RPC access**: Use authenticated RPC endpoints
- **Private key safety**: Bot doesn't handle private keys directly
- **Monitor access**: Regularly review API key permissions
- **Update dependencies**: Keep dependencies up to date for security patches

## Performance Optimization

- Adjust `update_interval_seconds` based on volatility
- Use WebSocket connections for real-time data (future enhancement)
- Implement caching for token prices and contract data
- Batch position queries when possible

## Limitations

- Simplified delta calculation (can be enhanced with Greeks)
- Basic volatility estimation (could use external oracles)
- Limited to supported protocols (extensible)
- Requires manual monitoring for optimal performance
- Does not account for gas costs in profitability calculations

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] Advanced Greeks calculation (theta, vega)
- [ ] Multi-chain support (Polygon, Arbitrum, etc.)
- [ ] Auto-compounding of earned fees
- [ ] Machine learning for optimal rebalancing
- [ ] Dashboard UI for monitoring
- [ ] Telegram/Discord alerts
- [ ] Backtesting framework
- [ ] Portfolio optimization

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Disclaimer

This software is for educational purposes only. Use at your own risk. The authors are not responsible for any financial losses incurred through the use of this bot. Always test thoroughly with small amounts before deploying with significant capital.

Cryptocurrency trading and liquidity provision carry significant risks including but not limited to impermanent loss, smart contract risks, and market volatility. Never invest more than you can afford to lose.

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/TomV77/uniswap-v3-delta-neutral-bot/issues
- Documentation: See this README and inline code documentation

## Acknowledgments

- Uniswap V3 team for the concentrated liquidity innovation
- Hyperliquid team for the derivatives platform
- vfat.io for sickle contract infrastructure
- Web3.py and aiohttp communities

---

**Note**: This is a sophisticated trading bot. Ensure you understand the strategies, risks, and code before using with real funds.
