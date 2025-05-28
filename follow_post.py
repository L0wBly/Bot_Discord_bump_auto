import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = 1374712467933888513
ROLE_ID = 1377230605309313085
DISBOARD_ID = 302050872383242240  # ID du bot DISBOARD
MESSAGE = "C'est l'heure de bumper !!"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    check_bump.start()

@tasks.loop(minutes=5)
async def check_bump():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("❌ Salon introuvable")
        return

    role = channel.guild.get_role(ROLE_ID)
    if role is None:
        print("❌ Rôle introuvable")
        return

    messages = [msg async for msg in channel.history(limit=50)]
    bump_found = False

    for message in messages:
        if message.author.id == DISBOARD_ID:
            # Vérifie si l'embed contient le texte "Bump effectué !"
            if message.embeds:
                embed = message.embeds[0]
                description = embed.description or ""
                if "Bump effectué !" in description:
                    now = datetime.now(timezone.utc)
                    time_diff = now - message.created_at

                    if time_diff < timedelta(hours=2):
                        print(f"✅ Bump récent détecté ({time_diff}), pas de ping.")
                        return
                    else:
                        print(f"🔔 Bump trouvé mais trop ancien ({time_diff}), on ping.")
                        bump_found = True
                        break

    if not bump_found:
        print("❗ Aucun bump récent détecté. On ping.")

    # Supprimer les anciens messages de ping
    for msg in messages:
        if msg.author == bot.user and f"{role.mention} {MESSAGE}" in msg.content:
            try:
                await msg.delete()
                print("🧹 Ancien ping supprimé.")
            except Exception as e:
                print(f"⚠️ Erreur de suppression : {e}")

    # Envoyer le nouveau message
    await channel.send(f"{role.mention} {MESSAGE}")
    print("📢 Ping envoyé.")

bot.run(TOKEN)
