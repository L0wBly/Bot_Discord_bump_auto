import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# === Chargement des variables d'environnement ===
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = 1374712467933888513
ROLE_ID = 1377230605309313085
DISBOARD_ID = 302050872383242240
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

    now = datetime.now(timezone.utc)
    messages = [msg async for msg in channel.history(limit=100)]

    bump_found = False

    for message in messages:
        age = now - message.created_at

        # Suppression des messages de plus de 12h et non épinglés
        if age > timedelta(hours=12) and not message.pinned:
            print(f"🕒 Message à supprimer: auteur={message.author} id={message.id} age={age}")
            try:
                await message.delete()
                print(f"🗑️ Supprimé : {message.author} - {message.content[:60]}")
            except discord.Forbidden:
                print("❌ Pas les permissions pour supprimer ce message.")
            except discord.HTTPException as e:
                print(f"⚠️ Erreur HTTP lors de la suppression : {e}")

        # Vérification bump Disboard récent
        if message.author.id == DISBOARD_ID and message.embeds:
            embed = message.embeds[0]
            description = embed.description or ""
            if "Bump effectué !" in description:
                if age < timedelta(hours=2):
                    print(f"✅ Bump récent détecté (âgé de {age}), pas de ping.")
                    return
                else:
                    print(f"🔔 Bump trop ancien (âgé de {age}), on ping.")
                    bump_found = True
                    break

    if not bump_found:
        print("❗ Aucun bump récent détecté, on ping.")

    # --- La suppression des anciens messages de ping est supprimée ici ---

    # Envoyer le nouveau ping
    try:
        await channel.send(f"{role.mention} {MESSAGE}")
        print("📢 Ping envoyé.")
    except Exception as e:
        print(f"⚠️ Erreur lors de l'envoi du ping : {e}")

bot.run(TOKEN)
