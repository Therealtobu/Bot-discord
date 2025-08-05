import os
import discord
from discord.ext import commands
from discord.utils import get
from keep_alive import keep_alive
import random
from datetime import datetime, timedelta

# -------------------------
# Cấu hình bot
# -------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Verify Config
ROLE_ID = 1400724722714542111
VERIFY_CHANNEL_ID = 1400732340677771356

# Ticket Config
GUILD_ID = 1372215595218505891
TICKET_CHANNEL_ID = 1400750812912685056
SUPPORTERS = ["__tobu", "caycotbietmua"]

# Trigger Words -> hiện hướng dẫn tải
TRIGGER_WORDS = [
    "hack", "hack android", "hack ios",
    "client android", "client ios",
    "executor android", "executor ios",
    "delta", "krnl"
]

# Banned words -> Mute + xóa spam
BANNED_WORDS = ["chửi", "bậy", "tục"]

# Link cấm
ILLEGAL_LINKS = ["discord.gg", "facebook.com"]

# Intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Lưu số lần vi phạm
mute_history = {}

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
        supporters_online = [m for m in guild.members if m.name in SUPPORTERS and m.status != discord.Status.offline]
        if not supporters_online:
            await interaction.response.send_message("❌ Hiện không có supporter nào online.", ephemeral=True)
            return
        supporter = random.choice(supporters_online)
        await interaction.response.send_message(
            f"✅ **{supporter.display_name}** sẽ hỗ trợ bạn!", ephemeral=True
        )
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            supporter: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        embed = discord.Embed(
            title="🎫 Ticket Hỗ Trợ",
            description=f"{supporter.mention} sẽ sớm hỗ trợ bạn.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())

# -------------------------
# Mute function
# -------------------------
async def mute_member(member, reason):
    now = datetime.now()
    if member.id not in mute_history:
        mute_history[member.id] = {"count": 0, "last_violation": now}

    # Reset nếu hơn 24h
    if (now - mute_history[member.id]["last_violation"]) > timedelta(days=1):
        mute_history[member.id]["count"] = 0

    mute_history[member.id]["count"] += 1
    mute_history[member.id]["last_violation"] = now

    count = mute_history[member.id]["count"]
    durations = {
        1: 5,        # phút
        2: 30,       # phút
        3: 60,       # phút
        4: 1440      # phút (1 ngày)
    }

    if count >= 5:
        await member.ban(reason="Vi phạm 5 lần")
        return f"🚫 {member} đã bị **ban vĩnh viễn** vì vi phạm 5 lần."

    mute_role = get(member.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await member.guild.create_role(name="Muted")
        for channel in member.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)

    await member.add_roles(mute_role)
    minutes = durations.get(count, 5)
    return f"🔇 {member} đã bị mute {minutes} phút. Lý do: {reason} (Lần {count})"

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
                description="Bấm nút **Verify/Xác Thực** để tương tác.",
                color=discord.Color.green()
            ),
            view=VerifyButton()
        )
    ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
    if ticket_channel:
        await ticket_channel.send(
            embed=discord.Embed(
                title="📢 Hỗ Trợ",
                description="Nếu bạn cần **Hỗ Trợ** hãy bấm nút **Tạo Ticket** ở dưới\n"
                "---------------------\n"
                "LƯU Ý: Vì các Mod khá bận nên việc Support vấn đề sẽ khá lâu và **Tuyệt đối không được spam nhiều ticket**.\n"
                "Khi tạo ticket thì **nói thẳng vấn đề luôn**.\n"
                "Nếu không tuân thủ các luật trên sẽ bị **mute 1 ngày**.",
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

    # 1. Hiện hướng dẫn nếu chứa trigger word
    if any(keyword in content for keyword in TRIGGER_WORDS):
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

    # 2. Check từ cấm hoặc link cấm
    if any(word in content for word in BANNED_WORDS) or any(link in content for link in ILLEGAL_LINKS):
        log_msg = await mute_member(message.author, "Ngôn từ/bài viết vi phạm")
        await message.channel.send(log_msg)
        # Xoá toàn bộ tin nhắn spam gần đây của user
        async for msg in message.channel.history(limit=50):
            if msg.author == message.author:
                await msg.delete()
        return

    await bot.process_commands(message)

# -------------------------
# Run Bot
# -------------------------
keep_alive()
if not DISCORD_TOKEN:
    print("❌ Lỗi: Chưa đặt DISCORD_TOKEN trong Render")
else:
    bot.run(DISCORD_TOKEN)
