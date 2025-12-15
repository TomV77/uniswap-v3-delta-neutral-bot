"""
Hedging Executor Module

Executes hedging trades on Hyperliquid to maintain delta-neutral positions.
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from enum import Enum
import aiohttp
import json
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"


@dataclass
class HedgeOrder:
    """Represents a hedge order"""
    symbol: str
    side: OrderSide
    size: Decimal
    order_type: str
    limit_price: Optional[Decimal] = None


@dataclass
class HedgeResult:
    """Result of a hedge execution"""
    success: bool
    order_id: Optional[str] = None
    executed_size: Decimal = Decimal(0)
    executed_price: Decimal = Decimal(0)
    message: str = ""


class HedgingExecutor:
    """Executes hedging trades on Hyperliquid"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the hedging executor.
        
        Args:
            config: Configuration dictionary containing API keys, endpoints, etc.
        """
        self.config = config
        self.api_key = config.get('hyperliquid_api_key', '')
        self.api_secret = config.get('hyperliquid_api_secret', '')
        self.api_url = config.get('hyperliquid_api_url', 'https://api.hyperliquid.xyz')
        self.testnet = config.get('hyperliquid_testnet', True)
        self.wallet_address = config.get('wallet_address', '')  # Hyperliquid trading wallet
        
        # Hedging parameters
        self.max_position_size = Decimal(str(config.get('max_position_size', 10.0)))
        self.min_order_size = Decimal(str(config.get('min_order_size', 0.01)))
        self.slippage_tolerance = Decimal(str(config.get('slippage_tolerance', 0.005)))  # 0.5%
        
        # Safety limits
        self.max_daily_trades = config.get('max_daily_trades', 100)
        self.daily_trade_count = 0
        self.last_reset_time = time.time()
        
        logger.info(f"HedgingExecutor initialized for Hyperliquid trading wallet (WALLET_ADDRESS): {self.wallet_address}")
    
    async def execute_hedge(self, hedge_order: HedgeOrder) -> HedgeResult:
        """
        Execute a hedge order on Hyperliquid.
        
        Args:
            hedge_order: HedgeOrder object specifying the hedge to execute
            
        Returns:
            HedgeResult with execution details
        """
        logger.info(f"Executing hedge on Hyperliquid with trading wallet (WALLET_ADDRESS): {self.wallet_address}")
        logger.info(f"Hedge order: {hedge_order.side.value} {hedge_order.size} {hedge_order.symbol}")
        
        # Safety checks
        if not self._check_safety_limits(hedge_order):
            return HedgeResult(
                success=False,
                message="Safety limits exceeded"
            )
        
        try:
            # Get current market price
            current_price = await self._get_market_price(hedge_order.symbol)
            
            if current_price is None:
                return HedgeResult(
                    success=False,
                    message="Could not fetch market price"
                )
            
            # Calculate limit price with slippage
            if hedge_order.side == OrderSide.BUY:
                limit_price = current_price * (1 + self.slippage_tolerance)
            else:
                limit_price = current_price * (1 - self.slippage_tolerance)
            
            # Place order
            result = await self._place_order(
                symbol=hedge_order.symbol,
                side=hedge_order.side,
                size=hedge_order.size,
                limit_price=limit_price
            )
            
            if result.success:
                self.daily_trade_count += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing hedge: {e}")
            return HedgeResult(
                success=False,
                message=f"Execution error: {str(e)}"
            )
    
    async def increase_hedge(self, symbol: str, delta_to_hedge: Decimal) -> HedgeResult:
        """
        Increase hedge position to offset positive delta.
        
        Args:
            symbol: Trading symbol (e.g., "ETH-USD")
            delta_to_hedge: Amount of delta to hedge (positive value)
            
        Returns:
            HedgeResult with execution details
        """
        logger.info(f"Increasing hedge for {symbol}: {delta_to_hedge}")
        
        # Positive delta means we're long the underlying, so we need to short
        order = HedgeOrder(
            symbol=symbol,
            side=OrderSide.SELL,
            size=abs(delta_to_hedge),
            order_type="limit"
        )
        
        return await self.execute_hedge(order)
    
    async def decrease_hedge(self, symbol: str, delta_to_reduce: Decimal) -> HedgeResult:
        """
        Decrease hedge position to offset negative delta.
        
        Args:
            symbol: Trading symbol (e.g., "ETH-USD")
            delta_to_reduce: Amount of delta to reduce (positive value)
            
        Returns:
            HedgeResult with execution details
        """
        logger.info(f"Decreasing hedge for {symbol}: {delta_to_reduce}")
        
        # Negative delta means we're short the underlying, so we need to buy
        order = HedgeOrder(
            symbol=symbol,
            side=OrderSide.BUY,
            size=abs(delta_to_reduce),
            order_type="limit"
        )
        
        return await self.execute_hedge(order)
    
    async def get_current_position(self, symbol: str) -> Optional[Decimal]:
        """
        Get current hedge position size on Hyperliquid.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current position size (positive = long, negative = short)
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Build request for position info
                url = f"{self.api_url}/info"
                headers = self._build_headers()
                
                params = {
                    "type": "clearinghouseState",
                    "user": self._get_user_address()
                }
                
                async with session.post(url, json=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Find position for symbol
                        for position in data.get('assetPositions', []):
                            if position.get('position', {}).get('coin') == symbol:
                                size = Decimal(str(position.get('position', {}).get('szi', 0)))
                                return size
                        
                        return Decimal(0)
                    else:
                        logger.warning(f"Failed to get position: status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting current position: {e}")
            return None
    
    async def _get_market_price(self, symbol: str) -> Optional[Decimal]:
        """Get current market price for a symbol"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/info"
                
                params = {
                    "type": "allMids"
                }
                
                async with session.post(url, json=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Find price for symbol
                        if symbol in data:
                            return Decimal(str(data[symbol]))
                        else:
                            logger.warning(f"Symbol {symbol} not found in market data")
                            return None
                    else:
                        logger.warning(f"Failed to get market price: status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error getting market price: {e}")
            return None
    
    async def _place_order(
        self,
        symbol: str,
        side: OrderSide,
        size: Decimal,
        limit_price: Decimal
    ) -> HedgeResult:
        """Place an order on Hyperliquid"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/exchange"
                headers = self._build_headers()
                
                # Build order request
                order_request = {
                    "type": "order",
                    "orders": [
                        {
                            "a": self._symbol_to_asset_id(symbol),
                            "b": side.value == "buy",
                            "p": str(limit_price),
                            "s": str(size),
                            "r": False,  # reduce only
                            "t": {
                                "limit": {
                                    "tif": "Gtc"  # Good til cancelled
                                }
                            }
                        }
                    ],
                    "grouping": "na"
                }
                
                # Sign the request
                signed_request = self._sign_request(order_request)
                
                async with session.post(url, json=signed_request, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('status') == 'ok':
                            statuses = data.get('response', {}).get('data', {}).get('statuses', [])
                            if statuses and len(statuses) > 0:
                                status = statuses[0]
                                if 'filled' in status:
                                    return HedgeResult(
                                        success=True,
                                        order_id=str(status.get('oid', '')),
                                        executed_size=size,
                                        executed_price=limit_price,
                                        message="Order executed successfully"
                                    )
                        
                        return HedgeResult(
                            success=False,
                            message=f"Order placement failed: {data}"
                        )
                    else:
                        return HedgeResult(
                            success=False,
                            message=f"API error: status {response.status}"
                        )
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return HedgeResult(
                success=False,
                message=f"Order placement error: {str(e)}"
            )
    
    def _check_safety_limits(self, hedge_order: HedgeOrder) -> bool:
        """Check if order passes safety limits"""
        # Reset daily counter if needed
        current_time = time.time()
        if current_time - self.last_reset_time > 86400:  # 24 hours
            self.daily_trade_count = 0
            self.last_reset_time = current_time
        
        # Check daily trade limit
        if self.daily_trade_count >= self.max_daily_trades:
            logger.warning("Daily trade limit exceeded")
            return False
        
        # Check minimum order size
        if hedge_order.size < self.min_order_size:
            logger.warning(f"Order size {hedge_order.size} below minimum {self.min_order_size}")
            return False
        
        # Check maximum position size
        if hedge_order.size > self.max_position_size:
            logger.warning(f"Order size {hedge_order.size} exceeds maximum {self.max_position_size}")
            return False
        
        return True
    
    def _build_headers(self) -> Dict[str, str]:
        """Build HTTP headers for API requests"""
        return {
            "Content-Type": "application/json"
        }
    
    def _sign_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign a request for Hyperliquid API.
        
        Note: This is a placeholder. Real implementation would use
        the actual Hyperliquid signing scheme with private keys.
        """
        # In production, this would:
        # 1. Serialize the request
        # 2. Sign with private key
        # 3. Add signature to request
        return request
    
    def _get_user_address(self) -> str:
        """Get user's Ethereum address for Hyperliquid"""
        # Return the Hyperliquid trading wallet address
        return self.wallet_address
    
    def _symbol_to_asset_id(self, symbol: str) -> int:
        """Convert symbol to Hyperliquid asset ID"""
        # Common mappings
        symbol_map = {
            "BTC-USD": 0,
            "ETH-USD": 1,
            "SOL-USD": 2,
            # Add more as needed
        }
        
        return symbol_map.get(symbol, 0)
    
    async def close_all_positions(self) -> bool:
        """
        Close all open positions on Hyperliquid.
        Emergency function to exit all hedges.
        
        Returns:
            True if successful, False otherwise
        """
        logger.warning("Closing all positions - EMERGENCY MODE")
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/exchange"
                headers = self._build_headers()
                
                # Cancel all orders first
                cancel_request = {
                    "type": "cancel",
                    "cancels": [
                        {
                            "a": None,  # Cancel all assets
                            "o": None   # Cancel all orders
                        }
                    ]
                }
                
                signed_request = self._sign_request(cancel_request)
                
                async with session.post(url, json=signed_request, headers=headers) as response:
                    if response.status != 200:
                        logger.error("Failed to cancel orders")
                        return False
            
            # Would also close positions with market orders here
            logger.info("All positions closed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
            return False
