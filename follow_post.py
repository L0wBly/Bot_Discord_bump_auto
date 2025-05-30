import discord
from discord.ext import commands, tasks
import os, json
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import pytz

# === Config et constantes ===
load_dotenv()
TOKEN        = os.getenv('DISCORD_TOKEN')
CHANNEL_ID   = 1374712467933888513  # Salon de bump
ROLE_ID      = 1377230605309313085  # Rôle bump
DISBOARD_ID  = 302050872383242240   # Disboard bot ID
BIRTHDAY_CHANNEL_ID = 1377990979100999700  # Salon anniversaire
GESTION_ROLE_CHANNEL_ID = 1378015393653985281  # Salon gestion de rôle
MESSAGE      = "C'est l'heure de bumper !!"
BIRTHDAY_FILE = "birthdays.json"
ANNIV_ROLE_NAME = "Anniversaire"

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command("help")

paris_tz = pytz.timezone("Europe/Paris")

# ========== Config Rôles via réactions ==========
REACTION_ROLES = {
    "📺": 1374482077394931893,      # Regarde l'anime
    "📖": 1374713188876025888,      # Lecteur des scans
    "📚": 1374747604763676763,      # Lecteur du manga
    "🟠": 1374747839795564554,      # Hina Tachibana
    "🔵": 1374753663255580742,      # Rui Tachibana
    "🟣": 1374753918340431892,      # Momo Kashiwabara
    "🟢": 1374753922140475435,      # Miu Ashihara
    "⚫": 1374754187027550318,      # Natsuo Fujii
    "🟤": 1374754130626609152,      # Fumiya Kurimoto
    "📝": 1374752611667935402,      # Poète
    "✍️": 1374752308013039726,      # Écrivain
}
REACTION_ROLE_MESSAGE_ID = None

# ==== Affichage date "31-05" -> "31 mai" ====
def format_date_jour_mois(date_str):
    mois_fr = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"
    ]
    try:
        jour, mois = date_str.split("-")
        mois_int = int(mois)
        mois_nom = mois_fr[mois_int - 1]
        return f"{int(jour)} {mois_nom}"
    except:
        return date_str

# Chargement des anniversaires
try:
    with open(BIRTHDAY_FILE, "r", encoding="utf-8") as f:
        birthdays = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    birthdays = {}

def save_birthdays():
    with open(BIRTHDAY_FILE, "w", encoding="utf-8") as f:
        json.dump(birthdays, f, ensure_ascii=False, indent=2)

