import os
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta, timezone
from keep_alive import keep_alive
import random
import json
import re
from github import Github
import base64

# -------------------------
# Cấu hình bot
# -------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "TobuTheXd/Bot-discord"  # Thay bằng tên repository
FILE_PATH = "data.json"

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
MUTE_TIME_BADWORD = 900  # 15 phút
MUTE_TIME_LINK = 86400  # 1 ngày
MUTE_ROLE_ID = 1402205863510282240
LOG_CHANNEL_ID = 1402205862985994361

# Voice Channel Hiển Thị Thành Viên
MEMBER_COUNT_CHANNEL_ID = 1402556153275093024

# Log Join/Leave
JOIN_CHANNEL_ID = 1402563416219975791
LEAVE_CHANNEL_ID = 1402564378569736272

# Caro Config
CARO_CHANNEL_ID = 1402622963823546369
BOARD_SIZES = {"3x3": 3, "5x5": 5}
games = {}
board_messages = {}
control_messages = {}
selected_board_size = {}

# Link bị cấm
BLOCK_LINKS = ["hentai", "porn", "xhamster" ]

# Từ cấm
BAD_WORDS = ["đm", "địt", "lồn", "buồi", "cặc", "mẹ mày", "fuck", "bitch", "dm", "cc"]

# Từ đáng ngờ cho thành viên mới (dưới 1 ngày)
SUSPICIOUS_WORDS = ["xin hack roblox", "xin krnl", "xin delta x", "hack roblox", "krnl", "delta x"]

# Khởi tạo dữ liệu từ GitHub
data = {}
g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
if g:
    try:
        repo = g.get_repo(REPO_NAME)
        file = repo.get_contents(FILE_PATH)
        loaded = json.loads(base64.b64decode(file.content).decode('utf-8'))
        data = {
            k: {
                'last_daily': datetime.fromisoformat(v['last_daily']) if v['last_daily'] else None,
            } for k, v in loaded.items()
        }
    except Exception as e:
        print(f"❌ Lỗi khi đọc data.json từ GitHub: {e}")
        data = {}
        repo.create_file(FILE_PATH, "Create data.json", json.dumps(data, indent=2))

def save_data():
    if g:
        try:
            repo = g.get_repo(REPO_NAME)
            content = {
                k: {
                    'last_daily': v['last_daily'].isoformat() if v['last_daily'] else None,
                } for k, v in data.items()
            }
            try:
                file = repo.get_contents(FILE_PATH)
                repo.update_file(
                    FILE_PATH,
                    f"Update data.json {datetime.now(timezone.utc).isoformat()}",
                    json.dumps(content, indent=2),
                    file.sha
                )
            except:
                repo.create_file(FILE_PATH, "Create data.json", json.dumps(content, indent=2))
        except Exception as e:
            print(f"❌ Lỗi khi đẩy data.json lên GitHub: {e}")

# Intents
intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# -------------------------
# Caro Game Class
# -------------------------
class CaroGame:
    def __init__(self, player1, player2=None, is_bot=False, size=5):
        self.size = size
        self.board = [[" " for _ in range(size)] for _ in range(size)]
        self.player1 = player1
        self.player2 = player2
        self.is_bot = is_bot
        self.current_player = player1
        self.symbols = {player1: "X", player2: "O" if player2 else "O"}
        self.buttons = []
        self.last_move_time = asyncio.get_event_loop().time()

    def create_board(self):
        self.buttons = []
        for i in range(self.size):
            row = []
            for j in range(self.size):
                label = "⬜" if self.board[i][j] == " " else ("❌" if self.board[i][j] == "X" else "⭕")
                style = discord.ButtonStyle.secondary if self.board[i][j] == " " else (
                    discord.ButtonStyle.success if self.board[i][j] == "X" else discord.ButtonStyle.danger
                )
                row.append(discord.ui.Button(label=label, style=style, custom_id=f"caro_{i}_{j}", disabled=self.board[i][j] != " ", row=i))
            self.buttons.append(row)

    def reset_board(self):
        self.board = [[" " for _ in range(self.size)] for _ in range(self.size)]
        self.current_player = self.player1
        self.last_move_time = asyncio.get_event_loop().time()
        self.create_board()

    def check_winner(self, symbol):
        for row in self.board:
            for i in range(self.size - 2):
                if row[i:i+3] == [symbol, symbol, symbol]:
                    return True
        for j in range(self.size):
            for i in range(self.size - 2):
                if [self.board[i+k][j] for k in range(3)] == [symbol, symbol, symbol]:
                    return True
        for i in range(self.size - 2):
            for j in range(self.size - 2):
                if [self.board[i+k][j+k] for k in range(3)] == [symbol, symbol, symbol]:
                    return True
        for i in range(self.size - 2):
            for j in range(2, self.size):
                if [self.board[i+k][j-k] for k in range(3)] == [symbol, symbol, symbol]:
                    return True
        if all(self.board[i][j] != " " for i in range(self.size) for j in range(self.size)):
            return "draw"
        return False

    def bot_move(self):
        empty_cells = [(i, j) for i in range(self.size) for j in range(self.size) if self.board[i][j] == " "]
        if empty_cells:
            return random.choice(empty_cells)
        return None

