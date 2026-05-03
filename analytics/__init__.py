"""Analytics package."""

# Deferred imports to avoid circular dependencies
def get_signal_formatter():
    from analytics.telegram_formatter import SignalFormatter
    return SignalFormatter

__all__ = ["get_signal_formatter"]