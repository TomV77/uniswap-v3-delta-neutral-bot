"""
Unit tests for main bot module
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from decimal import Decimal
import asyncio
import json
import tempfile
import os
import pytest

from bot.main import DeltaNeutralBot
from bot.position_reader import Position
from bot.risk_management import RiskMetrics
from bot.hedging_executor import HedgeResult


class TestDeltaNeutralBot(unittest.TestCase):
    """Test cases for DeltaNeutralBot"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        config_data = {
            'wallet_address': '0xTestWallet',
            'rpc_url': 'https://test.rpc',
            'update_interval_seconds': 1,
            'hedge_symbol': 'ETH-USD',
            'delta_threshold': 0.1
        }
        json.dump(config_data, self.temp_config)
        self.temp_config.close()
        
        self.bot = DeltaNeutralBot(self.temp_config.name)
    
    def tearDown(self):
        """Clean up"""
        os.unlink(self.temp_config.name)
    
    def test_initialization(self):
        """Test bot initialization"""
        self.assertIsNotNone(self.bot.position_reader)
        self.assertIsNotNone(self.bot.hedging_executor)
        self.assertIsNotNone(self.bot.risk_manager)
        self.assertEqual(self.bot.wallet_address, '0xTestWallet')
        self.assertEqual(self.bot.update_interval, 1)
    
    def test_load_config_valid(self):
        """Test loading valid config"""
        config = self.bot.config
        self.assertEqual(config['wallet_address'], '0xTestWallet')
        self.assertEqual(config['hedge_symbol'], 'ETH-USD')
    
    def test_load_config_missing_file(self):
        """Test loading config from missing file"""
        bot = DeltaNeutralBot('nonexistent.json')
        # Should use default config
        self.assertIsNotNone(bot.config)
        self.assertIn('delta_threshold', bot.config)
    
    def test_get_default_config(self):
        """Test default configuration"""
        from bot.config import get_default_config
        config = get_default_config()
        
        self.assertIn('wallet_address', config)
        self.assertIn('delta_threshold', config)
        self.assertIn('hedge_symbol', config)
        self.assertIn('update_interval_seconds', config)
    
    @pytest.mark.asyncio
    @patch.object(DeltaNeutralBot, '_fetch_positions')
    async def test_run_cycle_no_positions(self, mock_fetch):
        """Test bot cycle with no positions"""
        mock_fetch.return_value = []
        
        # Should complete without error
        await self.bot._run_cycle()
        
        self.assertTrue(mock_fetch.called)
    
    @pytest.mark.asyncio
    @patch.object(DeltaNeutralBot, '_fetch_positions')
    @patch.object(DeltaNeutralBot, '_analyze_positions')
    @patch('bot.main.HedgingExecutor.get_current_position')
    async def test_run_cycle_with_positions(self, mock_get_hedge, mock_analyze, mock_fetch):
        """Test bot cycle with positions"""
        # Setup mocks
        test_position = Position(
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
        
        test_metrics = RiskMetrics(
            impermanent_loss=Decimal('100'),
            impermanent_loss_percent=Decimal('0.02'),
            accumulated_fees=Decimal('20.01'),
            net_pnl=Decimal('-79.99'),
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.05'),
            gamma=Decimal('100'),
            needs_rebalance=False,
            recommended_hedge_size=Decimal('0')
        )
        
        mock_fetch.return_value = [test_position]
        mock_analyze.return_value = (Decimal('0.05'), [(test_position, test_metrics)])
        mock_get_hedge.return_value = Decimal('0')
        
        await self.bot._run_cycle()
        
        self.assertTrue(mock_fetch.called)
        self.assertTrue(mock_analyze.called)
    
    @pytest.mark.asyncio
    @patch('bot.main.PositionReader.fetch_positions')
    async def test_fetch_positions(self, mock_fetch):
        """Test fetching positions"""
        mock_fetch.return_value = []
        
        positions = await self.bot._fetch_positions()
        
        self.assertIsInstance(positions, list)
        self.assertTrue(mock_fetch.called)
    
    @pytest.mark.asyncio
    @patch('bot.main.RiskManagement.assess_position_risk')
    async def test_analyze_positions(self, mock_assess):
        """Test analyzing positions"""
        test_position = Position(
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
        
        test_metrics = RiskMetrics(
            impermanent_loss=Decimal('100'),
            impermanent_loss_percent=Decimal('0.02'),
            accumulated_fees=Decimal('20.01'),
            net_pnl=Decimal('-79.99'),
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.5'),
            gamma=Decimal('100'),
            needs_rebalance=False,
            recommended_hedge_size=Decimal('0.5')
        )
        
        mock_assess.return_value = test_metrics
        
        total_delta, metrics_list = await self.bot._analyze_positions([test_position])
        
        self.assertEqual(total_delta, Decimal('0.5'))
        self.assertEqual(len(metrics_list), 1)
    
    @pytest.mark.asyncio
    @patch('bot.main.HedgingExecutor.increase_hedge')
    @patch('bot.main.RiskManagement.calculate_optimal_hedge_size')
    async def test_execute_hedge_increase(self, mock_calc, mock_increase):
        """Test executing hedge increase"""
        mock_calc.return_value = Decimal('1.0')
        mock_increase.return_value = HedgeResult(
            success=True,
            order_id='test-order',
            executed_size=Decimal('1.0'),
            executed_price=Decimal('2000'),
            message='Success'
        )
        
        await self.bot._execute_hedge(Decimal('1.0'), Decimal('0'))
        
        self.assertTrue(mock_increase.called)
        self.assertEqual(self.bot.total_hedges_executed, 1)
    
    @pytest.mark.asyncio
    @patch('bot.main.HedgingExecutor.decrease_hedge')
    @patch('bot.main.RiskManagement.calculate_optimal_hedge_size')
    async def test_execute_hedge_decrease(self, mock_calc, mock_decrease):
        """Test executing hedge decrease"""
        mock_calc.return_value = Decimal('-1.0')
        mock_decrease.return_value = HedgeResult(
            success=True,
            order_id='test-order',
            executed_size=Decimal('1.0'),
            executed_price=Decimal('2000'),
            message='Success'
        )
        
        await self.bot._execute_hedge(Decimal('-1.0'), Decimal('0'))
        
        self.assertTrue(mock_decrease.called)
    
    @pytest.mark.asyncio
    @patch('bot.main.RiskManagement.calculate_optimal_hedge_size')
    async def test_execute_hedge_too_small(self, mock_calc):
        """Test executing hedge when adjustment is too small"""
        mock_calc.return_value = Decimal('0.001')  # Below min order size
        
        # Should not execute
        initial_count = self.bot.total_hedges_executed
        await self.bot._execute_hedge(Decimal('0.001'), Decimal('0'))
        
        # Count should not increase
        self.assertEqual(self.bot.total_hedges_executed, initial_count)
    
    def test_log_performance_report(self):
        """Test logging performance report"""
        test_position = Position(
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
        
        test_metrics = RiskMetrics(
            impermanent_loss=Decimal('100'),
            impermanent_loss_percent=Decimal('0.02'),
            accumulated_fees=Decimal('200'),
            net_pnl=Decimal('100'),
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.05'),
            gamma=Decimal('100'),
            needs_rebalance=False,
            recommended_hedge_size=Decimal('0')
        )
        
        metrics_list = [(test_position, test_metrics)]
        
        # Should not raise any exceptions
        self.bot._log_performance_report(metrics_list)
    
    @pytest.mark.asyncio
    @patch('bot.main.HedgingExecutor.close_all_positions')
    async def test_stop_with_close_positions(self, mock_close):
        """Test stopping bot with position closing"""
        self.bot.config['close_positions_on_shutdown'] = True
        mock_close.return_value = True
        
        await self.bot.stop()
        
        self.assertFalse(self.bot.running)
        self.assertTrue(mock_close.called)
    
    @pytest.mark.asyncio
    async def test_stop_without_close_positions(self):
        """Test stopping bot without position closing"""
        self.bot.config['close_positions_on_shutdown'] = False
        
        await self.bot.stop()
        
        self.assertFalse(self.bot.running)
    
    def test_signal_handler(self):
        """Test signal handler"""
        self.bot.running = True
        self.bot._signal_handler(2, None)
        self.assertFalse(self.bot.running)


if __name__ == '__main__':
    unittest.main()
