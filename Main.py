import os
import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime, timedelta
from keep_alive import keep_alive

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

# Anti-Spam & Filter Config
SPAM_LIMIT = 5
TIME_WINDOW = 30
MUTE_TIME = 60
user_messages = {}
user_offenses = {}  # Lưu số lần vi phạm để ban theo mốc

# Danh sách link bị mute (blocklist)
BLOCK_LINKS = [
    "discord.gg", "facebook.com"
    "roblox.com/games", "shorturl.at"
]

# Từ cấm
BAD_WORDS = ["đm", "địt", "lồn", "buồi", "cặc", "mẹ mày", "fuck", "bitch", "dm", "cc"]

# Log Channel ID
LOG_CHANNEL_ID = 1402205862985994361

# Intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

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
        supporters_online = []

        for member in guild.members:
            if member.name in SUPPORTERS and member.status != discord.Status.offline:
                supporters_online.append(member)

        if not supporters_online:
            await interaction.response.send_message("❌ Hiện không có supporter nào online, vui lòng thử lại sau.", ephemeral=True)
            return

        supporter = random.choice(supporters_online)
        await interaction.response.send_message(
            f"✅ **{supporter.display_name}** đã được đặt để hỗ trợ cho bạn, vui lòng kiểm tra ticket mới!",
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
            description=f"{supporter.mention} sẽ sớm hỗ trợ bạn.\nVui lòng nói vấn đề bạn cần hỗ trợ.",
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
        embed = discord.Embed(
            title="Xác Thực Thành Viên",
            description="Bấm nút **Verify/Xác Thực** ở dưới để có thể tương tác trong nhóm\n⬇️⬇️⬇️",
            color=discord.Color.green()
        )
        await verify_channel.send(embed=embed, view=VerifyButton())

    ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
    if ticket_channel:
        embed = discord.Embed(
            title="📢 Hỗ Trợ",
            description=(
                "Nếu bạn cần **Hỗ Trợ** hãy bấm nút **Tạo Ticket** ở dưới\n"
                "---------------------\n"
                "LƯU Ý: Vì các Mod khá bận nên việc Support vấn đề sẽ khá lâu và **Tuyệt đối không được spam nhiều ticket**.\n"
                "Khi tạo ticket thì **nói thẳng vấn đề luôn**.\n"
                "Nếu không tuân thủ các luật trên sẽ bị **mute 1 ngày**."
            ),
            color=discord.Color.orange()
        )
        await ticket_channel.send(embed=embed, view=CreateTicketView())

# -------------------------
# Xử lý mute/ban & log
# -------------------------
async def punish_and_log(message, reason="vi phạm"):
    try:
        guild = message.guild

        # Xóa tất cả tin nhắn gần đây của người vi phạm trong TIME_WINDOW giây
        async for msg in message.channel.history(limit=100):
            if msg.author == message.author and (datetime.utcnow() - msg.created_at).seconds <= TIME_WINDOW:
                try:
                    await msg.delete()
                except:
                    pass

        # Đếm số lần vi phạm
        user_id = message.author.id
        user_offenses[user_id] = user_offenses.get(user_id, 0) + 1
        offense_count = user_offenses[user_id]

        # Mốc ban
        ban_durations = {1: 600, 2: 1800, 3: 3600, 4: 86400}  # giây
        ban_time = ban_durations.get(offense_count, 86400)  # mặc định 24h

        # Ban user
        await guild.ban(message.author, reason=f"{reason} - Lần {offense_count}")
        await message.channel.send(
            f"⛔ {message.author.mention} đã bị **ban {ban_time // 60} phút** (Lần {offense_count}) vì {reason}!"
        )

        # Log vi phạm
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🚨 Phát hiện vi phạm",
                description=f"**Người vi phạm:** {message.author} ({message.author.mention})\n"
                            f"**Lý do:** {reason}\n**Lần vi phạm:** {offense_count}\n"
                            f"**Thời gian ban:** {ban_time // 60} phút",
                color=discord.Color.red()
            )
            embed.add_field(name="Nội dung tin nhắn", value=message.content or "*Không có nội dung*", inline=False)
            embed.add_field(name="Kênh", value=message.channel.mention, inline=True)
            embed.timestamp = datetime.utcnow()
            await log_channel.send(embed=embed)

        # Tự gỡ ban sau thời gian quy định
        await asyncio.sleep(ban_time)
        try:
            await guild.unban(discord.Object(id=user_id))
        except:
            pass

    except Exception as e:
        print(f"Lỗi punish/log: {e}")

# -------------------------
# On Message (AntiSpam + Filter + Trigger)
# -------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()

    # 1. Từ cấm
    if any(bad_word in content_lower for bad_word in BAD_WORDS):
        await punish_and_log(message, "gửi từ ngữ cấm")
        return

    # 2. Link bị cấm
    if any(block in content_lower for block in BLOCK_LINKS):
        await punish_and_log(message, "gửi link bị cấm")
        return

    # 3. Spam
    now = datetime.now()
    user_id = message.author.id
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(now)
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < timedelta(seconds=TIME_WINDOW)]

    if len(user_messages[user_id]) > SPAM_LIMIT:
        await punish_and_log(message, "spam tin nhắn")
        user_messages[user_id] = []
        return


# -------------------------
# Run Bot
# -------------------------
keep_alive()

if not DISCORD_TOKEN:
    print("❌ Lỗi: Chưa đặt DISCORD_TOKEN trong Environment Variables của Render")
else:
    bot.run(DISCORD_TOKEN)
