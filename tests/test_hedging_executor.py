"""
Unit tests for hedging_executor module
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
import asyncio
import pytest

from bot.hedging_executor import (
    HedgingExecutor,
    HedgeOrder,
    HedgeResult,
    OrderSide
)


class TestHedgingExecutor(unittest.TestCase):
    """Test cases for HedgingExecutor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'hyperliquid_api_key': 'test_key',
            'hyperliquid_api_secret': 'test_secret',
            'hyperliquid_api_url': 'https://api.hyperliquid.xyz',
            'hyperliquid_testnet': True,
            'wallet_address': '0x2D4de18344D54111d5327AE9F81e0c60D44AEd40',
            'max_position_size': 10.0,
            'min_order_size': 0.01,
            'slippage_tolerance': 0.005,
            'max_daily_trades': 100
        }
        self.executor = HedgingExecutor(self.config)
    
    def test_initialization(self):
        """Test HedgingExecutor initialization"""
        self.assertEqual(self.executor.api_key, 'test_key')
        self.assertEqual(self.executor.api_secret, 'test_secret')
        self.assertEqual(self.executor.wallet_address, '0x2D4de18344D54111d5327AE9F81e0c60D44AEd40')
        self.assertEqual(self.executor.max_position_size, Decimal('10.0'))
        self.assertEqual(self.executor.min_order_size, Decimal('0.01'))
    
    def test_check_safety_limits_valid(self):
        """Test safety limits check with valid order"""
        order = HedgeOrder(
            symbol='ETH-USD',
            side=OrderSide.BUY,
            size=Decimal('1.0'),
            order_type='limit'
        )
        
        result = self.executor._check_safety_limits(order)
        self.assertTrue(result)
    
    def test_check_safety_limits_too_small(self):
        """Test safety limits check with order too small"""
        order = HedgeOrder(
            symbol='ETH-USD',
            side=OrderSide.BUY,
            size=Decimal('0.005'),  # Below min_order_size
            order_type='limit'
        )
        
        result = self.executor._check_safety_limits(order)
        self.assertFalse(result)
    
    def test_check_safety_limits_too_large(self):
        """Test safety limits check with order too large"""
        order = HedgeOrder(
            symbol='ETH-USD',
            side=OrderSide.BUY,
            size=Decimal('20.0'),  # Above max_position_size
            order_type='limit'
        )
        
        result = self.executor._check_safety_limits(order)
        self.assertFalse(result)
    
    def test_check_safety_limits_daily_limit(self):
        """Test safety limits check with daily trade limit exceeded"""
        self.executor.daily_trade_count = 100
        
        order = HedgeOrder(
            symbol='ETH-USD',
            side=OrderSide.BUY,
            size=Decimal('1.0'),
            order_type='limit'
        )
        
        result = self.executor._check_safety_limits(order)
        self.assertFalse(result)
    
    @pytest.mark.asyncio
    @patch('bot.hedging_executor.aiohttp.ClientSession')
    async def test_get_market_price(self, mock_session):
        """Test getting market price"""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'ETH-USD': '2000.50'
        })
        
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        price = await self.executor._get_market_price('ETH-USD')
        
        self.assertIsNotNone(price)
        self.assertEqual(price, Decimal('2000.50'))
    
    @pytest.mark.asyncio
    @patch('bot.hedging_executor.aiohttp.ClientSession')
    async def test_get_market_price_not_found(self, mock_session):
        """Test getting market price for non-existent symbol"""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'BTC-USD': '50000'
        })
        
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        price = await self.executor._get_market_price('ETH-USD')
        
        self.assertIsNone(price)
    
    @pytest.mark.asyncio
    @patch('bot.hedging_executor.aiohttp.ClientSession')
    async def test_get_current_position(self, mock_session):
        """Test getting current position"""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'assetPositions': [
                {
                    'position': {
                        'coin': 'ETH-USD',
                        'szi': '-2.5'
                    }
                }
            ]
        })
        
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        position = await self.executor.get_current_position('ETH-USD')
        
        self.assertIsNotNone(position)
        self.assertEqual(position, Decimal('-2.5'))
    
    @pytest.mark.asyncio
    @patch('bot.hedging_executor.aiohttp.ClientSession')
    async def test_get_current_position_none(self, mock_session):
        """Test getting current position when no position exists"""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'assetPositions': []
        })
        
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        position = await self.executor.get_current_position('ETH-USD')
        
        self.assertEqual(position, Decimal('0'))
    
    @pytest.mark.asyncio
    @patch.object(HedgingExecutor, '_get_market_price')
    @patch.object(HedgingExecutor, '_place_order')
    async def test_execute_hedge_buy(self, mock_place_order, mock_get_price):
        """Test executing a buy hedge"""
        mock_get_price.return_value = Decimal('2000')
        mock_place_order.return_value = HedgeResult(
            success=True,
            order_id='test-order-1',
            executed_size=Decimal('1.0'),
            executed_price=Decimal('2010'),
            message='Order executed successfully'
        )
        
        order = HedgeOrder(
            symbol='ETH-USD',
            side=OrderSide.BUY,
            size=Decimal('1.0'),
            order_type='limit'
        )
        
        result = await self.executor.execute_hedge(order)
        
        self.assertTrue(result.success)
        self.assertEqual(result.order_id, 'test-order-1')
        self.assertEqual(self.executor.daily_trade_count, 1)
    
    @pytest.mark.asyncio
    @patch.object(HedgingExecutor, '_get_market_price')
    async def test_execute_hedge_no_price(self, mock_get_price):
        """Test executing hedge when market price unavailable"""
        mock_get_price.return_value = None
        
        order = HedgeOrder(
            symbol='ETH-USD',
            side=OrderSide.BUY,
            size=Decimal('1.0'),
            order_type='limit'
        )
        
        result = await self.executor.execute_hedge(order)
        
        self.assertFalse(result.success)
        self.assertIn('price', result.message.lower())
    
    @pytest.mark.asyncio
    @patch.object(HedgingExecutor, 'execute_hedge')
    async def test_increase_hedge(self, mock_execute_hedge):
        """Test increasing hedge position"""
        mock_execute_hedge.return_value = HedgeResult(success=True)
        
        result = await self.executor.increase_hedge('ETH-USD', Decimal('1.5'))
        
        # Should call execute_hedge with SELL order (to hedge long exposure)
        self.assertTrue(mock_execute_hedge.called)
        call_args = mock_execute_hedge.call_args[0][0]
        self.assertEqual(call_args.side, OrderSide.SELL)
        self.assertEqual(call_args.size, Decimal('1.5'))
    
    @pytest.mark.asyncio
    @patch.object(HedgingExecutor, 'execute_hedge')
    async def test_decrease_hedge(self, mock_execute_hedge):
        """Test decreasing hedge position"""
        mock_execute_hedge.return_value = HedgeResult(success=True)
        
        result = await self.executor.decrease_hedge('ETH-USD', Decimal('0.75'))
        
        # Should call execute_hedge with BUY order (to reduce short exposure)
        self.assertTrue(mock_execute_hedge.called)
        call_args = mock_execute_hedge.call_args[0][0]
        self.assertEqual(call_args.side, OrderSide.BUY)
        self.assertEqual(call_args.size, Decimal('0.75'))
    
    def test_symbol_to_asset_id(self):
        """Test symbol to asset ID conversion"""
        self.assertEqual(self.executor._symbol_to_asset_id('BTC-USD'), 0)
        self.assertEqual(self.executor._symbol_to_asset_id('ETH-USD'), 1)
        self.assertEqual(self.executor._symbol_to_asset_id('SOL-USD'), 2)
        self.assertEqual(self.executor._symbol_to_asset_id('UNKNOWN'), 0)


