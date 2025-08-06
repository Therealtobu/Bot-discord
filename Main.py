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
            description="Nếu bạn cần **Hỗ Trợ** hãy bấm nút **Tạo Ticket** ở dưới\n"
                "---------------------\n"
                "LƯU Ý: Vì các Mod khá bận nên việc Support vấn đề sẽ khá lâu và **Tuyệt đối không được spam nhiều ticket**.\n"
                "Khi tạo ticket thì **nói thẳng vấn đề luôn**.\n"
                "Nếu không tuân thủ các luật trên sẽ bị **mute 1 ngày**.",
            color=discord.Color.orange()
        )
        await ticket_channel.send(embed=embed, view=CreateTicketView())

    # Khởi động cập nhật số thành viên
    update_member_count.start()
    # ==========================
# Game Caro
# ==========================
CARO_BOARD_SIZE = 3  # 3x3

class CaroGame:
    def __init__(self, player_x, player_o, vs_bot=False):
        self.board = [[" " for _ in range(CARO_BOARD_SIZE)] for _ in range(CARO_BOARD_SIZE)]
        self.current_turn = "X"
        self.player_x = player_x
        self.player_o = player_o
        self.vs_bot = vs_bot
        self.game_over = False

    def make_move(self, x, y, player):
        if self.game_over or self.board[y][x] != " ":
            return False
        if (self.current_turn == "X" and player != self.player_x) or (self.current_turn == "O" and player != self.player_o):
            return False

        self.board[y][x] = self.current_turn
        if self.check_winner(self.current_turn):
            self.game_over = True
            return f"{player.mention} thắng!"
        elif self.is_full():
            self.game_over = True
            return "Trận đấu hòa!"
        else:
            self.current_turn = "O" if self.current_turn == "X" else "X"
            return True

    def is_full(self):
        return all(self.board[y][x] != " " for y in range(CARO_BOARD_SIZE) for x in range(CARO_BOARD_SIZE))

    def check_winner(self, mark):
        for y in range(CARO_BOARD_SIZE):
            if all(self.board[y][x] == mark for x in range(CARO_BOARD_SIZE)):
                return True
        for x in range(CARO_BOARD_SIZE):
            if all(self.board[y][x] == mark for y in range(CARO_BOARD_SIZE)):
                return True
        if all(self.board[i][i] == mark for i in range(CARO_BOARD_SIZE)):
            return True
        if all(self.board[i][CARO_BOARD_SIZE - 1 - i] == mark for i in range(CARO_BOARD_SIZE)):
            return True
        return False

    def get_board_str(self):
        return "\n".join([" | ".join(row) for row in self.board])


# ==========================
# View để chơi Caro
# ==========================
class CaroView(discord.ui.View):
    def __init__(self, game, channel):
        super().__init__(timeout=None)
        self.game = game
        self.channel = channel
        for y in range(CARO_BOARD_SIZE):
            row = []
            for x in range(CARO_BOARD_SIZE):
                btn = discord.ui.Button(label=" ", style=discord.ButtonStyle.secondary, row=y)
                btn.callback = self.make_callback(x, y, btn)
                row.append(btn)
                self.add_item(btn)

    def make_callback(self, x, y, btn):
        async def callback(interaction: discord.Interaction):
            result = self.game.make_move(x, y, interaction.user)
            if result is False:
                await interaction.response.send_message("Nước đi không hợp lệ!", ephemeral=True)
                return
            elif isinstance(result, str):  # Có người thắng hoặc hòa
                btn.label = self.game.current_turn
                btn.style = discord.ButtonStyle.success
                for item in self.children:
                    item.disabled = True
                await interaction.response.edit_message(content=f"**{result}**", view=self)
                await self.channel.send(view=CloseTicketView())  # hiện nút đóng ticket
                return
            else:
                btn.label = self.game.current_turn
                btn.style = discord.ButtonStyle.success
                btn.disabled = True
                await interaction.response.edit_message(content=f"Đến lượt: {self.game.current_turn}", view=self)

                # Nếu chơi với bot
                if self.game.vs_bot and self.game.current_turn == "O" and not self.game.game_over:
                    await asyncio.sleep(1)
                    empty_cells = [(ix, iy) for iy in range(CARO_BOARD_SIZE) for ix in range(CARO_BOARD_SIZE) if self.game.board[iy][ix] == " "]
                    if empty_cells:
                        bot_x, bot_y = random.choice(empty_cells)
                        bot_result = self.game.make_move(bot_x, bot_y, self.game.player_o)
                        for item in self.children:
                            if getattr(item, "row", None) == bot_y and item.label == " ":
                                item.label = "O"
                                item.style = discord.ButtonStyle.danger
                                item.disabled = True
                                break
                        if isinstance(bot_result, str):
                            for item in self.children:
                                item.disabled = True
                            await interaction.edit_original_response(content=f"**{bot_result}**", view=self)
                            await self.channel.send(view=CloseTicketView())
                        else:
                            await interaction.edit_original_response(content=f"Đến lượt: {self.game.current_turn}", view=self)
        return callback


# ==========================
# Nút chọn chế độ chơi
# ==========================
class CaroMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🤖 Chơi với máy", style=discord.ButtonStyle.green)
    async def play_vs_bot(self, interaction: discord.Interaction, button: discord.ui.Button):
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(f"caro-vsbot-{interaction.user.name}", overwrites=overwrites)
        game = CaroGame(interaction.user, bot.user, vs_bot=True)
        await channel.send(f"🎮 Bắt đầu chơi Caro với bot!\nLượt: **{game.current_turn}**", view=CaroView(game, channel))

    @discord.ui.button(label="👥 Chơi với người", style=discord.ButtonStyle.blurple)
    async def play_vs_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg = await interaction.response.send_message("Hãy tag người bạn muốn chơi trong vòng 10 giây...", ephemeral=True)
        try:
            def check(m):
                return m.author == interaction.user and m.mentions
            reply = await bot.wait_for("message", check=check, timeout=10)
            opponent = reply.mentions[0]
            await reply.delete()
        except asyncio.TimeoutError:
            await interaction.followup.send("⏳ Hết thời gian tag đối thủ!", ephemeral=True)
            return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            opponent: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel = await interaction.guild.create_text_channel(f"caro-{interaction.user.name}-vs-{opponent.name}", overwrites=overwrites)
        game = CaroGame(interaction.user, opponent)
        await channel.send(f"🎮 Bắt đầu chơi Caro!\nLượt: **{game.current_turn}**", view=CaroView(game, channel))


# ==========================
# Command để gửi menu Caro
# ==========================
@bot.command()
async def caro(ctx):
    embed = discord.Embed(
        title="🎯 Game Caro",
        description="Chọn chế độ chơi bên dưới:",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=CaroMenuView())


# ==========================
# Chạy bot
# ==========================
keep_alive()

if not DISCORD_TOKEN:
    print("❌ Chưa đặt DISCORD_TOKEN")
else:
    bot.run(DISCORD_TOKEN)