# === Commandes ANNIVERSAIRE stylées ===
@bot.command(name="anniv")
async def set_birthday(ctx, date: str = None):
    if not date:
        embed = discord.Embed(
            description="❓ Utilise la commande : `!anniv jj-mm` (exemple : `!anniv 14-06`)",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    if str(ctx.author.id) in birthdays:
        embed = discord.Embed(
            description="🚫 Tu as déjà enregistré ton anniversaire. Utilise `!modifanniv jj-mm` pour le modifier.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    try:
        datetime.strptime(date, "%d-%m")
    except ValueError:
        embed = discord.Embed(
            description="❌ Format incorrect. Merci d'utiliser : `!anniv jj-mm` (exemple : `!anniv 14-06`)",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    birthdays[str(ctx.author.id)] = date
    save_birthdays()
    embed = discord.Embed(
        description=f"🎂 Ton anniversaire a été enregistré pour le **{format_date_jour_mois(date)}** !",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"{ctx.author.display_name} 🎉")
    await ctx.send(embed=embed)

@bot.command(name="modifanniv")
async def modify_birthday(ctx, date: str = None):
    if not date:
        embed = discord.Embed(
            description="❓ Utilise la commande : `!modifanniv jj-mm` (exemple : `!modifanniv 14-06`)",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    if str(ctx.author.id) not in birthdays:
        embed = discord.Embed(
            description="🔒 Tu n'as pas encore enregistré ton anniversaire. Utilise d'abord `!anniv jj-mm`.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    try:
        datetime.strptime(date, "%d-%m")
    except ValueError:
        embed = discord.Embed(
            description="❌ Format incorrect. Merci d'utiliser : `!modifanniv jj-mm` (exemple : `!modifanniv 14-06`)",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    birthdays[str(ctx.author.id)] = date
    save_birthdays()
    embed = discord.Embed(
        description=f"🎉 Ton anniversaire a bien été modifié ! Nouvelle date : **{format_date_jour_mois(date)}**",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"{ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="suppranniv")
async def delete_birthday(ctx):
    if str(ctx.author.id) not in birthdays:
        embed = discord.Embed(
            description="🔒 Tu n'as pas encore enregistré ton anniversaire.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    del birthdays[str(ctx.author.id)]
    save_birthdays()
    embed = discord.Embed(
        description="🗑️ Ton anniversaire a bien été supprimé !",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name="annivs")
@commands.has_permissions(administrator=True)
async def list_birthdays(ctx):
    if not birthdays:
        embed = discord.Embed(
            title="Liste des anniversaires 🎂",
            description="Aucun anniversaire enregistré.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    sorted_bd = sorted(birthdays.items(), key=lambda x: datetime.strptime(x[1], "%d-%m"))
    embed = discord.Embed(
        title="🎉 Liste des anniversaires enregistrés",
        description="Voici tous les anniversaires du serveur, triés par date :",
        color=discord.Color.purple()
    )
    for uid, date_str in sorted_bd:
        member = ctx.guild.get_member(int(uid))
        name = member.display_name if member else f"ID {uid}"
        embed.add_field(
            name=f"📅 {format_date_jour_mois(date_str)}",
            value=f"👤 {name}",
            inline=False
        )
    await ctx.send(embed=embed)

# === Commande !help personnalisée ===
@bot.command(name="help")
async def help_command(ctx):
    embed = discord.Embed(
        title="📚 Commandes du bot",
        description="Voici la liste des commandes disponibles :",
        color=discord.Color.blurple()
    )
    embed.add_field(name="!anniv jj-mm", value="Enregistre ta date d'anniversaire (ex : !anniv 14-06)", inline=False)
    embed.add_field(name="!modifanniv jj-mm", value="Modifie ta date d'anniversaire", inline=False)
    embed.add_field(name="!suppranniv", value="Supprime ton anniversaire enregistré", inline=False)
    embed.add_field(name="!annivs", value="Affiche la liste de tous les anniversaires (admin)", inline=False)
    embed.add_field(name="!roles", value="Obtiens des rôles via réaction (dans 🛠·gestion-de-rôle)", inline=False)
    embed.add_field(name="Ping Bump auto", value="Le bot ping automatiquement pour bumper toutes les 2h si possible", inline=False)
    embed.add_field(name="Anniversaires 🎂", value=f"Le bot ping dans le salon d'anniversaire et attribue le rôle '{ANNIV_ROLE_NAME}' à ceux dont c'est l'anniversaire.", inline=False)
    await ctx.send(embed=embed)

# === Commande !roles pour envoi dans le bon salon ===
@bot.command(name="roles")
@commands.has_permissions(administrator=True)
async def send_reaction_roles(ctx):
    channel = bot.get_channel(GESTION_ROLE_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Salon de gestion des rôles introuvable.")
        return

    desc = "**Réagis avec l’émoji correspondant pour obtenir ou retirer un rôle :**\n\n"
    for emoji, role_id in REACTION_ROLES.items():
        role = ctx.guild.get_role(role_id)
        role_name = role.name if role else f"ID {role_id}"
        desc += f"> {emoji}  **→ {role_name}**\n\n"
    embed = discord.Embed(
        title="🌟 __Auto-attribution des rôles__",
        description=desc,
        color=discord.Color.brand_green()
    )
    embed.set_footer(text="Clique sur un émoji ci-dessous pour gérer tes rôles !")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/747/747376.png")  # icône sympa, change si tu veux
    msg = await channel.send(embed=embed)
    for emoji in REACTION_ROLES:
        await msg.add_reaction(emoji)
    # Enregistre l'ID du message pour gestion future
    with open("reaction_roles_msg.txt", "w") as f:
        f.write(str(msg.id))
    global REACTION_ROLE_MESSAGE_ID
    REACTION_ROLE_MESSAGE_ID = msg.id

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    if payload.channel_id != GESTION_ROLE_CHANNEL_ID:
        return
    global REACTION_ROLE_MESSAGE_ID
    if not REACTION_ROLE_MESSAGE_ID:
        try:
            with open("reaction_roles_msg.txt", "r") as f:
                REACTION_ROLE_MESSAGE_ID = int(f.read().strip())
        except:
            return
    if payload.message_id != REACTION_ROLE_MESSAGE_ID:
        return
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    emoji = str(payload.emoji)
    role_id = REACTION_ROLES.get(emoji)
    if role_id:
        role = guild.get_role(role_id)
        if role and member:
            await member.add_roles(role, reason="Ajout auto via réaction")
            print(f"✅ Rôle {role.name} ajouté à {member.display_name}")

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.channel_id != GESTION_ROLE_CHANNEL_ID:
        return
    global REACTION_ROLE_MESSAGE_ID
    if not REACTION_ROLE_MESSAGE_ID:
        try:
            with open("reaction_roles_msg.txt", "r") as f:
                REACTION_ROLE_MESSAGE_ID = int(f.read().strip())
        except:
            return
    if payload.message_id != REACTION_ROLE_MESSAGE_ID:
        return
    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    emoji = str(payload.emoji)
    role_id = REACTION_ROLES.get(emoji)
    if role_id:
        role = guild.get_role(role_id)
        if role and member:
            await member.remove_roles(role, reason="Retrait auto via réaction")
            print(f"❎ Rôle {role.name} retiré à {member.display_name}")

# === Gestion automatique des anniversaires & rôle ===
@tasks.loop(time=paris_tz.localize(datetime.combine(datetime.today(), datetime.strptime("10:00", "%H:%M").time())).timetz())
async def birthday_task():
    now = datetime.now(paris_tz)
    today_str = now.strftime("%d-%m")
    channel = bot.get_channel(BIRTHDAY_CHANNEL_ID)
    guild = channel.guild if channel else None

    if not channel or not guild:
        print("❌ Salon anniversaire ou serveur introuvable pour les anniversaires")
        return

    role_anniv = discord.utils.get(guild.roles, name=ANNIV_ROLE_NAME)
    if not role_anniv:
        print(f"❌ Rôle {ANNIV_ROLE_NAME} non trouvé. Crée le rôle exact « {ANNIV_ROLE_NAME} » dans ton serveur !")
        return

    users_today = [uid for uid, date in birthdays.items() if date == today_str]
    mentions = " ".join(f"<@{uid}>" for uid in users_today)
    if users_today:
        embed = discord.Embed(
            title="🎂 Bon anniversaire !",
            description=f"{mentions} Passe une super journée 🥳",
            color=discord.Color.gold()
        )
        embed.set_image(url="https://media.giphy.com/media/3o6Zt8zb1aA9n4cCZa/giphy.gif")
        await channel.send(embed=embed)
        print(f"🎉 Anniversaires fêtés aujourd'hui : {users_today}")

        for uid in users_today:
            member = guild.get_member(int(uid))
            if member and role_anniv not in member.roles:
                await member.add_roles(role_anniv, reason="C'est son anniversaire !")
                print(f"🎉 Rôle Anniversaire attribué à {member.display_name}")

    # Retirer le rôle Anniversaire à ceux qui ne sont pas nés aujourd'hui
    for member in guild.members:
        if role_anniv in member.roles and (str(member.id) not in users_today):
            await member.remove_roles(role_anniv, reason="Ce n'est plus son anniversaire")
            print(f"🎈 Rôle Anniversaire retiré à {member.display_name}")

# === Nettoyage automatique des anciens messages de ping bump et Disboard ===
async def cleanup_channel(channel):
    messages = [m async for m in channel.history(limit=100)]

    bot_msgs = [m for m in messages if m.author.id == bot.user.id and "C'est l'heure de bumper" in m.content]
    bot_msgs_sorted = sorted(bot_msgs, key=lambda m: m.created_at, reverse=False)
    bot_to_delete = bot_msgs_sorted[:-1]
    for m in bot_to_delete:
        try:
            await m.delete()
            print(f"🗑️ Message ping supprimé : {m.id}")
        except Exception as e:
            print(f"⚠️ Erreur suppression message ping : {e}")

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
    print(f"✅ Connecté en tant que {bot.user}")
    global REACTION_ROLE_MESSAGE_ID
    try:
        with open("reaction_roles_msg.txt", "r") as f:
            REACTION_ROLE_MESSAGE_ID = int(f.read().strip())
    except:
        REACTION_ROLE_MESSAGE_ID = None
    maintenance_task.start()
    birthday_task.start()

bot.run(TOKEN)
