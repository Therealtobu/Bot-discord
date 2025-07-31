import os
import discord
import requests
from discord.ext import commands
from keep_alive import keep_alive

# Token bot Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Từ khóa trigger tải client
TRIGGER_WORDS = [
    "hack android", "hack ios", "client android", "client ios",
    "executor android", "executor ios", "delta", "krnl"
]

# Hàm tìm script từ ScriptBlox
def search_script(keyword):
    try:
        search_url = f"https://scriptblox.com/api/script/search?q={keyword}&page=1"
        res = requests.get(search_url, timeout=5).json()

        if "scripts" not in res or len(res["scripts"]) == 0:
            return None, None

        first_script = res["scripts"][0]
        script_id = first_script["_id"]
        script_title = first_script.get("title", "Script")

        # Lấy chi tiết script
        detail_url = f"https://scriptblox.com/api/script/{script_id}"
        detail_res = requests.get(detail_url, timeout=5).json()

        if "script" not in detail_res:
            return script_title, None

        script_code = detail_res["script"]
        return script_title, script_code

    except Exception as e:
        return None, f"Lỗi khi tìm script: {e}"

@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()

    # Nếu chứa từ khóa "script <tên>"
    if content.startswith("script "):
        keyword = content.replace("script ", "").strip()
        title, code = search_script(keyword)

        if not title:
            await message.reply("❌ Không tìm thấy script nào phù hợp.")
            return
        if not code:
            await message.reply(f"❌ Không lấy được code cho `{title}`.")
            return

        # Gửi script
        await message.reply(
            f"📜 **Script tìm thấy:** {title}\n```lua\n{code}\n```"
        )
        return

    # Nếu chứa trigger tải client
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

# Giữ bot sống
keep_alive()

# Chạy bot
if not DISCORD_TOKEN:
    print("❌ Lỗi: Chưa đặt DISCORD_TOKEN trong Environment Variables của Render")
else:
    bot.run(DISCORD_TOKEN)