# -------------------------
# Verify Button
# -------------------------
class VerifyButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify / Xác Thực", style=discord.ButtonStyle.success)
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

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Ticket sẽ bị đóng trong 3 giây...", ephemeral=True)
        await asyncio.sleep(3)
        await interaction.channel.delete()

class CreateTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Tạo Ticket", style=discord.ButtonStyle.success)
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
    print(f"Current directory: {os.getcwd()}")

    try:
        # Verify Embed
        verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
        if verify_channel:
            print(f"✅ Tìm thấy kênh verify: {VERIFY_CHANNEL_ID}")
            async for msg in verify_channel.history(limit=50):
                if msg.author == bot.user:
                    try:
                        await msg.delete()
                        print(f"✅ Đã xóa tin nhắn cũ trong kênh verify")
                    except Exception as e:
                        print(f"❌ Lỗi khi xóa tin nhắn cũ trong verify: {e}")
            embed = discord.Embed(
                title="Xác Thực Thành Viên",
                description="Bấm nút **Verify/Xác Thực** ở dưới để có thể tương tác trong nhóm\n⬇️⬇️⬇️",
                color=discord.Color.green()
            )
            await verify_channel.send(embed=embed, view=VerifyButton())
            print(f"✅ Đã gửi embed verify đến kênh {verify_channel.name}")
        else:
            print(f"❌ Không tìm thấy kênh verify: {VERIFY_CHANNEL_ID}")

        # Ticket Embed
        ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
        if ticket_channel:
            print(f"✅ Tìm thấy kênh ticket: {TICKET_CHANNEL_ID}")
            async for msg in ticket_channel.history(limit=50):
                if msg.author == bot.user:
                    try:
                        await msg.delete()
                        print(f"✅ Đã xóa tin nhắn cũ trong kênh ticket")
                    except Exception as e:
                        print(f"❌ Lỗi khi xóa tin nhắn cũ trong ticket: {e}")
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
            print(f"✅ Đã gửi embed ticket đến kênh {ticket_channel.name}")
        else:
            print(f"❌ Không tìm thấy kênh ticket: {TICKET_CHANNEL_ID}")

        # Caro Embed
        caro_channel = bot.get_channel(CARO_CHANNEL_ID)
        if caro_channel:
            print(f"✅ Tìm thấy kênh caro: {CARO_CHANNEL_ID}")
            async for msg in caro_channel.history(limit=50):
                if msg.author == bot.user:
                    try:
                        await msg.delete()
                        print(f"✅ Đã xóa tin nhắn cũ trong kênh caro")
                    except Exception as e:
                        print(f"❌ Lỗi khi xóa tin nhắn cũ trong caro: {e}")
            embed = discord.Embed(
                title="Cờ Caro",
                description="Chọn chế độ chơi và kích thước bảng:",
                color=discord.Color.blue()
            )
            view = discord.ui.View()
            try:
                view.add_item(discord.ui.Button(label="Chơi với máy", style=discord.ButtonStyle.success, custom_id="play_bot"))
                view.add_item(discord.ui.Button(label="Chơi với người", style=discord.ButtonStyle.primary, custom_id="play_human"))
                select = discord.ui.Select(placeholder="Chọn kích thước bảng", options=[
                    discord.SelectOption(label="3x3", value="3x3"),
                    discord.SelectOption(label="5x5", value="5x5")
                ], custom_id="board_size")
                view.add_item(select)
                await caro_channel.send(embed=embed, view=view)
                print(f"✅ Đã gửi embed caro đến kênh: {caro_channel.name}")
            except Exception as e:
                print(f"❌ Lỗi khi gửi embed caro: {e}")
        else:
            print(f"❌ Không tìm thấy kênh caro: {CARO_CHANNEL_ID}")

        # Khởi động cập nhật số thành viên
        update_member_count.start()
        print("✅ Đã khởi động task update_member_count")

    except Exception as e:
        print(f"❌ Lỗi trong on_ready: {e}")

