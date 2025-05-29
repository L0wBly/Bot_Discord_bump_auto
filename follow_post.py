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
THROTTLE_MIN = 30

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

paris_tz = pytz.timezone("Europe/Paris")

# Chargement des compteurs avec gestion des erreurs JSON
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
    ts = dt.strftime('%Y-%m-%d %H:%M:%S')
    line = "=" * (len(ts) + 20)
    print(f"\n{line}\n  🕒 Heure Paris : {ts}\n{line}\n")

# Commande d'aide personnalisée
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(title="📖 Commandes disponibles", color=discord.Color.blurple())
    embed.add_field(name="!bumps", value="Affiche ton total de bumps.", inline=False)
    embed.add_field(name="!bumps [@membre]", value="Total de bumps d’un membre.", inline=False)
    embed.add_field(name="!bumpslead", value="Top 5 des bumpers.", inline=False)
    embed.add_field(name="!help", value="Ce message d’aide.", inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    # Commandes classiques du bot
    await bot.process_commands(message)

    # Détection automatique : le bot DISBOARD vient de confirmer un bump
    if (message.author.id == DISBOARD_ID
        and message.embeds
        and message.embeds[0].description
        and "Bump effectué !" in message.embeds[0].description):

        # On cherche le dernier message d'interaction "/bump"
        async for m in message.channel.history(limit=10, oldest_first=False):
            # On détecte une interaction slash /bump faite par un utilisateur (pas bot)
            if hasattr(m, "interaction") and m.interaction is not None:
                if getattr(m.interaction, "name", None) == "bump" and not m.author.bot:
                    user_id = str(m.author.id)
                    bumps[user_id] = bumps.get(user_id, 0) + 1
                    save_bumps()
                    print(f"🔄 Bump détecté et enregistré pour {m.author.display_name} (ID: {user_id})")
                    # Optionnel: message dans le salon pour informer
                    try:
                        await message.channel.send(
                            f"{m.author.mention} bump enregistré automatiquement ! Total : **{bumps[user_id]}**"
                        )
                    except:
                        pass
                    break
        return

    # Facultatif: si un utilisateur tape vraiment "/bump" en texte (rarement)
    if not message.author.bot and message.content.lower().startswith("/bump"):
        user_id = str(message.author.id)
        bumps[user_id] = bumps.get(user_id, 0) + 1
        save_bumps()
        await message.channel.send(
            f"{message.author.mention} bump enregistré ! Total : **{bumps[user_id]}**"
        )

@bot.command(name="bumps")
async def bumps_count(ctx, member: discord.Member = None):
    member = member or ctx.author
    cnt = bumps.get(str(member.id), 0)
    await ctx.send(f"{member.mention} a bumpé **{cnt}** fois.")

@bot.command(name="bumpslead")
async def bumps_leaderboard(ctx):
    if not bumps:
        return await ctx.send("Aucun bump enregistré.")
    top5 = sorted(bumps.items(), key=lambda kv: kv[1], reverse=True)[:5]
    embed = discord.Embed(title="🏆 Top 5 des bumpers", color=discord.Color.gold())
    for i, (uid, cnt) in enumerate(top5, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"ID {uid}"
        embed.add_field(name=f"#{i} – {name}", value=f"{cnt} bump{'s' if cnt>1 else ''}", inline=False)
    await ctx.send(embed=embed)

@tasks.loop(minutes=5)
async def check_bump():
    now_local = datetime.now(paris_tz)
    print_pretty_time(now_local)

    if now_local.hour < 11:
        print("⏸️ Pause matinale : pas de ping avant 11 h.")
        return

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"❌ Salon ({CHANNEL_ID}) introuvable.")
        return

    role = channel.guild.get_role(ROLE_ID)
    if not role:
        print(f"❌ Rôle ({ROLE_ID}) introuvable.")
        return

    now_utc = datetime.now(timezone.utc)
    msgs = [m async for m in channel.history(limit=100)]
    last_bump = None
    for m in msgs:
        if m.author.id == DISBOARD_ID and m.embeds:
            desc = m.embeds[0].description or ""
            if "Bump effectué !" in desc:
                last_bump = m
                break

    if last_bump:
        age = now_utc - last_bump.created_at
        if age < timedelta(hours=2):
            to_wait = timedelta(hours=2) - age
            mins, secs = divmod(to_wait.seconds, 60)
            print(f"✅ Dernier bump il y a {age}. Prochain rappel dans {mins} m {secs} s.")
            return

    print(f"❗ Aucun bump récent (ou plus de 2h écoulées). Envoi d'un rappel ping !")
    try:
        await channel.send(f"{role.mention} {MESSAGE}")
        print(f"📢 Ping envoyé à {role.name} dans {channel.name}")
    except Exception as e:
        print(f"⚠️ Erreur envoi ping: {e}")

@tasks.loop(time=dt_time(hour=0, minute=0, tzinfo=paris_tz))
async def daily_cleanup():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"❌ Salon cleanup ({CHANNEL_ID}) introuvable.")
        return

    msgs = [m async for m in channel.history(limit=200) if m.author.id == DISBOARD_ID]
    to_delete = msgs[1:]
    deleted = 0
    for i in range(0, len(to_delete), 100):
        chunk = to_delete[i:i+100]
        try:
            res = await channel.delete_messages(chunk)
            deleted += len(res)
        except:
            for m in chunk:
                try:
                    await m.delete()
                    deleted += 1
                except:
                    pass

    print(f"🧹 Nettoyage quotidien : {deleted} anciens DISBOARD supprimés.")

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user} (ID: {bot.user.id})")
    print(f"🔍 Vérifie channel ID: {CHANNEL_ID}, rôle ID: {ROLE_ID}")
    check_bump.start()
    daily_cleanup.start()

bot.run(TOKEN)
