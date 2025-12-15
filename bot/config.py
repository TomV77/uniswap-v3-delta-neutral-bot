"""
Configuration utilities for loading settings from environment variables and config files.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def load_config_from_env() -> Dict[str, Any]:
    """
    Load configuration from environment variables.
    
    Returns:
        Dictionary with configuration values from environment
    """
    config = {}
    
    # Wallet configuration
    if os.getenv('WALLET_ADDRESS'):
        config['wallet_address'] = os.getenv('WALLET_ADDRESS')
    
    # RPC configuration (Base chain only)
    if os.getenv('RPC_URL'):
        config['rpc_url'] = os.getenv('RPC_URL')
    
    # VFAT configuration
    if os.getenv('VFAT_API_URL'):
        config['vfat_api_url'] = os.getenv('VFAT_API_URL')
    if os.getenv('VFAT_SICKLE_ADDRESS'):
        config['sickle_contract_address'] = os.getenv('VFAT_SICKLE_ADDRESS')
    
    # Contract addresses (Base chain only)
    if os.getenv('UNISWAP_V3_NFT_ADDRESS'):
        config['uniswap_v3_nft_address'] = os.getenv('UNISWAP_V3_NFT_ADDRESS')
    
    if os.getenv('AERODROME_NFT_ADDRESS'):
        config['aerodrome_nft_address'] = os.getenv('AERODROME_NFT_ADDRESS')
    
    # Hyperliquid configuration
    if os.getenv('HYPERLIQUID_PRIVATE_KEY'):
        config['hyperliquid_api_key'] = os.getenv('HYPERLIQUID_PRIVATE_KEY')
        config['hyperliquid_api_secret'] = os.getenv('HYPERLIQUID_PRIVATE_KEY')
    
    if os.getenv('HYPERLIQUID_API_URL'):
        config['hyperliquid_api_url'] = os.getenv('HYPERLIQUID_API_URL')
    
    if os.getenv('HYPERLIQUID_TESTNET'):
        config['hyperliquid_testnet'] = os.getenv('HYPERLIQUID_TESTNET').lower() == 'true'
    
    # Bot configuration
    if os.getenv('UPDATE_INTERVAL_SECONDS'):
        config['update_interval_seconds'] = int(os.getenv('UPDATE_INTERVAL_SECONDS'))
    
    if os.getenv('HEDGE_SYMBOL'):
        config['hedge_symbol'] = os.getenv('HEDGE_SYMBOL')
    
    # Risk management thresholds
    if os.getenv('DELTA_THRESHOLD'):
        config['delta_threshold'] = float(os.getenv('DELTA_THRESHOLD'))
    
    if os.getenv('REBALANCE_THRESHOLD'):
        config['rebalance_threshold'] = float(os.getenv('REBALANCE_THRESHOLD'))
    
    if os.getenv('MAX_IMPERMANENT_LOSS'):
        config['max_impermanent_loss'] = float(os.getenv('MAX_IMPERMANENT_LOSS'))
    
    if os.getenv('MIN_FEE_COVERAGE'):
        config['min_fee_coverage'] = float(os.getenv('MIN_FEE_COVERAGE'))
    
    if os.getenv('VAR_CONFIDENCE'):
        config['var_confidence'] = float(os.getenv('VAR_CONFIDENCE'))
    
    if os.getenv('VOLATILITY_LOOKBACK'):
        config['volatility_lookback'] = int(os.getenv('VOLATILITY_LOOKBACK'))
    
    # Trading limits
    if os.getenv('MAX_POSITION_SIZE'):
        config['max_position_size'] = float(os.getenv('MAX_POSITION_SIZE'))
    
    if os.getenv('MAX_POSITION_VALUE'):
        config['max_position_value'] = float(os.getenv('MAX_POSITION_VALUE'))
    
    if os.getenv('MAX_LEVERAGE'):
        config['max_leverage'] = float(os.getenv('MAX_LEVERAGE'))
    
    if os.getenv('MIN_ORDER_SIZE'):
        config['min_order_size'] = float(os.getenv('MIN_ORDER_SIZE'))
    
    if os.getenv('SLIPPAGE_TOLERANCE'):
        config['slippage_tolerance'] = float(os.getenv('SLIPPAGE_TOLERANCE'))
    
    if os.getenv('MAX_DAILY_TRADES'):
        config['max_daily_trades'] = int(os.getenv('MAX_DAILY_TRADES'))
    
    # Operational settings
    if os.getenv('CLOSE_POSITIONS_ON_SHUTDOWN'):
        config['close_positions_on_shutdown'] = os.getenv('CLOSE_POSITIONS_ON_SHUTDOWN').lower() == 'true'
    
    return config


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from both file and environment variables.
    Environment variables take precedence over file configuration.
    
    Args:
        config_path: Path to JSON configuration file (optional)
        
    Returns:
        Merged configuration dictionary
    """
    config = {}
    
    # First, load from file if provided
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                logger.info(f"Configuration loaded from {config_path}")
            except Exception as e:
                logger.error(f"Error loading config file: {e}")
    
    # Then, override with environment variables
    env_config = load_config_from_env()
    config.update(env_config)
    
    # Log which configuration source was used
    if env_config:
        logger.info(f"Configuration overridden with {len(env_config)} environment variables")
    
    return config


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration values.
    
    Returns:
        Dictionary with default configuration
    """
    return {
        "wallet_address": "",
        "rpc_url": "",
        "vfat_api_url": "https://api.vfat.io",
        "update_interval_seconds": 60,
        "hedge_symbol": "ETH-USD",
        "delta_threshold": 0.1,
        "rebalance_threshold": 0.05,
        "max_impermanent_loss": 0.05,
        "min_fee_coverage": 1.5,
        "var_confidence": 0.95,
        "volatility_lookback": 30,
        "max_position_size": 10.0,
        "max_position_value": 100000,
        "max_leverage": 1.0,
        "min_order_size": 0.01,
        "slippage_tolerance": 0.005,
        "max_daily_trades": 100,
        "hyperliquid_testnet": True,
        "close_positions_on_shutdown": False
    }
