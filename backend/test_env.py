import os
from dotenv import load_dotenv

# 1. Charger les variables du fichier .env
load_dotenv()

# 2. Récupérer la variable
api_key = os.getenv("GOOGLE_API_KEY")

# 3. Vérification
if api_key:
    # On affiche seulement les 4 premiers et derniers caractères pour vérifier
    # Pas d'emoji : evite UnicodeEncodeError sur console Windows (cp1252)
    print("[OK] Succès ! Le fichier .env est bien chargé.")
    print(f"Clé détectée : {api_key[:4]}...{api_key[-4:]}")
else:
    print("[ECHEC] La variable GOOGLE_API_KEY n'a pas été trouvée.")
    print("Vérifie que ton fichier s'appelle exactement '.env' et qu'il est au bon endroit.")
