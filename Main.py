import os
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta, timezone
from keep_alive import keep_alive
import random

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
TIME_WINDOW = 30  # giây
MUTE_TIME = 900  # 15 phút
MUTE_ROLE_ID = 1402205863510282240
LOG_CHANNEL_ID = 1402205862985994361

# Voice Channel Hiển Thị Thành Viên
MEMBER_COUNT_CHANNEL_ID = 1402556153275093024

# Log Join/Leave
JOIN_CHANNEL_ID = 1402563416219975791
LEAVE_CHANNEL_ID = 1402564378569736272

user_messages = {}

# Link bị cấm
BLOCK_LINKS = ["youtube.com", "facebook.com"]

# Từ cấm
BAD_WORDS = ["đm", "địt", "lồn", "buồi", "cặc", "mẹ mày", "fuck", "bitch", "dm", "cc"]

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
# Cấu hình Caro
# -------------------------
CARO_CHANNEL_ID = 1402622963823546369  # <-- Đặt ID channel muốn gửi menu Caro

# -------------------------
# Caro Game
# -------------------------
class CaroMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎮 Chơi với Bot", style=discord.ButtonStyle.green)
    async def play_with_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_caro_ticket(interaction, bot_mode=True)

    @discord.ui.button(label="👥 Chơi với Người", style=discord.ButtonStyle.blurple)
    async def play_with_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📌 Vui lòng **tag người chơi** để bắt đầu.", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.mentions and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            opponent = msg.mentions[0]
            await start_caro_ticket(interaction, bot_mode=False, opponent=opponent)
        except asyncio.TimeoutError:
            await interaction.followup.send("❌ Hết thời gian chọn người chơi.", ephemeral=True)


class CaroButton(discord.ui.Button):
    def __init__(self, x, y, label="⬜", disabled=False):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=y, disabled=disabled)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: CaroGameView = self.view
        if view.game_over:
            return await interaction.response.send_message("❌ Trò chơi đã kết thúc.", ephemeral=True)

        if view.bot_mode:
            if interaction.user != view.player1:
                return await interaction.response.send_message("❌ Không phải lượt của bạn.", ephemeral=True)
        else:
            if interaction.user != view.current_turn:
                return await interaction.response.send_message("❌ Không phải lượt của bạn.", ephemeral=True)

        mark = "❌" if view.current_turn == view.player1 else "⭕"
        self.label = mark
        self.disabled = True
        view.board[self.y][self.x] = mark

        # Kiểm tra thắng
        if check_win(view.board, mark):
            view.game_over = True
            await interaction.response.edit_message(content=f"🏆 **{interaction.user.display_name}** đã thắng!", view=view)
            return

        # Chuyển lượt
        if view.bot_mode:
            view.current_turn = None
            await interaction.response.edit_message(view=view)
            await asyncio.sleep(1)
            await bot_move(view)
        else:
            view.current_turn = view.player2 if view.current_turn == view.player1 else view.player1
            await interaction.response.edit_message(content=f"🎯 Lượt của **{view.current_turn.display_name}**", view=view)


class CaroGameView(discord.ui.View):
    def __init__(self, player1, player2=None, bot_mode=False):
        super().__init__(timeout=None)
        self.player1 = player1
        self.player2 = player2
        self.bot_mode = bot_mode
        self.current_turn = player1
        self.game_over = False
        self.board = [["" for _ in range(5)] for _ in range(5)]

        for y in range(5):
            for x in range(5):
                self.add_item(CaroButton(x, y))


def check_win(board, mark):
    for y in range(5):
        for x in range(5):
            if x <= 1 and all(board[y][x+i] == mark for i in range(4)): return True
            if y <= 1 and all(board[y+i][x] == mark for i in range(4)): return True
            if x <= 1 and y <= 1 and all(board[y+i][x+i] == mark for i in range(4)): return True
            if x >= 3 and y <= 1 and all(board[y+i][x-i] == mark for i in range(4)): return True
    return False


async def bot_move(view: CaroGameView):
    for y in range(5):
        for x in range(5):
            if view.board[y][x] == "":
                view.board[y][x] = "⭕"
                for item in view.children:
                    if isinstance(item, CaroButton) and item.x == x and item.y == y:
                        item.label = "⭕"
                        item.disabled = True
                break
        else:
            continue
        break

    if check_win(view.board, "⭕"):
        view.game_over = True
        await view.message.edit(content="💻 Bot đã thắng!", view=view)
    else:
        view.current_turn = view.player1
        await view.message.edit(content=f"🎯 Lượt của **{view.player1.display_name}**", view=view)


