import discord
from discord.ext import commands, tasks
import os, json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta, time as dt_time
import pytz

# === Config et constantes ===
load_dotenv()
TOKEN        = os.getenv('DISCORD_TOKEN')
CHANNEL_ID   = 1374712467933888513
ROLE_ID      = 1377230605309313085
DISBOARD_ID  = 302050872383242240
MESSAGE      = "C'est l'heure de bumper !!"
DATA_FILE    = "bumps.json"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Désactiver la commande help par défaut
bot.remove_command("help")

# Fuseau horaire Paris
paris_tz = pytz.timezone("Europe/Paris")

# === Chargement des compteurs avec gestion des erreurs JSON ===
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        bumps = json.load(f)
        if not isinstance(bumps, dict):
            bumps = {}
except (FileNotFoundError, json.JSONDecodeError):
    bumps = {}

def save_bumps():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(bumps, f, ensure_ascii=False, indent=2)

def print_pretty_time(dt: datetime):
    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    line     = "=" * (len(time_str) + 38)
    print(f"\n{line}\n   🕒  Heure actuelle à Paris : {time_str}\n{line}\n")

# === Commande d'aide personnalisée ===
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 Aide – Commandes disponibles",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="!bumps",
        value="Affiche ton nombre total de bumps.",
        inline=False
    )
    embed.add_field(
        name="!bumps [@membre]",
        value="Affiche le nombre total de bumps d’un membre.",
        inline=False
    )
    embed.add_field(
        name="!bumpslead",
        value="Affiche le top 5 des membres ayant le plus bumpé.",
        inline=False
    )
    embed.add_field(
        name="!help",
        value="Affiche ce message d’aide.",
        inline=False
    )
    await ctx.send(embed=embed)

# === Suivi des bumps via message "/bump" ===
@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    if message.content.lower().startswith("/bump"):
        user_id = str(message.author.id)
        bumps[user_id] = bumps.get(user_id, 0) + 1
        save_bumps()
        await message.channel.send(
            f"{message.author.mention} ton bump a été enregistré ! Total bumps : **{bumps[user_id]}**"
        )

    await bot.process_commands(message)

# === Commande pour afficher les bumps ===
@bot.command(name="bumps")
async def bumps_count(ctx, member: discord.Member = None):
    member = member or ctx.author
    count = bumps.get(str(member.id), 0)
    await ctx.send(f"{member.mention} a bumpé **{count}** fois.")

# === Commande pour afficher le top 5 des bumpers ===
@bot.command(name="bumpslead")
async def bumps_leaderboard(ctx):
    if not bumps:
        await ctx.send("Aucun bump enregistré pour le moment.")
        return

    # Trie les utilisateurs par nombre de bumps desc.
    top5 = sorted(bumps.items(), key=lambda kv: kv[1], reverse=True)[:5]
    embed = discord.Embed(
        title="🏆 Top 5 des bumpers",
        color=discord.Color.gold()
    )
    for rank, (user_id, count) in enumerate(top5, start=1):
        member = ctx.guild.get_member(int(user_id))
        name = member.display_name if member else f"<Utilisateur supprimé {user_id}>"
        embed.add_field(
            name=f"#{rank} : {name}",
            value=f"• {count} bump{'s' if count > 1 else ''}",
            inline=False
        )
    await ctx.send(embed=embed)

# === Boucle de vérification du bump et ping ===
@tasks.loop(minutes=5.025)
async def check_bump():
    now_local = datetime.now(paris_tz)
    print_pretty_time(now_local)

    if now_local.hour < 11:
        print("⏸️ Pause matinale : pas de ping avant 11 h.")
        return

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Salon introuvable"); return

    role = channel.guild.get_role(ROLE_ID)
    if not role:
        print("❌ Rôle introuvable"); return

    now_utc  = datetime.now(timezone.utc)
    messages = [msg async for msg in channel.history(limit=200)]

    # Throttle : pas de ping si le dernier a moins de 30 min
    for msg in messages:
        if msg.author == bot.user and MESSAGE in msg.content:
            if (now_utc - msg.created_at) < timedelta(minutes=30):
                print("⏳ Dernier ping <30 min, j'attends.")
                return
            break

    # Supprime anciens pings du bot
    for msg in messages:
        if msg.author == bot.user and MESSAGE in msg.content:
            try: await msg.delete()
            except: pass

    # Recherche bump Disboard
    bump_found = False
    for message in messages:
        if message.author.id == DISBOARD_ID and message.embeds:
            age   = now_utc - message.created_at
            embed = message.embeds[0]
            if embed.description and "Bump effectué !" in embed.description:
                if age < timedelta(hours=2):
                    local_time = message.created_at.astimezone(paris_tz).strftime('%H:%M:%S')
                    print(f"✅ Bump récent ({age}), pas de ping.")
                    print(f"🕒 Heure du bump : {local_time}")
                    return
                else:
                    print(f"🔔 Bump trop ancien ({age}), on ping.")
                    bump_found = True
                    break

    if not bump_found:
        print("❗ Aucun bump récent, ping.")
        try:
            await channel.send(f"{role.mention} {MESSAGE}")
        except Exception as e:
            print(f"⚠️ Erreur envoi ping : {e}")

# === Nettoyage quotidien des messages DISBOARD ===
@tasks.loop(time=dt_time(hour=0, minute=0, tzinfo=paris_tz))
async def daily_cleanup():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Salon introuvable pour nettoyage quotidien"); return

    msgs = [msg async for msg in channel.history(limit=200) if msg.author.id == DISBOARD_ID]
    to_delete = msgs[1:]  # conserve le plus récent
    deleted = 0

    for i in range(0, len(to_delete), 100):
        chunk = to_delete[i:i+100]
        try:
            res = await channel.delete_messages(chunk)
            deleted += len(res)
        except:
            for m in chunk:
                try: await m.delete(); deleted += 1
                except: pass

    print(f"🧹 Nettoyage quotidien : {deleted} anciens DISBOARD supprimés.")

# === Démarrage des tâches ===
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    check_bump.start()
    daily_cleanup.start()

bot.run(TOKEN)
