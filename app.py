import streamlit as st
import requests
from pymongo import MongoClient

MONGO_URI = st.secrets.get("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["Cluster0"]
collection = db["translations"]

# Fonction pour récupérer une phrase aléatoire en français depuis l'API Tatoeba
def get_french_sentence():
    api_url = 'https://tatoeba.org/en/api_v0/search?from=fra&sort=random&limit=1&tags=francais'
    response = requests.get(api_url)

    if response.status_code == 200:
        data = response.json()
        if data['results']:
            return data['results'][0]['text']
    return "Erreur: Impossible de récupérer une phrase."

# Fonction pour sauvegarder dans MongoDB
def save_to_mongo(french_sentence, comorian_translation, username):
    doc = {
        "french_sentence": french_sentence,
        "comorian_translation": comorian_translation,
        "username": username
    }
    collection.insert_one(doc)

# Interface Streamlit
def main():
    st.title('Application de traduction en Comorien')

    # Initialiser la phrase française si elle n'existe pas
    if 'french_sentence' not in st.session_state:
        st.session_state.french_sentence = get_french_sentence()

    # Champ pour le nom d'utilisateur
    username = st.text_input("Entrez votre nom d'utilisateur", key="username_input")

    # Afficher la phrase française
    st.write(f"Phrase en français : {st.session_state.french_sentence}")

    # Champ de saisie pour la traduction, initialisé vide
    comorian_translation = st.text_area("Fasiri shiKomori", value="", key=f"translation_{st.session_state.french_sentence}")

    if st.button('Soumettre'):
        if not username:
            st.error("Veuillez entrer un nom d'utilisateur.")
        elif not comorian_translation:
            st.error("Veuillez entrer une traduction.")
        else:
            # Sauvegarder dans MongoDB
            save_to_mongo(st.session_state.french_sentence, comorian_translation, username)
            st.success("Traduction soumise avec succès !")
            # Réinitialiser la phrase française
            st.session_state.french_sentence = get_french_sentence()
            # Forcer le rechargement pour vider le champ et afficher la nouvelle phrase
            st.rerun()

if __name__ == '__main__':
    main()
