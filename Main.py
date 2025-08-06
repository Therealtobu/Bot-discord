import os import discord from discord.ext import commands from keep_alive import keep_alive import asyncio import random from datetime import datetime, timedelta

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") ROLE_ID = 1400724722714542111 VERIFY_CHANNEL_ID = 1400732340677771356 GUILD_ID = 1372215595218505891 TICKET_CHANNEL_ID = 1400750812912685056 SUPPORTERS = ["__tobu", "caycotbietmua"] LOG_CHANNEL_ID = 1402205862985994361

BAD_WORDS = ["đm", "địt", "lồn", "buồi", "cặc", "mẹ mày", "fuck", "bitch", "dm", "cc"] BLOCK_LINKS = ["youtube.com", "facebook.com"] SPAM_LIMIT = 5 TIME_WINDOW = 30 user_messages = {} user_offenses = {}

intents = discord.Intents.default() intents.members = True intents.presences = True intents.message_content = True bot = commands.Bot(command_prefix="/", intents=intents)

class VerifyButton(discord.ui.View): def init(self): super().init(timeout=None)

@discord.ui.button(label="✅ Verify / Xác Thực", style=discord.ButtonStyle.green)
async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
    role = interaction.guild.get_role(ROLE_ID)
    member = interaction.user
    if role in member.roles:
        await interaction.response.send_message("✅ Bạn đã được xác thực!", ephemeral=True)
    else:
        await member.add_roles(role)
        await interaction.response.send_message("🎉 Xác thực thành công!", ephemeral=True)

class CloseTicketView(discord.ui.View): def init(self): super().init(timeout=None)

@discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.red)
async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
    await interaction.response.send_message("🔒 Ticket sẽ bị đóng trong 3 giây...", ephemeral=True)
    await interaction.channel.delete()

class CreateTicketView(discord.ui.View): def init(self): super().init(timeout=None)

@discord.ui.button(label="📩 Tạo Ticket", style=discord.ButtonStyle.green)
async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
    guild = bot.get_guild(GUILD_ID)
    online_supporters = [m for m in guild.members if m.name in SUPPORTERS and m.status != discord.Status.offline]
    if not online_supporters:
        await interaction.response.send_message("❌ Hiện không có supporter online.", ephemeral=True)
        return
    supporter = random.choice(online_supporters)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        supporter: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
    embed = discord.Embed(title="🎛 Ticket Hỗ Trợ", description=f"{supporter.mention} sẽ hỗ trợ bạn sớm.", color=discord.Color.blue())
    await channel.send(content=interaction.user.mention, embed=embed, view=CloseTicketView())
    await interaction.response.send_message(f"✅ **{supporter.display_name}** sẽ hỗ trợ bạn!", ephemeral=True)

@bot.event async def on_ready(): print(f"✅ Bot đã đăng nhập: {bot.user}") verify_channel = bot.get_channel(VERIFY_CHANNEL_ID) if verify_channel: embed = discord.Embed(title="Xác Thực", description="Bấm để xác thực tham gia server!", color=discord.Color.green()) await verify_channel.send(embed=embed, view=VerifyButton()) ticket_channel = bot.get_channel(TICKET_CHANNEL_ID) if ticket_channel: embed = discord.Embed(title="📢 Hỗ Trợ", description="Bấm để tạo Ticket khi cần!", color=discord.Color.orange()) await ticket_channel.send(embed=embed, view=CreateTicketView())

async def handle_violation(message, reason): try: guild = message.guild user_id = message.author.id

# Xóa toàn bộ tin nhắn vi phạm trong TIME_WINDOW
    async for msg in message.channel.history(limit=100):
        if msg.author == message.author and (datetime.utcnow() - msg.created_at).total_seconds() <= TIME_WINDOW:
            try: await msg.delete()
            except: pass

    # Tính mốc mute
    user_offenses[user_id] = user_offenses.get(user_id, 0) + 1
    count = user_offenses[user_id]
    mute_times = {1: 60, 2: 300, 3: 1800, 4: 86400}  # giây
    duration = mute_times.get(count, 86400)

    # Têm vai trò Muted
    mute_role = discord.utils.get(guild.roles, name="Muted")
    if mute_role:
        await message.author.add_roles(mute_role, reason=reason)

    await message.channel.send(f"⛔ {message.author.mention} bị mute **{duration//60} phút** (Lần {count}) vì {reason}.")

    # Log
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(title="🚨 Vi phạm", color=discord.Color.red())
        embed.add_field(name="Người vi phạm", value=f"{message.author} ({message.author.mention})")
        embed.add_field(name="Lý do", value=reason)
        embed.add_field(name="Lần vi phạm", value=str(count))
        embed.add_field(name="Mute", value=f"{duration//60} phút")
        embed.timestamp = datetime.utcnow()
        await log_channel.send(embed=embed)

    await asyncio.sleep(duration)
    await message.author.remove_roles(mute_role, reason="Auto unmute")
    await message.channel.send(f"✅ {message.author.mention} đã được gỡ mute!")

except Exception as e:
    print(f"Lỗi xử lý vi phạm: {e}")

@bot.event async def on_message(message): if message.author.bot: return

content = message.content.lower()
# 1. Tục từ
if any(bad in content for bad in BAD_WORDS):
    await handle_violation(message, "ngôn từ tục tĩu ")
    return
# 2. Link bị cấm
if any(link in content for link in BLOCK_LINKS):
    await handle_violation(message, "gửi link cấm")
    return
# 3. Spam
now = datetime.now()
uid = message.author.id
user_messages.setdefault(uid, []).append(now)
user_messages[uid] = [t for t in user_messages[uid] if now - t < timedelta(seconds=TIME_WINDOW)]
if len(user_messages[uid]) > SPAM_LIMIT:
    await handle_violation(message, "spam tin nhắn")
    user_messages[uid] = []
    return

await bot.process_commands(message)

keep_alive() bot.run(DISCORD_TOKEN)
