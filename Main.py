import os
import discord
from discord.ext import commands, tasks
import asyncio
import aiohttp
import re
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

# Caro Config
CARO_CHANNEL_ID = 1402622963823546369

# Anti-Spam & Filter Config
SPAM_LIMIT = 5
TIME_WINDOW = 30
MUTE_TIME = 900
MUTE_ROLE_ID = 1402205863510282240
LOG_CHANNEL_ID = 1402205862985994361

# Voice Channel Hiển Thị Thành Viên
MEMBER_COUNT_CHANNEL_ID = 1402556153275093024

# Log Join/Leave
JOIN_CHANNEL_ID = 1402563416219975791
LEAVE_CHANNEL_ID = 1402564378569736272

# TikTok Notify
TIKTOK_USERNAME = "caycotbietmua"
TIKTOK_NOTIFY_CHANNEL_ID = 1402191653531549807
TIKTOK_CHECK_INTERVAL = 300
last_tiktok_video_id = None

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
# Ticket Buttons
# -------------------------
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Ticket sẽ bị đóng...", ephemeral=True)
        await interaction.channel.delete()

class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Tạo Ticket", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = bot.get_guild(GUILD_ID)
        supporters_online = [m for m in guild.members if m.name in SUPPORTERS and m.status != discord.Status.offline]
        if not supporters_online:
            await interaction.response.send_message("❌ Không có supporter nào online.", ephemeral=True)
            return
        supporter = random.choice(supporters_online)
        await interaction.response.send_message(f"✅ **{supporter.display_name}** sẽ hỗ trợ bạn.", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            supporter: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)

        embed = discord.Embed(
            title="🎫 Ticket Hỗ Trợ",
            description=f"{supporter.mention} sẽ hỗ trợ bạn.\nVui lòng mô tả vấn đề.",
            color=discord.Color.blue()
        )
        await ticket_channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())
        # -------------------------
# Caro Game (Thông minh + Ticket khi chơi)
# -------------------------
class CaroGame:
    def __init__(self, player1, player2, size=10):
        self.size = size
        self.board = [["⬜" for _ in range(size)] for _ in range(size)]
        self.player1 = player1
        self.player2 = player2
        self.turn = player1
        self.symbols = {player1: "❌", player2: "⭕"}
        self.game_over = False

    def display(self):
        return "\n".join("".join(row) for row in self.board)

    def place(self, player, x, y):
        if self.game_over:
            return False, "❌ Trò chơi đã kết thúc."
        if self.turn != player:
            return False, "⏳ Chưa đến lượt của bạn."
        if x < 0 or x >= self.size or y < 0 or y >= self.size:
            return False, "❌ Vị trí không hợp lệ."
        if self.board[y][x] != "⬜":
            return False, "❌ Ô này đã được đánh."

        self.board[y][x] = self.symbols[player]
        if self.check_win(self.symbols[player]):
            self.game_over = True
            return True, f"🎉 {player.mention} đã thắng!\n{self.display()}"
        elif all(cell != "⬜" for row in self.board for cell in row):
            self.game_over = True
            return True, f"🤝 Hòa!\n{self.display()}"

        self.turn = self.player1 if self.turn == self.player2 else self.player2
        return True, self.display()

    def check_win(self, symbol):
        for y in range(self.size):
            for x in range(self.size):
                if self.check_dir(x, y, 1, 0, symbol) or \
                   self.check_dir(x, y, 0, 1, symbol) or \
                   self.check_dir(x, y, 1, 1, symbol) or \
                   self.check_dir(x, y, 1, -1, symbol):
                    return True
        return False

    def check_dir(self, x, y, dx, dy, symbol):
        try:
            for i in range(5):
                if self.board[y + i*dy][x + i*dx] != symbol:
                    return False
            return True
        except IndexError:
            return False

active_games = {}

