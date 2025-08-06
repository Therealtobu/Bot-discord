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

# Caro Channel ID
CARO_CHANNEL_ID = 1402622963823546369

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

    @discord.ui.button(label="✅ Verify / Xác Thực", style=discord.ButtonStyle.green, custom_id="verify_button")
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

    @discord.ui.button(label="🔒 Đóng Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Ticket sẽ bị đóng trong 3 giây...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Tạo Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = bot.get_guild(GUILD_ID)
        supporters_online = [
            m for m in guild.members if m.name in SUPPORTERS and m.status != discord.Status.offline
        ]

        if not supporters_online:
            await interaction.response.send_message("❌ Không có supporter nào online!", ephemeral=True)
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
            description=f"{supporter.mention} sẽ hỗ trợ bạn.\nVui lòng mô tả vấn đề.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())

        await interaction.response.send_message(
            f"✅ Ticket của bạn đã được tạo và {supporter.mention} sẽ hỗ trợ sớm!",
            ephemeral=True
        )

# -------------------------
# Cập nhật số thành viên
# -------------------------
@tasks.loop(minutes=1)
async def update_member_count():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    total_members = len([m for m in guild.members if not m.bot])
    online_members = len([m for m in guild.members if not m.bot and m.status != discord.Status.offline])

    channel = guild.get_channel(MEMBER_COUNT_CHANNEL_ID)
    if channel:
        await channel.edit(name=f"📊 {total_members} thành viên | 🟢 {online_members} online")
        overwrite = discord.PermissionOverwrite(connect=False, view_channel=True, send_messages=False)
        await channel.set_permissions(guild.default_role, overwrite=overwrite)

# -------------------------
# Mute + Xóa tin nhắn + Log
# -------------------------
async def mute_and_log(message, reason="vi phạm"):
    try:
        mute_role = message.guild.get_role(MUTE_ROLE_ID)
        if not mute_role:
            return

        # Xóa tin nhắn vi phạm
        async for msg in message.channel.history(limit=200):
            if msg.author == message.author and (datetime.now(timezone.utc) - msg.created_at).seconds <= TIME_WINDOW:
                try:
                    await msg.delete()
                except:
                    pass

        await message.author.add_roles(mute_role)

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🚨 Vi phạm",
                description=f"**Người vi phạm:** {message.author.mention}\n**Lý do:** {reason}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed)

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

    if any(bad_word in content_lower for bad_word in BAD_WORDS):
        await mute_and_log(message, "Dùng từ ngữ tục tĩu")
        return

    if any(block in content_lower for block in BLOCK_LINKS):
        await mute_and_log(message, "Gửi link bị cấm")
        return

    now = datetime.now()
    uid = message.author.id
    if uid not in user_messages:
        user_messages[uid] = []
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if now - t < timedelta(seconds=TIME_WINDOW)]

    if len(user_messages[uid]) > SPAM_LIMIT:
        await mute_and_log(message, "Spam tin nhắn")
        user_messages[uid] = []
        return

    await bot.process_commands(message)
    # -------------------------
# Caro Game
# -------------------------
class CaroMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎮 Chơi với máy", style=discord.ButtonStyle.green, custom_id="play_with_bot")
    async def play_with_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await start_caro_ticket(interaction, bot_mode=True)

    @discord.ui.button(label="👥 Chơi với người", style=discord.ButtonStyle.blurple, custom_id="play_with_player")
    async def play_with_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📌 Vui lòng **tag đối thủ** để bắt đầu (10 giây).", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.mentions and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=10)
            opponent = msg.mentions[0]
            # Xóa tin nhắn tag sau khi nhận
            await msg.delete()
            await start_caro_ticket(interaction, bot_mode=False, opponent=opponent)
        except asyncio.TimeoutError:
            async for m in interaction.channel.history(limit=20):
                if m.author == interaction.user:
                    await m.delete()
            await interaction.followup.send("⏳ Hết thời gian chọn đối thủ. Tin nhắn đã bị xóa.", ephemeral=True)


class CaroButton(discord.ui.Button):
    def __init__(self, x, y, label="⬜", disabled=False):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, row=y, disabled=disabled, custom_id=f"caro_{x}_{y}")
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

        # Kiểm tra thắng hoặc hòa
        if check_win(view.board, mark):
            view.game_over = True
            await interaction.response.edit_message(content=f"🏆 **{interaction.user.display_name}** đã thắng!", view=view_with_close(view))
            return

        if all(cell != "" for row in view.board for cell in row):  # Hòa
            view.game_over = True
            await interaction.response.edit_message(content="🤝 Trận đấu hòa!", view=view_with_close(view))
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


def view_with_close(view):
    close_btn = CloseTicketView()
    for item in view.children:
        close_btn.add_item(item)
    return close_btn


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
        await view.message.edit(content="💻 Bot đã thắng!", view=view_with_close(view))
    elif all(cell != "" for row in view.board for cell in row):
        view.game_over = True
        await view.message.edit(content="🤝 Trận đấu hòa!", view=view_with_close(view))
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
# On Ready
# -------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")

    bot.add_view(CaroMenuView())
    bot.add_view(VerifyButton())
    bot.add_view(CreateTicketView())
    bot.add_view(CloseTicketView())

    # Gửi menu Caro
    caro_channel = bot.get_channel(CARO_CHANNEL_ID)
    if caro_channel:
        try:
            await caro_channel.purge(limit=10)
        except:
            pass
        embed = discord.Embed(
            title="🎮 Chơi Caro",
            description="Bấm nút để tạo phòng Caro chơi với người khác hoặc bot.",
            color=discord.Color.blurple()
        )
        await caro_channel.send(embed=embed, view=CaroMenuView())

    # Gửi Verify
    verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if verify_channel:
        embed = discord.Embed(
            title="Xác Thực Thành Viên",
            description="Bấm nút **Verify/Xác Thực** để tương tác.",
            color=discord.Color.green()
        )
        await verify_channel.send(embed=embed, view=VerifyButton())

    # Gửi Ticket
    ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
    if ticket_channel:
        embed = discord.Embed(
            title="📢 Hỗ Trợ",
            description="Bấm nút **Tạo Ticket** nếu cần hỗ trợ.",
            color=discord.Color.orange()
        )
        await ticket_channel.send(embed=embed, view=CreateTicketView())

    # Chạy server stats
    update_member_count.start()

# -------------------------
# Run Bot
# -------------------------
keep_alive()
if not DISCORD_TOKEN:
    print("❌ Chưa đặt DISCORD_TOKEN")
else:
    bot.run(DISCORD_TOKEN)
