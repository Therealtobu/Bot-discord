import os
import discord
from discord.ext import commands
from keep_alive import keep_alive
import openai

# Lấy token bot Discord và API key OpenAI từ biến môi trường Render
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Cấu hình OpenAI
openai.api_key = OPENAI_KEY

# Biến lưu trạng thái chat GPT cho từng user
active_gpt_users = set()

# Intents
intents = discord.Intents.default()
intents.message_content = True

# Bot
bot = commands.Bot(command_prefix="/", intents=intents)

# Từ khóa trigger
TRIGGER_WORDS = [
    "hack android", "hack ios", "client android", "client ios",
    "executor android", "executor ios", "delta", "krnl"
]

@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()

    # 1️⃣ Bắt đầu chat GPT khi gọi
    if "chat gpt ơi" in content:
        active_gpt_users.add(message.author.id)
        await message.reply("🤖 Xin chào! Bạn muốn hỏi gì?")
        return

    # 2️⃣ Dừng chat GPT khi nói tạm biệt
    if "tạm biệt" in content:
        if message.author.id in active_gpt_users:
            active_gpt_users.remove(message.author.id)
            await message.reply("👋 Tạm biệt! Khi nào cần thì gọi mình nha.")
        return

    # 3️⃣ Nếu đang bật chế độ GPT, trả lời bằng ChatGPT
    if message.author.id in active_gpt_users:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Bạn là ChatGPT, trả lời ngắn gọn, dễ hiểu."},
                    {"role": "user", "content": content}
                ]
            )
            reply = response.choices[0].message["content"]
            await message.reply(reply)
        except Exception as e:
            await message.reply(f"⚠️ Lỗi: {e}")
        return

    # 4️⃣ Trigger Words
    if any(keyword in content for keyword in TRIGGER_WORDS):
        embed = discord.Embed(
            title="📌 Cách tải và client hỗ trợ",
            description=(
     "**Nếu bạn không biết cách tải thì đây nha**\n"
                "👉 [Bấm vào đây để xem hướng dẫn TikTok](https://vt.tiktok.com/ZSSdjBjVE/)\n\n"
                "---------------------\n"
                "**Còn đối với Android thì quá dễ nên mình hok cần phải chỉ nữa**\n"
                "---------------------\n"
                "**Các client mình đang cóa**\n\n"
                "---------------------\n"
                "**Đối với IOS**\n"
                "---------------------\n"
                "📥 𝗞𝗿𝗻𝗹 𝗩𝗡𝗚: [Bấm ở đây để tải về](https://www.mediafire.com/file/jfx8ynxsxwgyok1/KrnlxVNG+V10.ipa/file)\n"
                "📥 𝗗𝗲𝗹𝘁𝗮 𝗫 𝗩𝗡𝗚 𝗙𝗶𝘅 𝗟𝗮𝗴: [Bấm tại đây để tải về](https://www.mediafire.com/file/7hk0mroimozu08b/DeltaxVNG+Fix+Lag+V6.ipa/file)\n\n"
                "---------------------\n"
                "**Đối với Android**\n"
                "---------------------\n"
                "📥 𝗞𝗿𝗻𝗹 𝗩𝗡𝗚: [Bấm tại đây để tải về](https://tai.natushare.com/GAMES/Blox_Fruit/Blox_Fruit_Krnl_VNG_2.681_BANDISHARE.apk)\n"
                "📥 𝗙𝗶𝗹𝗲 𝗟𝗼𝗴𝗶𝗻 𝗗𝗲𝗹𝘁𝗮: [Bấm vào đây để tải về](https://link.nestvui.com/BANDISHARE/GAME/Blox_Fruit/Roblox_VNG_Login_Delta_BANDISHARE.apk)\n"
                "📥 𝗙𝗶𝗹𝗲 𝗵𝗮𝗰𝗸 𝗗𝗲𝗹𝘁𝗮 𝗫 𝗩𝗡𝗚: [Bấm vào đây để tải về](https://download.nestvui.com/BANDISHARE/GAME/Blox_Fruit/Delta_X_VNG_V65_BANDISHARE.iO.apk)\n\n"
                "---------------------\n"
                "✨ **Chúc bạn một ngày vui vẻ**\n"
                "*Bot made by: @__tobu*"
            ),
            color=discord.Color.blue()
        )
        await message.reply(embed=embed)
        return

    await bot.process_commands(message)

# Khởi động web server keep_alive
keep_alive()

# Chạy bot
if not DISCORD_TOKEN:
    print("❌ Lỗi: Chưa đặt DISCORD_TOKEN trong Environment Variables của Render")
else:
    bot.run(DISCORD_TOKEN)
