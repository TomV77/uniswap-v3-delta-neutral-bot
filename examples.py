"""
Example usage of the Delta-Neutral Bot

This example demonstrates how to use the bot programmatically
and how to interact with its components.
"""

import asyncio
from decimal import Decimal
from bot.position_reader import PositionReader, Position
from bot.hedging_executor import HedgingExecutor, HedgeOrder, OrderSide
from bot.risk_management import RiskManagement


async def example_position_analysis():
    """Example: Analyze a mock position"""
    print("=" * 80)
    print("EXAMPLE 1: Position Analysis")
    print("=" * 80)
    
    # Create a mock position (in production, this would be fetched from chain)
    # Note: These are example token addresses for demonstration purposes only
    position = Position(
        position_id='example-1',
        protocol='uniswap',
        token0='0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',  # WETH (example address)
        token1='0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',  # USDC (example address)
        token0_symbol='WETH',
        token1_symbol='USDC',
        liquidity=Decimal('1000000'),
        tick_lower=-887220,
        tick_upper=887220,
        current_tick=0,
        token0_amount=Decimal('2.5'),      # 2.5 ETH
        token1_amount=Decimal('5000'),      # 5000 USDC
        unclaimed_fees0=Decimal('0.05'),    # 0.05 ETH
        unclaimed_fees1=Decimal('100'),     # 100 USDC
        price=Decimal('2000'),              # 1 ETH = 2000 USDC
        total_value_usd=Decimal('10000')    # $10,000 position
    )
    
    # Initialize risk manager
    config = {
        'delta_threshold': 0.1,
        'rebalance_threshold': 0.05,
        'max_impermanent_loss': 0.05,
        'min_fee_coverage': 1.5
    }
    risk_manager = RiskManagement(config)
    
    # Analyze the position
    risk_metrics = risk_manager.assess_position_risk(position, current_volatility=Decimal('0.6'))
    
    print(f"\nPosition: {position.position_id}")
    print(f"Protocol: {position.protocol}")
    print(f"Pair: {position.token0_symbol}/{position.token1_symbol}")
    print(f"Total Value: ${position.total_value_usd}")
    print(f"\nToken Amounts:")
    print(f"  {position.token0_symbol}: {position.token0_amount}")
    print(f"  {position.token1_symbol}: {position.token1_amount}")
    print(f"\nUnclaimed Fees:")
    print(f"  {position.token0_symbol}: {position.unclaimed_fees0}")
    print(f"  {position.token1_symbol}: {position.unclaimed_fees1}")
    
    # Display risk metrics
    risk_report = risk_manager.get_risk_report(risk_metrics)
    print(f"\n{'Risk Analysis':=^60}")
    print(f"Delta: {risk_report['delta']:.4f} ETH")
    print(f"Gamma: {risk_report['gamma']:.2f}")
    print(f"Impermanent Loss: ${risk_report['impermanent_loss_usd']:.2f} ({risk_report['impermanent_loss_percent']:.2f}%)")
    print(f"Fees Earned: ${risk_report['accumulated_fees_usd']:.2f}")
    print(f"Net PnL: ${risk_report['net_pnl_usd']:.2f}")
    print(f"Value at Risk (95%): ${risk_report['value_at_risk_usd']:.2f}")
    print(f"Downside Risk: ${risk_report['downside_risk_usd']:.2f}")
    print(f"Risk Level: {risk_report['risk_level']}")
    print(f"Needs Rebalance: {risk_report['needs_rebalance']}")
    if risk_report['needs_rebalance']:
        print(f"Recommended Hedge: {risk_report['recommended_hedge_size']:.4f} ETH")


