"""
Risk Management Module

Computes and manages risk metrics including downside risk, fees, impermanent loss,
and other considerations for delta-neutral liquidity provision.
"""

import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Risk metrics for a position"""
    impermanent_loss: Decimal
    impermanent_loss_percent: Decimal
    accumulated_fees: Decimal
    net_pnl: Decimal
    downside_risk: Decimal
    value_at_risk: Decimal
    delta: Decimal
    gamma: Decimal
    needs_rebalance: bool
    recommended_hedge_size: Decimal


class RiskManagement:
    """Manages risk calculations and thresholds for delta-neutral strategy"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize risk management.
        
        Args:
            config: Configuration dictionary with risk parameters
        """
        self.config = config
        
        # Risk thresholds
        self.delta_threshold = Decimal(str(config.get('delta_threshold', 0.1)))
        self.max_impermanent_loss = Decimal(str(config.get('max_impermanent_loss', 0.05)))  # 5%
        self.min_fee_coverage = Decimal(str(config.get('min_fee_coverage', 1.5)))  # Fees should cover IL by 1.5x
        self.rebalance_threshold = Decimal(str(config.get('rebalance_threshold', 0.05)))  # 5% delta change
        
        # VaR parameters
        self.var_confidence = Decimal(str(config.get('var_confidence', 0.95)))  # 95% confidence
        self.volatility_lookback = config.get('volatility_lookback', 30)  # days
        
        # Position limits
        self.max_position_value = Decimal(str(config.get('max_position_value', 100000)))
        self.max_leverage = Decimal(str(config.get('max_leverage', 1.0)))
    
    def calculate_impermanent_loss(
        self,
        initial_price: Decimal,
        current_price: Decimal,
        initial_token0: Decimal,
        initial_token1: Decimal
    ) -> Decimal:
        """
        Calculate impermanent loss for a liquidity position.
        
        IL = (Value if held) - (Value in LP) / (Value if held)
        
        Args:
            initial_price: Price when position was opened
            current_price: Current price
            initial_token0: Initial amount of token0
            initial_token1: Initial amount of token1
            
        Returns:
            Impermanent loss as a decimal (e.g., 0.05 = 5% loss)
        """
        try:
            if initial_price <= 0 or current_price <= 0:
                return Decimal(0)
            
            # Price ratio
            price_ratio = current_price / initial_price
            
            # For a standard AMM (constant product formula)
            # IL = 2 * sqrt(price_ratio) / (1 + price_ratio) - 1
            sqrt_ratio = Decimal(math.sqrt(float(price_ratio)))
            il = 2 * sqrt_ratio / (1 + price_ratio) - 1
            
            return abs(il)
            
        except Exception as e:
            logger.error(f"Error calculating impermanent loss: {e}")
            return Decimal(0)
    
    def calculate_concentrated_il(
        self,
        current_price: Decimal,
        lower_price: Decimal,
        upper_price: Decimal,
        entry_price: Decimal
    ) -> Decimal:
        """
        Calculate impermanent loss for concentrated liquidity positions.
        
        Concentrated liquidity has different IL characteristics than full-range positions.
        
        Args:
            current_price: Current price
            lower_price: Lower bound of liquidity range
            upper_price: Upper bound of liquidity range
            entry_price: Price when position was entered
            
        Returns:
            Impermanent loss percentage
        """
        try:
            if current_price <= 0 or entry_price <= 0:
                return Decimal(0)
            
            # Check if price is within range
            if current_price < lower_price or current_price > upper_price:
                # Price out of range - position is fully in one token
                # Maximum IL occurs here
                return self.calculate_impermanent_loss(
                    entry_price,
                    current_price,
                    Decimal(1),
                    Decimal(1)
                )
            
            # For concentrated positions, IL is amplified within the range
            # Approximate using the concentration factor
            concentration_factor = Decimal(2) / (
                (upper_price - lower_price) / ((upper_price + lower_price) / 2)
            )
            
            base_il = self.calculate_impermanent_loss(
                entry_price,
                current_price,
                Decimal(1),
                Decimal(1)
            )
            
            # Concentrated IL is approximately base IL * concentration factor
            return base_il * concentration_factor
            
        except Exception as e:
            logger.error(f"Error calculating concentrated IL: {e}")
            return Decimal(0)
    
    def calculate_downside_risk(
        self,
        position_value: Decimal,
        current_price: Decimal,
        volatility: Decimal,
        time_horizon_days: int = 1
    ) -> Decimal:
        """
        Calculate downside risk using historical volatility.
        
        Args:
            position_value: Current position value
            current_price: Current price
            volatility: Historical volatility (annualized)
            time_horizon_days: Risk horizon in days
            
        Returns:
            Downside risk amount
        """
        try:
            if volatility <= 0 or position_value <= 0:
                return Decimal(0)
            
            # Adjust volatility for time horizon
            time_factor = Decimal(math.sqrt(time_horizon_days / 365))
            adjusted_vol = volatility * time_factor
            
            # Approximate downside move (2 standard deviations)
            downside_move = current_price * adjusted_vol * Decimal(2)
            
            # Calculate potential loss
            downside_risk = position_value * (downside_move / current_price)
            
            return downside_risk
            
        except Exception as e:
            logger.error(f"Error calculating downside risk: {e}")
            return Decimal(0)
    
    def calculate_value_at_risk(
        self,
        position_value: Decimal,
        volatility: Decimal,
        confidence: Optional[Decimal] = None
    ) -> Decimal:
        """
        Calculate Value at Risk (VaR) for a position.
        
        Args:
            position_value: Current position value
            volatility: Historical volatility (annualized)
            confidence: Confidence level (default from config)
            
        Returns:
            VaR amount
        """
        try:
            if confidence is None:
                confidence = self.var_confidence
            
            # Z-score for confidence level
            # 95% confidence ≈ 1.645, 99% ≈ 2.326
            if confidence >= Decimal('0.99'):
                z_score = Decimal('2.326')
            elif confidence >= Decimal('0.95'):
                z_score = Decimal('1.645')
            else:
                z_score = Decimal('1.282')  # 90%
            
            # Daily VaR
            daily_vol = volatility / Decimal(math.sqrt(365))
            var = position_value * daily_vol * z_score
            
            return var
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return Decimal(0)
    
    def calculate_position_delta(
        self,
        token0_amount: Decimal,
        token1_amount: Decimal,
        current_price: Decimal
    ) -> Decimal:
        """
        Calculate delta (directional exposure) of a position.
        
        Delta = 0 means perfectly neutral
        Delta > 0 means long exposure
        Delta < 0 means short exposure
        
        Args:
            token0_amount: Amount of token0
            token1_amount: Amount of token1
            current_price: Current price (token1/token0)
            
        Returns:
            Delta in token0 terms
        """
        try:
            if current_price <= 0:
                return Decimal(0)
            
            # Convert token1 to token0 equivalent
            token1_in_token0 = token1_amount / current_price
            
            # Delta is the difference
            delta = token0_amount - token1_in_token0
            
            return delta
            
        except Exception as e:
            logger.error(f"Error calculating delta: {e}")
            return Decimal(0)
    
    def calculate_gamma(
        self,
        liquidity: Decimal,
        current_tick: int,
        tick_lower: int,
        tick_upper: int
    ) -> Decimal:
        """
        Calculate gamma (rate of change of delta).
        
        Gamma measures how much delta changes with price movements.
        High gamma means delta changes rapidly.
        
        Args:
            liquidity: Position liquidity
            current_tick: Current pool tick
            tick_lower: Lower tick of position
            tick_upper: Upper tick of position
            
        Returns:
            Gamma value
        """
        try:
            if liquidity <= 0:
                return Decimal(0)
            
            # Check if in range
            if current_tick < tick_lower or current_tick > tick_upper:
                return Decimal(0)
            
            # Gamma is highest at the middle of the range
            range_width = tick_upper - tick_lower
            if range_width == 0:
                return Decimal(0)
            
            tick_from_center = abs(current_tick - (tick_lower + tick_upper) // 2)
            
            # Simplified gamma calculation
            # In reality, this would be more complex based on the curve
            gamma = liquidity / Decimal(range_width) * (
                Decimal(1) - Decimal(tick_from_center) / Decimal(range_width / 2)
            )
            
            return max(gamma, Decimal(0))
            
        except Exception as e:
            logger.error(f"Error calculating gamma: {e}")
            return Decimal(0)
    
    def assess_position_risk(
        self,
        position: Any,  # Position object from position_reader
        current_volatility: Decimal = Decimal('0.5')  # Default 50% annualized
    ) -> RiskMetrics:
        """
        Comprehensive risk assessment for a position.
        
        Args:
            position: Position object
            current_volatility: Current market volatility estimate
            
        Returns:
            RiskMetrics object
        """
        try:
            # Calculate impermanent loss
            il = self.calculate_concentrated_il(
                current_price=position.price,
                lower_price=self._tick_to_price(position.tick_lower),
                upper_price=self._tick_to_price(position.tick_upper),
                entry_price=position.price  # Simplified - would track actual entry
            )
            
            # Calculate fees
            accumulated_fees = position.unclaimed_fees0 + position.unclaimed_fees1
            
            # Net PnL (fees - IL)
            il_value = position.total_value_usd * il
            net_pnl = accumulated_fees - il_value
            
            # Calculate delta
            delta = self.calculate_position_delta(
                position.token0_amount,
                position.token1_amount,
                position.price
            )
            
            # Calculate gamma
            gamma = self.calculate_gamma(
                position.liquidity,
                position.current_tick,
                position.tick_lower,
                position.tick_upper
            )
            
            # Calculate downside risk
            downside_risk = self.calculate_downside_risk(
                position.total_value_usd,
                position.price,
                current_volatility
            )
            
            # Calculate VaR
            var = self.calculate_value_at_risk(
                position.total_value_usd,
                current_volatility
            )
            
            # Determine if rebalance is needed
            delta_ratio = abs(delta * position.price / position.total_value_usd) if position.total_value_usd > 0 else Decimal(0)
            needs_rebalance = delta_ratio > self.rebalance_threshold
            
            # Recommend hedge size
            recommended_hedge_size = delta if needs_rebalance else Decimal(0)
            
            return RiskMetrics(
                impermanent_loss=il_value,
                impermanent_loss_percent=il,
                accumulated_fees=accumulated_fees,
                net_pnl=net_pnl,
                downside_risk=downside_risk,
                value_at_risk=var,
                delta=delta,
                gamma=gamma,
                needs_rebalance=needs_rebalance,
                recommended_hedge_size=recommended_hedge_size
            )
            
        except Exception as e:
            logger.error(f"Error assessing position risk: {e}")
            return RiskMetrics(
                impermanent_loss=Decimal(0),
                impermanent_loss_percent=Decimal(0),
                accumulated_fees=Decimal(0),
                net_pnl=Decimal(0),
                downside_risk=Decimal(0),
                value_at_risk=Decimal(0),
                delta=Decimal(0),
                gamma=Decimal(0),
                needs_rebalance=False,
                recommended_hedge_size=Decimal(0)
            )
    
    def should_hedge(self, risk_metrics: RiskMetrics) -> bool:
        """
        Determine if hedging is needed based on risk metrics.
        
        Args:
            risk_metrics: RiskMetrics object
            
        Returns:
            True if hedging should be performed
        """
        # Check if delta exceeds threshold
        if abs(risk_metrics.delta) > self.delta_threshold:
            logger.info(f"Delta {risk_metrics.delta} exceeds threshold {self.delta_threshold}")
            return True
        
        # Check if IL is too high and not covered by fees
        if risk_metrics.impermanent_loss_percent > self.max_impermanent_loss:
            fee_coverage = (
                risk_metrics.accumulated_fees / risk_metrics.impermanent_loss
                if risk_metrics.impermanent_loss > 0
                else Decimal('inf')
            )
            if fee_coverage < self.min_fee_coverage:
                logger.info("IL too high and not covered by fees")
                return True
        
        return risk_metrics.needs_rebalance
    
    def calculate_optimal_hedge_size(
        self,
        current_delta: Decimal,
        current_hedge_position: Decimal,
        target_delta: Decimal = Decimal(0)
    ) -> Decimal:
        """
        Calculate optimal hedge size to achieve target delta.
        
        Args:
            current_delta: Current position delta
            current_hedge_position: Current hedge position on Hyperliquid
            target_delta: Target delta (default 0 for delta-neutral)
            
        Returns:
            Required hedge adjustment (positive = increase short, negative = decrease short)
        """
        # Calculate delta including current hedge
        net_delta = current_delta + current_hedge_position
        
        # Calculate required adjustment
        adjustment = net_delta - target_delta
        
        return adjustment
    
    def _tick_to_price(self, tick: int) -> Decimal:
        """
        Convert tick to price.
        
        Args:
            tick: Tick value
            
        Returns:
            Price
        """
        try:
            # Uniswap V3 tick formula: price = 1.0001^tick
            return Decimal(str(1.0001 ** tick))
        except Exception as e:
            logger.error(f"Error converting tick to price: {e}")
            return Decimal(0)
    
    def get_risk_report(self, risk_metrics: RiskMetrics) -> Dict[str, Any]:
        """
        Generate a human-readable risk report.
        
        Args:
            risk_metrics: RiskMetrics object
            
        Returns:
            Dictionary with risk report
        """
        return {
            "impermanent_loss_usd": float(risk_metrics.impermanent_loss),
            "impermanent_loss_percent": float(risk_metrics.impermanent_loss_percent * 100),
            "accumulated_fees_usd": float(risk_metrics.accumulated_fees),
            "net_pnl_usd": float(risk_metrics.net_pnl),
            "downside_risk_usd": float(risk_metrics.downside_risk),
            "value_at_risk_usd": float(risk_metrics.value_at_risk),
            "delta": float(risk_metrics.delta),
            "gamma": float(risk_metrics.gamma),
            "needs_rebalance": risk_metrics.needs_rebalance,
            "recommended_hedge_size": float(risk_metrics.recommended_hedge_size),
            "risk_level": self._assess_risk_level(risk_metrics)
        }
    
    def _assess_risk_level(self, risk_metrics: RiskMetrics) -> str:
        """Assess overall risk level"""
        if risk_metrics.net_pnl < -risk_metrics.impermanent_loss:
            return "HIGH"
        elif abs(risk_metrics.delta) > self.delta_threshold * 2:
            return "HIGH"
        elif risk_metrics.needs_rebalance:
            return "MEDIUM"
        else:
            return "LOW"
