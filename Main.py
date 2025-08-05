import os
import discord
from discord.ext import commands
from keep_alive import keep_alive
import random

# -------------------------
# Cấu hình bot
# -------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Verify Config
ROLE_ID = 1400724722714542111  # Role Verify của bạn
VERIFY_CHANNEL_ID = 1400732340677771356  # Channel gửi nút Verify

# Ticket Config
GUILD_ID = 1372215595218505891  # Server ID
TICKET_CHANNEL_ID = 1400750812912685056  # Channel gửi nút Ticket (bạn cần đổi)
SUPPORTERS = ["__tobu", "caycotbietmua"]

# Trigger Words
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

        # Kiểm tra supporter nào online
        for member in guild.members:
            if member.name in SUPPORTERS and member.status != discord.Status.offline:
                supporters_online.append(member)

        if not supporters_online:
            await interaction.response.send_message("❌ Hiện không có supporter nào online, vui lòng thử lại sau.", ephemeral=True)
            return

        # Chọn ngẫu nhiên supporter đang online
        supporter = random.choice(supporters_online)

        await interaction.response.send_message(
            f"✅ **{supporter.display_name}** đã được đặt để hỗ trợ cho bạn, vui lòng kiểm tra ticket mới!",
            ephemeral=True
        )

        # Tạo kênh ticket riêng
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

        # Gửi tin nhắn vào ticket
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

    # Gửi Verify Message
    verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if verify_channel:
        embed = discord.Embed(
            title="Xác Thực Thành Viên",
            description="Bấm nút **Verify/Xác Thực** ở dưới để có thể tương tác trong nhóm\n⬇️⬇️⬇️",
            color=discord.Color.green()
        )
        await verify_channel.send(embed=embed, view=VerifyButton())

    # Gửi Ticket Message
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
                "*Bot made by: @__tobu*"
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
