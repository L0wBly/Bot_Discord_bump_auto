import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import pytz

# === Config et constantes ===
load_dotenv()
TOKEN        = os.getenv('DISCORD_TOKEN')
CHANNEL_ID   = 1374712467933888513  # ID du salon de bump
ROLE_ID      = 1377230605309313085  # ID du rôle à ping
DISBOARD_ID  = 302050872383242240   # Disboard bot ID
MESSAGE      = "C'est l'heure de bumper !!"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

paris_tz = pytz.timezone("Europe/Paris")

# Nettoyage automatique des anciens messages
async def cleanup_channel(channel):
    messages = [m async for m in channel.history(limit=100)]

    # 1. SUPPRESSION DES PINGS BOT (on garde le plus récent)
    bot_msgs = [m for m in messages if m.author.id == bot.user.id and "C'est l'heure de bumper" in m.content]
    bot_msgs_sorted = sorted(bot_msgs, key=lambda m: m.created_at, reverse=False)
    bot_to_delete = bot_msgs_sorted[:-1]
    for m in bot_to_delete:
        try:
            await m.delete()
            print(f"🗑️ Message ping supprimé : {m.id}")
        except Exception as e:
            print(f"⚠️ Erreur suppression message ping : {e}")

    # 2. SUPPRESSION DES ANCIENS DISBOARD (on garde le plus récent)
    disboard_msgs = []
    for m in messages:
        is_disboard = (m.author.id == DISBOARD_ID)
        has_bump = False
        if m.embeds and m.embeds[0].description and "Bump effectué" in m.embeds[0].description:
            has_bump = True
        elif m.content and "Bump effectué" in m.content:
            has_bump = True
        elif m.embeds and m.embeds[0].title and "DISBOARD : La liste des serveurs publics" in m.embeds[0].title:
            has_bump = True
        if is_disboard and has_bump:
            disboard_msgs.append(m)
    disboard_msgs_sorted = sorted(disboard_msgs, key=lambda m: m.created_at, reverse=False)
    disboard_to_delete = disboard_msgs_sorted[:-1]
    for m in disboard_to_delete:
        try:
            await m.delete()
            print(f"🗑️ Message disboard supprimé : {m.id}")
        except Exception as e:
            print(f"⚠️ Erreur suppression message disboard : {e}")

# Pour garder l'heure du dernier ping bump
last_ping_time = None

@tasks.loop(minutes=5)
async def maintenance_task():
    global last_ping_time

    now_local = datetime.now(paris_tz)
    now_utc = datetime.now(timezone.utc)
    ts = now_local.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*40}\n  🕒 Heure Paris : {ts}\n{'='*40}\n")

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"❌ Salon ({CHANNEL_ID}) introuvable.")
        return

    # Nettoyage
    await cleanup_channel(channel)

    if now_local.hour < 11:
        print("⏸️ Pause matinale : pas de ping avant 11 h.")
        return

    # Check dernier bump Disboard
    msgs = [m async for m in channel.history(limit=100)]
    last_disboard_bump = None
    for m in msgs:
        if m.author.id == DISBOARD_ID and m.embeds:
            desc = m.embeds[0].description or ""
            if "Bump effectué !" in desc or "Bump réussi" in (m.embeds[0].title or ""):
                last_disboard_bump = m
                break

    bump_ok = False
    if last_disboard_bump:
        age = now_utc - last_disboard_bump.created_at
        if age >= timedelta(hours=2):
            bump_ok = True
        else:
            mins, secs = divmod((timedelta(hours=2) - age).seconds, 60)
            print(f"✅ Dernier bump il y a {age}. Prochain ping dans {mins} min {secs} sec si besoin.")
    else:
        bump_ok = True

    if bump_ok:
        if not last_ping_time or (now_utc - last_ping_time) >= timedelta(minutes=30):
            try:
                role = channel.guild.get_role(ROLE_ID)
                await channel.send(f"<@&{ROLE_ID}> {MESSAGE}\nN’oubliez pas de faire `/bump` dans ce salon !")
                last_ping_time = now_utc
                print(f"📢 Ping envoyé à {role.name} dans {channel.name} | {now_local.strftime('%H:%M')}")
            except Exception as e:
                print(f"⚠️ Erreur envoi ping: {e}")
        else:
            to_wait = timedelta(minutes=30) - (now_utc - last_ping_time)
            mins, secs = divmod(to_wait.seconds, 60)
            print(f"⌛ Ping déjà envoyé il y a moins de 30min. Prochain possible dans {mins} min {secs} sec.")
    else:
        print("⏳ Le bump n'est pas encore possible, on attend 2h depuis le dernier bump Disboard.")

@bot.event
async def on_message(message):
    # Nettoyage instantané si Disboard répond (optionnel mais ça "force" le nettoyage)
    if (
        message.author.id == DISBOARD_ID
        and message.embeds
        and (
            (message.embeds[0].title and "DISBOARD" in message.embeds[0].title)
            or (message.embeds[0].description and "Bump effectué" in message.embeds[0].description)
        )
    ):
        await cleanup_channel(message.channel)
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user})")
    maintenance_task.start()  # Une seule tâche toutes les 5 min

bot.run(TOKEN)