async def example_delta_calculation():
    """Example: Calculate delta for different positions"""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Delta Calculation Scenarios")
    print("=" * 80)
    
    config = {'delta_threshold': 0.1}
    risk_manager = RiskManagement(config)
    
    scenarios = [
        {
            'name': 'Delta-Neutral Position',
            'token0_amount': Decimal('1.5'),
            'token1_amount': Decimal('3000'),
            'price': Decimal('2000')
        },
        {
            'name': 'Long-Biased Position',
            'token0_amount': Decimal('2.0'),
            'token1_amount': Decimal('2000'),
            'price': Decimal('2000')
        },
        {
            'name': 'Short-Biased Position',
            'token0_amount': Decimal('1.0'),
            'token1_amount': Decimal('4000'),
            'price': Decimal('2000')
        }
    ]
    
    for scenario in scenarios:
        delta = risk_manager.calculate_position_delta(
            scenario['token0_amount'],
            scenario['token1_amount'],
            scenario['price']
        )
        
        print(f"\n{scenario['name']}:")
        print(f"  ETH: {scenario['token0_amount']}")
        print(f"  USDC: {scenario['token1_amount']}")
        print(f"  Price: ${scenario['price']}")
        print(f"  Delta: {delta:.4f} ETH")
        
        if delta > 0:
            print(f"  → Long exposure: Need to SHORT {abs(delta):.4f} ETH to hedge")
        elif delta < 0:
            print(f"  → Short exposure: Need to LONG {abs(delta):.4f} ETH to hedge")
        else:
            print(f"  → Delta-neutral: No hedging needed")


async def example_impermanent_loss():
    """Example: Calculate IL for different price movements"""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Impermanent Loss Scenarios")
    print("=" * 80)
    
    config = {}
    risk_manager = RiskManagement(config)
    
    initial_price = Decimal('2000')
    
    price_scenarios = [
        ('No Change', Decimal('2000')),
        ('+10% Price Increase', Decimal('2200')),
        ('+50% Price Increase', Decimal('3000')),
        ('+100% Price Increase (2x)', Decimal('4000')),
        ('-10% Price Decrease', Decimal('1800')),
        ('-50% Price Decrease', Decimal('1000')),
    ]
    
    print(f"\nInitial Price: ${initial_price}")
    print(f"\n{'Scenario':<30} {'New Price':<15} {'IL %':<10} {'IL Impact':<20}")
    print("-" * 80)
    
    for name, new_price in price_scenarios:
        il = risk_manager.calculate_impermanent_loss(
            initial_price,
            new_price,
            Decimal('1'),
            Decimal('2000')
        )
        
        # Calculate on $10k position
        il_dollar = il * Decimal('10000')
        
        print(f"{name:<30} ${new_price:<14} {float(il)*100:<9.2f}% ${float(il_dollar):<19.2f}")


async def example_hedging_strategy():
    """Example: Demonstrate hedging strategy"""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Hedging Strategy Simulation")
    print("=" * 80)
    
    config = {'delta_threshold': 0.1}
    risk_manager = RiskManagement(config)
    
    # Initial position: Long 2.0 ETH worth of exposure
    lp_delta = Decimal('2.0')
    current_hedge = Decimal('0')  # No hedge yet
    
    print(f"\nInitial State:")
    print(f"  LP Position Delta: {lp_delta} ETH (long exposure)")
    print(f"  Current Hedge: {current_hedge} ETH")
    print(f"  Net Delta: {lp_delta + current_hedge} ETH")
    
    # Calculate optimal hedge
    optimal_hedge = risk_manager.calculate_optimal_hedge_size(
        current_delta=lp_delta,
        current_hedge_position=current_hedge,
        target_delta=Decimal('0')
    )
    
    print(f"\nHedging Decision:")
    print(f"  Required Adjustment: {optimal_hedge} ETH")
    print(f"  Action: SHORT {abs(optimal_hedge)} ETH on Hyperliquid")
    
    # After hedging
    new_hedge = current_hedge - optimal_hedge  # Short = negative position
    net_delta = lp_delta + new_hedge
    
    print(f"\nAfter Hedging:")
    print(f"  LP Position Delta: {lp_delta} ETH")
    print(f"  Hedge Position: {new_hedge} ETH (short)")
    print(f"  Net Delta: {net_delta} ETH")
    print(f"  Status: {'✓ Delta-Neutral' if abs(net_delta) < Decimal('0.01') else '✗ Not Neutral'}")


