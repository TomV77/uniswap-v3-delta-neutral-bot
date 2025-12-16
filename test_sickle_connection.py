#!/usr/bin/env python3
"""
Test Sickle Connection Script

This script tests the Web3 connection and contract calls to verify
that the Uniswap V3 position manager contract can be queried successfully.

This mirrors the functionality of sickle.js for troubleshooting.
"""

import sys
import os
from web3 import Web3
from web3.exceptions import ContractLogicError, BadFunctionCallOutput
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_sickle_connection():
    """Test connection to Uniswap V3 contract on Base Chain"""
    
    # Configuration - Get from environment variables or use defaults
    RPC_URL = os.getenv('RPC_URL', 'https://base-mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID')
    SICKLE_ADDRESS = os.getenv('VFAT_SICKLE_ADDRESS', '0xa1B402db32CCAEEF1E18A52eE1F50aeaa5535d9B')
    POSITIONS_MANAGER = os.getenv('UNISWAP_V3_NFT_ADDRESS', '0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1')
    TOKEN_ID = int(os.getenv('TEST_TOKEN_ID', '4294280'))
    
    logger.info("=" * 80)
    logger.info("Testing Sickle Connection to Uniswap V3 on Base Chain")
    logger.info("=" * 80)
    
    if 'YOUR_INFURA_PROJECT_ID' in RPC_URL:
        logger.warning("⚠ Using default RPC URL - set RPC_URL environment variable for actual testing")
    
    try:
        # Step 1: Initialize Web3
        logger.info(f"Connecting to RPC: {RPC_URL}")
        w3 = Web3(Web3.HTTPProvider(
            RPC_URL,
            request_kwargs={'timeout': 60}
        ))
        
        # Step 2: Verify connection
        if not w3.is_connected():
            logger.error("❌ Failed to connect to Web3 provider")
            return False
        
        logger.info("✓ Web3 connected successfully")
        
        # Step 3: Get current block number
        try:
            block_number = w3.eth.block_number
            logger.info(f"✓ Current block number: {block_number}")
        except Exception as e:
            logger.error(f"❌ Failed to get block number: {e}")
            return False
        
        # Step 4: Checksum addresses
        try:
            sickle_address = w3.to_checksum_address(SICKLE_ADDRESS)
            contract_address = w3.to_checksum_address(POSITIONS_MANAGER)
            logger.info(f"✓ Sickle address (checksummed): {sickle_address}")
            logger.info(f"✓ Contract address (checksummed): {contract_address}")
        except Exception as e:
            logger.error(f"❌ Failed to checksum addresses: {e}")
            return False
        
        # Step 5: Create contract instance with ABI
        abi = [
            {
                "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
                "name": "positions",
                "outputs": [
                    {"internalType": "uint96", "name": "nonce", "type": "uint96"},
                    {"internalType": "address", "name": "operator", "type": "address"},
                    {"internalType": "address", "name": "token0", "type": "address"},
                    {"internalType": "address", "name": "token1", "type": "address"},
                    {"internalType": "uint24", "name": "fee", "type": "uint24"},
                    {"internalType": "int24", "name": "tickLower", "type": "int24"},
                    {"internalType": "int24", "name": "tickUpper", "type": "int24"},
                    {"internalType": "uint128", "name": "liquidity", "type": "uint128"},
                    {"internalType": "uint256", "name": "feeGrowthInside0LastX128", "type": "uint256"},
                    {"internalType": "uint256", "name": "feeGrowthInside1LastX128", "type": "uint256"},
                    {"internalType": "uint128", "name": "tokensOwed0", "type": "uint128"},
                    {"internalType": "uint128", "name": "tokensOwed1", "type": "uint128"}
                ],
                "stateMutability": "view",
                "type": "function"
            }
        ]
        
        logger.info("Creating contract instance...")
        contract = w3.eth.contract(address=contract_address, abi=abi)
        logger.info("✓ Contract instance created")
        
        # Step 6: Test balanceOf call
        logger.info(f"\nTesting balanceOf for address: {sickle_address}")
        try:
            balance = contract.functions.balanceOf(sickle_address).call()
            logger.info(f"✓ Balance query successful: {balance} position(s)")
        except ContractLogicError as e:
            logger.error(f"❌ Contract logic error in balanceOf: {e}")
            logger.error("This usually means the contract reverted the call")
            return False
        except BadFunctionCallOutput as e:
            logger.error(f"❌ Bad function call output in balanceOf: {e}")
            logger.error("This could mean:")
            logger.error("  - Contract address is incorrect")
            logger.error("  - Contract is not deployed at this address")
            logger.error("  - ABI doesn't match the contract")
            logger.error("  - RPC endpoint is not synced")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error in balanceOf: {type(e).__name__}: {e}")
            return False
        
        # Step 7: Test positions call
        logger.info(f"\nTesting positions for token ID: {TOKEN_ID}")
        try:
            position = contract.functions.positions(TOKEN_ID).call()
            logger.info("✓ Position query successful")
            logger.info(f"\n{'=' * 80}")
            logger.info("Position Details:")
            logger.info(f"{'=' * 80}")
            logger.info(f"Nonce: {position[0]}")
            logger.info(f"Operator: {position[1]}")
            logger.info(f"Token0: {position[2]}")
            logger.info(f"Token1: {position[3]}")
            logger.info(f"Fee Tier: {position[4] / 10000}%")
            logger.info(f"Tick Lower: {position[5]}")
            logger.info(f"Tick Upper: {position[6]}")
            logger.info(f"Liquidity: {position[7]}")
            logger.info(f"Fee Growth Inside 0: {position[8]}")
            logger.info(f"Fee Growth Inside 1: {position[9]}")
            logger.info(f"Tokens Owed 0: {position[10] / 1e18:.6f} (assuming 18 decimals)")
            logger.info(f"Tokens Owed 1: {position[11] / 1e6:.2f} (assuming 6 decimals)")
            logger.info(f"{'=' * 80}")
        except ContractLogicError as e:
            logger.error(f"❌ Contract logic error in positions: {e}")
            logger.error("The position may not exist or may be owned by a different address")
            return False
        except BadFunctionCallOutput as e:
            logger.error(f"❌ Bad function call output in positions: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error in positions: {type(e).__name__}: {e}")
            return False
        
        logger.info("\n✓ All tests passed successfully!")
        logger.info("The contract is accessible and functioning correctly.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in test: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = test_sickle_connection()
    sys.exit(0 if success else 1)
