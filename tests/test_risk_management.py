"""
Unit tests for risk_management module
"""

import unittest
from decimal import Decimal
import math

from bot.risk_management import RiskManagement, RiskMetrics
from bot.position_reader import Position


class TestRiskManagement(unittest.TestCase):
    """Test cases for RiskManagement"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'delta_threshold': 0.1,
            'max_impermanent_loss': 0.05,
            'min_fee_coverage': 1.5,
            'rebalance_threshold': 0.05,
            'var_confidence': 0.95,
            'volatility_lookback': 30,
            'max_position_value': 100000,
            'max_leverage': 1.0
        }
        self.risk_manager = RiskManagement(self.config)
    
    def test_initialization(self):
        """Test RiskManagement initialization"""
        self.assertEqual(self.risk_manager.delta_threshold, Decimal('0.1'))
        self.assertEqual(self.risk_manager.max_impermanent_loss, Decimal('0.05'))
        self.assertEqual(self.risk_manager.min_fee_coverage, Decimal('1.5'))
    
    def test_calculate_impermanent_loss_no_change(self):
        """Test IL calculation when price doesn't change"""
        il = self.risk_manager.calculate_impermanent_loss(
            initial_price=Decimal('2000'),
            current_price=Decimal('2000'),
            initial_token0=Decimal('1'),
            initial_token1=Decimal('2000')
        )
        
        # When price doesn't change, IL should be 0
        self.assertAlmostEqual(float(il), 0.0, places=4)
    
    def test_calculate_impermanent_loss_2x_price(self):
        """Test IL calculation when price doubles"""
        il = self.risk_manager.calculate_impermanent_loss(
            initial_price=Decimal('1000'),
            current_price=Decimal('2000'),
            initial_token0=Decimal('1'),
            initial_token1=Decimal('1000')
        )
        
        # For 2x price change, IL is approximately 5.7%
        self.assertGreater(il, Decimal('0.05'))
        self.assertLess(il, Decimal('0.06'))
    
    def test_calculate_impermanent_loss_half_price(self):
        """Test IL calculation when price halves"""
        il = self.risk_manager.calculate_impermanent_loss(
            initial_price=Decimal('2000'),
            current_price=Decimal('1000'),
            initial_token0=Decimal('1'),
            initial_token1=Decimal('2000')
        )
        
        # For 0.5x price change, IL is approximately 5.7%
        self.assertGreater(il, Decimal('0.05'))
        self.assertLess(il, Decimal('0.06'))
    
    def test_calculate_impermanent_loss_zero_price(self):
        """Test IL calculation with zero price"""
        il = self.risk_manager.calculate_impermanent_loss(
            initial_price=Decimal('0'),
            current_price=Decimal('2000'),
            initial_token0=Decimal('1'),
            initial_token1=Decimal('2000')
        )
        
        # Should handle gracefully
        self.assertEqual(il, Decimal('0'))
    
    def test_calculate_concentrated_il_in_range(self):
        """Test concentrated IL when price is in range"""
        il = self.risk_manager.calculate_concentrated_il(
            current_price=Decimal('2000'),
            lower_price=Decimal('1800'),
            upper_price=Decimal('2200'),
            entry_price=Decimal('2000')
        )
        
        # Should be minimal when price hasn't moved
        self.assertGreaterEqual(il, Decimal('0'))
    
    def test_calculate_concentrated_il_out_of_range(self):
        """Test concentrated IL when price is out of range"""
        il = self.risk_manager.calculate_concentrated_il(
            current_price=Decimal('2500'),
            lower_price=Decimal('1800'),
            upper_price=Decimal('2200'),
            entry_price=Decimal('2000')
        )
        
        # Should be higher when out of range
        self.assertGreater(il, Decimal('0'))
    
    def test_calculate_downside_risk(self):
        """Test downside risk calculation"""
        risk = self.risk_manager.calculate_downside_risk(
            position_value=Decimal('10000'),
            current_price=Decimal('2000'),
            volatility=Decimal('0.5'),
            time_horizon_days=1
        )
        
        # Should return a positive risk value
        self.assertGreater(risk, Decimal('0'))
        self.assertLess(risk, Decimal('10000'))
    
    def test_calculate_downside_risk_zero_volatility(self):
        """Test downside risk with zero volatility"""
        risk = self.risk_manager.calculate_downside_risk(
            position_value=Decimal('10000'),
            current_price=Decimal('2000'),
            volatility=Decimal('0'),
            time_horizon_days=1
        )
        
        # Should handle gracefully
        self.assertEqual(risk, Decimal('0'))
    
    def test_calculate_value_at_risk(self):
        """Test VaR calculation"""
        var = self.risk_manager.calculate_value_at_risk(
            position_value=Decimal('10000'),
            volatility=Decimal('0.5')
        )
        
        # Should return a positive VaR
        self.assertGreater(var, Decimal('0'))
        self.assertLess(var, Decimal('10000'))
    
    def test_calculate_value_at_risk_high_confidence(self):
        """Test VaR with high confidence level"""
        var_95 = self.risk_manager.calculate_value_at_risk(
            position_value=Decimal('10000'),
            volatility=Decimal('0.5'),
            confidence=Decimal('0.95')
        )
        
        var_99 = self.risk_manager.calculate_value_at_risk(
            position_value=Decimal('10000'),
            volatility=Decimal('0.5'),
            confidence=Decimal('0.99')
        )
        
        # Higher confidence should give higher VaR
        self.assertGreater(var_99, var_95)
    
    def test_calculate_position_delta_neutral(self):
        """Test delta calculation for neutral position"""
        delta = self.risk_manager.calculate_position_delta(
            token0_amount=Decimal('1.5'),
            token1_amount=Decimal('3000'),
            current_price=Decimal('2000')
        )
        
        # Delta = 1.5 - (3000 / 2000) = 1.5 - 1.5 = 0
        self.assertEqual(delta, Decimal('0'))
    
    def test_calculate_position_delta_long(self):
        """Test delta calculation for long position"""
        delta = self.risk_manager.calculate_position_delta(
            token0_amount=Decimal('2.0'),
            token1_amount=Decimal('2000'),
            current_price=Decimal('2000')
        )
        
        # Delta = 2.0 - (2000 / 2000) = 2.0 - 1.0 = 1.0
        self.assertEqual(delta, Decimal('1.0'))
    
    def test_calculate_position_delta_short(self):
        """Test delta calculation for short position"""
        delta = self.risk_manager.calculate_position_delta(
            token0_amount=Decimal('1.0'),
            token1_amount=Decimal('4000'),
            current_price=Decimal('2000')
        )
        
        # Delta = 1.0 - (4000 / 2000) = 1.0 - 2.0 = -1.0
        self.assertEqual(delta, Decimal('-1.0'))
    
    def test_calculate_gamma_in_range(self):
        """Test gamma calculation for in-range position"""
        gamma = self.risk_manager.calculate_gamma(
            liquidity=Decimal('1000000'),
            current_tick=0,
            tick_lower=-1000,
            tick_upper=1000
        )
        
        # Should be positive when in range
        self.assertGreater(gamma, Decimal('0'))
    
    def test_calculate_gamma_out_of_range(self):
        """Test gamma calculation for out-of-range position"""
        gamma = self.risk_manager.calculate_gamma(
            liquidity=Decimal('1000000'),
            current_tick=2000,
            tick_lower=-1000,
            tick_upper=1000
        )
        
        # Should be zero when out of range
        self.assertEqual(gamma, Decimal('0'))
    
    def test_assess_position_risk(self):
        """Test comprehensive position risk assessment"""
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
            unclaimed_fees0=Decimal('0.05'),
            unclaimed_fees1=Decimal('100'),
            price=Decimal('2000'),
            total_value_usd=Decimal('6000')
        )
        
        metrics = self.risk_manager.assess_position_risk(position)
        
        self.assertIsInstance(metrics, RiskMetrics)
        self.assertGreaterEqual(metrics.impermanent_loss, Decimal('0'))
        self.assertGreaterEqual(metrics.accumulated_fees, Decimal('0'))
        self.assertIsInstance(metrics.needs_rebalance, bool)
    
    def test_should_hedge_high_delta(self):
        """Test hedge decision with high delta"""
        metrics = RiskMetrics(
            impermanent_loss=Decimal('100'),
            impermanent_loss_percent=Decimal('0.02'),
            accumulated_fees=Decimal('200'),
            net_pnl=Decimal('100'),
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.5'),  # High delta
            gamma=Decimal('100'),
            needs_rebalance=True,
            recommended_hedge_size=Decimal('0.5')
        )
        
        should_hedge = self.risk_manager.should_hedge(metrics)
        self.assertTrue(should_hedge)
    
    def test_should_hedge_low_delta(self):
        """Test hedge decision with low delta"""
        metrics = RiskMetrics(
            impermanent_loss=Decimal('100'),
            impermanent_loss_percent=Decimal('0.02'),
            accumulated_fees=Decimal('200'),
            net_pnl=Decimal('100'),
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.05'),  # Low delta
            gamma=Decimal('100'),
            needs_rebalance=False,
            recommended_hedge_size=Decimal('0')
        )
        
        should_hedge = self.risk_manager.should_hedge(metrics)
        self.assertFalse(should_hedge)
    
    def test_should_hedge_high_il(self):
        """Test hedge decision with high IL"""
        metrics = RiskMetrics(
            impermanent_loss=Decimal('1000'),
            impermanent_loss_percent=Decimal('0.10'),  # 10% IL
            accumulated_fees=Decimal('500'),  # Not enough to cover
            net_pnl=Decimal('-500'),
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.05'),
            gamma=Decimal('100'),
            needs_rebalance=False,
            recommended_hedge_size=Decimal('0')
        )
        
        should_hedge = self.risk_manager.should_hedge(metrics)
        self.assertTrue(should_hedge)
    
    def test_calculate_optimal_hedge_size_positive_delta(self):
        """Test optimal hedge calculation with positive delta"""
        adjustment = self.risk_manager.calculate_optimal_hedge_size(
            current_delta=Decimal('1.5'),
            current_hedge_position=Decimal('-0.5'),
            target_delta=Decimal('0')
        )
        
        # Net delta = 1.5 + (-0.5) = 1.0
        # Need to adjust by 1.0
        self.assertEqual(adjustment, Decimal('1.0'))
    
    def test_calculate_optimal_hedge_size_negative_delta(self):
        """Test optimal hedge calculation with negative delta"""
        adjustment = self.risk_manager.calculate_optimal_hedge_size(
            current_delta=Decimal('-1.5'),
            current_hedge_position=Decimal('0.5'),
            target_delta=Decimal('0')
        )
        
        # Net delta = -1.5 + 0.5 = -1.0
        # Need to adjust by -1.0
        self.assertEqual(adjustment, Decimal('-1.0'))
    
    def test_tick_to_price(self):
        """Test tick to price conversion"""
        # Tick 0 should be price 1
        price = self.risk_manager._tick_to_price(0)
        self.assertAlmostEqual(float(price), 1.0, places=4)
        
        # Positive tick should give higher price
        price_positive = self.risk_manager._tick_to_price(1000)
        self.assertGreater(price_positive, Decimal('1'))
        
        # Negative tick should give lower price
        price_negative = self.risk_manager._tick_to_price(-1000)
        self.assertLess(price_negative, Decimal('1'))
    
    def test_get_risk_report(self):
        """Test risk report generation"""
        metrics = RiskMetrics(
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
        
        report = self.risk_manager.get_risk_report(metrics)
        
        self.assertIsInstance(report, dict)
        self.assertIn('impermanent_loss_usd', report)
        self.assertIn('accumulated_fees_usd', report)
        self.assertIn('net_pnl_usd', report)
        self.assertIn('risk_level', report)
        self.assertIn(report['risk_level'], ['LOW', 'MEDIUM', 'HIGH'])


class TestRiskMetrics(unittest.TestCase):
    """Test cases for RiskMetrics dataclass"""
    
    def test_risk_metrics_creation(self):
        """Test creating RiskMetrics"""
        metrics = RiskMetrics(
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
        
        self.assertEqual(metrics.impermanent_loss, Decimal('100'))
        self.assertEqual(metrics.net_pnl, Decimal('100'))
        self.assertFalse(metrics.needs_rebalance)


class TestRiskManagementEdgeCases(unittest.TestCase):
    """Test edge cases and error handling in RiskManagement"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'delta_threshold': 0.1,
            'max_impermanent_loss': 0.05,
            'min_fee_coverage': 1.5,
            'rebalance_threshold': 0.05,
            'var_confidence': 0.95,
            'volatility_lookback': 30,
            'max_position_value': 100000,
            'max_leverage': 1.0
        }
        self.risk_manager = RiskManagement(self.config)
    
    def test_calculate_concentrated_il_equal_bounds(self):
        """Test concentrated IL when upper_price equals lower_price"""
        il = self.risk_manager.calculate_concentrated_il(
            current_price=Decimal('2000'),
            lower_price=Decimal('2000'),
            upper_price=Decimal('2000'),
            entry_price=Decimal('2000')
        )
        
        # Should handle gracefully and return 0
        self.assertEqual(il, Decimal('0'))
    
    def test_calculate_concentrated_il_inverted_bounds(self):
        """Test concentrated IL when upper_price < lower_price"""
        il = self.risk_manager.calculate_concentrated_il(
            current_price=Decimal('2000'),
            lower_price=Decimal('2200'),
            upper_price=Decimal('1800'),
            entry_price=Decimal('2000')
        )
        
        # Should handle gracefully and return 0
        self.assertEqual(il, Decimal('0'))
    
    def test_calculate_concentrated_il_negative_price(self):
        """Test concentrated IL with negative current price"""
        il = self.risk_manager.calculate_concentrated_il(
            current_price=Decimal('-100'),
            lower_price=Decimal('1800'),
            upper_price=Decimal('2200'),
            entry_price=Decimal('2000')
        )
        
        # Should handle gracefully and return 0
        self.assertEqual(il, Decimal('0'))
    
    def test_should_hedge_with_zero_il(self):
        """Test hedge decision with zero IL but high delta"""
        metrics = RiskMetrics(
            impermanent_loss=Decimal('0'),
            impermanent_loss_percent=Decimal('0'),
            accumulated_fees=Decimal('100'),
            net_pnl=Decimal('100'),
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.15'),  # High delta
            gamma=Decimal('100'),
            needs_rebalance=False,
            recommended_hedge_size=Decimal('0.15')
        )
        
        should_hedge = self.risk_manager.should_hedge(metrics)
        self.assertTrue(should_hedge)  # Should hedge due to high delta
    
    def test_should_hedge_with_zero_fees_and_il(self):
        """Test hedge decision with both zero fees and zero IL"""
        metrics = RiskMetrics(
            impermanent_loss=Decimal('0'),
            impermanent_loss_percent=Decimal('0'),
            accumulated_fees=Decimal('0'),
            net_pnl=Decimal('0'),
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.05'),
            gamma=Decimal('100'),
            needs_rebalance=False,
            recommended_hedge_size=Decimal('0')
        )
        
        should_hedge = self.risk_manager.should_hedge(metrics)
        self.assertFalse(should_hedge)  # Should not hedge
    
    def test_calculate_optimal_hedge_size_zero_hedge(self):
        """Test optimal hedge with zero current hedge"""
        adjustment = self.risk_manager.calculate_optimal_hedge_size(
            current_delta=Decimal('2.0'),
            current_hedge_position=Decimal('0'),
            target_delta=Decimal('0')
        )
        
        # Should need to hedge full delta
        self.assertEqual(adjustment, Decimal('2.0'))
    
    def test_calculate_optimal_hedge_size_overhedged(self):
        """Test optimal hedge when position is over-hedged"""
        adjustment = self.risk_manager.calculate_optimal_hedge_size(
            current_delta=Decimal('1.0'),
            current_hedge_position=Decimal('-2.0'),
            target_delta=Decimal('0')
        )
        
        # Net delta = 1.0 + (-2.0) = -1.0
        # Need to reduce hedge (positive adjustment to close shorts)
        self.assertEqual(adjustment, Decimal('-1.0'))
    
    def test_calculate_position_delta_very_small_price(self):
        """Test delta calculation with very small price"""
        delta = self.risk_manager.calculate_position_delta(
            token0_amount=Decimal('1.0'),
            token1_amount=Decimal('1000'),
            current_price=Decimal('0.001')
        )
        
        # token1_in_token0 = 1000 / 0.001 = 1,000,000
        # delta = 1.0 - 1,000,000 = -999,999
        self.assertLess(delta, Decimal('0'))
        self.assertGreater(delta, Decimal('-1000000'))
    
    def test_calculate_gamma_with_zero_liquidity(self):
        """Test gamma calculation with zero liquidity"""
        gamma = self.risk_manager.calculate_gamma(
            liquidity=Decimal('0'),
            current_tick=0,
            tick_lower=-1000,
            tick_upper=1000
        )
        
        # Should return 0 for zero liquidity
        self.assertEqual(gamma, Decimal('0'))
    
    def test_calculate_gamma_at_range_edge(self):
        """Test gamma calculation when price is exactly at range bounds"""
        # At lower bound
        gamma_lower = self.risk_manager.calculate_gamma(
            liquidity=Decimal('1000000'),
            current_tick=-1000,
            tick_lower=-1000,
            tick_upper=1000
        )
        
        # At upper bound
        gamma_upper = self.risk_manager.calculate_gamma(
            liquidity=Decimal('1000000'),
            current_tick=1000,
            tick_lower=-1000,
            tick_upper=1000
        )
        
        # Should be positive at edges but lower than center
        self.assertGreaterEqual(gamma_lower, Decimal('0'))
        self.assertGreaterEqual(gamma_upper, Decimal('0'))
    
    def test_assess_risk_level_high_negative_pnl(self):
        """Test risk level assessment with high negative PnL"""
        metrics = RiskMetrics(
            impermanent_loss=Decimal('1000'),
            impermanent_loss_percent=Decimal('0.10'),
            accumulated_fees=Decimal('100'),
            net_pnl=Decimal('-1500'),  # Very negative
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.05'),
            gamma=Decimal('100'),
            needs_rebalance=False,
            recommended_hedge_size=Decimal('0')
        )
        
        risk_level = self.risk_manager._assess_risk_level(metrics)
        self.assertEqual(risk_level, 'HIGH')
    
    def test_assess_risk_level_very_high_delta(self):
        """Test risk level assessment with very high delta"""
        metrics = RiskMetrics(
            impermanent_loss=Decimal('100'),
            impermanent_loss_percent=Decimal('0.02'),
            accumulated_fees=Decimal('200'),
            net_pnl=Decimal('100'),
            downside_risk=Decimal('500'),
            value_at_risk=Decimal('300'),
            delta=Decimal('0.25'),  # More than 2x threshold (0.1)
            gamma=Decimal('100'),
            needs_rebalance=False,
            recommended_hedge_size=Decimal('0.25')
        )
        
        risk_level = self.risk_manager._assess_risk_level(metrics)
        self.assertEqual(risk_level, 'HIGH')


if __name__ == '__main__':
    unittest.main()
