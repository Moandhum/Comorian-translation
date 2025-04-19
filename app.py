import streamlit as st
import requests
from pymongo import MongoClient
import numpy as np
import random
MONGO_URI = st.secrets.get("MONGO_URI")




client = MongoClient(MONGO_URI)
db = client["Cluster0"]
collection = db["translations"]


# Listes de mots-clés pour détecter le sentiment
SENTIMENT_KEYWORDS = {
    "positif": ["heureux", "content", "bien", "joli", "beau", "super", "merveilleux", "gentil", "aime", "amour", "plaisir", "sourire"],
    "négatif": ["triste", "mal", "fatigué", "dur", "froid", "mauvais", "n'aime", "déteste", "peur", "ennuyeux", "difficile"],
    "neutre": []  # Les phrases neutres sont celles qui ne contiennent ni mots positifs ni négatifs
}

# Fonction pour détecter le sentiment d'une phrase
def detect_sentiment(sentence):
    sentence = sentence.lower()
    # Compter les mots positifs et négatifs
    positive_count = sum(1 for word in SENTIMENT_KEYWORDS["positif"] if word in sentence)
    negative_count = sum(1 for word in SENTIMENT_KEYWORDS["négatif"] if word in sentence)
    
    if positive_count > negative_count:
        return "positif"
    elif negative_count > positive_count:
        return "négatif"
    else:
        return "neutre"

# Fonction pour récupérer une phrase via l'API Tatoeba
def get_french_sentence(sentiment=None):
    api_url = 'https://tatoeba.org/en/api_v0/search?from=fra&sort=random&limit=10&tags=francais'
    
    max_attempts = 10  # Nombre maximum de tentatives pour trouver une phrase correspondant au sentiment
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(api_url)
            if response.status_code == 200:
                data = response.json()
                if data['results']:
                    # Parcourir les phrases récupérées pour en trouver une qui correspond
                    for result in data['results']:
                        sentence = result['text']
                        # Filtrer les phrases : moins de 10 mots et pas d'erreur
                        if len(sentence.split()) <= 10 and not sentence.startswith("Erreur"):
                            detected_sentiment = detect_sentiment(sentence)
                            # Si aucun sentiment spécifié, retourner la première phrase valide
                            if not sentiment:
                                return sentence
                            # Si le sentiment détecté correspond à celui demandé, retourner la phrase
                            if detected_sentiment == sentiment:
                                return sentence
            # Si aucune phrase ne correspond, continuer à essayer
            attempt += 1
        except Exception as e:
            return f"Erreur : {str(e)}"
    
    return f"Erreur : Aucune phrase correspondant au sentiment '{sentiment}' n'a été trouvée."

# Fonction pour sauvegarder dans MongoDB
def save_to_mongo(french_sentence, comorian_translation, username, sentiment=None):
    doc = {
        "french_sentence": french_sentence,
        "comorian_translation": comorian_translation,
        "username": username,
        "sentiment": sentiment if sentiment else "non spécifié"
    }
    collection.insert_one(doc)

# Interface Streamlit
def main():
    st.title('Salam! A ton tour de participer à la traduction de phrase en Comorien\nYe Mdjuzi nɗawe')

    # Initialiser la phrase française et le sentiment si non défini
    if 'french_sentence' not in st.session_state:
        st.session_state.french_sentence = get_french_sentence()
        st.session_state.sentiment = None

    # Champ pour le nom d'utilisateur
    username = st.text_input("Entrez votre nom d'utilisateur", key="username_input")

    # Sélection du thème de sentiment
    st.subheader("Choisissez un thème de sentiment")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Positif"):
            st.session_state.sentiment = "positif"
            st.session_state.french_sentence = get_french_sentence(sentiment="positif")
            st.rerun()
    with col2:
        if st.button("Négatif"):
            st.session_state.sentiment = "négatif"
            st.session_state.french_sentence = get_french_sentence(sentiment="négatif")
            st.rerun()
    with col3:
        if st.button("Neutre"):
            st.session_state.sentiment = "neutre"
            st.session_state.french_sentence = get_french_sentence(sentiment="neutre")
            st.rerun()

    # Afficher la phrase française
    st.write(f"Phrase en français (Sentiment : {st.session_state.sentiment if st.session_state.sentiment else 'non spécifié'}) : {st.session_state.french_sentence}")

    # Bouton pour actualiser la phrase
    if st.button("Actualiser la phrase"):
        st.session_state.french_sentence = get_french_sentence(sentiment=st.session_state.sentiment)
        st.rerun()

    # Champ de saisie pour la traduction
    comorian_translation = st.text_area("Fasiri shiKomori", value="", key=f"translation_{st.session_state.french_sentence}")

    # Bouton pour soumettre
    if st.button('Soumettre'):
        if not username:
            st.error("Veuillez entrer un nom d'utilisateur.")
        elif not comorian_translation:
            st.error("Veuillez entrer une traduction.")
        else:
            # Sauvegarder dans MongoDB
            save_to_mongo(st.session_state.french_sentence, comorian_translation, username, st.session_state.sentiment)
            st.success("Traduction soumise avec succès !")
            # Réinitialiser la phrase française et garder le sentiment
            st.session_state.french_sentence = get_french_sentence(sentiment=st.session_state.sentiment)
            st.rerun()

if __name__ == '__main__':
    main()