# -------------------------
# Cập nhật số thành viên & online
# -------------------------
@tasks.loop(minutes=1)
async def update_member_count():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print(f"❌ Không tìm thấy guild: {GUILD_ID}")
        return

    total_members = len([m for m in guild.members if not m.bot and not m.system])
    online_members = len([m for m in guild.members if not m.bot and not m.system and m.status != discord.Status.offline])

    channel = guild.get_channel(MEMBER_COUNT_CHANNEL_ID)
    if channel:
        try:
            await channel.edit(name=f"📊 {total_members} thành viên | 🟢 {online_members} online")
            overwrite = discord.PermissionOverwrite(connect=False, view_channel=True, send_messages=False)
            await channel.set_permissions(guild.default_role, overwrite=overwrite)
            print(f"✅ Đã cập nhật kênh thành viên: {total_members} thành viên, {online_members} online")
        except Exception as e:
            print(f"❌ Lỗi khi cập nhật số thành viên: {e}")

# -------------------------
# Thông báo khi có người vào / rời
# -------------------------
@bot.event
async def on_member_join(member):
    if member.bot or member.system:
        return
    channel = bot.get_channel(JOIN_CHANNEL_ID)
    if channel:
        try:
            embed = discord.Embed(
                title="👋 Chào mừng thành viên mới!",
                description=f"Xin chào {member.mention}, chúc bạn vui vẻ trong server!",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.timestamp = datetime.now(timezone.utc)
            await channel.send(embed=embed)
            print(f"✅ Đã gửi thông báo member join: {member.name}")
        except Exception as e:
            print(f"❌ Lỗi khi gửi thông báo member join: {e}")

@bot.event
async def on_member_remove(member):
    if member.bot or member.system:
        return
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if channel:
        try:
            embed = discord.Embed(
                title="👋 Tạm biệt!",
                description=f"Thành viên **{member.name}** đã rời khỏi server.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            embed.timestamp = datetime.now(timezone.utc)
            await channel.send(embed=embed)
            print(f"✅ Đã gửi thông báo member leave: {member.name}")
        except Exception as e:
            print(f"❌ Lỗi khi gửi thông báo member leave: {e}")

# -------------------------
# Mute + Xóa tin nhắn + Log
# -------------------------
async def mute_and_log(message, reason="vi phạm", mute_time=900):
    try:
        mute_role = message.guild.get_role(MUTE_ROLE_ID)
        if not mute_role:
            print("❌ Không tìm thấy role mute!")
            return

        async for msg in message.channel.history(limit=50):
            if msg.author == message.author and (datetime.now(timezone.utc) - msg.created_at).seconds <= TIME_WINDOW:
                try:
                    await msg.delete()
                    print(f"✅ Đã xóa tin nhắn của {message.author.name}")
                except Exception as e:
                    print(f"❌ Lỗi khi xóa tin nhắn: {e}")

        await message.author.add_roles(mute_role)
        print(f"✅ Đã mute {message.author.name} trong {mute_time // 60} phút")

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="🚨 Phát hiện vi phạm",
                description=f"**Người vi phạm:** {message.author.mention}\n**Lý do:** {reason}\n**Thời gian mute:** {mute_time // 60} phút",
                color=discord.Color.red()
            )
            embed.add_field(name="Nội dung", value=f"||{message.content or '*Không có nội dung*'}||", inline=False)
            embed.add_field(name="Kênh", value=message.channel.mention, inline=True)
            embed.add_field(name="Lưu ý", value="Cân nhắc khi xem", inline=False)
            embed.timestamp = datetime.now(timezone.utc)
            await log_channel.send(embed=embed)
            print(f"✅ Đã gửi log vi phạm cho {message.author.name}")

        await asyncio.sleep(mute_time)
        await message.author.remove_roles(mute_role)
        print(f"✅ Đã bỏ mute {message.author.name}")

    except Exception as e:
        print(f"❌ Lỗi mute_and_log: {e}")

# -------------------------
# On Message (Filter + Anti-Spam)
# -------------------------
user_messages = {}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content_lower = message.content.lower()

    # Extract URLs and check bad words only in non-URL parts
    urls = re.findall(r'(https?://\S+)', message.content)
    non_url_content = re.sub(r'https?://\S+', '', content_lower)
    has_bad_word = any(bad_word in non_url_content for bad_word in BAD_WORDS)

    if has_bad_word:
        await mute_and_log(message, "dùng từ ngữ tục tĩu", MUTE_TIME_BADWORD)
        return

    if any(block in content_lower for block in BLOCK_LINKS):
        await mute_and_log(message, "gửi link bị cấm", MUTE_TIME_LINK)
        return

    now = datetime.now(timezone.utc)
    uid = message.author.id
    if uid not in user_messages:
        user_messages[uid] = []
    user_messages[uid].append(now)
    user_messages[uid] = [t for t in user_messages[uid] if now - t < timedelta(seconds=TIME_WINDOW)]

    if len(user_messages[uid]) > SPAM_LIMIT:
        await mute_and_log(message, "spam tin nhắn", MUTE_TIME_BADWORD)
        user_messages[uid] = []
        return

    # Kiểm tra thành viên mới gửi tin nhắn đáng ngờ
    member = message.author
    if member.joined_at and (now - member.joined_at) < timedelta(days=1):
        has_suspicious_word = any(word in content_lower for word in SUSPICIOUS_WORDS)
        if has_suspicious_word:
            try:
                await message.channel.send(
                    f"⚠️ **Cảnh báo**: Thành viên {member.mention} chưa đủ 1 ngày trong server để gửi các nội dung như trên. Cân nhắc khi gửi!",
                    ephemeral=True
                )
                print(f"✅ Đã gửi cảnh báo thành viên mới trong kênh {message.channel.name} cho {member.name}")
            except Exception as e:
                print(f"❌ Lỗi khi gửi cảnh báo thành viên mới: {e}")

    await bot.process_commands(message)

# -------------------------
# Caro Interaction Handler
# -------------------------
@bot.event
async def on_interaction(interaction: discord.Interaction):
    custom_id = interaction.data.get("custom_id")
    print(f"🔍 Interaction received: {custom_id}")

    # Xử lý menu chọn kích thước bảng
    if custom_id == "board_size":
        size = BOARD_SIZES.get(interaction.data.get("values")[0], 5)
        selected_board_size[interaction.user.id] = size
        print(f"🔍 User {interaction.user.name} selected board size: {size}x{size}")
        await interaction.response.defer(ephemeral=True)
        return

    # Xử lý Verify và Ticket
    if custom_id == "verify_button":
        await VerifyButton().verify_button(interaction, discord.ui.Button())
    elif custom_id == "create_ticket":
        await CreateTicketView().create_ticket(interaction, discord.ui.Button())
    elif custom_id == "close":
        await CloseTicketView().close(interaction, discord.ui.Button())

    # Xử lý Caro: Chơi với máy
    elif custom_id == "play_bot":
        size = selected_board_size.get(interaction.user.id, 5)
        print(f"🔍 Board size for play_bot: {size}x{size}")

        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        try:
            channel = await guild.create_text_channel(f"caro-{interaction.user.name}", overwrites=overwrites)
            print(f"✅ Created channel for play_bot: {channel.name}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi tạo kênh caro: {e}", ephemeral=True)
            print(f"❌ Error creating channel for play_bot: {e}")
            return

        game = CaroGame(interaction.user, is_bot=True, size=size)
        games[channel.id] = game
        game.create_board()

        embed = discord.Embed(title=f"Cờ Caro {size}x{size}", description=f"Lượt của {interaction.user.mention}\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.blue())
        view = discord.ui.View()
        component_count = 0
        for row in game.buttons:
            for button in row:
                if component_count < 23:
                    view.add_item(button)
                    component_count += 1
                else:
                    print(f"❌ Skipped adding button: Maximum components reached")

        control_view = discord.ui.View()
        close_button = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_caro_{channel.id}", disabled=True)
        replay_button = discord.ui.Button(label="Chơi lại", style=discord.ButtonStyle.primary, custom_id=f"replay_{channel.id}", disabled=True)
        control_view.add_item(replay_button)
        control_view.add_item(close_button)

        try:
            board_message = await channel.send(embed=embed, view=view)
            board_messages[channel.id] = board_message.id
            control_message = await channel.send(view=control_view)
            control_messages[channel.id] = control_message.id
            print(f"✅ Sent caro board (message_id: {board_message.id}) and controls (message_id: {control_message.id}) to channel: {channel.name}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi gửi bảng caro: {e}", ephemeral=True)
            print(f"❌ Error sending caro board: {e}")
            return

        await interaction.response.send_message(f"Ticket đã được tạo tại {channel.mention}", ephemeral=True)

        while channel.id in games:
            if asyncio.get_event_loop().time() - games[channel.id].last_move_time > 30:
                try:
                    await channel.send(f"{interaction.user.mention} không thao tác trong 30 giây. Trò chơi kết thúc!")
                    if channel.id in control_messages:
                        try:
                            control_message = await channel.fetch_message(control_messages[channel.id])
                            control_view = discord.ui.View()
                            close_button = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_caro_{channel.id}", disabled=False)
                            replay_button = discord.ui.Button(label="Chơi lại", style=discord.ButtonStyle.primary, custom_id=f"replay_{channel.id}", disabled=False)
                            control_view.add_item(replay_button)
                            control_view.add_item(close_button)
                            await control_message.edit(view=control_view)
                            print(f"✅ Enabled control buttons after timeout in channel: {channel.name}")
                        except Exception as e:
                            print(f"❌ Error enabling control buttons after timeout: {e}")
                    await channel.delete()
                    if channel.id in games:
                        del games[channel.id]
                    if channel.id in board_messages:
                        del board_messages[channel.id]
                    if channel.id in control_messages:
                        del control_messages[channel.id]
                except Exception as e:
                    print(f"❌ Lỗi khi xóa kênh caro: {e}")
                break
            await asyncio.sleep(5)

    # Xử lý Caro: Chơi với người
    elif custom_id == "play_human":
        await interaction.response.send_message("Vui lòng tag một người chơi khác (không phải bot hoặc chính bạn)!", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel and len(m.mentions) == 1
        try:
            msg = await bot.wait_for("message", check=check, timeout=30)
            opponent = msg.mentions[0]
            print(f"🔍 Opponent tagged: {opponent.name}")
            if opponent.bot:
                await interaction.followup.send("Không thể chơi với bot! Vui lòng tag một người chơi khác.", ephemeral=True)
                print("❌ Tagged a bot")
                return
            if opponent == interaction.user:
                await interaction.followup.send("Không thể chơi với chính mình! Vui lòng tag người khác.", ephemeral=True)
                print("❌ Tagged self")
                return

            size = selected_board_size.get(interaction.user.id, 5)
            print(f"🔍 Board size for play_human: {size}x{size}")

            guild = interaction.guild
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                opponent: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
            }
            try:
                channel = await guild.create_text_channel(f"caro-{interaction.user.name}-vs-{opponent.name}", overwrites=overwrites)
                print(f"✅ Created channel for play_human: {channel.name}")
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi khi tạo kênh caro: {e}", ephemeral=True)
                print(f"❌ Error creating channel for play_human: {e}")
                return

            game = CaroGame(interaction.user, opponent, size=size)
            games[channel.id] = game
            game.create_board()

            embed = discord.Embed(title=f"Cờ Caro {size}x{size}", description=f"Lượt của {interaction.user.mention}\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.blue())
            view = discord.ui.View()
            component_count = 0
            for row in game.buttons:
                for button in row:
                    if component_count < 23:
                        view.add_item(button)
                        component_count += 1
                    else:
                        print(f"❌ Skipped adding button: Maximum components reached")

            control_view = discord.ui.View()
            close_button = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_caro_{channel.id}", disabled=True)
            replay_button = discord.ui.Button(label="Chơi lại", style=discord.ButtonStyle.primary, custom_id=f"replay_{channel.id}", disabled=True)
            control_view.add_item(replay_button)
            control_view.add_item(close_button)

            try:
                board_message = await channel.send(embed=embed, view=view)
                board_messages[channel.id] = board_message.id
                control_message = await channel.send(view=control_view)
                control_messages[channel.id] = control_message.id
                print(f"✅ Sent caro board (message_id: {board_message.id}) and controls (message_id: {control_message.id}) to channel: {channel.name}")
            except Exception as e:
                await interaction.followup.send(f"❌ Lỗi khi gửi bảng caro: {e}", ephemeral=True)
                print(f"❌ Error sending caro board: {e}")
                return

            await interaction.followup.send(f"Ticket đã được tạo tại {channel.mention}", ephemeral=True)

            while channel.id in games:
                if asyncio.get_event_loop().time() - games[channel.id].last_move_time > 30:
                    try:
                        await channel.send(f"{games[channel.id].current_player.mention} không thao tác trong 30 giây. Trò chơi kết thúc!")
                        if channel.id in control_messages:
                            try:
                                control_message = await channel.fetch_message(control_messages[channel.id])
                                control_view = discord.ui.View()
                                close_button = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_caro_{channel.id}", disabled=False)
                                replay_button = discord.ui.Button(label="Chơi lại", style=discord.ButtonStyle.primary, custom_id=f"replay_{channel.id}", disabled=False)
                                control_view.add_item(replay_button)
                                control_view.add_item(close_button)
                                await control_message.edit(view=control_view)
                                print(f"✅ Enabled control buttons after timeout in channel: {channel.name}")
                            except Exception as e:
                                print(f"❌ Error enabling control buttons after timeout: {e}")
                        await channel.delete()
                        if channel.id in games:
                            del games[channel.id]
                        if channel.id in board_messages:
                            del board_messages[channel.id]
                        if channel.id in control_messages:
                            del control_messages[channel.id]
                    except Exception as e:
                        print(f"❌ Lỗi khi xóa kênh caro: {e}")
                    break
                await asyncio.sleep(5)

        except asyncio.TimeoutError:
            await interaction.followup.send("Hết thời gian chờ! Vui lòng thử lại.", ephemeral=True)
            print("❌ Timeout waiting for opponent tag")

    # Xử lý nhấn ô trên bảng caro
    elif custom_id.startswith("caro_"):
        channel_id = interaction.channel_id
        if channel_id not in games:
            await interaction.response.send_message("Trò chơi không tồn tại!", ephemeral=True)
            print("❌ Game not found")
            return

        game = games[channel_id]
        if interaction.user != game.current_player and not (game.is_bot and interaction.user == game.player1):
            await interaction.response.send_message("Không phải lượt của bạn!", ephemeral=True)
            print(f"❌ Not your turn: {interaction.user.name}")
            return

        game.last_move_time = asyncio.get_event_loop().time()

        try:
            _, row, col = custom_id.split("_")
            row, col = int(row), int(col)
        except Exception as e:
            await interaction.response.send_message("❌ Lỗi khi xử lý nước đi!", ephemeral=True)
            print(f"❌ Error parsing caro move: {e}")
            return

        game.board[row][col] = game.symbols[game.current_player]

        winner = game.check_winner(game.symbols[game.current_player])
        game.create_board()

        embed = discord.Embed(title=f"Cờ Caro {game.size}x{game.size}", description=f"Lượt của {game.current_player.mention}\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.blue())
        view = discord.ui.View()
        component_count = 0
        for row in game.buttons:
            for button in row:
                if component_count < 23:
                    view.add_item(button)
                    component_count += 1
                else:
                    print(f"❌ Skipped adding button: Maximum components reached")

        try:
            if winner == True:
                embed = discord.Embed(title=f"Cờ Caro {game.size}x{game.size}", description=f"{interaction.user.mention} thắng!\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.green())
                await interaction.response.edit_message(embed=embed, view=view)
                if channel_id in control_messages:
                    try:
                        control_message = await interaction.channel.fetch_message(control_messages[channel_id])
                        control_view = discord.ui.View()
                        close_button = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_caro_{channel_id}", disabled=False)
                        replay_button = discord.ui.Button(label="Chơi lại", style=discord.ButtonStyle.primary, custom_id=f"replay_{channel_id}", disabled=False)
                        control_view.add_item(replay_button)
                        control_view.add_item(close_button)
                        await control_message.edit(view=control_view)
                        print(f"✅ Enabled control buttons after win in channel: {interaction.channel.name}")
                    except Exception as e:
                        print(f"❌ Error enabling control buttons: {e}")
                print(f"✅ Game ended: {interaction.user.name} wins")
                return
            elif winner == "draw":
                embed = discord.Embed(title=f"Cờ Caro {game.size}x{game.size}", description="Hòa!\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.yellow())
                await interaction.response.edit_message(embed=embed, view=view)
                if channel_id in control_messages:
                    try:
                        control_message = await interaction.channel.fetch_message(control_messages[channel_id])
                        control_view = discord.ui.View()
                        close_button = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_caro_{channel_id}", disabled=False)
                        replay_button = discord.ui.Button(label="Chơi lại", style=discord.ButtonStyle.primary, custom_id=f"replay_{channel_id}", disabled=False)
                        control_view.add_item(replay_button)
                        control_view.add_item(close_button)
                        await control_message.edit(view=control_view)
                        print(f"✅ Enabled control buttons after draw in channel: {interaction.channel.name}")
                    except Exception as e:
                        print(f"❌ Error enabling control buttons: {e}")
                print("✅ Game ended: Draw")
                return

            if game.is_bot:
                game.current_player = game.player2
                bot_move = game.bot_move()
                if bot_move:
                    row, col = bot_move
                    game.board[row][col] = game.symbols[game.player2]
                    game.last_move_time = asyncio.get_event_loop().time()
                    winner = game.check_winner(game.symbols[game.player2])
                    game.create_board()

                    view = discord.ui.View()
                    component_count = 0
                    for row in game.buttons:
                        for button in row:
                            if component_count < 23:
                                view.add_item(button)
                                component_count += 1
                            else:
                                print(f"❌ Skipped adding button: Maximum components reached")

                    if winner == True:
                        embed = discord.Embed(title=f"Cờ Caro {game.size}x{game.size}", description="Bot thắng!\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.red())
                        await interaction.response.edit_message(embed=embed, view=view)
                        if channel_id in control_messages:
                            try:
                                control_message = await interaction.channel.fetch_message(control_messages[channel_id])
                                control_view = discord.ui.View()
                                close_button = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_caro_{channel_id}", disabled=False)
                                replay_button = discord.ui.Button(label="Chơi lại", style=discord.ButtonStyle.primary, custom_id=f"replay_{channel_id}", disabled=False)
                                control_view.add_item(replay_button)
                                control_view.add_item(close_button)
                                await control_message.edit(view=control_view)
                                print(f"✅ Enabled control buttons after bot win in channel: {interaction.channel.name}")
                            except Exception as e:
                                print(f"❌ Error enabling control buttons: {e}")
                        print("✅ Game ended: Bot wins")
                        return
                    elif winner == "draw":
                        embed = discord.Embed(title=f"Cờ Caro {game.size}x{game.size}", description="Hòa!\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.yellow())
                        await interaction.response.edit_message(embed=embed, view=view)
                        if channel_id in control_messages:
                            try:
                                control_message = await interaction.channel.fetch_message(control_messages[channel_id])
                                control_view = discord.ui.View()
                                close_button = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_caro_{channel_id}", disabled=False)
                                replay_button = discord.ui.Button(label="Chơi lại", style=discord.ButtonStyle.primary, custom_id=f"replay_{channel_id}", disabled=False)
                                control_view.add_item(replay_button)
                                control_view.add_item(close_button)
                                await control_message.edit(view=control_view)
                                print(f"✅ Enabled control buttons after draw in channel: {interaction.channel.name}")
                            except Exception as e:
                                print(f"❌ Error enabling control buttons: {e}")
                        print("✅ Game ended: Draw")
                        return

                    game.current_player = game.player1
                    embed = discord.Embed(title=f"Cờ Caro {game.size}x{game.size}", description=f"Lượt của {game.player1.mention}\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.blue())
                    await interaction.response.edit_message(embed=embed, view=view)
                    print(f"✅ Bot moved, now {game.player1.name}'s turn")
            else:
                game.current_player = game.player2 if game.current_player == game.player1 else game.player1
                embed = discord.Embed(title=f"Cờ Caro {game.size}x{game.size}", description=f"Lượt của {game.current_player.mention}\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.blue())
                await interaction.response.edit_message(embed=embed, view=view)
                print(f"✅ Now {game.current_player.name}'s turn")
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi cập nhật bảng caro: {e}", ephemeral=True)
            print(f"❌ Error updating caro board: {e}")

    # Xử lý nút Chơi lại
    elif custom_id.startswith("replay_"):
        channel_id = int(custom_id.split("_")[1])
        if channel_id not in games:
            await interaction.response.send_message("Trò chơi không tồn tại!", ephemeral=True)
            print("❌ Replay: Game not found")
            return

        game = games[channel_id]
        game.reset_board()
        embed = discord.Embed(title=f"Cờ Caro {game.size}x{game.size}", description=f"Lượt của {game.current_player.mention}\nTọa độ: A1 = (0,0), B2 = (1,1), ...", color=discord.Color.blue())
        view = discord.ui.View()
        component_count = 0
        for row in game.buttons:
            for button in row:
                if component_count < 23:
                    view.add_item(button)
                    component_count += 1
                else:
                    print(f"❌ Skipped adding button: Maximum components reached")

        try:
            if channel_id in board_messages:
                board_message = await interaction.channel.fetch_message(board_messages[channel_id])
                await board_message.edit(embed=embed, view=view)
                print(f"✅ Renewed board message (message_id: {board_messages[channel_id]}) in channel: {interaction.channel.name}")
            else:
                board_message = await interaction.channel.send(embed=embed, view=view)
                board_messages[channel_id] = board_message.id
                print(f"✅ Sent new board message (message_id: {board_message.id}) in channel: {interaction.channel.name}")

            if channel_id in control_messages:
                try:
                    control_message = await interaction.channel.fetch_message(control_messages[channel_id])
                    control_view = discord.ui.View()
                    close_button = discord.ui.Button(label="Đóng Ticket", style=discord.ButtonStyle.danger, custom_id=f"close_caro_{channel_id}", disabled=True)
                    replay_button = discord.ui.Button(label="Chơi lại", style=discord.ButtonStyle.primary, custom_id=f"replay_{channel_id}", disabled=True)
                    control_view.add_item(replay_button)
                    control_view.add_item(close_button)
                    await control_message.edit(view=control_view)
                    print(f"✅ Updated control message (message_id: {control_messages[channel_id]}) in channel: {interaction.channel.name}")
                except Exception as e:
                    control_message = await interaction.channel.send(view=control_view)
                    control_messages[channel_id] = control_message.id
                    print(f"✅ Sent new control message (message_id: {control_message.id}) in channel: {interaction.channel.name}")
            await interaction.response.defer()
            print(f"✅ Game replayed in channel: {interaction.channel.name}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Lỗi khi reset bảng caro: {e}", ephemeral=True)
            print(f"❌ Error replaying game: {e}")

    # Xử lý nút Đóng Ticket
    elif custom_id.startswith("close_caro_"):
        channel_id = int(custom_id.split("_")[2])
        if channel_id in games:
            del games[channel_id]
        if channel_id in board_messages:
            del board_messages[channel_id]
        if channel_id in control_messages:
            del control_messages[channel_id]
        try:
            await interaction.channel.delete()
            await interaction.response.send_message("Ticket đã được đóng!", ephemeral=True)
            print(f"✅ Closed channel: {interaction.channel.name}")
        except Exception as e:
            print(f"❌ Error closing channel: {e}")

# -------------------------
# Run Bot
# -------------------------
keep_alive()

if not DISCORD_TOKEN:
    print("❌ Chưa đặt DISCORD_TOKEN")
elif not GITHUB_TOKEN:
    print("❌ Chưa đặt GITHUB_TOKEN")
else:
    bot.run(DISCORD_TOKEN)