class TestHedgeOrder(unittest.TestCase):
    """Test cases for HedgeOrder dataclass"""
    
    def test_hedge_order_creation(self):
        """Test creating a HedgeOrder"""
        order = HedgeOrder(
            symbol='ETH-USD',
            side=OrderSide.BUY,
            size=Decimal('1.5'),
            order_type='limit',
            limit_price=Decimal('2000')
        )
        
        self.assertEqual(order.symbol, 'ETH-USD')
        self.assertEqual(order.side, OrderSide.BUY)
        self.assertEqual(order.size, Decimal('1.5'))
        self.assertEqual(order.limit_price, Decimal('2000'))


class TestHedgeResult(unittest.TestCase):
    """Test cases for HedgeResult dataclass"""
    
    def test_hedge_result_success(self):
        """Test creating a successful HedgeResult"""
        result = HedgeResult(
            success=True,
            order_id='order-123',
            executed_size=Decimal('1.0'),
            executed_price=Decimal('2000'),
            message='Success'
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.order_id, 'order-123')
        self.assertEqual(result.executed_size, Decimal('1.0'))
    
    def test_hedge_result_failure(self):
        """Test creating a failed HedgeResult"""
        result = HedgeResult(
            success=False,
            message='Order failed'
        )
        
        self.assertFalse(result.success)
        self.assertEqual(result.message, 'Order failed')
        self.assertIsNone(result.order_id)


if __name__ == '__main__':
    unittest.main()
