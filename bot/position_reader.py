"""
Position Reader Module

Fetches position details from vfat.io sickle contracts, Aerodrome, and Uniswap v3.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from decimal import Decimal
import aiohttp
import asyncio
import time
from web3 import Web3
from web3.contract import Contract
from web3.exceptions import ContractLogicError, BadFunctionCallOutput

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents a liquidity position"""
    position_id: str
    protocol: str  # 'uniswap' or 'aerodrome'
    token0: str
    token1: str
    token0_symbol: str
    token1_symbol: str
    liquidity: Decimal
    tick_lower: int
    tick_upper: int
    current_tick: int
    token0_amount: Decimal
    token1_amount: Decimal
    unclaimed_fees0: Decimal
    unclaimed_fees1: Decimal
    price: Decimal
    total_value_usd: Decimal


class PositionReader:
    """Reads and fetches position details from multiple sources"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the position reader.
        
        Args:
            config: Configuration dictionary containing RPC URLs, contract addresses, etc.
        """
        self.config = config
        self.rpc_url = config.get('rpc_url', '')
        self.vfat_api_url = config.get('vfat_api_url', 'https://api.vfat.io')
        self.sickle_contract_address = config.get('sickle_contract_address', '')
        self.uniswap_v3_nft_address = config.get('uniswap_v3_nft_address', '')
        self.aerodrome_nft_address = config.get('aerodrome_nft_address', '')
        
        # Retry configuration
        self.max_retries = config.get('max_rpc_retries', 3)
        self.retry_delay = config.get('rpc_retry_delay', 2)  # seconds
        
        # Initialize Web3 with connection validation
        if self.rpc_url:
            self.w3 = self._initialize_web3()
        else:
            self.w3 = None
            logger.warning("No RPC URL provided, Web3 functionality disabled")
    
    def _initialize_web3(self) -> Optional[Web3]:
        """
        Initialize Web3 with connection validation and retry logic.
        
        Returns:
            Web3 instance if connection successful, None otherwise
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Initializing Web3 connection (attempt {attempt + 1}/{self.max_retries})...")
                w3 = Web3(Web3.HTTPProvider(
                    self.rpc_url,
                    request_kwargs={'timeout': 60}  # 60 second timeout
                ))
                
                # Test connection
                if w3.is_connected():
                    block_number = w3.eth.block_number
                    logger.info(f"✓ Web3 connected successfully to {self.rpc_url}")
                    logger.info(f"✓ Current block number: {block_number}")
                    
                    # Verify chain ID (Base mainnet = 8453)
                    try:
                        chain_id = w3.eth.chain_id
                        logger.info(f"✓ Connected to chain ID: {chain_id}")
                        if chain_id != 8453:
                            logger.warning(f"⚠ Expected Base mainnet (chain ID 8453), got {chain_id}")
                    except Exception as e:
                        logger.warning(f"Could not verify chain ID: {e}")
                    
                    return w3
                else:
                    logger.warning(f"Web3 connection check failed (attempt {attempt + 1}/{self.max_retries})")
                    
            except Exception as e:
                logger.error(f"Web3 initialization error (attempt {attempt + 1}/{self.max_retries}): {e}")
            
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
        
        logger.error(f"Failed to initialize Web3 after {self.max_retries} attempts")
        return None
    
    def _verify_contract_deployed(self, address: str) -> bool:
        """
        Verify that a contract is deployed at the given address.
        
        Args:
            address: Contract address to verify
            
        Returns:
            True if contract code exists at address, False otherwise
        """
        if not self.w3:
            return False
        
        try:
            checksummed = self.w3.to_checksum_address(address)
            code = self.w3.eth.get_code(checksummed)
            
            # Contract code should be non-empty (more than just '0x')
            has_code = len(code) > 2
            
            if has_code:
                logger.debug(f"✓ Contract verified at {checksummed} (code length: {len(code)} bytes)")
            else:
                logger.error(f"❌ No contract code found at {checksummed}")
                logger.error("This address does not contain a deployed contract")
                
            return has_code
            
        except Exception as e:
            logger.error(f"Error verifying contract at {address}: {e}")
            return False
    
    async def _call_contract_function_with_retry(self, contract_function, *args, function_name: str = "unknown", **kwargs):
        """
        Call a contract function with retry logic.
        
        Args:
            contract_function: The contract function to call
            *args: Positional arguments for the function
            function_name: Name of the function being called (for better error messages)
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the contract function call
            
        Raises:
            Exception: If all retry attempts fail
        """
        for attempt in range(self.max_retries):
            try:
                result = contract_function(*args, **kwargs).call()
                return result
            except (ContractLogicError, BadFunctionCallOutput) as e:
                error_type = type(e).__name__
                logger.error(f"Could not decode contract function call to {function_name}()")
                logger.error(f"Error type: {error_type} (attempt {attempt + 1}/{self.max_retries})")
                logger.error(f"Error details: {e}")
                
                if isinstance(e, BadFunctionCallOutput):
                    logger.error("Could not transact with/call contract function, is contract deployed correctly and chain synced?")
                    logger.error("Possible causes:")
                    logger.error("  1. Contract not deployed at the specified address")
                    logger.error("  2. ABI mismatch between provided ABI and actual contract")
                    logger.error("  3. RPC endpoint not fully synced with blockchain")
                    logger.error("  4. Network connectivity issues")
                    logger.error(f"  5. Function arguments may be incorrect: {args}")
                
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying contract call in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error calling contract function {function_name} (attempt {attempt + 1}/{self.max_retries}): {type(e).__name__}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    raise
        
        raise Exception(f"Contract function {function_name} call failed after {self.max_retries} attempts")
    
    async def fetch_positions(self, wallet_address: str) -> List[Position]:
        """
        Fetch all positions for a given wallet address.
        
        Args:
            wallet_address: Ethereum address of the wallet (LP position wallet, not Hyperliquid trading wallet)
            
        Returns:
            List of Position objects
        """
        logger.info(f"Fetching LP positions for VFAT_SICKLE_ADDRESS wallet: {wallet_address}")
        
        positions = []
        
        # Fetch from multiple sources
        try:
            uniswap_positions = await self._fetch_uniswap_positions(wallet_address)
            positions.extend(uniswap_positions)
        except Exception as e:
            logger.error(f"Error fetching Uniswap positions: {e}")
        
        try:
            aerodrome_positions = await self._fetch_aerodrome_positions(wallet_address)
            positions.extend(aerodrome_positions)
        except Exception as e:
            logger.error(f"Error fetching Aerodrome positions: {e}")
        
        try:
            sickle_positions = await self._fetch_sickle_positions(wallet_address)
            positions.extend(sickle_positions)
        except Exception as e:
            logger.error(f"Error fetching Sickle positions: {e}")
        
        logger.info(f"Found {len(positions)} total positions")
        return positions
    
    async def _fetch_uniswap_positions(self, wallet_address: str) -> List[Position]:
        """Fetch Uniswap V3 positions"""
        positions = []
        
        if not self.w3 or not self.uniswap_v3_nft_address:
            logger.warning("Uniswap V3 NFT contract not configured")
            return positions
        
        # Validate and checksum wallet address
        try:
            wallet_address = self.w3.to_checksum_address(wallet_address)
        except Exception as e:
            logger.error(f"Invalid wallet address format: {wallet_address}, error: {e}")
            return positions
        
        try:
            # Verify contract is deployed
            if not self._verify_contract_deployed(self.uniswap_v3_nft_address):
                logger.error(f"Uniswap V3 NFT contract not found at {self.uniswap_v3_nft_address}")
                logger.error("Please verify the contract address is correct for Base Chain")
                return positions
            
            # Get positions from Uniswap V3 NFT contract
            nft_contract = self._get_uniswap_nft_contract()
            
            if nft_contract:
                logger.info(f"Fetching Uniswap V3 positions for VFAT_SICKLE_ADDRESS: {wallet_address}")
                
                # Get token IDs owned by wallet with retry logic
                try:
                    balance = await self._call_contract_function_with_retry(
                        nft_contract.functions.balanceOf, wallet_address,
                        function_name="balanceOf"
                    )
                    logger.info(f"Found {balance} Uniswap V3 NFT positions")
                except Exception as e:
                    logger.error(f"Failed to call balanceOf for address {wallet_address}")
                    logger.error(f"Contract address: {self.uniswap_v3_nft_address}")
                    logger.error(f"RPC URL: {self.rpc_url}")
                    logger.info("Troubleshooting steps:")
                    logger.info("  1. Verify RPC endpoint is accessible and synced")
                    logger.info("  2. Verify contract address is correct for Base Chain")
                    logger.info("  3. Verify wallet address format is valid")
                    logger.info("  4. Check that Web3 provider is properly initialized")
                    return positions
                
                for i in range(balance):
                    token_id = None  # Initialize to avoid NameError in exception handling
                    try:
                        token_id = await self._call_contract_function_with_retry(
                            nft_contract.functions.tokenOfOwnerByIndex, wallet_address, i,
                            function_name="tokenOfOwnerByIndex"
                        )
                        logger.debug(f"Processing NFT token ID: {token_id}")
                        
                        position_data = await self._call_contract_function_with_retry(
                            nft_contract.functions.positions, token_id,
                            function_name="positions"
                        )
                        
                        # Parse position data
                        position = self._parse_uniswap_position(token_id, position_data)
                        if position:
                            positions.append(position)
                            logger.info(f"Successfully parsed position {token_id}")
                    except Exception as e:
                        logger.error(f"Error processing Uniswap position {i} (token {token_id if token_id else 'unknown'}): {e}")
                        continue
        except Exception as e:
            logger.error(f"Error in _fetch_uniswap_positions: {e}", exc_info=True)
        
        return positions
    
    async def _fetch_aerodrome_positions(self, wallet_address: str) -> List[Position]:
        """Fetch Aerodrome positions"""
        positions = []
        
        if not self.w3 or not self.aerodrome_nft_address:
            logger.warning("Aerodrome NFT contract not configured")
            return positions
        
        # Validate and checksum wallet address
        try:
            wallet_address = self.w3.to_checksum_address(wallet_address)
        except Exception as e:
            logger.error(f"Invalid wallet address format: {wallet_address}, error: {e}")
            return positions
        
        try:
            # Verify contract is deployed
            if not self._verify_contract_deployed(self.aerodrome_nft_address):
                logger.error(f"Aerodrome NFT contract not found at {self.aerodrome_nft_address}")
                logger.error("Please verify the contract address is correct for Base Chain")
                return positions
            
            # Get positions from Aerodrome NFT contract
            nft_contract = self._get_aerodrome_nft_contract()
            
            if nft_contract:
                logger.info(f"Fetching Aerodrome positions for VFAT_SICKLE_ADDRESS: {wallet_address}")
                
                # Similar to Uniswap, get positions owned by wallet with retry logic
                try:
                    balance = await self._call_contract_function_with_retry(
                        nft_contract.functions.balanceOf, wallet_address,
                        function_name="balanceOf"
                    )
                    logger.info(f"Found {balance} Aerodrome NFT positions")
                except Exception as e:
                    logger.error(f"Failed to call balanceOf for address {wallet_address}")
                    logger.error(f"Contract address: {self.aerodrome_nft_address}")
                    return positions
                
                for i in range(balance):
                    token_id = None  # Initialize to avoid NameError in exception handling
                    try:
                        token_id = await self._call_contract_function_with_retry(
                            nft_contract.functions.tokenOfOwnerByIndex, wallet_address, i,
                            function_name="tokenOfOwnerByIndex"
                        )
                        logger.debug(f"Processing Aerodrome NFT token ID: {token_id}")
                        
                        position_data = await self._call_contract_function_with_retry(
                            nft_contract.functions.positions, token_id,
                            function_name="positions"
                        )
                        
                        # Parse position data
                        position = self._parse_aerodrome_position(token_id, position_data)
                        if position:
                            positions.append(position)
                            logger.info(f"Successfully parsed Aerodrome position {token_id}")
                    except Exception as e:
                        logger.error(f"Error processing Aerodrome position {i} (token {token_id if token_id else 'unknown'}): {e}")
                        continue
        except Exception as e:
            logger.error(f"Error in _fetch_aerodrome_positions: {e}", exc_info=True)
        
        return positions
    
    async def _fetch_sickle_positions(self, wallet_address: str) -> List[Position]:
        """
        Fetch positions via vfat.io sickle contracts.
        
        Note: VFAT.io does not provide a public REST API for position data.
        This method attempts to query the sickle contract directly via Web3
        or uses the VFAT API if available.
        """
        positions = []
        
        # Validate wallet address
        if self.w3:
            try:
                wallet_address = self.w3.to_checksum_address(wallet_address)
            except Exception as e:
                logger.error(f"Invalid wallet address format: {wallet_address}, error: {e}")
                return positions
        
        try:
            # Try API first (if endpoint exists)
            async with aiohttp.ClientSession() as session:
                # Query vfat.io API for sickle contract positions
                # Note: This endpoint may not exist - VFAT.io primarily provides web UI, not public API
                url = f"{self.vfat_api_url}/positions/{wallet_address}"
                
                logger.debug(f"Attempting to fetch sickle positions from: {url}")
                
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Parse sickle positions
                            for pos_data in data.get('positions', []):
                                position = self._parse_sickle_position(pos_data)
                                if position:
                                    positions.append(position)
                            
                            logger.info(f"Fetched {len(positions)} positions from VFAT API")
                        elif response.status == 404:
                            logger.warning(f"VFAT API endpoint not found (404): {url}")
                            logger.info("VFAT.io may not provide a public REST API. Consider fetching positions directly from sickle contracts via Web3.")
                        else:
                            logger.warning(f"VFAT API returned status {response.status} for {url}")
                except asyncio.TimeoutError:
                    logger.warning(f"VFAT API request timed out: {url}")
                except aiohttp.ClientError as e:
                    logger.warning(f"VFAT API request failed: {e}")
                    
        except Exception as e:
            logger.error(f"Error in _fetch_sickle_positions: {e}", exc_info=True)
        
        # If no positions found via API and we have sickle contract, try direct contract interaction
        if not positions and self.sickle_contract_address and self.w3:
            logger.info("Attempting to fetch positions directly from sickle contract")
            positions = await self._fetch_sickle_positions_from_contract(wallet_address)
        
        return positions
    
    async def _fetch_sickle_positions_from_contract(self, wallet_address: str) -> List[Position]:
        """
        Fetch positions directly from sickle contract via Web3.
        
        TODO: Implement direct sickle contract interaction.
        Required information:
        - Sickle contract ABI (needs to be obtained from contract deployment or Etherscan)
        - Contract methods for querying positions (likely: getUserPositions(), getPosition(), etc.)
        - Position data structure returned by the contract
        - Reference: https://vfat.io or sickle contract documentation
        """
        positions = []
        
        if not self.w3 or not self.sickle_contract_address:
            return positions
        
        try:
            logger.info("Direct sickle contract querying not yet implemented")
            logger.info(f"Sickle contract address: {self.sickle_contract_address}")
            logger.info("To implement: obtain sickle contract ABI and implement position fetching logic")
        except Exception as e:
            logger.error(f"Error fetching from sickle contract: {e}", exc_info=True)
        
        return positions
    
    def _get_uniswap_nft_contract(self) -> Optional[Contract]:
        """Get Uniswap V3 NFT Position Manager contract"""
        if not self.w3 or not self.uniswap_v3_nft_address:
            return None
        
        try:
            # Ensure address is checksummed
            contract_address = self.w3.to_checksum_address(self.uniswap_v3_nft_address)
        except Exception as e:
            logger.error(f"Invalid Uniswap V3 NFT contract address: {self.uniswap_v3_nft_address}, error: {e}")
            return None
        
        # Minimal ABI for position reading
        abi = [
            {
                "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "owner", "type": "address"},
                    {"internalType": "uint256", "name": "index", "type": "uint256"}
                ],
                "name": "tokenOfOwnerByIndex",
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
        
        try:
            return self.w3.eth.contract(address=contract_address, abi=abi)
        except Exception as e:
            logger.error(f"Error creating Uniswap V3 NFT contract instance: {e}")
            return None
    
    def _get_aerodrome_nft_contract(self) -> Optional[Contract]:
        """Get Aerodrome NFT Position Manager contract"""
        if not self.w3 or not self.aerodrome_nft_address:
            return None
        
        try:
            # Ensure address is checksummed
            contract_address = self.w3.to_checksum_address(self.aerodrome_nft_address)
        except Exception as e:
            logger.error(f"Invalid Aerodrome NFT contract address: {self.aerodrome_nft_address}, error: {e}")
            return None
        
        # Similar ABI to Uniswap V3
        abi = [
            {
                "inputs": [{"internalType": "address", "name": "owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"internalType": "address", "name": "owner", "type": "address"},
                    {"internalType": "uint256", "name": "index", "type": "uint256"}
                ],
                "name": "tokenOfOwnerByIndex",
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
        
        try:
            return self.w3.eth.contract(address=contract_address, abi=abi)
        except Exception as e:
            logger.error(f"Error creating Aerodrome NFT contract instance: {e}")
            return None
    
    def _parse_uniswap_position(self, token_id: int, position_data: tuple) -> Optional[Position]:
        """Parse Uniswap V3 position data"""
        try:
            # Extract position data from tuple
            (nonce, operator, token0, token1, fee, tick_lower, tick_upper, 
             liquidity, fee_growth0, fee_growth1, tokens_owed0, tokens_owed1) = position_data
            
            # Calculate amounts (simplified - real implementation would use pool state)
            # This would require querying the pool contract for current tick and sqrt price
            
            return Position(
                position_id=f"uniswap-{token_id}",
                protocol="uniswap",
                token0=token0,
                token1=token1,
                token0_symbol="TOKEN0",  # Would need to query token contract
                token1_symbol="TOKEN1",  # Would need to query token contract
                liquidity=Decimal(liquidity),
                tick_lower=tick_lower,
                tick_upper=tick_upper,
                current_tick=0,  # Would need to query pool contract
                token0_amount=Decimal(0),  # Would calculate from liquidity and ticks
                token1_amount=Decimal(0),  # Would calculate from liquidity and ticks
                unclaimed_fees0=Decimal(tokens_owed0),
                unclaimed_fees1=Decimal(tokens_owed1),
                price=Decimal(0),  # Would calculate from current tick
                total_value_usd=Decimal(0)  # Would calculate from amounts and prices
            )
        except Exception as e:
            logger.error(f"Error parsing Uniswap position {token_id}: {e}")
            return None
    
    def _parse_aerodrome_position(self, token_id: int, position_data: tuple) -> Optional[Position]:
        """Parse Aerodrome position data"""
        try:
            # Similar structure to Uniswap
            (nonce, operator, token0, token1, fee, tick_lower, tick_upper, 
             liquidity, fee_growth0, fee_growth1, tokens_owed0, tokens_owed1) = position_data
            
            return Position(
                position_id=f"aerodrome-{token_id}",
                protocol="aerodrome",
                token0=token0,
                token1=token1,
                token0_symbol="TOKEN0",
                token1_symbol="TOKEN1",
                liquidity=Decimal(liquidity),
                tick_lower=tick_lower,
                tick_upper=tick_upper,
                current_tick=0,
                token0_amount=Decimal(0),
                token1_amount=Decimal(0),
                unclaimed_fees0=Decimal(tokens_owed0),
                unclaimed_fees1=Decimal(tokens_owed1),
                price=Decimal(0),
                total_value_usd=Decimal(0)
            )
        except Exception as e:
            logger.error(f"Error parsing Aerodrome position {token_id}: {e}")
            return None
    
    def _parse_sickle_position(self, pos_data: Dict[str, Any]) -> Optional[Position]:
        """Parse position data from vfat.io sickle contracts"""
        try:
            return Position(
                position_id=f"sickle-{pos_data.get('id', 'unknown')}",
                protocol=pos_data.get('protocol', 'unknown'),
                token0=pos_data.get('token0', ''),
                token1=pos_data.get('token1', ''),
                token0_symbol=pos_data.get('token0_symbol', 'TOKEN0'),
                token1_symbol=pos_data.get('token1_symbol', 'TOKEN1'),
                liquidity=Decimal(str(pos_data.get('liquidity', 0))),
                tick_lower=pos_data.get('tick_lower', 0),
                tick_upper=pos_data.get('tick_upper', 0),
                current_tick=pos_data.get('current_tick', 0),
                token0_amount=Decimal(str(pos_data.get('token0_amount', 0))),
                token1_amount=Decimal(str(pos_data.get('token1_amount', 0))),
                unclaimed_fees0=Decimal(str(pos_data.get('unclaimed_fees0', 0))),
                unclaimed_fees1=Decimal(str(pos_data.get('unclaimed_fees1', 0))),
                price=Decimal(str(pos_data.get('price', 0))),
                total_value_usd=Decimal(str(pos_data.get('total_value_usd', 0)))
            )
        except Exception as e:
            logger.error(f"Error parsing sickle position: {e}")
            return None
    
    async def get_position_delta(self, position: Position) -> Decimal:
        """
        Calculate the delta (directional exposure) of a position.
        
        For a liquidity position, delta represents the net directional exposure
        to price movements. A delta of 0 would be perfectly delta-neutral.
        
        Args:
            position: Position object
            
        Returns:
            Delta value (positive = long exposure, negative = short exposure)
        """
        try:
            # Simplified delta calculation
            # Real implementation would consider:
            # - Current price relative to range
            # - Token amounts
            # - Impermanent loss sensitivity
            
            # Convert token1 amount to token0 equivalent
            # If price = 2000 (meaning 1 token0 = 2000 token1, e.g., 1 ETH = 2000 USDC)
            # Then to convert token1 to token0: divide by price
            # Example: 3000 USDC / 2000 = 1.5 ETH equivalent
            if position.price > 0:
                token1_in_token0 = position.token1_amount / position.price
                net_delta = position.token0_amount - token1_in_token0
                return net_delta
            else:
                return Decimal(0)
        except Exception as e:
            logger.error(f"Error calculating position delta: {e}")
            return Decimal(0)
