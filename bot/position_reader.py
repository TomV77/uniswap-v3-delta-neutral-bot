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
from web3 import Web3
from web3.contract import Contract

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
        
        # Initialize Web3
        if self.rpc_url:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        else:
            self.w3 = None
            logger.warning("No RPC URL provided, Web3 functionality disabled")
    
    async def fetch_positions(self, wallet_address: str) -> List[Position]:
        """
        Fetch all positions for a given wallet address.
        
        Args:
            wallet_address: Ethereum address of the wallet
            
        Returns:
            List of Position objects
        """
        logger.info(f"Fetching positions for wallet: {wallet_address}")
        
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
        
        try:
            # Get positions from Uniswap V3 NFT contract
            # This is a simplified version - real implementation would use the actual contract ABI
            nft_contract = self._get_uniswap_nft_contract()
            
            if nft_contract:
                # Get token IDs owned by wallet
                balance = nft_contract.functions.balanceOf(wallet_address).call()
                
                for i in range(balance):
                    token_id = nft_contract.functions.tokenOfOwnerByIndex(wallet_address, i).call()
                    position_data = nft_contract.functions.positions(token_id).call()
                    
                    # Parse position data
                    position = self._parse_uniswap_position(token_id, position_data)
                    if position:
                        positions.append(position)
        except Exception as e:
            logger.error(f"Error in _fetch_uniswap_positions: {e}")
        
        return positions
    
    async def _fetch_aerodrome_positions(self, wallet_address: str) -> List[Position]:
        """Fetch Aerodrome positions"""
        positions = []
        
        if not self.w3 or not self.aerodrome_nft_address:
            logger.warning("Aerodrome NFT contract not configured")
            return positions
        
        try:
            # Get positions from Aerodrome NFT contract
            # This is a simplified version - real implementation would use the actual contract ABI
            nft_contract = self._get_aerodrome_nft_contract()
            
            if nft_contract:
                # Similar to Uniswap, get positions owned by wallet
                balance = nft_contract.functions.balanceOf(wallet_address).call()
                
                for i in range(balance):
                    token_id = nft_contract.functions.tokenOfOwnerByIndex(wallet_address, i).call()
                    position_data = nft_contract.functions.positions(token_id).call()
                    
                    # Parse position data
                    position = self._parse_aerodrome_position(token_id, position_data)
                    if position:
                        positions.append(position)
        except Exception as e:
            logger.error(f"Error in _fetch_aerodrome_positions: {e}")
        
        return positions
    
    async def _fetch_sickle_positions(self, wallet_address: str) -> List[Position]:
        """Fetch positions via vfat.io sickle contracts"""
        positions = []
        
        try:
            async with aiohttp.ClientSession() as session:
                # Query vfat.io API for sickle contract positions
                url = f"{self.vfat_api_url}/positions/{wallet_address}"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Parse sickle positions
                        for pos_data in data.get('positions', []):
                            position = self._parse_sickle_position(pos_data)
                            if position:
                                positions.append(position)
                    else:
                        logger.warning(f"vfat.io API returned status {response.status}")
        except Exception as e:
            logger.error(f"Error in _fetch_sickle_positions: {e}")
        
        return positions
    
    def _get_uniswap_nft_contract(self) -> Optional[Contract]:
        """Get Uniswap V3 NFT Position Manager contract"""
        if not self.w3 or not self.uniswap_v3_nft_address:
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
        
        return self.w3.eth.contract(address=self.uniswap_v3_nft_address, abi=abi)
    
    def _get_aerodrome_nft_contract(self) -> Optional[Contract]:
        """Get Aerodrome NFT Position Manager contract"""
        if not self.w3 or not self.aerodrome_nft_address:
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
        
        return self.w3.eth.contract(address=self.aerodrome_nft_address, abi=abi)
    
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
            if position.price > 0:
                token1_in_token0 = position.token1_amount * position.price
                net_delta = position.token0_amount - token1_in_token0
                return net_delta
            else:
                return Decimal(0)
        except Exception as e:
            logger.error(f"Error calculating position delta: {e}")
            return Decimal(0)
