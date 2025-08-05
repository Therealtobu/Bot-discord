import os
import discord
from discord import app_commands
from discord.ext import commands
import random
from keep_alive import keep_alive
import asyncio
import yt_dlp

# -------------------------
# Cấu hình bot
# -------------------------
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

bot = commands.Bot(command_prefix="!", intents=intents)

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
        await asyncio.sleep(3)
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
            f"✅ **{supporter.display_name}** đã được đặt để hỗ trợ cho bạn!",
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
# Slash Commands Music
# -------------------------
@bot.tree.command(name="play", description="Phát nhạc từ YouTube")
async def play(interaction: discord.Interaction, url: str):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❌ Bạn cần vào voice channel trước!", ephemeral=True)
        return

    voice_channel = interaction.user.voice.channel
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if not vc:
        vc = await voice_channel.connect()

    ydl_opts = {"format": "bestaudio/best"}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        audio_url = info['url']
        vc.play(discord.FFmpegPCMAudio(audio_url), after=lambda e: print("Hoàn thành phát nhạc"))

    await interaction.response.send_message(f"🎵 Đang phát: **{info['title']}**")

@bot.tree.command(name="stop", description="Dừng phát nhạc")
async def stop(interaction: discord.Interaction):
    vc = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if vc:
        await vc.disconnect()
        await interaction.response.send_message("⏹ Đã dừng phát nhạc")
    else:
        await interaction.response.send_message("❌ Bot không ở trong voice channel", ephemeral=True)

# -------------------------
# On Ready
# -------------------------
@bot.event
async def on_ready():
    await bot.tree.sync()
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
            description="Nếu bạn cần **Hỗ Trợ** hãy bấm nút **Tạo Ticket** ở dưới",
            color=discord.Color.orange()
        )
        await ticket_channel.send(embed=embed, view=CreateTicketView())

# -------------------------
# On Message (Trigger)
# -------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()
    if (
        "có" in content
        and ("không" in content or "ko" in content)
        and any(keyword in content for keyword in TRIGGER_WORDS)
    ):
        embed = discord.Embed(
            title="📌 Cách tải và client hỗ trợ",
            description=(
                "**Nếu bạn không biết cách tải thì đây nha**\n"
                "👉 [Bấm vào đây để xem hướng dẫn TikTok](https://vt.tiktok.com/ZSSdjBjVE/)\n\n"
                "**Đối với IOS**\n"
                "📥 Krnl VNG: [Tải](https://www.mediafire.com/file/jfx8ynxsxwgyok1/KrnlxVNG+V10.ipa/file)\n"
                "📥 Delta X VNG Fix Lag: [Tải](https://www.mediafire.com/file/7hk0mroimozu08b/DeltaxVNG+Fix+Lag+V6.ipa/file)\n\n"
                "**Đối với Android**\n"
                "📥 Krnl VNG: [Tải](https://tai.natushare.com/GAMES/Blox_Fruit/Blox_Fruit_Krnl_VNG_2.681_BANDISHARE.apk)\n"
                "📥 File login Delta: [Tải](https://link.nestvui.com/BANDISHARE/GAME/Blox_Fruit/Roblox_VNG_Login_Delta_BANDISHARE.apk)\n"
                "📥 File hack Delta X VNG: [Tải](https://download.nestvui.com/BANDISHARE/GAME/Blox_Fruit/Delta_X_VNG_V65_BANDISHARE.iO.apk)"
            ),
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
    print("❌ Lỗi: Chưa đặt DISCORD_TOKEN trong Environment Variables của Render")
else:
    bot.run(DISCORD_TOKEN)
