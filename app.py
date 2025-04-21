import streamlit as st
from pymongo import MongoClient
import requests
import json

# Connexion à MongoDB
client = MongoClient("mongodb://localhost:27017")
db = client["comorian_app"]
collection = db["translations"]

# Fonction pour récupérer une phrase via Ollama en local
def get_french_sentence(sentiment=None):
    api_url = "http://localhost:11434/api/generate"  # URL de l'API Ollama en local
    model_name = "tinyllama"  # Modèle à utiliser, remplacez par votre modèle (ex. llama3, gemma)
    
    # Définir le prompt en fonction du sentiment
    sentiment_prompt = {
        "positif": "Génère une phrase positive en français, maximum 10 mots.",
        "négatif": "Génère une phrase négative en français, maximum 10 mots.",
        "neutre": "Génère une phrase neutre en français, maximum 10 mots."
    }.get(sentiment, "Génère une phrase en français, maximum 10 mots.")
    
    payload = {
        "model": model_name,
        "prompt": sentiment_prompt,
        "stream": False,  # Réponse unique, pas de streaming
    
        }
    
    
    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Extraire la phrase générée
        sentence = data.get("response", "").strip()
        
        # Vérifier la longueur (moins de 10 mots) et la validité
        if len(sentence.split()) <= 10 and sentence and not sentence.lower().startswith("erreur"):
            return sentence
        return "Erreur : Phrase non valide ou trop longue."
    except requests.exceptions.ConnectionError:
        return "Erreur : Serveur Ollama non actif. Lancez 'ollama serve'."
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return f"Erreur : Modèle '{model_name}' non trouvé. Vérifiez avec 'ollama list'."
        return f"Erreur HTTP : {str(e)}"
    except Exception as e:
        return f"Erreur : {str(e)}"

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
    st.title('Salam! A ton tour de participer à la traduction de phrase en Comorien\nYe Mdjuzi ndawe')

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