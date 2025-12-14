"""
Main Bot Entry Point

Orchestrates the delta-neutral hedging bot, coordinating position reading,
risk assessment, and hedge execution.
"""

import asyncio
import logging
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from decimal import Decimal
from dotenv import load_dotenv
import signal

from bot.position_reader import PositionReader, Position
from bot.hedging_executor import HedgingExecutor, OrderSide
from bot.risk_management import RiskManagement, RiskMetrics
from bot.config import load_config, get_default_config

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)


class DeltaNeutralBot:
    """Main bot orchestrating delta-neutral hedging strategy"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the bot.
        
        Args:
            config_path: Path to configuration file (optional, env vars take precedence)
        """
        # Load configuration from file and environment variables
        self.config = load_config(config_path)
        
        # Fall back to defaults if no config loaded
        if not self.config:
            logger.warning("No configuration loaded, using defaults")
            self.config = get_default_config()
        
        # Initialize components
        self.position_reader = PositionReader(self.config)
        self.hedging_executor = HedgingExecutor(self.config)
        self.risk_manager = RiskManagement(self.config)
        
        # Bot state
        self.running = False
        self.wallet_address = self.config.get('wallet_address', '')
        self.update_interval = self.config.get('update_interval_seconds', 60)
        self.hedge_symbol = self.config.get('hedge_symbol', 'ETH-USD')
        
        # Performance tracking
        self.total_hedges_executed = 0
        self.total_fees_paid = Decimal(0)
        self.total_pnl = Decimal(0)
        
        logger.info("DeltaNeutralBot initialized")
    

    
    async def start(self):
        """Start the bot main loop"""
        logger.info("Starting DeltaNeutralBot...")
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            while self.running:
                await self._run_cycle()
                
                if self.running:
                    logger.info(f"Waiting {self.update_interval} seconds until next cycle...")
                    await asyncio.sleep(self.update_interval)
        except Exception as e:
            logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            await self.stop()
    
    async def _run_cycle(self):
        """Run one complete bot cycle"""
        logger.info("=" * 80)
        logger.info("Starting new bot cycle")
        logger.info("=" * 80)
        
        try:
            # Step 1: Fetch all positions
            positions = await self._fetch_positions()
            
            if not positions:
                logger.warning("No positions found")
                return
            
            # Step 2: Analyze positions and calculate total delta
            total_delta, risk_metrics_list = await self._analyze_positions(positions)
            
            # Step 3: Get current hedge position
            current_hedge = await self.hedging_executor.get_current_position(self.hedge_symbol)
            if current_hedge is None:
                logger.error("Could not fetch current hedge position")
                current_hedge = Decimal(0)
            
            # Step 4: Calculate net delta including hedge
            net_delta = total_delta + current_hedge
            logger.info(f"Total LP Delta: {total_delta}")
            logger.info(f"Current Hedge: {current_hedge}")
            logger.info(f"Net Delta: {net_delta}")
            
            # Step 5: Determine if hedging is needed
            needs_hedge = abs(net_delta) > self.risk_manager.delta_threshold
            
            if needs_hedge:
                await self._execute_hedge(net_delta, current_hedge)
            else:
                logger.info("Position is within delta threshold, no hedging needed")
            
            # Step 6: Generate and log reports
            self._log_performance_report(risk_metrics_list)
            
        except Exception as e:
            logger.error(f"Error in bot cycle: {e}", exc_info=True)
    
    async def _fetch_positions(self) -> List[Position]:
        """Fetch all positions"""
        logger.info("Fetching positions...")
        
        if not self.wallet_address:
            logger.error("No wallet address configured")
            return []
        
        positions = await self.position_reader.fetch_positions(self.wallet_address)
        logger.info(f"Found {len(positions)} positions")
        
        return positions
    
    async def _analyze_positions(self, positions: List[Position]) -> tuple:
        """
        Analyze all positions and calculate metrics.
        
        Returns:
            Tuple of (total_delta, list of risk_metrics)
        """
        logger.info("Analyzing positions...")
        
        total_delta = Decimal(0)
        risk_metrics_list = []
        
        for position in positions:
            # Calculate risk metrics
            risk_metrics = self.risk_manager.assess_position_risk(position)
            risk_metrics_list.append((position, risk_metrics))
            
            # Accumulate delta
            total_delta += risk_metrics.delta
            
            # Log position details
            logger.info(f"\nPosition: {position.position_id}")
            logger.info(f"  Protocol: {position.protocol}")
            logger.info(f"  Pair: {position.token0_symbol}/{position.token1_symbol}")
            logger.info(f"  Value: ${position.total_value_usd}")
            logger.info(f"  Delta: {risk_metrics.delta}")
            logger.info(f"  IL: {risk_metrics.impermanent_loss_percent * 100:.2f}%")
            logger.info(f"  Fees: ${risk_metrics.accumulated_fees}")
            logger.info(f"  Net PnL: ${risk_metrics.net_pnl}")
            
            # Generate detailed risk report
            risk_report = self.risk_manager.get_risk_report(risk_metrics)
            logger.info(f"  Risk Level: {risk_report['risk_level']}")
        
        return total_delta, risk_metrics_list
    
    async def _execute_hedge(self, net_delta: Decimal, current_hedge: Decimal):
        """
        Execute hedge to neutralize delta.
        
        Args:
            net_delta: Current net delta including hedge
            current_hedge: Current hedge position
        """
        logger.info("Executing hedge adjustment...")
        
        # Calculate required adjustment
        required_adjustment = self.risk_manager.calculate_optimal_hedge_size(
            current_delta=net_delta - current_hedge,
            current_hedge_position=current_hedge,
            target_delta=Decimal(0)
        )
        
        logger.info(f"Required hedge adjustment: {required_adjustment}")
        
        # Determine action
        if abs(required_adjustment) < self.hedging_executor.min_order_size:
            logger.info("Adjustment too small, skipping")
            return
        
        # Execute the hedge
        if required_adjustment > 0:
            # Need to increase short position (or decrease long)
            result = await self.hedging_executor.increase_hedge(
                self.hedge_symbol,
                abs(required_adjustment)
            )
        else:
            # Need to decrease short position (or increase long)
            result = await self.hedging_executor.decrease_hedge(
                self.hedge_symbol,
                abs(required_adjustment)
            )
        
        # Log result
        if result.success:
            logger.info(f"✓ Hedge executed successfully")
            logger.info(f"  Order ID: {result.order_id}")
            logger.info(f"  Size: {result.executed_size}")
            logger.info(f"  Price: {result.executed_price}")
            
            self.total_hedges_executed += 1
        else:
            logger.error(f"✗ Hedge execution failed: {result.message}")
    
    def _log_performance_report(self, risk_metrics_list: List[tuple]):
        """Log overall performance report"""
        logger.info("\n" + "=" * 80)
        logger.info("PERFORMANCE REPORT")
        logger.info("=" * 80)
        
        # Aggregate metrics
        total_value = Decimal(0)
        total_il = Decimal(0)
        total_fees = Decimal(0)
        total_pnl = Decimal(0)
        
        for position, metrics in risk_metrics_list:
            total_value += position.total_value_usd
            total_il += metrics.impermanent_loss
            total_fees += metrics.accumulated_fees
            total_pnl += metrics.net_pnl
        
        logger.info(f"Total Position Value: ${total_value}")
        logger.info(f"Total Impermanent Loss: ${total_il}")
        logger.info(f"Total Fees Earned: ${total_fees}")
        logger.info(f"Total Net PnL: ${total_pnl}")
        logger.info(f"Total Hedges Executed: {self.total_hedges_executed}")
        logger.info("=" * 80)
    
    async def stop(self):
        """Stop the bot gracefully"""
        logger.info("Stopping DeltaNeutralBot...")
        self.running = False
        
        # Optional: Close all positions on shutdown
        close_on_shutdown = self.config.get('close_positions_on_shutdown', False)
        if close_on_shutdown:
            logger.warning("Closing all hedge positions...")
            await self.hedging_executor.close_all_positions()
        
        logger.info("Bot stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False


async def main():
    """Main entry point"""
    # Parse command line arguments
    config_path = "config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    # Create and start bot
    bot = DeltaNeutralBot(config_path)
    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot terminated by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