@bot.command(name="caro")
async def caro(ctx, opponent: discord.Member = None):
    """Bắt đầu chơi caro với bot hoặc người khác."""
    if ctx.channel.id != CARO_CHANNEL_ID:
        return await ctx.send("❌ Bạn chỉ có thể chơi caro trong kênh được chỉ định.")

    if opponent is None or opponent == bot.user:
        opponent = bot.user
    if opponent == ctx.author:
        return await ctx.send("❌ Bạn không thể chơi với chính mình.")

    game_key = frozenset({ctx.author.id, opponent.id})
    if game_key in active_games:
        return await ctx.send("❌ Trò chơi giữa hai người này đang diễn ra.")

    game = CaroGame(ctx.author, opponent)
    active_games[game_key] = game

    # Tạo ticket khi chơi với bot hoặc người
    guild = bot.get_guild(GUILD_ID)
    supporter = ctx.author if opponent == bot.user else opponent
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        ctx.author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        supporter: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    ticket_channel = await guild.create_text_channel(
        f"caro-{ctx.author.name}",
        overwrites=overwrites
    )

    await ticket_channel.send(f"🎮 **Bắt đầu chơi Caro**: {ctx.author.mention} vs {supporter.mention}\n{game.display()}")

    await ctx.send(f"✅ Trò chơi Caro đã được tạo trong {ticket_channel.mention}")

@bot.command(name="danh")
async def danh(ctx, x: int, y: int):
    """Đánh nước Caro tại tọa độ (x, y)."""
    game_key = next((key for key in active_games if ctx.author.id in key), None)
    if not game_key:
        return await ctx.send("❌ Bạn không đang trong trò chơi Caro nào.")

    game = active_games[game_key]
    success, message = game.place(ctx.author, x, y)
    await ctx.send(message)

    # Nếu chơi với bot => bot đánh thông minh
    if not game.game_over and game.turn == bot.user:
        move = bot_caro_move(game)
        if move:
            game.place(bot.user, *move)
            await ctx.send(f"🤖 Bot đánh tại {move}\n{game.display()}")

def bot_caro_move(game: CaroGame):
    """Bot đánh thông minh: ưu tiên thắng, chặn thua."""
    # Chặn thua hoặc thắng ngay
    for y in range(game.size):
        for x in range(game.size):
            if game.board[y][x] == "⬜":
                game.board[y][x] = game.symbols[bot.user]
                if game.check_win(game.symbols[bot.user]):
                    game.board[y][x] = "⬜"
                    return (x, y)
                game.board[y][x] = "⬜"

    for y in range(game.size):
        for x in range(game.size):
            if game.board[y][x] == "⬜":
                game.board[y][x] = game.symbols[game.player1]
                if game.check_win(game.symbols[game.player1]):
                    game.board[y][x] = "⬜"
                    return (x, y)
                game.board[y][x] = "⬜"

    # Nếu không thì đánh ngẫu nhiên
    empty_cells = [(x, y) for y in range(game.size) for x in range(game.size) if game.board[y][x] == "⬜"]
    return random.choice(empty_cells) if empty_cells else None

# -------------------------
# Các event khác (giữ nguyên như code gốc của bạn)
# -------------------------
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập: {bot.user}")
    verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
    if verify_channel:
        embed = discord.Embed(
            title="Xác Thực Thành Viên",
            description="Bấm nút **Verify/Xác Thực** để tham gia.\n⬇️⬇️⬇️",
            color=discord.Color.green()
        )
        await verify_channel.send(embed=embed, view=VerifyButton())
    ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
    if ticket_channel:
        embed = discord.Embed(
            title="📢 Hỗ Trợ",
            description="Bấm **Tạo Ticket** nếu cần hỗ trợ.\nKhông spam ticket!",
            color=discord.Color.orange()
        )
        await ticket_channel.send(embed=embed, view=CreateTicketView())
    update_member_count.start()
    check_tiktok_new_video.start()

# -------------------------
# Run Bot
# -------------------------
keep_alive()

if not DISCORD_TOKEN:
    print("❌ Chưa đặt DISCORD_TOKEN")
else:
    bot.run(DISCORD_TOKEN)
