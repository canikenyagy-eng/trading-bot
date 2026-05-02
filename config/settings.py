"""
General Configuration Settings for Trading Intelligence Engine.
"""

# MetaTrader 5 Connection
MT5_CONFIG = {
    "path": None,           # MT5 terminal path (Wine/bridge on macOS)
    "login": None,          # Account login
    "password": None,      # Account password
    "server": None,        # Broker server
    "timeout": 60000,       # Connection timeout (ms)
}

# Telegram Configuration
TELEGRAM_CONFIG = {
    "bot_token": None,     # Bot API token
    "chat_id": None,       # Target chat ID
    "short_enabled": True,
    "full_enabled": True,
}

# Symbols to Analyze
SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY",
    "USDCHF", "AUDUSD", "USDCAD",
    "NZDUSD", "EURJPY", "GBPJPY",
]

# Timeframes
TIMEFRAMES = {
    "signal": "M15",           # Signal generation timeframe
    "analysis": "H1",         # Analysis timeframe
    "context": "H4",           # Higher timeframe context
    "structure": "D1",         # Daily for structure
}

# Risk Management
RISK_CONFIG = {
    "max_risk_per_trade": 0.02,      # 2% max risk
    "max_pairs_open": 5,
    "max_correlated_exposure": 0.06,  # Max 6% correlated exposure
    "max_daily_risk": 0.05,          # Max 5% daily risk
}

# Session Times (UTC)
SESSION_TIMES = {
    "sydney": (22, 7),
    "tokyo": (0, 9),
    "london": (7, 16),
    "new_york": (13, 22),
}

# Execution Settings (Simulator Only)
EXECUTION_CONFIG = {
    "mode": "simulator",     # simulator | paper | disabled
    "spread_penalty": 2.0,   # pips added for spread
    "slippage_model": "fixed",  # fixed | dynamic
    "slippage_pips": 1.0,
}

# Backtest Settings
BACKTEST_CONFIG = {
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "initial_balance": 10000,
    "commission": 0.0,          # Per lot
    "leverage": 100,
}

# Analytics Settings
ANALYTICS_CONFIG = {
    "rolling_window": 50,        # Trades for rolling stats
    "mfe_mae_periods": [5, 10, 20],
    "track_session_stats": True,
    "track_regime_stats": True,
}

# Signal Settings
SIGNAL_CONFIG = {
    "min_structure_confluence": 0.5,
    "cooldown_minutes": 15,
    "signal_ttl_minutes": 60,
    "consolidation_threshold": 0.0005,
}

# Logging
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    "file": "trading_engine.log",
    "max_bytes": 10485760,  # 10MB
    "backup_count": 5,
}

# Settings end