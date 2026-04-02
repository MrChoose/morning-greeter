import json
import os
from typing import Dict, Set, Tuple, Optional
import discord
from discord.ext import commands
DATA_FILE = "greeting_state.json"
TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = 1220654082822377514  # 換成你的 Discord ID
PREFIX = "!"
def load_state() -> Dict[str, Dict[str, str]]:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
def save_state(state: Dict[str, Dict[str, str]]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
async def collect_new_speakers(
    channel: discord.TextChannel,
    after_id: Optional[int],
) -> Tuple[Set[int], Optional[int]]:
    users: Set[int] = set()
    newest_id: Optional[int] = None
    after_obj = discord.Object(id=after_id) if after_id else None
    async for msg in channel.history(after=after_obj, oldest_first=True, limit=None):
        newest_id = msg.id
        if msg.author.bot:
            continue
        users.add(msg.author.id)
    return users, newest_id
async def resolve_display_name(guild: discord.Guild, user_id: int) -> str:
    try:
        member = await guild.fetch_member(user_id)
        return member.display_name
    except discord.NotFound:
        user = await guild.fetch_user(user_id)
        return user.name
    except discord.HTTPException:
        return f"<@{user_id}>"
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)
@bot.command(name="早安")
async def morning(ctx: commands.Context):
    if ctx.author.bot:
        return
    if ctx.author.id != OWNER_ID:
        return
    if not isinstance(ctx.channel, discord.TextChannel):
        return
    state = load_state()
    channel_key = str(ctx.channel.id)
    channel_state = state.get(channel_key, {})
    last_id_str = channel_state.get("last_greeted_message_id")
    last_id = int(last_id_str) if last_id_str else None
    if last_id is None:
        channel_state["last_greeted_message_id"] = str(ctx.message.id)
        state[channel_key] = channel_state
        save_state(state)
        await ctx.author.send("已建立基準，之後會從此訊息後開始抓取新發言者。")
        return
    user_ids, newest_id = await collect_new_speakers(ctx.channel, last_id)
    if not user_ids:
        await ctx.author.send("這段期間沒有新發言者。")
        return
    lines = []
    for uid in user_ids:
        if uid == OWNER_ID:
            continue
        name = await resolve_display_name(ctx.guild, uid)
        lines.append(f"{name} 早安！:mrchoo4Hi:")
    message = ""
    for line in lines:
        if len(message) + len(line) + 1 > 2000:
            await ctx.author.send(message)
            message = ""
        message += line + "\n"
    if message:
        await ctx.author.send(message)
    if newest_id:
        channel_state["last_greeted_message_id"] = str(newest_id)
        state[channel_key] = channel_state
        save_state(state)
if not TOKEN:
    raise RuntimeError("Missing DISCORD_TOKEN environment variable")

bot.run(TOKEN)
