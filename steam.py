import requests

URL_RECHERCHE = "https://store.steampowered.com/api/storesearch/"
URL_PROMOS = "https://store.steampowered.com/api/featuredcategories"


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


if __name__ == "__main__":
    for jeu in promos_du_moment():
        print(jeu["discount_percent"], jeu["final_price"], jeu["name"])
