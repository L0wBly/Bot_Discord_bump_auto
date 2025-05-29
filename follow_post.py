import discord
from discord.ext import commands, tasks
import os, json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import pytz

# === Config et constantes ===
load_dotenv()
TOKEN        = os.getenv('DISCORD_TOKEN')
CHANNEL_ID   = 1374712467933888513  # ID du salon dédié au bump
ROLE_ID      = 1377230605309313085
DISBOARD_ID  = 302050872383242240
MESSAGE      = "C'est l'heure de bumper !!"
DATA_FILE    = "bumps.json"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

paris_tz = pytz.timezone("Europe/Paris")

# === Chargement compteur bumps ===
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        bumps = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    bumps = {}

def save_bumps():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(bumps, f, ensure_ascii=False, indent=2)

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 Commandes disponibles",
        description="Voici la liste des commandes pour le bump !",
        color=discord.Color.blurple()
    )
    embed.add_field(name="!bump", value="Fait un bump (compteur + vrai bump Disboard, seulement si c'est possible).", inline=False)
    embed.add_field(name="!bumps", value="Affiche ton nombre de bumps.", inline=False)
    embed.add_field(name="!bumps [@membre]", value="Affiche le nombre de bumps d’un membre.", inline=False)
    embed.add_field(name="!bumpslead", value="Affiche le classement des top bumpers.", inline=False)
    embed.add_field(name="!help", value="Affiche ce message d’aide.", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="bump")