async def start_caro_ticket(interaction, bot_mode=False, opponent=None):
    guild = interaction.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    if bot_mode:
        title = f"caro-bot-{interaction.user.name}"
    else:
        overwrites[opponent] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        title = f"caro-vs-{interaction.user.name}-{opponent.name}"

    ticket_channel = await guild.create_text_channel(title, overwrites=overwrites)

    view = CaroGameView(player1=interaction.user, player2=opponent, bot_mode=bot_mode)
    msg = await ticket_channel.send(
        content=f"🎮 Bắt đầu Caro! {'(với Bot)' if bot_mode else f'({interaction.user.mention} vs {opponent.mention})'}\n🎯 Lượt của **{interaction.user.display_name}**",
        view=view
    )
    view.message = msg

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

    # Khởi tạo view
    bot.add_view(CaroMenuView())
    bot.add_view(VerifyButton())
    bot.add_view(CreateTicketView())
    bot.add_view(CloseTicketView())

    # Caro
    caro_channel = bot.get_channel(CARO_CHANNEL_ID)
    if caro_channel and isinstance(caro_channel, discord.TextChannel):
        try:
            await caro_channel.purge(limit=10)
            embed = discord.Embed(
                title="🎮 Chơi Caro",
                description="Bấm nút để tạo phòng Caro chơi với người khác hoặc bot.",
                color=discord.Color.blurple()
            )
            await caro_channel.send(embed=embed, view=CaroMenuView())
        except Exception as e:
            print(f"❌ Lỗi gửi Caro menu: {e}")
    else:
        print("⚠️ Không tìm thấy Caro channel hoặc không phải TextChannel")

    # Verify
    verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if verify_channel and isinstance(verify_channel, discord.TextChannel):
        try:
            embed = discord.Embed(
                title="Xác Thực Thành Viên",
                description="Bấm nút **Verify/Xác Thực** ở dưới để có thể tương tác trong nhóm\n⬇️⬇️⬇️",
                color=discord.Color.green()
            )
            await verify_channel.send(embed=embed, view=VerifyButton())
        except Exception as e:
            print(f"❌ Lỗi gửi Verify menu: {e}")
    else:
        print("⚠️ Không tìm thấy Verify channel hoặc không phải TextChannel")
# -------------------------
# Cập nhật số thành viên & online
# -------------------------
@tasks.loop(minutes=1)
async def update_member_count():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    total_members = len([m for m in guild.members if not m.bot and not m.system])
    online_members = len([m for m in guild.members if not m.bot and not m.system and m.status != discord.Status.offline])

    channel = guild.get_channel(MEMBER_COUNT_CHANNEL_ID)
    if channel:
        await channel.edit(name=f"📊 {total_members} thành viên | 🟢 {online_members} online")
        overwrite = discord.PermissionOverwrite(connect=False, view_channel=True, send_messages=False)
        await channel.set_permissions(guild.default_role, overwrite=overwrite)

# -------------------------
# Thông báo khi có người vào / rời
# -------------------------
@bot.event
async def on_member_join(member):
    if member.bot or member.system:
        return
    channel = bot.get_channel(JOIN_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="👋 Chào mừng thành viên mới!",
            description=f"Xin chào {member.mention}, chúc bạn vui vẻ trong server!",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.timestamp = datetime.now(timezone.utc)
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    if member.bot or member.system:
        return
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="👋 Tạm biệt!",
            description=f"Thành viên **{member.name}** đã rời khỏi server.",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.timestamp = datetime.now(timezone.utc)
        await channel.send(embed=embed)

# -------------------------
# Mute + Xóa tin nhắn + Log
# -------------------------
async def mute_and_log(message, reason="vi phạm"):
    try:
        mute_role = message.guild.get_role(MUTE_ROLE_ID)
        if not mute_role:
            print("❌ Không tìm thấy role mute!")
            return

        # Xóa toàn bộ tin nhắn vi phạm trong TIME_WINDOW giây
        async for msg in message.channel.history(limit=200):
            if msg.author == message.author and (datetime.now(timezone.utc) - msg.created_at).seconds <= TIME_WINDOW:
                try:
                    await msg.delete()
                except:
                    pass

        # Mute user
        await message.author.add_roles(mute_role)

        # Gửi log
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🚨 Phát hiện vi phạm",
                description=f"**Người vi phạm:** {message.author.mention}\n**Lý do:** {reason}\n**Thời gian mute:** 15 phút",
                color=discord.Color.red()
            )
            embed.add_field(name="Nội dung", value=message.content or "*Không có nội dung*", inline=False)
            embed.add_field(name="Kênh", value=message.channel.mention, inline=True)
            embed.timestamp = datetime.now(timezone.utc)
            await log_channel.send(embed=embed)

        # Gỡ mute sau MUTE_TIME
        await asyncio.sleep(MUTE_TIME)
        await message.author.remove_roles(mute_role)

    except Exception as e:
        print(f"Lỗi mute_and_log: {e}")

# -------------------------
# On Message (Filter + Anti-Spam)
# -------------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()

    # 1. Từ cấm
    if any(bad_word in content_lower for bad_word in BAD_WORDS):
        await mute_and_log(message, "dùng từ ngữ tục tĩu")
        return

    # 2. Link bị cấm
    if any(block in content_lower for block in BLOCK_LINKS):
        await mute_and_log(message, "gửi link bị cấm")
        return

    # 3. Anti spam
    now = datetime.now()
    uid = message.author.id
    if uid not in user_messages:
        user_messages[uid] = []
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if now - t < timedelta(seconds=TIME_WINDOW)]

    if len(user_messages[uid]) > SPAM_LIMIT:
        await mute_and_log(message, "spam tin nhắn")
        user_messages[uid] = []
        return

    await bot.process_commands(message)

# -------------------------
# Run Bot
# -------------------------
keep_alive()

if not DISCORD_TOKEN:
    print("❌ Chưa đặt DISCORD_TOKEN")
else:
    bot.run(DISCORD_TOKEN)
