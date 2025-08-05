import os
import json
import discord
from discord.ext import commands
from keep_alive import keep_alive
import random
from datetime import datetime, timedelta

# -------------------------
# Cấu hình bot
# -------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# File lưu vi phạm
VIOLATIONS_FILE = "violations.json"

# Kênh log staff
LOG_CHANNEL_ID = 1402205862985994361

# Verify Config
ROLE_ID = 1400724722714542111
VERIFY_CHANNEL_ID = 1400732340677771356

# Ticket Config
GUILD_ID = 1372215595218505891
TICKET_CHANNEL_ID = 1400750812912685056
SUPPORTERS = ["__tobu", "caycotbietmua"]

# Trigger Words
TRIGGER_WORDS = [
    "hack", "hack android", "hack ios",
    "client android", "client ios",
    "executor android", "executor ios",
    "delta", "krnl"
]

# Link cấm
BLOCKED_LINKS = ["discord.gg/", "discord.com/invite/", "facebook.com", "fb.me"]

# Cấu hình mute nhiều cấp độ (phút)
MUTE_DURATIONS = {
    1: 5,
    2: 30,
    3: 60,
    4: 1440,
    5: 0  # 0 = vĩnh viễn
}

# Intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

# Bot
bot = commands.Bot(command_prefix="/", intents=intents)