async def example_risk_thresholds():
    """Example: Show risk threshold triggering"""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Risk Threshold Triggers")
    print("=" * 80)
    
    config = {
        'delta_threshold': 0.1,
        'max_impermanent_loss': 0.05,
        'min_fee_coverage': 1.5
    }
    risk_manager = RiskManagement(config)
    
    # Scenario 1: High delta
    print("\nScenario 1: High Delta")
    metrics1 = {
        'impermanent_loss': Decimal('100'),
        'impermanent_loss_percent': Decimal('0.02'),
        'accumulated_fees': Decimal('200'),
        'net_pnl': Decimal('100'),
        'downside_risk': Decimal('500'),
        'value_at_risk': Decimal('300'),
        'delta': Decimal('0.5'),  # High!
        'gamma': Decimal('100'),
        'needs_rebalance': True,
        'recommended_hedge_size': Decimal('0.5')
    }
    from bot.risk_management import RiskMetrics
    rm1 = RiskMetrics(**metrics1)
    should_hedge1 = risk_manager.should_hedge(rm1)
    print(f"  Delta: {rm1.delta}")
    print(f"  Threshold: {config['delta_threshold']}")
    print(f"  Should Hedge: {'YES ✓' if should_hedge1 else 'NO'}")
    
    # Scenario 2: High IL, low fees
    print("\nScenario 2: High IL, Low Fee Coverage")
    metrics2 = {
        'impermanent_loss': Decimal('1000'),
        'impermanent_loss_percent': Decimal('0.10'),  # 10%
        'accumulated_fees': Decimal('500'),  # Not enough
        'net_pnl': Decimal('-500'),
        'downside_risk': Decimal('500'),
        'value_at_risk': Decimal('300'),
        'delta': Decimal('0.05'),
        'gamma': Decimal('100'),
        'needs_rebalance': False,
        'recommended_hedge_size': Decimal('0')
    }
    rm2 = RiskMetrics(**metrics2)
    should_hedge2 = risk_manager.should_hedge(rm2)
    fee_coverage = rm2.accumulated_fees / rm2.impermanent_loss if rm2.impermanent_loss > 0 else Decimal('inf')
    print(f"  IL: {rm2.impermanent_loss_percent * 100}%")
    print(f"  Fee Coverage Ratio: {fee_coverage:.2f}x")
    print(f"  Required Coverage: {config['min_fee_coverage']}x")
    print(f"  Should Hedge: {'YES ✓' if should_hedge2 else 'NO'}")
    
    # Scenario 3: All good
    print("\nScenario 3: Healthy Position")
    metrics3 = {
        'impermanent_loss': Decimal('100'),
        'impermanent_loss_percent': Decimal('0.01'),
        'accumulated_fees': Decimal('500'),
        'net_pnl': Decimal('400'),
        'downside_risk': Decimal('500'),
        'value_at_risk': Decimal('300'),
        'delta': Decimal('0.05'),
        'gamma': Decimal('100'),
        'needs_rebalance': False,
        'recommended_hedge_size': Decimal('0')
    }
    rm3 = RiskMetrics(**metrics3)
    should_hedge3 = risk_manager.should_hedge(rm3)
    print(f"  Delta: {rm3.delta}")
    print(f"  IL: {rm3.impermanent_loss_percent * 100}%")
    print(f"  Net PnL: ${rm3.net_pnl}")
    print(f"  Should Hedge: {'YES ✓' if should_hedge3 else 'NO'}")


async def main():
    """Run all examples"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "DELTA-NEUTRAL BOT EXAMPLES" + " " * 37 + "║")
    print("╚" + "=" * 78 + "╝")
    
    await example_position_analysis()
    await example_delta_calculation()
    await example_impermanent_loss()
    await example_hedging_strategy()
    await example_risk_thresholds()
    
    print("\n" + "=" * 80)
    print("Examples completed! Check the README.md for more information.")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    asyncio.run(main())
