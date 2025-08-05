import os
import discord
from discord.ext import commands, tasks
import random
import json
import aiohttp
from keep_alive import keep_alive

# ===========================
# Load config.json
# ===========================
CONFIG_FILE = "config.json"
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
else:
    config = {
        "level_roles": [],
        "voice_channel_id": None,
        "last_tiktok_id": "",
        "log_channel_id": 1402191653531549807,
        "tiktok_notify_channel_id": 1402191653531549807
    }

def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

# ===========================
# Bot config
# ===========================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ROLE_ID = 1400724722714542111
VERIFY_CHANNEL_ID = 1400732340677771356
GUILD_ID = 1372215595218505891
TICKET_CHANNEL_ID = 1400750812912685056
SUPPORTERS = ["__tobu", "caycotbietmua"]

TRIGGER_WORDS = [
    "hack", "hack android", "hack ios",
    "client android", "client ios",
    "executor android", "executor ios",
    "delta", "krnl"
]

# Intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

# Bot
bot = commands.Bot(command_prefix="/", intents=intents)
spam_tracker = {}

# ===========================
# Verify Button
# ===========================
class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify / Xác Thực", style=discord.ButtonStyle.green)
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(ROLE_ID)
        member = interaction.user
        if role in member.roles:
            await interaction.response.send_message("✅ Bạn đã được xác thực trước đó!", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message("🎉 Bạn đã được xác thực thành công!", ephemeral=True)

# ===========================
# Ticket System
# ===========================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Ticket sẽ bị đóng trong 3 giây...", ephemeral=True)
        await interaction.channel.delete()

class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Tạo Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = bot.get_guild(GUILD_ID)
        supporters_online = [m for m in guild.members if m.name in SUPPORTERS and m.status != discord.Status.offline]
        if not supporters_online:
            await interaction.response.send_message("❌ Hiện không có supporter nào online.", ephemeral=True)
            return
        supporter = random.choice(supporters_online)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            supporter: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )
        embed = discord.Embed(
            title="🎫 Ticket Hỗ Trợ",
            description=f"{supporter.mention} sẽ hỗ trợ bạn.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())
        await interaction.response.send_message("✅ Ticket đã được tạo!", ephemeral=True)

# ===========================
# Anti-spam & Anti-link
# ===========================
async def mute_and_log(member, reason):
    guild = member.guild
    mute_role = discord.utils.get(guild.roles, name="Muted")
    if not mute_role:
        mute_role = await guild.create_role(name="Muted")
        for channel in guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)
    await member.add_roles(mute_role)
    log_channel = bot.get_channel(config["log_channel_id"])
    if log_channel:
        await log_channel.send(f"🔇 {member.mention} bị mute 1 ngày. Lý do: **{reason}**")
    # Unmute sau 24h
    await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(days=1))
    await member.remove_roles(mute_role)

# ===========================
# TikTok Notify
# ===========================
@tasks.loop(minutes=5)
async def check_tiktok():
    username = "caycotbietmua"
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://www.tiktok.com/@{username}?lang=en") as resp:
            if resp.status != 200:
                return
            html = await resp.text()
            if '"id":"' in html:
                vid_id = html.split('"id":"')[1].split('"')[0]
                if vid_id != config["last_tiktok_id"]:
                    config["last_tiktok_id"] = vid_id
                    save_config()
                    channel = bot.get_channel(config["tiktok_notify_channel_id"])
                    if channel:
                        await channel.send(f"Adu Ad mới ra video oải cả chưởng nè ae @everyone\nhttps://www.tiktok.com/@{username}/video/{vid_id}")

# ===========================
# On Ready
# ===========================
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")
    guild = bot.get_guild(GUILD_ID)

    # Tạo role cấp độ nếu chưa có
    if not config["level_roles"]:
        for i in range(8):
            role = await guild.create_role(name=f"Cấp độ {i}")
            config["level_roles"].append(role.id)
        save_config()

    # Tạo voice channel thống kê nếu chưa có
    if not config["voice_channel_id"]:
        vc = await guild.create_voice_channel(f"👥 Thành viên: {guild.member_count}")
        config["voice_channel_id"] = vc.id
        save_config()

    # Gửi Verify
    verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if verify_channel:
        await verify_channel.send(embed=discord.Embed(
            title="Xác Thực Thành Viên",
            description="Bấm **Verify** để vào nhóm",
            color=discord.Color.green()
        ), view=VerifyButton())

    # Gửi Ticket
    ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
    if ticket_channel:
        await ticket_channel.send(embed=discord.Embed(
            title="📢 Hỗ Trợ",
            description="Bấm **Tạo Ticket** để được giúp",
            color=discord.Color.orange()
        ), view=CreateTicketView())

    check_tiktok.start()

