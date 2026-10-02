import os

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODELES = ["gemini-flash-latest", "gemini-flash-lite-latest"]

CONSIGNE = """Tu es le conseiller d'un bot Discord de bons plans jeux vidéo PC.
On te donne la liste des bons plans du moment et la question d'un joueur.
Recommande un à trois jeux de cette liste qui correspondent à sa demande,
en expliquant brièvement pourquoi et en rappelant leur prix et le magasin.
N'invente jamais de prix ni de promotion : utilise uniquement la liste fournie.
Si rien ne correspond, dis-le simplement.
Réponds en français, en tutoyant, en moins de 1200 caractères."""


def conseiller(question, bons_plans):
    for modele in MODELES:
        try:
            reponse = client.models.generate_content(
                model=modele,
                contents=f"Bons plans du moment :\n{bons_plans}\n\nQuestion du joueur : {question}",
                config=types.GenerateContentConfig(
                    system_instruction=CONSIGNE,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            return reponse.text
        except errors.ServerError as erreur:
            print(f"{modele} indisponible : {erreur.code}")
            derniere_erreur = erreur
    raise derniere_erreur


if __name__ == "__main__":
    plans = "- Hades : 6.12 € (-75 %)\n- Stardew Valley : 9.79 € (-30 %)\n- ELDEN RING : 59.99 €"
    print(conseiller("Je cherche un jeu calme pour me détendre, à moins de 10 €", plans))
