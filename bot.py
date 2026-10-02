import asyncio
from datetime import datetime
import os

import discord
import requests
from discord.ext import commands, tasks
from dotenv import load_dotenv
from google.genai import errors as erreurs_gemini

import alertes
import conseil
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


async def repondre(ctx, *args, **kwargs):
    fil = getattr(ctx, "fil", None)
    if fil is None:
        try:
            fil = await ctx.message.create_thread(
                name=ctx.message.content[:100], auto_archive_duration=60
            )
        except discord.HTTPException as erreur:
            print(f"Création du fil impossible ({erreur}), réponse dans le salon")
            fil = ctx.channel
        ctx.fil = fil
    await fil.send(*args, **kwargs)


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    if not verifier_alertes.is_running():
        verifier_alertes.start()


@bot.event
async def on_command_error(ctx, erreur):
    if isinstance(erreur, commands.MissingRequiredArgument):
        exemple = ctx.command.usage or "hades"
        await repondre(ctx,f"Il manque une information. Exemple : `!{ctx.command} {exemple}`")
    elif isinstance(erreur, commands.BadArgument):
        await repondre(ctx,f"Je n'ai pas compris. Exemple : `!{ctx.command} {ctx.command.usage}`")
    elif isinstance(erreur, (commands.CommandNotFound, commands.CheckFailure)):
        return
    else:
        print(f"Erreur dans !{ctx.command} : {erreur!r}")
        await repondre(ctx,"Une erreur est survenue, désolé.")


@bot.command()
async def ping(ctx):
    await repondre(ctx,"pong")


@bot.command()
async def promo(ctx, *, nom):
    try:
        async with ctx.typing():
            jeu = await asyncio.to_thread(steam.chercher_jeu, nom)
    except (requests.RequestException, KeyError, ValueError):
        await repondre(ctx,"Steam ne répond pas pour l'instant, réessaie dans un moment.")
        return

    if jeu is None:
        await repondre(ctx,f"Je n'ai trouvé aucun jeu pour « {nom} ».")
        return

    prix = jeu.get("price")
    if prix is None:
        await repondre(ctx,f"**{jeu['name']}** n'a pas de prix sur Steam (jeu gratuit ou pas encore sorti).")
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
    await repondre(ctx,embed=encart)


@bot.command()
async def promos(ctx):
    try:
        async with ctx.typing():
            jeux = await asyncio.to_thread(steam.promos_du_moment)
    except (requests.RequestException, KeyError, ValueError):
        await repondre(ctx,"Steam ne répond pas pour l'instant, réessaie dans un moment.")
        return

    if not jeux:
        await repondre(ctx,"Aucune promotion mise en avant sur Steam pour l'instant.")
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
    await repondre(ctx,embed=encart)


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
        await repondre(ctx,"Le service des jeux offerts ne répond pas, réessaie dans un moment.")
        return

    if not jeux:
        await repondre(ctx,"Aucun jeu offert en ce moment.")
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
    await repondre(ctx,embed=encart)


@bot.command(usage="hades 10")
async def alerte(ctx, *, texte):
    nom, _, prix_texte = texte.rpartition(" ")
    try:
        prix_cible = round(float(prix_texte.replace(",", ".").replace("€", "")) * 100)
    except (ValueError, OverflowError):
        prix_cible = 0
    if not nom or prix_cible <= 0:
        await repondre(ctx,"Format attendu : `!alerte nom du jeu prix`. Exemple : `!alerte hades 10`")
        return

    try:
        async with ctx.typing():
            jeu = await asyncio.to_thread(steam.chercher_jeu, nom)
    except (requests.RequestException, KeyError, ValueError):
        await repondre(ctx,"Steam ne répond pas pour l'instant, réessaie dans un moment.")
        return

    if jeu is None:
        await repondre(ctx,f"Je n'ai trouvé aucun jeu pour « {nom} ».")
        return
    if jeu.get("price") is None:
        await repondre(ctx,f"**{jeu['name']}** n'a pas de prix sur Steam, impossible de le surveiller.")
        return

    numero = alertes.ajouter(ctx.author.id, jeu["id"], jeu["name"], prix_cible)
    actuel = jeu["price"]["final"] / 100
    await repondre(
        ctx,
        f"Alerte n°{numero} créée : je te préviens en message privé quand **{jeu['name']}** "
        f"passe à {prix_cible / 100:.2f} € ou moins (prix actuel : {actuel:.2f} €)."
    )


@bot.command(name="mes-alertes")
async def mes_alertes(ctx):
    liste = alertes.lister(ctx.author.id)
    if not liste:
        await repondre(ctx,"Tu n'as aucune alerte. Crées-en une avec `!alerte hades 10`.")
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
    await repondre(ctx,embed=encart)


@bot.command(usage="3")
async def stop(ctx, numero: int):
    if alertes.supprimer(numero, ctx.author.id):
        await repondre(ctx,f"Alerte n°{numero} supprimée.")
    else:
        await repondre(ctx,f"Tu n'as pas d'alerte n°{numero}. Vérifie avec `!mes-alertes`.")


@bot.command(name="conseil", usage="un jeu calme à moins de 10 €")
async def demander_conseil(ctx, *, question):
    try:
        async with ctx.typing():
            promos = await asyncio.to_thread(steam.promos_du_moment)
            offerts = await asyncio.to_thread(gratuits.jeux_gratuits)
    except (requests.RequestException, KeyError, ValueError):
        await repondre(ctx,"Je n'arrive pas à récupérer les bons plans, réessaie dans un moment.")
        return

    lignes = ["Promotions Steam :"]
    for jeu in promos[:20]:
        lignes.append(
            f"- {jeu['name']} : {jeu['final_price'] / 100:.2f} € (-{jeu['discount_percent']} %)"
        )
    lignes.append("Jeux offerts :")
    for jeu in offerts[:10]:
        lignes.append(f"- {jeu['title'].removesuffix(' Giveaway')} ({jeu['platforms']})")

    try:
        async with ctx.typing():
            reponse = await asyncio.to_thread(conseil.conseiller, question, "\n".join(lignes))
    except erreurs_gemini.APIError:
        await repondre(ctx,"Le conseiller ne répond pas pour l'instant, réessaie dans un moment.")
        return

    await repondre(ctx,(reponse or "Je n'ai pas de conseil à te donner cette fois.")[:2000])


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
