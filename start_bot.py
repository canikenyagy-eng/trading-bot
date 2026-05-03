"""Quick Telegram Bot Starter."""
import asyncio
from telegram import Bot
from telegram.error import TimedOut

# === КОНФИГУРАЦИЯ ===
TOKEN = "8608494961:AAGHrERt8b4MIgTWeaqg-Qn3K-XNo6GzZAQ"
CHAT_ID = "1916051263"

async def main():
    bot = Bot(token=TOKEN)
    
    print("=" * 40)
    print("TRADING INTELLIGENCE ENGINE")
    print("=" * 40)
    
    # Test connection
    try:
        me = await bot.get_me()
        print(f"Logged in as: @{me.username}")
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Send startup message
    try:
        await bot.send_message(
            chat_id=CHAT_ID,
            text="🤖 *Trading Intelligence Engine Started*\n\n" +
                 "Bot работает!\n" +
                 "Analysis only - no auto trading.",
            parse_mode="Markdown"
        )
        print("Message sent to Telegram!")
    except TimedOut:
        print("Timeout sending message...")
    except Exception as e:
        print(f"Send error: {e}")
    
    print("\nBot is running...")
    print("Press Ctrl+C to stop")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\nStopped")

if __name__ == "__main__":
    asyncio.run(main())