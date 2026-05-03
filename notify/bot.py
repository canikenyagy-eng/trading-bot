"""
Telegram Bot Integration.

This module provides Telegram bot functionality for:
- Receiving market data (placeholder)
- Sending signals
- Receiving commands

CRITICAL: This is for notifications ONLY. No auto-trading.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio

# Telegram Bot Token and Chat ID
TELEGRAM_BOT_TOKEN = "8608494961:AAGHrERt8b4MIgTWeaqg-Qn3K-XNo6GzZAQ"
TELEGRAM_CHAT_ID = "1916051263"

from telegram import (
    Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)

from core.signal_engine import SignalEvaluation
from telegram.formatter import SignalFormatter


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    bot_token: str = ""
    chat_id: str = ""
    short_enabled: bool = True
    full_enabled: bool = True
    
    # Commands
    /start, /help, /status, /signals, /stop


class TradingBot:
    """Telegram bot for trading signals.
    
    CRITICAL: Notifications only. No trade execution.
    """
    
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.formatter = SignalFormatter()
        self.app = None
        self.is_running = False
        
        # Signal queue
        self.signal_queue: List[SignalEvaluation] = []
        
        # Callbacks
        self.on_command: Dict[str, callable] = {}
        self.on_signal: callable = None
    
    async def start(self) -> None:
        """Start the bot."""
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self._start_command))
        self.app.add_handler(CommandHandler("help", self._help_command))
        self.app.add_handler(CommandHandler("status", self._status_command))
        self.app.add_handler(CommandHandler("signals", self._signals_command))
        self.app.add_handler(CommandHandler("settings", self._settings_command))
        self.app.add_handler(CommandHandler("stop", self._stop_command))
        
        # Start polling
        await self.app.initialize()
        await self.app.start()
        self.is_running = True
        
        # Send startup message
        await self.send_message("🤖 Trading Intelligence Engine Started\n\nBot untuk notifikasi signal saja. TIDAK ada auto-trade.")
    
    async def stop(self) -> None:
        """Stop the bot."""
        if self.app:
            await self.app.stop()
            await self.app.shutdown()
        self.is_running = False
    
    async def send_signal(self, signal: SignalEvaluation) -> None:
        """Send signal to Telegram.
        
        Args:
            signal: SignalEvaluation to send
        """
        message = self.formatter.format_accepted(signal)
        
        if message:
            await self.send_message(message)
    
    async def send_message(self, text: str, reply_markup: Any = None) -> None:
        """Send message to configured chat."""
        if not self.is_running:
            return
        
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Error sending message: {e}")
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "🤖 Trading Intelligence Engine\n\n"
            "Saya adalah bot notifikasi untuk SMC analysis.\n\n"
            "Gunakan /help untuk melihat perintah."
        )
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = """
📚 *Perintah yang Tersedia:*

/start - Mulai bot
/help - Panduan ini
/status - Status engine
/signals - Daftar signal terakhir
/settings - Pengaturan
/stop - Hentikan bot
        """
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        status = f"""
📊 *Status Engine:*

Running: {self.is_running}
Signals in queue: {len(self.signal_queue)}
        """
        await update.message.reply_text(status, parse_mode="Markdown")
    
    async def _signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /signals command."""
        if not self.signal_queue:
            await update.message.reply_text("Tidak ada signal dalam antrian.")
        else:
            text = f"📊 *Signal Terakhir ({len(self.signal_queue)}):*\n\n"
            
            for i, signal in enumerate(self.signal_queue[-5:], 1):
                text += f"{i}. {signal.symbol} {signal.direction.value}\n"
            
            await update.message.reply_text(text, parse_mode="Markdown")
    
    async def _settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /settings command."""
        text = """
⚙️ *Pengaturan:*

Short signals: Enabled
Full signals: Enabled
        """
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def _stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stop command."""
        await update.message.reply_text("Menghentikan bot...")
        await self.stop()


# Simple async runner
async def run_bot(token: str, chat_id: str) -> None:
    """Run the bot."""
    bot = TradingBot(token, chat_id)
    await bot.start()
    
    # Keep running
    try:
        while bot.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await bot.stop()


# Sync wrapper for easier use
def run_bot_sync() -> None:
    """Run bot synchronously."""
    asyncio.run(run_bot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID))


# Telegram Bot End