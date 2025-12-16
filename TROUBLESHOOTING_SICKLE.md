# Troubleshooting Guide: Sickle Contract Connection Issues

This guide helps diagnose and resolve common issues when connecting to Uniswap V3 / Aerodrome positions via Sickle contracts.

## Table of Contents
1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Error Messages](#common-error-messages)
3. [Environment Setup](#environment-setup)
4. [Testing Tools](#testing-tools)
5. [Step-by-Step Troubleshooting](#step-by-step-troubleshooting)

---

## Quick Diagnostics

### Test Your Configuration

**Using Python:**
```bash
python test_sickle_connection.py
```

**Using Node.js:**
```bash
npm run sickle
```

Both scripts will test:
- ✅ RPC endpoint connectivity
- ✅ Current block number (confirms chain sync)
- ✅ Contract deployment verification
- ✅ balanceOf function call
- ✅ positions function call

---

## Common Error Messages

### Error 1: "Could not decode contract function call to balanceOf(address)"

**Symptom:**
```
Could not decode contract function call to balanceOf()
Error type: BadFunctionCallOutput
Could not transact with/call contract function, is contract deployed correctly and chain synced?
```

**Possible Causes:**
1. **Contract not deployed** - No contract exists at the specified address
2. **Wrong contract address** - Address is for a different network (e.g., Ethereum mainnet instead of Base)
3. **ABI mismatch** - The ABI doesn't match the actual contract at that address
4. **RPC not synced** - The RPC endpoint hasn't synced to the latest block
5. **Invalid wallet address** - The address parameter is malformed

**Solutions:**

#### 1. Verify Contract Deployment
```python
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('YOUR_RPC_URL'))
contract_address = '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1'  # Uniswap V3 on Base
code = w3.eth.get_code(Web3.to_checksum_address(contract_address))

if len(code) > 2:
    print("✓ Contract deployed")
else:
    print("❌ No contract at this address")
```

#### 2. Verify Chain ID
```python
chain_id = w3.eth.chain_id
print(f"Connected to chain ID: {chain_id}")
# Base mainnet = 8453
# Ethereum mainnet = 1
```

#### 3. Verify RPC Sync
```python
block_number = w3.eth.block_number
print(f"Current block: {block_number}")
# Compare with https://basescan.org/ to ensure it's recent
```

#### 4. Verify Wallet Address Format
```python
try:
    checksummed = w3.to_checksum_address('0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B')
    print(f"✓ Valid address: {checksummed}")
except:
    print("❌ Invalid address format")
```

---

### Error 2: "Could not transact with/call contract function"

**Symptom:**
```
Could not transact with/call contract function, is contract deployed correctly and chain synced?
```

**Possible Causes:**
1. **Network connectivity issues** - RPC endpoint unreachable
2. **Rate limiting** - Too many requests to RPC endpoint
3. **Timeout** - Request took too long
4. **Invalid function parameters** - Wrong argument types or values

**Solutions:**

#### 1. Test RPC Connectivity
```bash
curl -X POST YOUR_RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

Expected response:
```json
{"jsonrpc":"2.0","id":1,"result":"0x..."}
```

#### 2. Check Rate Limits
If using Infura/Alchemy:
- Free tier: 100,000 requests/day (Infura), 300M compute units/month (Alchemy)
- Upgrade if you're hitting limits
- Use multiple RPC endpoints with fallback

#### 3. Increase Timeout
In `.env`:
```bash
# Increase timeout if network is slow
RPC_RETRY_DELAY=5
MAX_RPC_RETRIES=5
```

#### 4. Use Alternative RPC Endpoints

**Base Chain Options:**
```bash
# Infura
RPC_URL=https://base-mainnet.infura.io/v3/YOUR_PROJECT_ID

# Alchemy
RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY

# Public (may be slower)
RPC_URL=https://mainnet.base.org

# Ankr
RPC_URL=https://rpc.ankr.com/base
```

---

### Error 3: "Web3 connection check failed"

**Symptom:**
```
Web3 initialization error (attempt 1/3): ...
Web3 connection check failed
```

**Possible Causes:**
1. **Invalid RPC URL** - URL is malformed or incorrect
2. **Network firewall** - Your network blocks the RPC endpoint
3. **DNS issues** - Cannot resolve the RPC endpoint hostname
4. **Service outage** - The RPC provider is down

**Solutions:**

#### 1. Verify RPC URL Format
```bash
# Correct format:
https://base-mainnet.infura.io/v3/YOUR_PROJECT_ID

# Wrong formats:
http://base-mainnet.infura.io/v3/YOUR_PROJECT_ID  # Missing 's' in https
https://base-mainnet.infura.io/YOUR_PROJECT_ID    # Missing '/v3/'
https://mainnet.infura.io/v3/YOUR_PROJECT_ID      # Wrong network (Ethereum, not Base)
```

#### 2. Test Connectivity
```bash
# Ping the endpoint
ping base-mainnet.infura.io

# Test HTTPS
curl -I https://base-mainnet.infura.io/v3/YOUR_PROJECT_ID
```

#### 3. Check Provider Status
- Infura: https://status.infura.io/
- Alchemy: https://status.alchemy.com/
- Base: https://status.base.org/

---

### Error 4: "No positions found"

**Symptom:**
```
Found 0 Uniswap V3 NFT positions
No positions found
```

**Possible Causes:**
1. **Wrong wallet address** - Using wrong address for position tracking
2. **Positions on different protocol** - Positions are on Aerodrome, not Uniswap
3. **Positions on different chain** - Positions are on Ethereum, not Base
4. **No positions** - Wallet actually has no LP positions

**Solutions:**

#### 1. Verify Wallet Has Positions
Check on block explorer:
- Base: https://basescan.org/address/YOUR_WALLET_ADDRESS
- Look for ERC721 tokens from Uniswap V3 or Aerodrome

#### 2. Check vfat.io
Visit https://vfat.io/ and connect your wallet to see positions

#### 3. Verify Correct Address in .env
```bash
# This should be the address that HOLDS the LP positions
# NOT your Hyperliquid trading address
VFAT_SICKLE_ADDRESS=0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B
```

#### 4. Check Both Protocols
Positions might be on Aerodrome instead of Uniswap:
```bash
# Set Aerodrome contract address in .env
AERODROME_NFT_ADDRESS=0xYourAerodromeNFTAddress
```

---

## Environment Setup

### Required Environment Variables

Create a `.env` file:
```bash
# Copy from template
cp .env.example .env

# Edit with your values
nano .env
```

**Critical Variables:**
```bash
# Base Chain RPC (REQUIRED)
RPC_URL=https://base-mainnet.infura.io/v3/YOUR_PROJECT_ID

# LP Position Wallet (REQUIRED)
VFAT_SICKLE_ADDRESS=0xYourSickleWalletAddress

# Uniswap V3 NFT Manager on Base (Pre-configured)
UNISWAP_V3_NFT_ADDRESS=0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1

# Optional: Increase retries for unstable networks
MAX_RPC_RETRIES=5
RPC_RETRY_DELAY=3
```

### Verify Configuration

**Python:**
```python
from bot.config import load_config

config = load_config()
print(f"RPC URL: {config.get('rpc_url')}")
print(f"Sickle Address: {config.get('vfat_sickle_wallet_address')}")
print(f"Uniswap NFT: {config.get('uniswap_v3_nft_address')}")
```

**Check .env is loaded:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
print(f"RPC_URL: {os.getenv('RPC_URL')}")
print(f"VFAT_SICKLE_ADDRESS: {os.getenv('VFAT_SICKLE_ADDRESS')}")
```

---

## Testing Tools

### 1. Python Test Script

**File:** `test_sickle_connection.py`

**Run:**
```bash
python test_sickle_connection.py
```

**What it tests:**
- Web3 connection to Base Chain
- Current block number
- Contract deployment verification
- balanceOf call with specific address
- positions call with specific token ID

**Expected Output:**
```
Testing Sickle Connection to Uniswap V3 on Base Chain
✓ Web3 connected successfully
✓ Current block number: 12345678
✓ Connected to chain ID: 8453
✓ Sickle address (checksummed): 0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B
✓ Contract address (checksummed): 0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1
✓ Contract verified at 0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1
✓ Balance query successful: 1 position(s)
✓ Position query successful
```

### 2. Node.js Test Script

**File:** `sickle.js`

**Run:**
```bash
npm run sickle
# or
node sickle.js
```

**What it tests:**
- Same as Python script but using web3.js v4
- Useful to compare behavior between implementations

---

## Step-by-Step Troubleshooting

### Step 1: Verify Python Environment

```bash
# Check Python version (requires 3.8+)
python --version

# Verify web3.py is installed
pip list | grep web3

# Reinstall if needed
pip install --upgrade web3
```

### Step 2: Verify Node.js Environment

```bash
# Check Node version (requires 14+)
node --version

# Check npm version
npm --version

# Install dependencies
npm install

# Verify web3 installation
npm list web3
```

### Step 3: Test RPC Connection

```bash
# Save as test_rpc.py
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('YOUR_RPC_URL'))
print(f"Connected: {w3.is_connected()}")
print(f"Block: {w3.eth.block_number}")
print(f"Chain ID: {w3.eth.chain_id}")
```

```bash
python test_rpc.py
```

### Step 4: Verify Contract Addresses

**Uniswap V3 on Base:**
- Contract: `0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1`
- Verify on Basescan: https://basescan.org/address/0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1

**Your Sickle Wallet:**
- Check on Basescan: https://basescan.org/address/YOUR_SICKLE_ADDRESS
- Verify it holds Uniswap V3 NFT tokens (ERC721)

### Step 5: Run Test Scripts

```bash
# Python comprehensive test
python test_sickle_connection.py

# Node.js test
npm run sickle

# Full bot test (if environment is configured)
python -m bot.main
```

### Step 6: Check Logs

```bash
# View bot logs
tail -f bot.log

# Search for errors
grep "ERROR" bot.log

# Search for connection issues
grep "Web3\|connection\|contract" bot.log
```

---

## Advanced Debugging

### Enable Debug Logging

**In Python:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Or in .env:**
```bash
LOG_LEVEL=DEBUG
```

### Inspect Contract Calls

```python
from web3 import Web3

w3 = Web3(Web3.HTTPProvider('YOUR_RPC_URL'))
contract_address = '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1'

# Get contract bytecode
code = w3.eth.get_code(Web3.to_checksum_address(contract_address))
print(f"Contract code length: {len(code)} bytes")

# Create contract instance
abi = [...]  # Your ABI
contract = w3.eth.contract(address=contract_address, abi=abi)

# Test function manually
try:
    result = contract.functions.balanceOf('0xYourAddress').call()
    print(f"Success: {result}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
```

### Compare with Working Implementation

If Python fails but Node.js works (or vice versa):

1. Compare RPC URLs (exactly the same?)
2. Compare contract addresses (checksummed the same?)
3. Compare ABIs (identical structure?)
4. Compare function call syntax
5. Check library versions (web3.py vs web3.js)

---

## Getting Help

If you're still stuck after trying these steps:

1. **Gather Information:**
   - Error messages (full stack trace)
   - Configuration (sanitize private keys!)
   - Python/Node versions
   - RPC provider and endpoint
   - Contract addresses used

2. **Check Existing Issues:**
   - GitHub Issues: https://github.com/TomV77/uniswap-v3-delta-neutral-bot/issues
   - Look for similar error messages

3. **Create New Issue:**
   - Include all information from step 1
   - Include output from test scripts
   - Describe what you've already tried

4. **Useful Resources:**
   - Web3.py docs: https://web3py.readthedocs.io/
   - Web3.js docs: https://web3js.readthedocs.io/
   - Uniswap V3 docs: https://docs.uniswap.org/
   - Base Chain docs: https://docs.base.org/

---

## Quick Reference

### Contract Addresses (Base Chain)

```bash
# Uniswap V3 NFT Position Manager
0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1

# Uniswap V3 Factory
0x33128a8fC17869897dcE68Ed026d694621f6FDfD

# WETH on Base
0x4200000000000000000000000000000000000006

# USDC on Base
0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
```

### RPC Endpoints

```bash
# Infura (requires API key)
https://base-mainnet.infura.io/v3/YOUR_PROJECT_ID

# Alchemy (requires API key)
https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY

# Public Base RPC
https://mainnet.base.org

# Ankr (free)
https://rpc.ankr.com/base
```

### Common Commands

```bash
# Test Python implementation
python test_sickle_connection.py

# Test Node.js implementation
npm run sickle

# Run bot
python -m bot.main

# View logs
tail -f bot.log

# Check environment
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('RPC_URL'))"
```

---

## Success Checklist

Before running the bot in production, verify:

- [ ] RPC connection works (test scripts pass)
- [ ] Correct chain ID (8453 for Base)
- [ ] Contract deployed and verified
- [ ] Wallet address is correct (holds LP positions)
- [ ] balanceOf returns expected position count
- [ ] positions call returns valid data
- [ ] All environment variables set in .env
- [ ] Dependencies installed (Python and Node.js)
- [ ] Test scripts run without errors
- [ ] Logs show successful connection

Once all items are checked, your Sickle connection should be working correctly!
