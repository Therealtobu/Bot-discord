import os
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta, timezone
from keep_alive import keep_alive
import random
import json
import re

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

# Caro Config
CARO_CHANNEL_ID = 1402622963823546369
BOARD_SIZES = {"3x3": 3, "5x5": 5}
games = {}
board_messages = {}
control_messages = {}
selected_board_size = {}

# Link bị cấm
BLOCK_LINKS = ["youtube.com", "facebook.com"]

# Từ cấm
BAD_WORDS = ["đm", "địt", "lồn", "buồi", "cặc", "mẹ mày", "fuck", "bitch", "dm", "cc"]

# Slot Config
SLOT_CHANNEL_ID = 1405959238240702524   # Thay bằng ID kênh slot cố định
ADMIN_ROLE_ID = 1404851048052559872  # Thay bằng ID vai trò admin
symbols = ['🍒', '🍋', '🍉', '7', '⭐', '💎']
multipliers = [2, 3, 4, 5, 10, 20]

data = {}
try:
    with open('/data/data.json', 'r') as f:  # Dùng Render Disk
        loaded = json.load(f)
        data = {
            k: {
                'money': v['money'],
                'last_daily': datetime.fromisoformat(v['last_daily']) if v['last_daily'] else None,
                'spin_count': v.get('spin_count', 0),
                'ban_until': datetime.fromisoformat(v['ban_until']) if v['ban_until'] else None,
                'spin_timestamps': [datetime.fromisoformat(t) for t in v.get('spin_timestamps', [])]
            } for k, v in loaded.items()
        }
except FileNotFoundError:
    pass

def save_data():
    with open('/data/data.json', 'w') as f:  # Dùng Render Disk
        json.dump({
            k: {
                'money': v['money'],
                'last_daily': v['last_daily'].isoformat() if v['last_daily'] else None,
                'spin_count': v.get('spin_count', 0),
                'ban_until': v['ban_until'].isoformat() if v['ban_until'] else None,
                'spin_timestamps': [t.isoformat() for t in v.get('spin_timestamps', [])]
            } for k, v in data.items()
        }, f)

def get_weights(tier):
    # Tăng mạnh xác suất trúng khi tier cao
    w = [100 - 5 * tier, 90 - 4 * tier, 80 - 3 * tier, 70 - 2 * tier, 50 + 5 * tier, 30 + 15 * tier]
    w = [max(10, x) for x in w]
    return w

def spin(tier):
    weights = get_weights(tier)
    reels = random.choices(symbols, weights=weights, k=3)
    return reels

def get_payout(reels, bet):
    if reels[0] == reels[1] == reels[2]:
        # Trùng 3 biểu tượng: Nhân theo hệ số
        idx = symbols.index(reels[0])
        return bet * multipliers[idx]
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        # Trùng 2 biểu tượng: Nhận 1.5x tiền cược
        return int(bet * 1.5)
    else:
        # Không trùng: Nhận lại 50% tiền cược
        return int(bet * 0.5)

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
    print(f"Can write to directory: {os.access('/data', os.W_OK)}")

    try:
        # Verify Embed
        verify_channel = bot.get_channel(VERIFY_CHANNEL_ID)
        if verify_channel:
            async for msg in verify_channel.history(limit=50):
                if msg.author == bot.user:
                    try:
                        await msg.delete()
                    except:
                        pass
            embed = discord.Embed(
                title="Xác Thực Thành Viên",
                description="Bấm nút **Verify/Xác Thực** ở dưới để có thể tương tác trong nhóm\n⬇️⬇️⬇️",
                color=discord.Color.green()
            )
            await verify_channel.send(embed=embed, view=VerifyButton())
        else:
            print(f"❌ Không tìm thấy kênh verify: {VERIFY_CHANNEL_ID}")

        # Ticket Embed
        ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
        if ticket_channel:
            async for msg in ticket_channel.history(limit=50):
                if msg.author == bot.user:
                    try:
                        await msg.delete()
                    except:
                        pass
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
        else:
            print(f"❌ Không tìm thấy kênh ticket: {TICKET_CHANNEL_ID}")

        # Caro Embed
        caro_channel = bot.get_channel(CARO_CHANNEL_ID)
        if caro_channel:
            async for msg in caro_channel.history(limit=50):
                if msg.author == bot.user:
                    try:
                        await msg.delete()
                    except:
                        pass
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
                print(f"✅ Sent caro embed to channel: {caro_channel.name}")
            except Exception as e:
                print(f"❌ Lỗi khi gửi embed caro: {e}")
        else:
            print(f"❌ Không tìm thấy kênh caro: {CARO_CHANNEL_ID}")

        # Khởi động cập nhật số thành viên
        update_member_count.start()

    except Exception as e:
        print(f"❌ Lỗi trong on_ready: {e}")

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
        try:
            await channel.edit(name=f"📊 {total_members} thành viên | 🟢 {online_members} online")
            overwrite = discord.PermissionOverwrite(connect=False, view_channel=True, send_messages=False)
            await channel.set_permissions(guild.default_role, overwrite=overwrite)
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
        except Exception as e:
            print(f"❌ Lỗi khi gửi thông báo member leave: {e}")

