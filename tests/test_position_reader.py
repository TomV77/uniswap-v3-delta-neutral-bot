"""
Unit tests for position_reader module
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
import asyncio

from bot.position_reader import PositionReader, Position


class TestPositionReader(unittest.TestCase):
    """Test cases for PositionReader"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'rpc_url': 'https://mainnet.infura.io/v3/test',
            'vfat_api_url': 'https://api.vfat.io',
            'sickle_contract_address': '0x1234567890123456789012345678901234567890',
            'uniswap_v3_nft_address': '0xC36442b4a4522E871399CD717aBDD847Ab11FE88',
            'aerodrome_nft_address': '0xAerodromeNFT',
        }
        self.reader = PositionReader(self.config)
    
    def test_initialization(self):
        """Test PositionReader initialization"""
        self.assertEqual(self.reader.vfat_api_url, 'https://api.vfat.io')
        self.assertEqual(self.reader.sickle_contract_address, '0x1234567890123456789012345678901234567890')
    
    def test_initialization_without_rpc(self):
        """Test initialization without RPC URL"""
        config = {}
        reader = PositionReader(config)
        self.assertIsNone(reader.w3)
    
    @patch('bot.position_reader.aiohttp.ClientSession')
    async def test_fetch_sickle_positions(self, mock_session):
        """Test fetching positions from sickle contracts"""
        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'positions': [
                {
                    'id': 'test-1',
                    'protocol': 'uniswap',
                    'token0': '0xToken0',
                    'token1': '0xToken1',
                    'token0_symbol': 'ETH',
                    'token1_symbol': 'USDC',
                    'liquidity': 1000000,
                    'tick_lower': -887220,
                    'tick_upper': 887220,
                    'current_tick': 0,
                    'token0_amount': 1.5,
                    'token1_amount': 3000,
                    'unclaimed_fees0': 0.01,
                    'unclaimed_fees1': 20,
                    'price': 2000,
                    'total_value_usd': 6000
                }
            ]
        })
        
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        positions = await self.reader._fetch_sickle_positions('0xWallet')
        
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].protocol, 'uniswap')
        self.assertEqual(positions[0].token0_symbol, 'ETH')
        self.assertEqual(positions[0].total_value_usd, Decimal('6000'))
    
    def test_parse_sickle_position(self):
        """Test parsing sickle position data"""
        pos_data = {
            'id': 'test-1',
            'protocol': 'uniswap',
            'token0': '0xToken0',
            'token1': '0xToken1',
            'token0_symbol': 'ETH',
            'token1_symbol': 'USDC',
            'liquidity': 1000000,
            'tick_lower': -887220,
            'tick_upper': 887220,
            'current_tick': 0,
            'token0_amount': 1.5,
            'token1_amount': 3000,
            'unclaimed_fees0': 0.01,
            'unclaimed_fees1': 20,
            'price': 2000,
            'total_value_usd': 6000
        }
        
        position = self.reader._parse_sickle_position(pos_data)
        
        self.assertIsNotNone(position)
        self.assertEqual(position.position_id, 'sickle-test-1')
        self.assertEqual(position.protocol, 'uniswap')
        self.assertEqual(position.token0_symbol, 'ETH')
        self.assertEqual(position.token1_symbol, 'USDC')
        self.assertEqual(position.liquidity, Decimal('1000000'))
    
    def test_parse_sickle_position_invalid(self):
        """Test parsing invalid sickle position data"""
        pos_data = {}
        position = self.reader._parse_sickle_position(pos_data)
        # Should handle gracefully and return a position with defaults
        self.assertIsNotNone(position)
    
    async def test_get_position_delta(self):
        """Test delta calculation for a position"""
        position = Position(
            position_id='test-1',
            protocol='uniswap',
            token0='0xToken0',
            token1='0xToken1',
            token0_symbol='ETH',
            token1_symbol='USDC',
            liquidity=Decimal('1000000'),
            tick_lower=-887220,
            tick_upper=887220,
            current_tick=0,
            token0_amount=Decimal('1.5'),
            token1_amount=Decimal('3000'),
            unclaimed_fees0=Decimal('0.01'),
            unclaimed_fees1=Decimal('20'),
            price=Decimal('2000'),
            total_value_usd=Decimal('6000')
        )
        
        delta = await self.reader.get_position_delta(position)
        
        # Delta = token0_amount - (token1_amount / price)
        # = 1.5 - (3000 / 2000) = 1.5 - 1.5 = 0
        self.assertEqual(delta, Decimal('0'))
    
    async def test_get_position_delta_long(self):
        """Test delta calculation for long-biased position"""
        position = Position(
            position_id='test-1',
            protocol='uniswap',
            token0='0xToken0',
            token1='0xToken1',
            token0_symbol='ETH',
            token1_symbol='USDC',
            liquidity=Decimal('1000000'),
            tick_lower=-887220,
            tick_upper=887220,
            current_tick=0,
            token0_amount=Decimal('2.0'),
            token1_amount=Decimal('2000'),
            unclaimed_fees0=Decimal('0.01'),
            unclaimed_fees1=Decimal('20'),
            price=Decimal('2000'),
            total_value_usd=Decimal('6000')
        )
        
        delta = await self.reader.get_position_delta(position)
        
        # Delta = 2.0 - (2000 / 2000) = 2.0 - 1.0 = 1.0 (long)
        self.assertEqual(delta, Decimal('1.0'))
    
    async def test_get_position_delta_zero_price(self):
        """Test delta calculation with zero price"""
        position = Position(
            position_id='test-1',
            protocol='uniswap',
            token0='0xToken0',
            token1='0xToken1',
            token0_symbol='ETH',
            token1_symbol='USDC',
            liquidity=Decimal('1000000'),
            tick_lower=-887220,
            tick_upper=887220,
            current_tick=0,
            token0_amount=Decimal('1.5'),
            token1_amount=Decimal('3000'),
            unclaimed_fees0=Decimal('0.01'),
            unclaimed_fees1=Decimal('20'),
            price=Decimal('0'),
            total_value_usd=Decimal('6000')
        )
        
        delta = await self.reader.get_position_delta(position)
        
        # Should handle zero price gracefully
        self.assertEqual(delta, Decimal('0'))
    
    def test_tick_to_price(self):
        """Test tick to price conversion"""
        # Tick 0 should be approximately price 1
        price = self.reader._tick_to_price(0)
        self.assertAlmostEqual(float(price), 1.0, places=4)
        
        # Positive tick should give higher price
        price_positive = self.reader._tick_to_price(1000)
        self.assertGreater(price_positive, Decimal('1'))
        
        # Negative tick should give lower price
        price_negative = self.reader._tick_to_price(-1000)
        self.assertLess(price_negative, Decimal('1'))


class TestPosition(unittest.TestCase):
    """Test cases for Position dataclass"""
    
    def test_position_creation(self):
        """Test creating a Position object"""
        position = Position(
            position_id='test-1',
            protocol='uniswap',
            token0='0xToken0',
            token1='0xToken1',
            token0_symbol='ETH',
            token1_symbol='USDC',
            liquidity=Decimal('1000000'),
            tick_lower=-887220,
            tick_upper=887220,
            current_tick=0,
            token0_amount=Decimal('1.5'),
            token1_amount=Decimal('3000'),
            unclaimed_fees0=Decimal('0.01'),
            unclaimed_fees1=Decimal('20'),
            price=Decimal('2000'),
            total_value_usd=Decimal('6000')
        )
        
        self.assertEqual(position.position_id, 'test-1')
        self.assertEqual(position.protocol, 'uniswap')
        self.assertEqual(position.token0_symbol, 'ETH')
        self.assertEqual(position.liquidity, Decimal('1000000'))


def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


if __name__ == '__main__':
    unittest.main()
