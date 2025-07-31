import discord
import os
from discord.ext import commands
from keep_alive import keep_alive  # 👉 Kích hoạt Flask server

# Lấy token từ biến môi trường
TOKEN = os.getenv("DISCORD_TOKEN")  

# Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# 👉 Gọi hàm giữ bot sống
keep_alive()

# Từ khoá trigger
TRIGGER_WORDS = [
    "hack android", "hack ios", "client android", "client ios",
    "executor android", "executor ios", "delta", "krnl"
]

@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập với tên: {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()
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

    await bot.process_commands(message)

@bot.command()
async def script(ctx):
    await ctx.send(
        "🔗 Đây là script bạn cần:\n```lua\nloadstring(game:HttpGet('https://raw.githubusercontent.com/Therealtobu/Applehub/refs/heads/main/Applehubcuatobu.lua'))()\n```"
    )

@bot.command()
async def rule(ctx):
    await ctx.send(
        "📜 Quy tắc sử dụng bot:\n"
        "1. Không spam lệnh\n"
        "2. Không chia sẻ mã độc\n"
        "3. Tôn trọng người khác\n"
        "4. Sử dụng đúng mục đích hỗ trợ"
    )

# Chạy bot
if TOKEN is None:
    print("❌ Lỗi: Bạn chưa đặt biến môi trường DISCORD_TOKEN")
else:
    bot.run(TOKEN)
