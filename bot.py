import asyncio
from datetime import datetime
import os

import discord
import requests
from discord.ext import commands, tasks
from dotenv import load_dotenv

import alertes
import gratuits
import steam

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SALON = "bot-09"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.check
async def uniquement_dans_le_salon(ctx):
    return getattr(ctx.channel, "name", None) == SALON


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    if not verifier_alertes.is_running():
        verifier_alertes.start()


@bot.event
async def on_command_error(ctx, erreur):
    if isinstance(erreur, commands.MissingRequiredArgument):
        exemple = ctx.command.usage or "hades"
        await ctx.send(f"Il manque une information. Exemple : `!{ctx.command} {exemple}`")
    elif isinstance(erreur, commands.BadArgument):
        await ctx.send(f"Je n'ai pas compris. Exemple : `!{ctx.command} {ctx.command.usage}`")
    elif isinstance(erreur, (commands.CommandNotFound, commands.CheckFailure)):
        return
    else:
        print(f"Erreur dans !{ctx.command} : {erreur!r}")
        await ctx.send("Une erreur est survenue, désolé.")


@bot.command()
async def ping(ctx):
    await ctx.send("pong")


@bot.command()
async def promo(ctx, *, nom):
    try:
        async with ctx.typing():
            jeu = await asyncio.to_thread(steam.chercher_jeu, nom)
    except (requests.RequestException, KeyError, ValueError):
        await ctx.send("Steam ne répond pas pour l'instant, réessaie dans un moment.")
        return

    if jeu is None:
        await ctx.send(f"Je n'ai trouvé aucun jeu pour « {nom} ».")
        return

    prix = jeu.get("price")
    if prix is None:
        await ctx.send(f"**{jeu['name']}** n'a pas de prix sur Steam (jeu gratuit ou pas encore sorti).")
        return

    initial = prix["initial"] / 100
    final = prix["final"] / 100
    en_promo = final < initial

    encart = discord.Embed(
        title=jeu["name"],
        url=f"https://store.steampowered.com/app/{jeu['id']}",
        color=discord.Color.green() if en_promo else discord.Color.light_grey(),
    )
    encart.set_thumbnail(url=jeu.get("tiny_image"))
    encart.add_field(name="Prix", value=f"{final:.2f} €")
    if en_promo:
        reduction = round((1 - final / initial) * 100)
        encart.add_field(name="Prix habituel", value=f"~~{initial:.2f} €~~")
        encart.add_field(name="Réduction", value=f"-{reduction} %")
    else:
        encart.description = "Pas de promotion en ce moment."
    encart.set_footer(text="Source : Steam")
    await ctx.send(embed=encart)


@bot.command()
async def promos(ctx):
    try:
        async with ctx.typing():
            jeux = await asyncio.to_thread(steam.promos_du_moment)
    except (requests.RequestException, KeyError, ValueError):
        await ctx.send("Steam ne répond pas pour l'instant, réessaie dans un moment.")
        return

    if not jeux:
        await ctx.send("Aucune promotion mise en avant sur Steam pour l'instant.")
        return

    lignes = []
    for jeu in jeux[:10]:
        final = jeu["final_price"] / 100
        initial = jeu["original_price"] / 100
        lien = f"https://store.steampowered.com/app/{jeu['id']}"
        lignes.append(
            f"**-{jeu['discount_percent']} %** · [{jeu['name']}]({lien}) · "
            f"{final:.2f} € ~~{initial:.2f} €~~"
        )

    encart = discord.Embed(
        title="Promotions Steam du moment",
        description="\n".join(lignes),
        color=discord.Color.green(),
    )
    encart.set_footer(text="Source : Steam")
    await ctx.send(embed=encart)