# -------------------------
# Mute + Xóa tin nhắn + Log
# -------------------------
async def mute_and_log(message, reason="vi phạm"):
    try:
        mute_role = message.guild.get_role(MUTE_ROLE_ID)
        if not mute_role:
            print("❌ Không tìm thấy role mute!")
            return

        async for msg in message.channel.history(limit=50):
            if msg.author == message.author and (datetime.now(timezone.utc) - msg.created_at).seconds <= TIME_WINDOW:
                try:
                    await msg.delete()
                except:
                    pass

        await message.author.add_roles(mute_role)

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

        await asyncio.sleep(MUTE_TIME)
        await message.author.remove_roles(mute_role)

    except Exception as e:
        print(f"❌ Lỗi mute_and_log: {e}")

# -------------------------
# On Message (Filter + Anti-Spam + Slot Commands)
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
        await mute_and_log(message, "dùng từ ngữ tục tĩu")
        return

    if any(block in content_lower for block in BLOCK_LINKS):
        await mute_and_log(message, "gửi link bị cấm")
        return

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

    # Slot commands in specific channel without prefix
    if message.channel.id == SLOT_CHANNEL_ID:
        content = message.content.lower().strip().split()
        if not content:
            return

        cmd = content[0]
        user_id = str(message.author.id)

        if cmd == 'help':
            help_msg = "Hướng dẫn chơi:\n" \
                       "- spin <số tiền>: Quay slot (cược >=100). Cược cao hơn tăng tier (bet//1000, max 5), tăng mạnh xác suất trúng item xịn.\n" \
                       "- Không trùng: Nhận lại 50% tiền cược.\n" \
                       "- Trùng 2 biểu tượng: Nhận 1.5x tiền cược.\n" \
                       "- Trùng 3 biểu tượng: Nhận 2x-20x tiền cược tùy biểu tượng.\n" \
                       "- gift @user <số tiền>: Tặng tiền cho người khác.\n" \
                       "- daily: Nhận 5k tiền hàng ngày.\n" \
                       "- leaderboard: Xem bảng xếp hạng tiền.\n" \
                       "- add @user <số tiền>: Admin thêm tiền (có thể âm).\n" \
                       "- mod @user <số tiền>: Admin set tiền.\n" \
                       "Lưu ý: Quay 10 lần trong 1 phút sẽ bị 'cảnh sát bắt' (đùa thôi), mất hết tiền và ban chơi 1 ngày."
            await message.channel.send(help_msg)
            return

        if user_id not in data:
            data[user_id] = {'money': 10000, 'last_daily': None, 'spin_count': 0, 'ban_until': None, 'spin_timestamps': []}
            save_data()

        if cmd == 'spin':
            if len(content) < 2:
                await message.channel.send("Sử dụng: spin <số tiền cược>")
                return
            try:
                bet = int(content[1])
                if bet < 100:
                    await message.channel.send("Cược tối thiểu là 100")
                    return
            except ValueError:
                await message.channel.send("Số tiền cược không hợp lệ")
                return

            user_data = data[user_id]
            now = datetime.now(timezone.utc)
            if user_data['ban_until'] and user_data['ban_until'] > now:
                await message.channel.send("Bạn bị ban chơi trong 1 ngày do bị 'cảnh sát bắt' (đùa thôi)!")
                return

            money = user_data['money']
            if money < bet:
                await message.channel.send("Không đủ tiền")
                return

            # Cập nhật danh sách thời gian quay
            user_data['spin_timestamps'] = [t for t in user_data.get('spin_timestamps', []) if (now - t).total_seconds() <= 60]
            user_data['spin_timestamps'].append(now)
            user_data['money'] -= bet
            user_data['spin_count'] += 1
            save_data()

            tier = min(bet // 1000, 5)
            reels = spin(tier)

            # Hiệu ứng quay giống máy slot
            msg = await message.channel.send("🎰 Đang quay... |")
            spin_anim = ['|', '/', '-', '\\']
            for i in range(6):  # 6 frame để mượt hơn
                await asyncio.sleep(0.3)  # Thời gian mỗi frame
                temp_reels = [
                    reels[0] if i >= 2 else random.choice(symbols),
                    reels[1] if i >= 4 else random.choice(symbols),
                    reels[2] if i >= 6 else random.choice(symbols)
                ]
                anim_char = spin_anim[i % len(spin_anim)]
                await msg.edit(content=f"🎰 Đang quay... {anim_char} {' '.join(temp_reels)}")

            final_reels = ' '.join(reels)
            payout = get_payout(reels, bet)
            net = payout - bet

            user_data['money'] += payout
            save_data()

            if reels[0] == reels[1] == reels[2]:
                await msg.edit(content=f"🎰 {final_reels} Bạn thắng lớn {net}! (Tổng {payout}) Tiền: {user_data['money']}")
            elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
                await msg.edit(content=f"🎰 {final_reels} Trùng 2! Thắng {net}! (Tổng {payout}) Tiền: {user_data['money']}")
            else:
                await msg.edit(content=f"🎰 {final_reels} Không trùng! Nhận lại {payout}. Tiền: {user_data['money']}")

            # Check for 'police catch' after spin
            if len(user_data['spin_timestamps']) >= 10:
                await message.channel.send("🚔 Bạn bị 'cảnh sát bắt' (đùa thôi)! Mất hết tiền và không chơi được trong 1 ngày.")
                user_data['money'] = 0
                user_data['ban_until'] = now + timedelta(days=1)
                user_data['spin_timestamps'] = []
                user_data['spin_count'] = 0
                save_data()

        elif cmd == 'gift':
            if len(content) < 3 or not message.mentions:
                await message.channel.send("Sử dụng: gift @người_dùng <số_tiền>")
                return
            target = message.mentions[0]
            if target.bot or target.id == message.author.id:
                return
            try:
                amount = int(content[2])
                if amount <= 0:
                    return
            except ValueError:
                return

            user_data = data[user_id]
            if user_data['money'] < amount:
                await message.channel.send("Không đủ tiền")
                return

            target_id = str(target.id)
            if target_id not in data:
                data[target_id] = {'money': 0, 'last_daily': None, 'spin_count': 0, 'ban_until': None, 'spin_timestamps': []}

            user_data['money'] -= amount
            data[target_id]['money'] += amount
            save_data()

            await message.channel.send(f"Tặng {amount} cho {target.mention}")

        elif cmd == 'daily':
            user_data = data[user_id]
            last = user_data['last_daily']
            today = datetime.now(timezone.utc).date()
            if last is None or last.date() < today:
                user_data['money'] += 5000
                user_data['last_daily'] = datetime.now(timezone.utc)
                save_data()
                await message.channel.send(f"Nhận 5k hàng ngày! Tiền: {user_data['money']}")
            else:
                await message.channel.send("Đã nhận hôm nay rồi.")

        elif cmd == 'leaderboard':
            sorted_users = sorted(data.items(), key=lambda x: x[1]['money'], reverse=True)[:10]
            msg = "Bảng xếp hạng:\n"
            for i, (uid, d) in enumerate(sorted_users, 1):
                user = bot.get_user(int(uid))
                name = user.name if user else uid
                msg += f"{i}. {name}: {d['money']}\n"
            await message.channel.send(msg)

        elif cmd in ['add', 'mod']:
            is_admin = any(role.id == ADMIN_ROLE_ID for role in message.author.roles)
            if not is_admin:
                return
            if len(content) < 3 or not message.mentions:
                await message.channel.send(f"Sử dụng: {cmd} @người_dùng <số_tiền>")
                return
            target = message.mentions[0]
            if target.bot:
                return
            try:
                amount = int(content[2])
            except ValueError:
                return

            target_id = str(target.id)
            if target_id not in data:
                data[target_id] = {'money': 0, 'last_daily': None, 'spin_count': 0, 'ban_until': None, 'spin_timestamps': []}

            if cmd == 'add':
                data[target_id]['money'] += amount
            elif cmd == 'mod':
                data[target_id]['money'] = amount
            save_data()

            await message.channel.send(f"Đã {cmd} tiền cho {target.mention} thành {data[target_id]['money']}")

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
                        except:
                            print(f"❌ Error enabling control buttons after timeout")
                    await channel.delete()
                    if channel.id in games:
                        del games[channel.id]
                    if channel.id in board_messages:
                        del board_messages[channel.id]
                    if channel.id in control_messages:
                        del control_messages[channel.id]
                except:
                    pass
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
                            except:
                                print(f"❌ Error enabling control buttons after timeout")
                        await channel.delete()
                        if channel.id in games:
                            del games[channel.id]
                        if channel.id in board_messages:
                            del board_messages[channel.id]
                        if channel.id in control_messages:
                            del control_messages[channel.id]
                    except:
                        pass
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
        except:
            await interaction.response.send_message("❌ Lỗi khi xử lý nước đi!", ephemeral=True)
            print("❌ Error parsing caro move")
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
                    except:
                        print(f"❌ Error enabling control buttons")
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
                    except:
                        print(f"❌ Error enabling control buttons")
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
                            except:
                                print(f"❌ Error enabling control buttons")
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
                            except:
                                print(f"❌ Error enabling control buttons")
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
                except:
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
        except:
            print("❌ Error closing channel")

# -------------------------
# Run Bot
# -------------------------
keep_alive()

if not DISCORD_TOKEN:
    print("❌ Chưa đặt DISCORD_TOKEN")
else:
    bot.run(DISCORD_TOKEN)
