import os

import requests
from dotenv import load_dotenv

load_dotenv()
CLE = os.getenv("ITAD_API_KEY")
URL = "https://api.isthereanydeal.com"


def comparer(appid):
    reponse = requests.get(
        f"{URL}/games/lookup/v1", params={"key": CLE, "appid": appid}, timeout=10
    )
    reponse.raise_for_status()
    recherche = reponse.json()
    if not recherche["found"]:
        return None

    reponse = requests.post(
        f"{URL}/games/prices/v3",
        params={"key": CLE, "country": "FR"},
        json=[recherche["game"]["id"]],
        timeout=10,
    )
    reponse.raise_for_status()
    resultats = reponse.json()
    if not resultats:
        return None

    jeu = resultats[0]
    return {
        "offres": sorted(jeu["deals"], key=lambda offre: offre["price"]["amountInt"]),
        "plus_bas": jeu["historyLow"]["all"],
    }


def promos_du_moment(nombre=60):
    reponse = requests.get(
        f"{URL}/deals/v2",
        params={"key": CLE, "country": "FR", "limit": nombre, "sort": "-trending"},
        timeout=10,
    )
    reponse.raise_for_status()
    return reponse.json()["list"]


if __name__ == "__main__":
    for jeu in promos_du_moment(10):
        offre = jeu["deal"]
        print(jeu["title"], "|", offre["shop"]["name"], "|", offre["price"]["amount"], f"-{offre['cut']} %")


