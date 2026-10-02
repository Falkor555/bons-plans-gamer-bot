import requests

URL_GRATUITS = "https://www.gamerpower.com/api/giveaways"


def jeux_gratuits():
    parametres = {"type": "game", "platform": "pc"}
    reponse = requests.get(URL_GRATUITS, params=parametres, timeout=10)
    reponse.raise_for_status()
    donnees = reponse.json()
    if not isinstance(donnees, list):
        return []
    return donnees


if __name__ == "__main__":
    for jeu in jeux_gratuits():
        print(jeu["end_date"], "|", jeu["platforms"], "|", jeu["title"])
