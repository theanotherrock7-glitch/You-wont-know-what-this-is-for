import os
import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from dotenv import load_dotenv
import asyncio
import random

# Load .env
load_dotenv()

# Get secrets
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini client
gemini = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# Bot setup
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --- Helper Functions ---
def parse_duration(duration_str: str) -> int:
    """Convert human-friendly duration to seconds (max 3 months)."""
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "M": 2592000}
    try:
        if duration_str[-1] in units:
            seconds = int(duration_str[:-1]) * units[duration_str[-1]]
            return min(seconds, 2592000 * 3)  # max 3 months
        else:
            return int(duration_str)  # fallback: raw seconds
    except:
        return None

# --- Bot Events ---
@bot.event
async def on_ready():
    await tree.sync()  # Sync slash commands globally
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    print(f"🌐 Connected to {len(bot.guilds)} guilds")

# --- Slash Commands ---
@tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! `{latency}ms`", ephemeral=True)

@tree.command(name="say", description="Make the bot repeat your message")
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message)

@tree.command(name="info", description="Show bot information")
async def info(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Mini Cat Bot",
        description="A Discord bot powered by Gemini AI",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="Servers", value=f"{len(bot.guilds)}", inline=True)
    embed.add_field(name="Users", value=f"{len(bot.users)}", inline=True)
    embed.set_footer(text="Made with discord.py + google-genai")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- AI Command ---
@tree.command(name="ask", description="Ask Gemini AI anything")
async def ask(interaction: discord.Interaction, prompt: str):
    if not gemini:
        await interaction.response.send_message(
            "❌ Gemini AI is not configured. Add GEMINI_API_KEY.", ephemeral=True
        )
        return
    await interaction.response.defer()
    try:
        response = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        text = response.text or "No response generated."
        await interaction.followup.send(text)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Error: {e}")

# --- AI Auto-Chat ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if bot.user.mentioned_in(message) and gemini:
        await message.channel.typing()
        try:
            prompt = f"You are Mini Cat, a helpful, fun Discord AI.\nUser: {message.content}"
            response = gemini.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            text = response.text or "Hmm... I don’t know what to say 😅"
            await message.reply(text)
        except Exception as e:
            await message.reply(f"😿 AI error: {e}")

    await bot.process_commands(message)

# --- Giveaway Command ---
@tree.command(name="giveaway", description="Start a giveaway 🎁")
@app_commands.describe(
    duration="Duration (1s - 3M, e.g., 30s, 5m, 1h, 2d, 1w, 3M)",
    prize="The prize for the giveaway",
    image="Optional: attach an image"
)
async def giveaway(interaction: discord.Interaction, duration: str, prize: str, image: discord.Attachment = None):
    seconds = parse_duration(duration)
    if not seconds:
        await interaction.response.send_message(
            "❌ Invalid duration! Use `30s`, `5m`, `1h`, `2d`, `1w`, `3M`.", ephemeral=True
        )
        return

    giveaway_image_url = image.url if image else "https://i.imgur.com/u8yZ5qk.png"

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\nReact with 🎉 to enter!\nEnds in `{duration}`.",
        color=discord.Color.gold()
    )
    embed.set_image(url=giveaway_image_url)
    embed.set_footer(text=f"Hosted by {interaction.user.name}")

    await interaction.response.send_message(embed=embed)
    sent = await interaction.original_response()
    await sent.add_reaction("🎉")

    await asyncio.sleep(seconds)

    msg = await interaction.channel.fetch_message(sent.id)
    users = [u async for u in msg.reactions[0].users() if not u.bot]

    if not users:
        await interaction.followup.send("😿 No one entered the giveaway.")
        return

    winner = random.choice(users)
    await interaction.followup.send(f"🎉 Congratulations {winner.mention}! You won **{prize}**!")

# --- Run Bot ---
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ Missing DISCORD_BOT_TOKEN environment variable.")
    else:
        bot.run(DISCORD_TOKEN)
