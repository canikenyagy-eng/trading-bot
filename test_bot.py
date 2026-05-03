"""Quick test Telegram bot."""
import asyncio
from telegram import Bot

# Your credentials
TOKEN = "8608494961:AAGHrERt8b4MIgTWeaqg-Qn3K-XNo6GzZAQ"
CHAT_ID = "1916051263"

async def test():
    bot = Bot(token=TOKEN)
    
    # Send test message
    await bot.send_message(
        chat_id=CHAT_ID,
        text="✅ Trading Intelligence Engine sudah terhubung!\n\nBot работает!"
    )
    print("Message sent!")

if __name__ == "__main__":
    asyncio.run(test())