async def custom_bump(ctx):
    bump_channel = bot.get_channel(CHANNEL_ID)
    if not bump_channel:
        embed = discord.Embed(
            title=":warning: Problème détecté",
            description="Le salon de bump n'est pas trouvé. Merci de vérifier la configuration du bot.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Contacte un admin pour corriger !")
        await ctx.send(embed=embed)
        return

    # Chercher le dernier "Bump effectué !" dans le channel dédié
    now_utc = datetime.now(timezone.utc)
    msgs = [m async for m in bump_channel.history(limit=50)]
    last_bump = None
    for m in msgs:
        if m.author.id == DISBOARD_ID and m.embeds:
            desc = m.embeds[0].description or ""
            if "Bump effectué !" in desc:
                last_bump = m
                break

    bump_possible = True
    if last_bump:
        age = now_utc - last_bump.created_at
        if age < timedelta(hours=2):
            bump_possible = False

    if bump_possible:
        user_id = str(ctx.author.id)
        bumps[user_id] = bumps.get(user_id, 0) + 1
        save_bumps()
        await bump_channel.send("/bump")
        embed = discord.Embed(
            title=":rocket: Bump réussi !",
            description=(
                f"Bravo {ctx.author.mention} !\n"
                f"Tu viens de bumper le serveur dans {bump_channel.mention}.\n\n"
                f"✨ Tu as désormais **{bumps[user_id]}** bump{'s' if bumps[user_id] > 1 else ''} !"
            ),
            color=discord.Color.from_rgb(24, 190, 76),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else discord.Embed.Empty)
        embed.set_footer(text="Merci de faire vivre le serveur ❤️ | Bump par "+ctx.author.display_name)
        await ctx.send(embed=embed)
    else:
        time_left = timedelta(hours=2) - (now_utc - last_bump.created_at)
        mins, secs = divmod(time_left.seconds, 60)
        hours, mins = divmod(mins, 60)
        embed = discord.Embed(
            title=":hourglass_flowing_sand: Trop tôt pour bumper !",
            description=(
                f"Le dernier bump Disboard a été fait récemment dans {bump_channel.mention}.\n"
                f"⏰ Il faut attendre **{hours}h {mins}min {secs}sec** avant de pouvoir bumper à nouveau !\n\n"
                f"Essaye encore un peu plus tard 😉"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="Cooldown anti-spam — Merci de ta patience !")
        await ctx.send(embed=embed)

@bot.command(name="bumps")
async def bumps_count(ctx, member: discord.Member = None):
    member = member or ctx.author
    cnt = bumps.get(str(member.id), 0)
    colors = [discord.Color.blurple(), discord.Color.blue(), discord.Color.teal(), discord.Color.green()]
    color = colors[hash(member.id) % len(colors)]  # Un effet de couleur par user
    embed = discord.Embed(
        title=f"🌟 Bumps de {member.display_name}",
        color=color,
        description=(
            f"{member.mention} a bumpé le serveur **{cnt}** fois !\n"
            f"{'✨ Bravo !' if cnt > 0 else '⏳ Il est temps de bumper !'}"
        ),
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else discord.Embed.Empty)
    embed.set_footer(text="Top Bumper du serveur 💎" if cnt > 0 else "Viens bumper pour apparaitre ici !")
    await ctx.send(embed=embed)

@bot.command(name="bumpslead")
async def bumps_leaderboard(ctx):
    if not bumps:
        embed = discord.Embed(
            title="Aucun bump enregistré 💤",
            description="Personne n'a encore bumpé ! Sois le premier avec !bump",
            color=discord.Color.greyple()
        )
        await ctx.send(embed=embed)
        return
    top5 = sorted(bumps.items(), key=lambda kv: kv[1], reverse=True)[:5]
    embed = discord.Embed(
        title="🏆 Top 5 des bumpers",
        color=discord.Color.gold(),
        description="**Classement des meilleurs bumpers du serveur !**\n\n"
    )
    medals = [":first_place:", ":second_place:", ":third_place:", ":medal:", ":medal:"]
    lines = []
    for i, (uid, cnt) in enumerate(top5, 1):
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"ID {uid}"
        avatar = member.avatar.url if member else None
        medal = medals[i-1] if i <= len(medals) else f"#{i}"
        lines.append(f"{medal} **{name}** — `{cnt}` bump{'s' if cnt > 1 else ''}")
        if i == 1 and avatar:
            embed.set_thumbnail(url=avatar)
    embed.description += "\n".join(lines)
    embed.set_footer(text="Qui sera le prochain numéro 1 ? 🚀")
    embed.timestamp = datetime.now()
    await ctx.send(embed=embed)

# Nettoyage automatique des anciens messages
async def cleanup_channel(channel):
    messages = [m async for m in channel.history(limit=500)]
    # Messages DISBOARD (hors le plus récent)
    disboard_msgs = [m for m in messages if m.author.id == DISBOARD_ID]
    disboard_to_delete = disboard_msgs[1:]  # on garde le plus récent

    # Messages du bot (hors le plus récent)
    bot_msgs = [m for m in messages if m.author.id == bot.user.id and MESSAGE in m.content]
    bot_to_delete = bot_msgs[1:]  # on garde le plus récent

    to_delete = disboard_to_delete + bot_to_delete

    now = datetime.now(timezone.utc)
    bulk_delete = []
    single_delete = []
    for m in to_delete:
        age = (now - m.created_at).days
        if age < 14:
            bulk_delete.append(m)
        else:
            single_delete.append(m)

    deleted = 0
    for i in range(0, len(bulk_delete), 100):
        chunk = bulk_delete[i:i+100]
        try:
            await channel.delete_messages(chunk)
            deleted += len(chunk)
            print(f"🗑️ Bulk delete : {len(chunk)} messages supprimés")
        except Exception as e:
            print(f"⚠️ Erreur bulk delete : {e}")

    for m in single_delete:
        try:
            await m.delete()
            deleted += 1
            print(f"🗑️ Message {m.id} supprimé individuellement")
        except Exception as e:
            print(f"⚠️ Erreur suppression message {m.id} : {e}")

    print(f"🧹 Nettoyage : {deleted} anciens messages supprimés.")

@tasks.loop(minutes=5)
async def check_bump():
    now_local = datetime.now(paris_tz)
    ts = now_local.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*40}\n  🕒 Heure Paris : {ts}\n{'='*40}\n")

    if now_local.hour < 11:
        print("⏸️ Pause matinale : pas de ping avant 11 h.")
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await cleanup_channel(channel)
        return

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"❌ Salon ({CHANNEL_ID}) introuvable.")
        return

    role = channel.guild.get_role(ROLE_ID)
    if not role:
        print(f"❌ Rôle ({ROLE_ID}) introuvable.")
        await cleanup_channel(channel)
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
            await cleanup_channel(channel)
            return

    print(f"❗ Aucun bump récent (ou plus de 2h écoulées). Envoi d'un rappel ping !")
    try:
        await channel.send(f"{role.mention} {MESSAGE}")
        print(f"📢 Ping envoyé à {role.name} dans {channel.name}")
    except Exception as e:
        print(f"⚠️ Erreur envoi ping: {e}")

    # Nettoyage automatique après chaque passage de la boucle
    await cleanup_channel(channel)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user})")
    check_bump.start()

bot.run(TOKEN)
