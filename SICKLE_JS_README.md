# Sickle.js - Uniswap V3 Position Monitor

## Overview

`sickle.js` is a standalone Node.js utility script that queries Uniswap V3 positions directly from the NonfungiblePositionManager contract on Base Chain. It provides detailed position information including liquidity, tick ranges, and uncollected fees.

## Features

- Connects to Base Chain via Infura RPC endpoint
- Queries Uniswap V3 NonfungiblePositionManager contract
- Fetches position details for specific Token IDs (NFT numbers)
- Displays position information including:
  - Token0 and Token1 addresses
  - Fee tier
  - Tick lower and upper bounds
  - Current liquidity
  - Uncollected fees for both tokens

## Prerequisites

- Node.js v14 or higher
- npm (Node Package Manager)
- Valid Infura API key for Base Chain access
- Sickle wallet address with Uniswap V3 positions

## Installation

1. Install dependencies:
```bash
npm install
```

This will install the required `web3` package (v4.x).

## Configuration

The script currently uses the following hardcoded values:

- **RPC URL**: `https://base-mainnet.infura.io/v3/c0660434a7f448b0a99f1b5d049e95e6`
- **Sickle Address**: `0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B`
- **Position Manager**: `0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1` (Uniswap V3 on Base)
- **Token ID**: `4294280` (⚠️ **Hardcoded - will be made configurable in future update**)

### Important Note on TOKEN_ID

The Token ID is currently hardcoded in the script. This is a known limitation that will be addressed in a future update to support:
- Dynamic token ID discovery
- Multiple position monitoring
- Configuration file support

## Usage

Run the script:
```bash
node sickle.js
```

Or use the npm script:
```bash
npm run sickle
```

### Expected Output

When successful, the script outputs:
```
Current Block Number: 12345678

Your Sickle (0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B) owns 1 Uniswap V3 position(s)

Fetching details for Token ID #4294280...
=== Position Details ===
Token0: WETH @ 0x4200000000000000000000000000000000000006
Token1: USDC @ 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
Fee Tier: 0.3%
Tick Lower: -193980
Tick Upper: -193800
Liquidity: 123456789012345
Uncollected Fees (WETH): 0.001234
Uncollected Fees (USDC): 2.45

Success! This matches your VFAT.io CL-60 WETH/USDC 0.3% position.
You can now monitor fees, check in-range status, or build harvesting logic.
```

## Integration with Python Bot

This script demonstrates the logic for querying Uniswap V3 positions that can be integrated into the main Python bot. The `bot/position_reader.py` module uses similar contract interaction patterns.

### Python Test Script

A Python equivalent of `sickle.js` is available for troubleshooting:

**File:** `test_sickle_connection.py`

**Usage:**
```bash
python test_sickle_connection.py
```

**Features:**
- Tests Web3 connection to Base Chain
- Verifies contract deployment
- Tests balanceOf and positions calls
- Provides detailed error diagnostics
- Mirrors sickle.js functionality for comparison

**Use Cases:**
- Debugging contract call issues
- Verifying RPC endpoint connectivity
- Comparing behavior between Node.js and Python implementations
- Troubleshooting "Could not decode contract function call" errors

See [TROUBLESHOOTING_SICKLE.md](TROUBLESHOOTING_SICKLE.md) for complete troubleshooting guide.

## Technical Details

### Contract Interface

The script uses the Uniswap V3 NonfungiblePositionManager ABI with:
- `balanceOf(address)`: Returns number of positions owned by an address
- `positions(uint256)`: Returns detailed position data for a given Token ID

### Position Data Structure

The `positions()` function returns:
- `nonce`: Nonce for permit functionality
- `operator`: Approved operator address
- `token0`: Address of token0
- `token1`: Address of token1
- `fee`: Fee tier (in hundredths of a bip, e.g., 3000 = 0.3%)
- `tickLower`: Lower tick boundary
- `tickUpper`: Upper tick boundary
- `liquidity`: Current liquidity amount
- `feeGrowthInside0LastX128`: Fee growth inside position for token0
- `feeGrowthInside1LastX128`: Fee growth inside position for token1
- `tokensOwed0`: Uncollected fees for token0
- `tokensOwed1`: Uncollected fees for token1

## Known Limitations

1. **Hardcoded Token ID**: Currently set to `4294280`. Future versions will support dynamic token ID input.
2. **Single Position**: Only queries one position at a time.
3. **No Token Symbol Resolution**: Shows addresses instead of symbols (WETH/USDC are inferred).
4. **No Current Tick**: Does not fetch pool's current tick for in-range status.

## Future Enhancements

- [ ] Environment variable support for configuration
- [ ] Command-line arguments for Token ID
- [ ] Automatic discovery of all positions for a sickle address
- [ ] Pool current tick fetching for in-range detection
- [ ] Token symbol resolution via contract calls
- [ ] CSV/JSON export of position data
- [ ] Integration with Python bot for unified monitoring

## Troubleshooting

### Network Errors
```
Error: request to https://base-mainnet.infura.io/v3/... failed
```
- Check internet connectivity
- Verify Infura API key is valid
- Ensure Base Chain is supported by your Infura plan
- Try alternative RPC endpoints (see [TROUBLESHOOTING_SICKLE.md](TROUBLESHOOTING_SICKLE.md))

### Invalid Position
```
Error: execution reverted
```
- Verify the Token ID exists
- Confirm the token is owned by the specified sickle address
- Check if the position has been closed/burned

### Contract Call Errors
```
Could not decode contract function call to balanceOf
```
- Ensure contract is deployed at the address
- Verify you're connected to Base Chain (chain ID 8453)
- Check RPC endpoint is synced
- See comprehensive troubleshooting guide: [TROUBLESHOOTING_SICKLE.md](TROUBLESHOOTING_SICKLE.md)

### Testing Connection
Use the Python test script to diagnose issues:
```bash
python test_sickle_connection.py
```

This will verify:
- Web3 connection
- Contract deployment
- Function calls (balanceOf, positions)

For detailed troubleshooting steps, see [TROUBLESHOOTING_SICKLE.md](TROUBLESHOOTING_SICKLE.md).

## License

MIT License - See LICENSE file for details

## See Also

- Main Bot Documentation: [README.md](README.md)
- Position Reader Module: `bot/position_reader.py`
- Uniswap V3 Documentation: https://docs.uniswap.org/