def echeance(fin):
    try:
        date = datetime.strptime(fin, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "sans date de fin"
    return f"jusqu'au {date:%d/%m}"


@bot.command()
async def gratuit(ctx):
    try:
        async with ctx.typing():
            jeux = await asyncio.to_thread(gratuits.jeux_gratuits)
    except (requests.RequestException, ValueError):
        await ctx.send("Le service des jeux offerts ne répond pas, réessaie dans un moment.")
        return

    if not jeux:
        await ctx.send("Aucun jeu offert en ce moment.")
        return

    lignes = []
    for jeu in jeux[:15]:
        titre = jeu["title"].removesuffix(" Giveaway")
        lignes.append(
            f"[{titre}]({jeu['open_giveaway_url']}) · {jeu['platforms']} · {echeance(jeu['end_date'])}"
        )

    encart = discord.Embed(
        title="Jeux offerts en ce moment",
        description="\n".join(lignes),
        color=discord.Color.gold(),
    )
    encart.set_footer(text="Source : GamerPower")
    await ctx.send(embed=encart)


@bot.command(usage="hades 10")
async def alerte(ctx, *, texte):
    nom, _, prix_texte = texte.rpartition(" ")
    try:
        prix_cible = round(float(prix_texte.replace(",", ".").replace("€", "")) * 100)
    except (ValueError, OverflowError):
        prix_cible = 0
    if not nom or prix_cible <= 0:
        await ctx.send("Format attendu : `!alerte nom du jeu prix`. Exemple : `!alerte hades 10`")
        return

    try:
        async with ctx.typing():
            jeu = await asyncio.to_thread(steam.chercher_jeu, nom)
    except (requests.RequestException, KeyError, ValueError):
        await ctx.send("Steam ne répond pas pour l'instant, réessaie dans un moment.")
        return

    if jeu is None:
        await ctx.send(f"Je n'ai trouvé aucun jeu pour « {nom} ».")
        return
    if jeu.get("price") is None:
        await ctx.send(f"**{jeu['name']}** n'a pas de prix sur Steam, impossible de le surveiller.")
        return

    numero = alertes.ajouter(ctx.author.id, jeu["id"], jeu["name"], prix_cible)
    actuel = jeu["price"]["final"] / 100
    await ctx.send(
        f"Alerte n°{numero} créée : je te préviens en message privé quand **{jeu['name']}** "
        f"passe à {prix_cible / 100:.2f} € ou moins (prix actuel : {actuel:.2f} €)."
    )


@bot.command(name="mes-alertes")
async def mes_alertes(ctx):
    liste = alertes.lister(ctx.author.id)
    if not liste:
        await ctx.send("Tu n'as aucune alerte. Crées-en une avec `!alerte hades 10`.")
        return

    lignes = [
        f"**n°{alerte['id']}** · {alerte['nom']} · {alerte['prix_cible'] / 100:.2f} € ou moins"
        for alerte in liste
    ]
    encart = discord.Embed(
        title=f"Alertes de {ctx.author.display_name}",
        description="\n".join(lignes),
        color=discord.Color.blue(),
    )
    encart.set_footer(text="Pour en supprimer une : !stop numéro")
    await ctx.send(embed=encart)


@bot.command(usage="3")
async def stop(ctx, numero: int):
    if alertes.supprimer(numero, ctx.author.id):
        await ctx.send(f"Alerte n°{numero} supprimée.")
    else:
        await ctx.send(f"Tu n'as pas d'alerte n°{numero}. Vérifie avec `!mes-alertes`.")


@tasks.loop(minutes=30)
async def verifier_alertes():
    liste = alertes.toutes()
    if not liste:
        return

    appids = {alerte["appid"] for alerte in liste}
    try:
        prix = await asyncio.to_thread(steam.prix_actuels, appids)
    except (requests.RequestException, KeyError, ValueError):
        return

    for alerte in liste:
        actuel = prix.get(alerte["appid"])
        if actuel is None or actuel > alerte["prix_cible"]:
            continue
        try:
            utilisateur = await bot.fetch_user(alerte["user_id"])
            await utilisateur.send(
                f"Bon plan : **{alerte['nom']}** est à {actuel / 100:.2f} € sur Steam "
                f"(ton alerte : {alerte['prix_cible'] / 100:.2f} € ou moins).\n"
                f"https://store.steampowered.com/app/{alerte['appid']}"
            )
        except discord.HTTPException as erreur:
            print(f"Alerte n°{alerte['id']} : message privé impossible ({erreur})")
            continue
        alertes.supprimer(alerte["id"], alerte["user_id"])


bot.run(TOKEN)
