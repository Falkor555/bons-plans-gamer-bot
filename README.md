# Bon Plan Gamer

Bot Discord qui aide à trouver les bons plans jeux vidéo sur PC : prix et promotions Steam, jeux offerts, alertes de prix en message privé et recommandations par un LLM (Gemini).

Projet réalisé dans le cadre du module Python & IA.

## Commandes

Le bot ne répond que dans le salon `bot-09`.

| Commande | Effet | Réponse |
|---|---|---|
| `!promo hades` | Prix actuel d'un jeu sur Steam, avec la réduction s'il y en a une | salon |
| `!promos` | Promotions Steam du moment, triées par réduction | salon |
| `!gratuit` | Jeux offerts en ce moment sur PC | salon |
| `!aide` | Liste des commandes | salon |
| `!alerte hades 10` | Crée une alerte : le bot prévient quand le jeu passe à 10 € ou moins | fil |
| `!mes-alertes` | Liste ses alertes, avec leur numéro | fil |
| `!stop 3` | Supprime son alerte n°3 | fil |
| `!conseil un jeu calme à moins de 10 €` | Recommande un à trois jeux parmi les bons plans du moment | fil |

Les réponses utiles à tous arrivent dans le salon. Les réponses personnelles arrivent dans un fil créé sous la commande, pour ne pas encombrer le salon.

## Installation

Il faut Python 3.13 et un bot créé sur le [portail développeur Discord](https://discord.com/developers/applications).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Remplir ensuite `.env` :

| Variable | Où l'obtenir |
|---|---|
| `DISCORD_TOKEN` | Portail développeur Discord, onglet Bot |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) |

Le fichier `.env` contient des secrets : il est ignoré par git et ne doit pas être partagé.

Côté Discord, le bot a besoin de :

- l'intent **Message Content**, à activer dans l'onglet Bot du portail ;
- dans le salon `bot-09`, les permissions **Envoyer des messages**, **Intégrer des liens**, **Créer des fils publics** et **Envoyer des messages dans les fils**.

## Lancement

```powershell
.\.venv\Scripts\python.exe bot.py
```

Le terminal affiche `Connecté en tant que …` quand le bot est prêt.

## Déploiement

Sur un serveur Linux, le bot tourne comme service systemd : il démarre avec le serveur et redémarre seul après un arrêt. Le fichier `bons-plans-gamer.service` suppose que le projet est dans `/root/bons-plans-gamer-bot`.

Les commandes ci-dessous se lancent depuis le dossier du projet. `serveur` désigne l'hôte SSH.

```powershell
ssh serveur 'mkdir -p /root/bons-plans-gamer-bot'
scp bot.py steam.py gratuits.py alertes.py conseil.py requirements.txt .env serveur:/root/bons-plans-gamer-bot/
ssh serveur 'cd /root/bons-plans-gamer-bot && chmod 600 .env && python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt'
scp bons-plans-gamer.service serveur:/etc/systemd/system/
ssh serveur 'systemctl daemon-reload && systemctl enable --now bons-plans-gamer'
```

| Besoin | Commande |
|---|---|
| Voir ce que le bot affiche | `ssh serveur 'journalctl -u bons-plans-gamer -n 30 --no-pager'` |
| Redémarrer après une mise à jour du code | `ssh serveur 'systemctl restart bons-plans-gamer'` |
| Arrêter le bot | `ssh serveur 'systemctl stop bons-plans-gamer'` |

Le bot ne doit tourner qu'à un seul endroit à la fois : lancé en local pendant que le service est actif, il répond en double.

## Fonctionnement

| Fichier | Rôle |
|---|---|
| `bot.py` | Commandes Discord, gestion des erreurs, boucle de vérification des alertes |
| `steam.py` | Appels à l'API du magasin Steam : recherche d'un jeu, promotions, prix par identifiant |
| `gratuits.py` | Appel à l'API GamerPower pour les jeux offerts |
| `alertes.py` | Stockage des alertes dans une base SQLite (`alertes.db`, créée au premier lancement) |
| `conseil.py` | Appel à Gemini pour la recommandation |

### Alertes

Toutes les 30 minutes, et une fois au démarrage, le bot demande à Steam le prix de tous les jeux surveillés en une seule requête. Quand un prix atteint la cible, il envoie un message privé à l'auteur de l'alerte puis la supprime. Si le message privé échoue, l'alerte est conservée et retentée au passage suivant.

### Conseil

Un LLM ne connaît pas les prix du jour et peut en inventer. Le bot récupère donc les promotions Steam et les jeux offerts, les transmet à Gemini avec la question du joueur, et lui impose par une consigne système de ne recommander que des jeux de cette liste.

## Limites

- Les prix viennent de Steam uniquement, en euros (magasin français).
- `!promo` et `!alerte` retiennent le premier résultat de la recherche Steam : `!promo hades` peut renvoyer Hades II.
- `!conseil` choisit parmi les promotions mises en avant par Steam et les jeux offerts, pas dans tout le catalogue.
- Le salon est reconnu par son nom : un salon renommé n'est plus écouté.
- Les fils sont visibles par tous les membres du salon.
- Les commandes tapées à l'intérieur d'un fil sont ignorées.
