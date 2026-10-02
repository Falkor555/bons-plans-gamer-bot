import requests

URL_RECHERCHE = "https://store.steampowered.com/api/storesearch/"
URL_PROMOS = "https://store.steampowered.com/api/featuredcategories"
URL_DETAILS = "https://store.steampowered.com/api/appdetails"


def chercher_jeu(nom):
    parametres = {"term": nom, "cc": "fr", "l": "french"}
    reponse = requests.get(URL_RECHERCHE, params=parametres, timeout=10)
    reponse.raise_for_status()
    resultats = reponse.json()["items"]
    if not resultats:
        return None
    return resultats[0]


def promos_du_moment():
    parametres = {"cc": "fr", "l": "french"}
    reponse = requests.get(URL_PROMOS, params=parametres, timeout=10)
    reponse.raise_for_status()
    jeux = reponse.json()["specials"]["items"]
    return sorted(jeux, key=lambda jeu: jeu["discount_percent"], reverse=True)


def prix_actuels(appids):
    parametres = {
        "appids": ",".join(str(appid) for appid in appids),
        "cc": "fr",
        "filters": "price_overview",
    }
    reponse = requests.get(URL_DETAILS, params=parametres, timeout=10)
    reponse.raise_for_status()
    prix = {}
    for appid, infos in reponse.json().items():
        if infos["success"] and infos["data"]:
            prix[int(appid)] = infos["data"]["price_overview"]["final"]
    return prix


if __name__ == "__main__":
    print(prix_actuels([1145360, 730, 413150]))