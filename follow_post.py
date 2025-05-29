import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta, time as dt_time
import pytz

# === Chargement des variables d'environnement ===
load_dotenv()
TOKEN        = os.getenv('DISCORD_TOKEN')
CHANNEL_ID   = 1374712467933888513
ROLE_ID      = 1377230605309313085
DISBOARD_ID  = 302050872383242240
MESSAGE      = "C'est l'heure de bumper !!"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Fuseau horaire Paris (gère heure d'été/hiver)
paris_tz = pytz.timezone("Europe/Paris")

def print_pretty_time(dt: datetime):
    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    line     = "=" * (len(time_str) + 20)
    print(f"\n{line}")
    print(f"     🕒 Heure actuelle à Paris : {time_str}     ")
    print(f"{line}\n")

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    check_bump.start()
    daily_cleanup.start()

@tasks.loop(minutes=5)
async def check_bump():
    # 1) Heure actuelle
    now_local = datetime.now(paris_tz)
    print_pretty_time(now_local)

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Salon introuvable")
        return

    role = channel.guild.get_role(ROLE_ID)
    if not role:
        print("❌ Rôle introuvable")
        return

    now_utc  = datetime.now(timezone.utc)
    messages = [msg async for msg in channel.history(limit=100)]

    # 2) Supprimer tous les anciens pings de ce bot
    for msg in messages:
        if msg.author == bot.user and MESSAGE in msg.content:
            try:
                await msg.delete()
                print(f"🧹 Ancien ping supprimé : {msg.content[:50]}")
            except Exception as e:
                print(f"⚠️ Erreur suppression ancien ping : {e}")

    # 3) Recherche du bump Disboard
    bump_found = False
    for message in messages:
        if message.author.id == DISBOARD_ID and message.embeds:
            age   = now_utc - message.created_at
            embed = message.embeds[0]
            if embed.description and "Bump effectué !" in embed.description:
                if age < timedelta(hours=2):
                    local_time_msg = message.created_at.astimezone(paris_tz).strftime('%H:%M:%S')
                    print(f"✅ Bump récent ({age}), pas de ping. Heure du bump: {local_time_msg}")
                    return
                else:
                    print(f"🔔 Bump trop ancien ({age}), on ping.")
                    bump_found = True
                    break

    if not bump_found:
        print("❗ Aucun bump récent détecté, on ping.")

    # 4) Envoi du nouveau ping
    try:
        await channel.send(f"{role.mention} {MESSAGE}")
        print("📢 Ping envoyé.")
    except Exception as e:
        print(f"⚠️ Erreur envoi ping : {e}")

@tasks.loop(time=dt_time(hour=0, minute=0, tzinfo=paris_tz))
async def daily_cleanup():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Salon introuvable pour nettoyage quotidien")
        return

    # Supprime jusqu'à 100 anciens messages DISBOARD
    def is_disboard(m: discord.Message):
        return m.author.id == DISBOARD_ID

    deleted = await channel.purge(limit=100, check=is_disboard)
    print(f"🧹 Nettoyage quotidien à minuit : {len(deleted)} messages DISBOARD supprimés.")

bot.run(TOKEN)
