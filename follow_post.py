import discord
from discord.ext import commands, tasks
import os, json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import pytz

# === Config et constantes ===
load_dotenv()
TOKEN        = os.getenv('DISCORD_TOKEN')
CHANNEL_ID   = 1374712467933888513  # Remplace par l'ID du salon de bump
ROLE_ID      = 1377230605309313085  # Remplace par l'ID du rôle pingé
DISBOARD_ID  = 302050872383242240   # Disboard bot ID
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

# Pour chaque salon, on stocke l'ID du dernier utilisateur à avoir fait /bump
last_bumper = {}

@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📖 Commandes disponibles",
        description="Voici la liste des commandes pour le bump !",
        color=discord.Color.blurple()
    )
    embed.add_field(name="!bumps", value="Affiche ton nombre de bumps.", inline=False)
    embed.add_field(name="!bumps [@membre]", value="Affiche le nombre de bumps d’un membre.", inline=False)
    embed.add_field(name="!bumpslead", value="Affiche le classement des top bumpers.", inline=False)
    embed.add_field(name="!help", value="Affiche ce message d’aide.", inline=False)
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
            description="Personne n'a encore bumpé ! Sois le premier avec /bump",
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

    # On repère les messages Disboard par ID ET si le message contient "Bump effectué !" dans le contenu ou l'embed
    disboard_msgs = []
    for m in messages:
        is_disboard = (m.author.id == DISBOARD_ID)
        has_bump = False
        if m.embeds and m.embeds[0].description and "Bump effectué" in m.embeds[0].description:
            has_bump = True
        elif m.content and "Bump effectué" in m.content:
            has_bump = True
        # Parfois le titre uniquement
        elif m.embeds and m.embeds[0].title and "DISBOARD : La liste des serveurs publics" in m.embeds[0].title:
            has_bump = True
        if is_disboard and has_bump:
            disboard_msgs.append(m)
    # Trie du plus ancien au plus récent
    disboard_msgs_sorted = sorted(disboard_msgs, key=lambda m: m.created_at, reverse=False)
    disboard_to_delete = disboard_msgs_sorted[:-1]  # On garde le plus récent

    # Même logique pour ton bot
    bot_msgs = [m for m in messages if m.author.id == bot.user.id and MESSAGE in m.content]
    bot_msgs_sorted = sorted(bot_msgs, key=lambda m: m.created_at, reverse=False)
    bot_to_delete = bot_msgs_sorted[:-1]

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


# Rappel automatique de bump (ping le rôle à la bonne heure)
@tasks.loop(minutes=5)
async def check_bump():
    now_local = datetime.now(paris_tz)
    ts = now_local.strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n{'='*40}\n  🕒 Heure Paris : {ts}\n{'='*40}\n")

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await cleanup_channel(channel)   # <- Nettoyage toutes les 5 min

    if now_local.hour < 11:
        print("⏸️ Pause matinale : pas de ping avant 11 h.")
        return

    if not channel:
        print(f"❌ Salon ({CHANNEL_ID}) introuvable.")
        return

    role = channel.guild.get_role(ROLE_ID)
    if not role:
        print(f"❌ Rôle ({ROLE_ID}) introuvable.")
        return

    # Chercher dernier "Bump effectué !" pour éviter le spam
    now_utc = datetime.now(timezone.utc)
    msgs = [m async for m in channel.history(limit=100)]
    last_bump = None
    for m in msgs:
        if m.author.id == DISBOARD_ID and m.embeds:
            desc = m.embeds[0].description or ""
            if "Bump effectué !" in desc or "Bump réussi" in (m.embeds[0].title or ""):
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
        await channel.send(f"<@&{ROLE_ID}> {MESSAGE}\nN’oubliez pas de faire `/bump` dans ce salon !")
        print(f"📢 Ping envoyé à {role.name} dans {channel.name}")
    except Exception as e:
        print(f"⚠️ Erreur envoi ping: {e}")


@bot.event
async def on_message(message):
    # Debug (optionnel)
    print(f"Message reçu : {message.author} | {message.content}")

    # 1. Détection du /bump
    if (
        "# bump" in message.content
        and "a utilisé" in message.content
        and not message.author.bot
    ):
        last_bumper[message.channel.id] = message.author.id
        print(f"Prépare bump pour {message.author} dans salon {message.channel.id}")

    # 2. Détection du message Disboard "Bump effectué !"
    if (
        message.author.id == DISBOARD_ID
        and message.embeds
        and (
            (message.embeds[0].title and "DISBOARD" in message.embeds[0].title)
            or (message.embeds[0].description and "Bump effectué" in message.embeds[0].description)
        )
    ):
        bumper_id = last_bumper.get(message.channel.id)
        if bumper_id:
            bumps[str(bumper_id)] = bumps.get(str(bumper_id), 0) + 1
            save_bumps()
            print(f"Bump ajouté pour {bumper_id} dans salon {message.channel.id}")
            last_bumper[message.channel.id] = None
        else:
            print("Pas trouvé de bumper associé à ce bump Disboard.")

        await cleanup_channel(message.channel)

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user})")
    check_bump.start()

bot.run(TOKEN)
