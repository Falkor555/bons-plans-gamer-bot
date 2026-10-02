import sqlite3

connexion = sqlite3.connect("alertes.db")
connexion.row_factory = sqlite3.Row
connexion.execute(
    """
    CREATE TABLE IF NOT EXISTS alertes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        appid INTEGER NOT NULL,
        nom TEXT NOT NULL,
        prix_cible INTEGER NOT NULL
    )
    """
)
connexion.commit()


def ajouter(user_id, appid, nom, prix_cible):
    with connexion:
        curseur = connexion.execute(
            "INSERT INTO alertes (user_id, appid, nom, prix_cible) VALUES (?, ?, ?, ?)",
            (user_id, appid, nom, prix_cible),
        )
    return curseur.lastrowid


def lister(user_id):
    return connexion.execute(
        "SELECT * FROM alertes WHERE user_id = ? ORDER BY id", (user_id,)
    ).fetchall()


def toutes():
    return connexion.execute("SELECT * FROM alertes ORDER BY id").fetchall()


def supprimer(alerte_id, user_id):
    with connexion:
        curseur = connexion.execute(
            "DELETE FROM alertes WHERE id = ? AND user_id = ?", (alerte_id, user_id)
        )
    return curseur.rowcount > 0


if __name__ == "__main__":
    numero = ajouter(1, 1145360, "Hades", 1000)
    print([dict(alerte) for alerte in lister(1)])
    print(supprimer(numero, 2), supprimer(numero, 1), lister(1))
