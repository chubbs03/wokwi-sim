import os
import asyncio
import logging
import re
import nest_asyncio
import aiohttp
import urllib.parse

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Apply asyncio patch
nest_asyncio.apply()

# === CONFIG ===
TELEGRAM_BOT_TOKEN = '8267082281:AAFp9JbD36OEAIN7-yJCPSWWpDzEO4-pJmw'
DEEPSEEK_API_KEY = 'sk-34c1116b28e24ad4add008420062d489'

# === LOGGING ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# wokwi API
WOKWI_PROJECT_API = "https://projects.api.wokwi.com/projects"

# === DeepSeek handler ===
async def ask_deepseek(message: str, system_prompt: str = "You are an expert Arduino + Wokwi simulator engineer. Generate both the Arduino code and the diagram.json for Wokwi simulation. \
Return only two separate code blocks: \
First block: sketch.ino inside triple backticks (), \
Second block: diagram.json inside triple backticks (json). \
Do not include any extra explanation or comments.") -> str:
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": message},
            {"role": "system", "content": system_prompt}
        ],
        "temperature": 0.7
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data["choices"][0]["message"]["content"]
            else:
                return f"❌ DeepSeek API error {response.status}"

# === Telegram command handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Ask any Arduino + Wokwi circuit question.")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    user_message = update.message.text
    await update.message.reply_text("🤖 Generating code and Wokwi simulation...")

    try:
        # Step 1: Ask DeepSeek for the response
        raw_reply = await ask_deepseek(user_message)

        # Step 2: Extract sketch.ino and diagram.json
        code_match = re.search(r"```(?:cpp|arduino)?\s*(.*?)```", raw_reply, re.DOTALL)
        json_match = re.search(r"```json\s*(.*?)```", raw_reply, re.DOTALL)

        if not code_match or not json_match:
            await update.message.reply_text("⚠️ Could not extract code or JSON from DeepSeek's response.")
            return

        arduino_code = code_match.group(1).strip()
        wokwi_json = json_match.group(1).strip()

        # Step 3: Clean Arduino code (remove comments and whitespace)
        cleaned_code = "\n".join([line for line in arduino_code.splitlines() if not line.strip().startswith("//")])

        # Step 4: Generate Wokwi simulation link
        encoded_json = urllib.parse.quote(wokwi_json)
        wokwi_link = f"https://project.wokwi.com/new?json={encoded_json}"

        # Step 5: Send results to user
        await update.message.reply_text("✅ Cleaned Arduino Code:\n\n" + f"```cpp\n{cleaned_code}\n```", parse_mode="Markdown")
        await update.message.reply_text("🔗 Wokwi Simulation Link:\n" + wokwi_link)

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("⚠️ Error processing your request.")

# === Main ===
async def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat))

    print("✅ Bot is running...")
    await app.run_polling()

# === Run bot ===
if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())