# -------------------------
# Hàm quản lý vi phạm
# -------------------------
def load_violations():
    try:
        with open(VIOLATIONS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_violations(data):
    with open(VIOLATIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_mute_duration(count):
    return MUTE_DURATIONS.get(count, 1440)  # mặc định 1 ngày nếu >4

# -------------------------
# Mute + log
# -------------------------
async def mute_and_log(member: discord.Member, reason: str, count: int):
    guild = member.guild
    mute_role = discord.utils.get(guild.roles, name="Muted")
    if not mute_role:
        mute_role = await guild.create_role(name="Muted")
        for channel in guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)

    violations = load_violations()
    uid = str(member.id)

    # Reset nếu quá 24h
    now = datetime.utcnow()
    if uid in violations:
        last_violation = datetime.fromisoformat(violations[uid]["last_violation"])
        if now - last_violation > timedelta(hours=24):
            count = 1

    violations[uid] = {
        "count": count,
        "last_violation": now.isoformat()
    }
    save_violations(violations)

    mute_minutes = get_mute_duration(count)

    await member.add_roles(mute_role, reason=reason)

    # Log
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="🔇 Thành viên bị mute",
            color=discord.Color.red()
        )
        embed.add_field(name="👤 Thành viên", value=member.mention, inline=False)
        embed.add_field(name="📌 Lý do", value=reason, inline=False)
        if mute_minutes == 0:
            embed.add_field(name="⏳ Thời gian", value="Vĩnh viễn", inline=False)
        else:
            embed.add_field(name="⏳ Thời gian", value=f"{mute_minutes} phút", inline=False)
        embed.add_field(name="📅 Thời điểm", value=now.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        await log_channel.send(embed=embed)

# -------------------------
# Xóa spam
# -------------------------
async def delete_recent_messages(message):
    now = datetime.utcnow()
    async for msg in message.channel.history(limit=50):
        if msg.author == message.author and (now - msg.created_at).total_seconds() <= 30:
            try:
                await msg.delete()
            except:
                pass

# -------------------------
# Verify Button
# -------------------------
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

# -------------------------
# Ticket Buttons
# -------------------------
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
        supporters_online = [
            m for m in guild.members
            if m.name in SUPPORTERS and m.status != discord.Status.offline
        ]
        if not supporters_online:
            await interaction.response.send_message("❌ Không có supporter nào online.", ephemeral=True)
            return
        supporter = random.choice(supporters_online)
        await interaction.response.send_message(
            f"✅ {supporter.display_name} sẽ hỗ trợ bạn, vui lòng kiểm tra ticket mới!",
            ephemeral=True
        )
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
            description=f"{supporter.mention} sẽ sớm hỗ trợ bạn.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())

# -------------------------
# On Ready
# -------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")

    verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if verify_channel:
        await verify_channel.send(
            embed=discord.Embed(
                title="Xác Thực Thành Viên",
                description="Bấm nút **Verify/Xác Thực** để vào server.",
                color=discord.Color.green()
            ),
            view=VerifyButton()
        )

    ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
    if ticket_channel:
        await ticket_channel.send(
            embed=discord.Embed(
                title="📢 Hỗ Trợ",
                description="Bấm **Tạo Ticket** để được hỗ trợ.",
                color=discord.Color.orange()
            ),
            view=CreateTicketView()
        )

# -------------------------
# On Message
# -------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()

    # Chặn link Discord/Facebook
    if any(bad in content for bad in BLOCKED_LINKS):
        violations = load_violations()
        uid = str(message.author.id)
        count = violations.get(uid, {}).get("count", 0) + 1
        await delete_recent_messages(message)
        await mute_and_log(message.author, "Gửi link cấm", count)
        return

    # Spam detection: hơn 5 tin trong 30s
    async for msg in message.channel.history(limit=50):
        if msg.author == message.author:
            recent_msgs = [
                m async for m in message.channel.history(limit=50)
                if m.author == message.author and
                (datetime.utcnow() - m.created_at).total_seconds() <= 30
            ]
            if len(recent_msgs) > 5:
                violations = load_violations()
                uid = str(message.author.id)
                count = violations.get(uid, {}).get("count", 0) + 1
                await delete_recent_messages(message)
                await mute_and_log(message.author, "Spam tin nhắn", count)
                return

    # Từ khóa trigger
    if (
        "có" in content
        and ("không" in content or "ko" in content)
        and any(keyword in content for keyword in TRIGGER_WORDS)
    ):
        embed = discord.Embed(
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
                "📥 𝗞𝗿𝗻𝗹 𝗩𝗡𝗚: [Bấm ở đây để tải về](https://www.mediafire.com/file/jfx8ynxsxwgyok1/KrnlxVNG+V10.ipa/file)\n"
                "📥 𝗗𝗲𝗹𝘁𝗮 𝗫 𝗩𝗡𝗚 𝗙𝗶𝘅 𝗟𝗮𝗴: [Bấm tại đây để tải về](https://www.mediafire.com/file/7hk0mroimozu08b/DeltaxVNG+Fix+Lag+V6.ipa/file)\n\n"
                "📥 𝗗𝗲𝗹𝘁𝗮 𝗫 𝗩𝗡𝗚: [Bấm vào đây để tải về](https://www.mediafire.com/file/g2opbrfuc7vs1cp/DeltaxVNG+V23.ipa/file?dkey=f2th7l5402u&r=169)\n\n"
                "---------------------\n"
                "**Đối với Android**\n"
                "---------------------\n"
                "📥 𝗞𝗿𝗻𝗹 𝗩𝗡𝗚: [Bấm tại đây để tải về](https://tai.natushare.com/GAMES/Blox_Fruit/Blox_Fruit_Krnl_VNG_2.681_BANDISHARE.apk)\n"
                "📥 𝗙𝗶𝗹𝗲 𝗹𝗼𝗴𝗶𝗻 𝗗𝗲𝗹𝘁𝗮: [Bấm vào đây để tải về](https://link.nestvui.com/BANDISHARE/GAME/Blox_Fruit/Roblox_VNG_Login_Delta_BANDISHARE.apk)\n"
                "📥 𝗙𝗶𝗹𝗲 𝗵𝗮𝗰𝗸 𝗗𝗲𝗹𝘁𝗮 𝗫 𝗩𝗡𝗚: [Bấm vào đây để tải về](https://download.nestvui.com/BANDISHARE/GAME/Blox_Fruit/Delta_X_VNG_V65_BANDISHARE.iO.apk)\n\n"
                "---------------------\n"
                "✨ **Chúc bạn một ngày vui vẻ**\n"
                "*Bot made by: @__tobu*",
            color=discord.Color.blue()
        )
        await message.reply(embed=embed)
        return

    await bot.process_commands(message)

# -------------------------
# Run Bot
# -------------------------
keep_alive()
if not DISCORD_TOKEN:
    print("❌ Lỗi: Chưa đặt DISCORD_TOKEN")
else:
    bot.run(DISCORD_TOKEN)