# ===========================
# On Message
# ===========================
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    content = message.content.lower()

    # Anti-link Discord lạ
    if "discord.gg/" in content and not str(message.guild.id) in content:
        await message.delete()
        await mute_and_log(message.author, "Gửi link Discord lạ")
        return

    # Anti-spam
    user_id = message.author.id
    spam_tracker.setdefault(user_id, []).append(content)
    if len(spam_tracker[user_id]) > 5 and len(set(spam_tracker[user_id][-5:])) == 1:
        await mute_and_log(message.author, "Spam câu/từ giống nhau")
        spam_tracker[user_id] = []

    # Trigger words
    if ("có" in content and ("không" in content or "ko" in content) and any(k in content for k in TRIGGER_WORDS)):
        await message.reply(embed=discord.Embed(
            title="📌 Cách tải và client hỗ trợ",
            description="**Nếu bạn không biết cách tải thì đây nha**\n"
                "👉 [Bấm vào đây để xem hướng dẫn TikTok](https://vt.tiktok.com/ZSSdjBjVE/)\n\n"
                "---------------------\n"
                "**Còn đối với Android thì quá dễ nên mình hok cần phải chỉ nữa**\n"
                "---------------------\n"
                "**Các client mình đang cóa**\n\n"
                "---------------------\n"
                "**Đối với IOS**\n"
                "---------------------\n"
                "📥 𝗞𝗿𝗻𝗹 𝗩𝗡𝗚: [Bấm ở đây để tải về](https://www.mediafire.com/file/jfx8ynxsxwgyok1/KrnlxVNG+V10.ipa/file)\n\n"
                "📥 𝗗𝗲𝗹𝘁𝗮 𝗫 𝗩𝗡𝗚 𝗙𝗶𝘅 𝗟𝗮𝗴: [Bấm tại đây để tải về](https://www.mediafire.com/file/7hk0mroimozu08b/DeltaxVNG+Fix+Lag+V6.ipa/file)\n\n"
                "📥 𝗗𝗲𝗹𝘁𝗮 𝗫 𝗩𝗡𝗚: [Bấm vào đây để tải về](https://www.mediafire.com/file/g2opbrfuc7vs1cp/DeltaxVNG+V23.ipa/file?dkey=f2th7l5402u&r=169)\n"
                "---------------------\n"
                "**Đối với Android**\n"
                "---------------------\n"
                "📥 𝗞𝗿𝗻𝗹 𝗩𝗡𝗚: [Bấm tại đây để tải về](https://tai.natushare.com/GAMES/Blox_Fruit/Blox_Fruit_Krnl_VNG_2.681_BANDISHARE.apk)\n"
                "📥 𝗙𝗶𝗹𝗲 𝗹𝗼𝗴𝗶𝗻 𝗗𝗲𝗹𝘁𝗮: [Bấm vào đây để tải về](https://link.nestvui.com/BANDISHARE/GAME/Blox_Fruit/Roblox_VNG_Login_Delta_BANDISHARE.apk)\n"
                "📥 𝗙𝗶𝗹𝗲 𝗵𝗮𝗰𝗸 𝗗𝗲𝗹𝘁𝗮 𝗫 𝗩𝗡𝗚: [Bấm vào đây để tải về](https://download.nestvui.com/BANDISHARE/GAME/Blox_Fruit/Delta_X_VNG_V65_BANDISHARE.iO.apk)\n\n"
                "---------------------\n"
                "✨ **Chúc bạn một ngày vui vẻ**\n"
                "*Bot made by: @__tobu*"   
            
            color=discord.Color.blue()
        ))

    await bot.process_commands(message)

# ===========================
# Run bot
# ===========================
keep_alive()
bot.run(DISCORD_TOKEN)
