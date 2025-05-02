import streamlit as st
import requests
from pymongo import MongoClient
import numpy as np
import random



MONGO_URI = st.secrets.get("MONGO_URI")


# Connexion à MongoDB local
try:
    client = MongoClient(MONGO_URI)
    db = client["Cluster0"]
    collection = db["translations"]

except Exception as e:
    st.error(f"Erreur de connexion MongoDB : {str(e)}")
    st.stop()

# Mots clés par thématique
MOTS_CLES = {
    "salutations": ["bonjour", "salut", "bonsoir", "merci", "aurevoir", "coucou", "ravi", "nom", "appelle", "prénom", "famille"],
    "voyage": ["gare", "aéroport", "train", "bus", "taxi", "billet", "hôtel", "carte", "bateau", "port", "île", "océan", "plage", "voyage"],
    "maison": ["cuisine", "chambre", "salon", "clé", "lampe", "table", "chaise", "maison", "toit", "cour", "bananier", "mangue", "coco", "village"],
    "école": ["classe", "cahier", "stylo", "livre", "professeur", "élève", "examen", "école", "leçon", "apprendre", "étudier", "savoir"],
    "vie_quotidienne": ["marché", "plage", "travail", "sport", "musique", "nourriture", "matin", "poisson", "riz", "prière", "mosquée", "fête", "mariage", "soleil"]
}

# Fonction pour récupérer une phrase via l’API Tatoeba
def get_french_sentence():
    api_url = 'https://tatoeba.org/en/api_v0/search?from=fra&to=none&query={}&sort=random'
    max_attempts = 8
    attempt = 0

    # Choisir un thème et un mot clé aléatoires
    theme = random.choice(list(MOTS_CLES.keys()))
    mot_cle = random.choice(MOTS_CLES[theme])

    while attempt < max_attempts:
        try:
            # Faire une requête avec le mot clé
            response = requests.get(api_url.format(mot_cle))
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    for result in data['results']:
                        sentence = result['text']
                        # Vérifier que la phrase a ≤10 mots, ne commence pas par "Erreur", et semble cohérente
                        if (len(sentence.split()) <= 10 and 
                            not sentence.startswith("Erreur") and 
                            mot_cle.lower() in sentence.lower()):  # Vérifie que le mot est présent
                            return sentence
            attempt += 1
        except Exception as e:
            st.warning(f"Erreur API Tatoeba : {str(e)}")
            attempt += 1
    # Fallback si aucune phrase n’est trouvée
    return f"Erreur : Aucune phrase avec '{mot_cle}' trouvée."

# Fonction pour sauvegarder dans MongoDB (inchangée)
def save_to_mongo(french_sentence, comorian_translation, username, dialect):
    try:
        doc = {
            "french_sentence": french_sentence,
            "comorian_translation": comorian_translation,
            "username": username,
            "dialect": dialect
        }
        collection.insert_one(doc)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde dans MongoDB : {str(e)}")

# Fonction pour afficher les traductions (inchangée)
def display_translations():
    st.sidebar.markdown(
        """
        <style>
        .sidebar .sidebar-content {
            background-color: rgba(0, 0, 139, 0.3);
            padding: 10px;
            border-radius: 5px;
        }
        .translation-item {
            margin-bottom: 10px;
            padding: 5px;
            border-bottom: 1px solid #ccc;
            font-size: 14px;
        }
        @media (max-width: 600px) {
            .sidebar .sidebar-content {
                padding: 5px;
            }
            .translation-item {
                font-size: 12px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.sidebar.subheader("Traductions précédentes")
    try:
        translations = collection.find().sort("_id", -1).limit(10)
        count = 0
        for translation in translations:
            count += 1
            st.sidebar.markdown(
                f"""
                <div class="translation-item">
                    <strong>Français :</strong> {translation.get('french_sentence', 'Non disponible')}<br>
                    <strong>ShiKomori :</strong> {translation.get('comorian_translation', 'Non disponible')}<br>
                    <strong>Dialecte :</strong> {translation.get('dialect', 'Non spécifié')}<br>
                    <strong>Utilisateur :</strong> {translation.get('username', 'Anonyme')}
                </div>
                """,
                unsafe_allow_html=True
            )
        if count == 0:
            st.sidebar.write("Aucune traduction trouvée dans la base.")
    except Exception as e:
        st.sidebar.error(f"Erreur lors de la récupération des traductions : {str(e)}")

# Interface Streamlit (inchangée)
def main():
    # CSS global pour une application responsive
    st.markdown(
        """
        <style>
        .main {
            padding: 10px;
        }
        h1 {
            font-size: 24px;
            line-height: 1.2;
        }
        h3 {
            font-size: 18px;
        }
        .stButton > button {
            width: 100%;
            margin-bottom: 10px;
        }
        .stTextInput, .stTextArea {
            width: 100%;
        }
        .dialect-button-shingazidja {
            background-color: #87CEFA;
            color: black;
            padding: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            width: 100%;
            margin-bottom: 10px;
        }
        .dialect-button-shindzouani {
            background-color: #FF9999;
            color: black;
            padding: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            width: 100%;
            margin-bottom: 10px;
        }
        .dialect-button-shimwali {
            background-color: #FFFF99;
            color: black;
            padding: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            width: 100%;
            margin-bottom: 10px;
        }
        .dialect-button-shimaore {
            background-color: #FFFFFF;
            color: black;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            cursor: pointer;
            width: 100%;
            margin-bottom: 10px;
        }
        .dialect-button-shingazidja:hover, .dialect-button-shindzouani:hover, 
        .dialect-button-shimwali:hover, .dialect-button-shimaore:hover {
            opacity: 0.8;
        }
        @media (max-width: 600px) {
            h1 {
                font-size: 20px;
            }
            h3 {
                font-size: 16px;
            }
            .stButton > button {
                font-size: 14px;
                padding: 8px;
            }
            .stTextInput > div > div > input, .stTextArea > div > div > textarea {
                font-size: 14px;
            }
            .st-emotion-cache-1r4qj8v {
                flex-direction: column;
            }
            .st-emotion-cache-1r4qj8v > div {
                width: 100% !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Compter le nombre total de traductions
    try:
        total_translations = collection.count_documents({})
        target = 100
        progress_text = f"{total_translations}/{target}"
    except Exception as e:
        total_translations = 0
        progress_text = "Erreur lors du comptage"
        st.error(f"Erreur MongoDB : {str(e)}")
# Titre principal
    st.markdown(
        f"""
        <h2 style="color: #00008B;">
            🌍 Salam ! Traduis des phrases en comorien et aide-nous à augmenter le chiffre ci-dessous.</h2>
        <h2 style="color: #00008B;">On est à <span style="color: #228B22;">{progress_text}</span> phrases traduites ! 💪
        </h2>
        """,
        unsafe_allow_html=True
    )

    # Afficher les traductions dans la barre latérale
    display_translations()

    # Section des rappels de règles
    with st.expander("Quelques rappels des règles du shiKomori", expanded=False):
        st.markdown(
            '<h2 style="color: #800020; font-weight: bold;">Quelques rappels des règles du shiKomori</h2>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<h3 style="color: #0000FF;">1. Règles orthographiques</h3>',
            unsafe_allow_html=True
        )
        st.markdown("""
        - **Son [OU]** : S'écrit avec **u**.  
          *Exemple* : *mdru* (personne) au lieu de « mdrou ».  
        - **Son [OI]** : S'écrit avec **wa**.  
          *Exemple* : *mwana* (enfant) au lieu de « moina ».  
        - **Son [CH]** : S'écrit avec **sh**.  
          *Exemple* : *shiyo* (enfant) au lieu de « chiyo ».  
        - **Son [TCH]** : S'écrit avec **c**.  
          *Exemple* : *cai* (thé) au lieu de « tchai ».  
        """)
        st.markdown(
            '<h3 style="color: #0000FF;">2. Conjugaison du verbe « soma » (lire, apprendre, étudier)</h3>',
            unsafe_allow_html=True
        )
        st.markdown("**Forme affirmative**")
        affirmative_data = [
            {"Personne": "1ère sing. (je)", "Conjugaison": "ngamsomo"},
            {"Personne": "2ème sing. (tu)", "Conjugaison": "ngosomo"},
            {"Personne": "3ème sing. (il/elle)", "Conjugaison": "ngusomo"},
            {"Personne": "1ère plur. (nous)", "Conjugaison": "ngarisomao"},
            {"Personne": "2ème plur. (vous)", "Conjugaison": "ngamsomao"},
            {"Personne": "3ème plur. (ils/elles)", "Conjugaison": "ngwasomao"},
        ]
        st.table(affirmative_data)
        st.markdown("**Forme négative**")
        negative_data = [
            {"Personne": "1ère sing. (je)", "Conjugaison": "ntsusoma"},
            {"Personne": "2ème sing. (tu)", "Conjugaison": "kutsusoma"},
            {"Personne": "3ème sing. (il/elle)", "Conjugaison": "katsusoma"},
            {"Personne": "1ère plur. (nous)", "Conjugaison": "ntsusomao"},
            {"Personne": "2ème plur. (vous)", "Conjugaison": "kutsusomao"},
            {"Personne": "3ème plur. (ils/elles)", "Conjugaison": "katsusomao"},
        ]
        st.table(negative_data)

    # Section choix du dialecte
    st.markdown(
        '<h3 style="color: #00008B;">Choisissez le dialecte pour votre traduction</h3>',
        unsafe_allow_html=True
    )

    # Boutons pour choisir le dialecte
    if 'selected_dialect' not in st.session_state:
        st.session_state.selected_dialect = None

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("Shingazidja", key="shingazidja"):
            st.session_state.selected_dialect = "Shingazidja"
    with col2:
        if st.button("Shindzouani", key="shindzouani"):
            st.session_state.selected_dialect = "Shindzouani"
    with col3:
        if st.button("Shimwali", key="shimwali"):
            st.session_state.selected_dialect = "Shimwali"
    with col4:
        if st.button("Shimaore", key="shimaore"):
            st.session_state.selected_dialect = "Shimaore"

    # Appliquer les styles CSS aux boutons
    st.markdown(
        """
        <script>
        document.querySelector('button[kind="secondary"][key="shingazidja"]').classList.add('dialect-button-shingazidja');
        document.querySelector('button[kind="secondary"][key="shindzouani"]').classList.add('dialect-button-shindzouani');
        document.querySelector('button[kind="secondary"][key="shimwali"]').classList.add('dialect-button-shimwali');
        document.querySelector('button[kind="secondary"][key="shimaore"]').classList.add('dialect-button-shimaore');
        </script>
        """,
        unsafe_allow_html=True
    )

    # Afficher le dialecte sélectionné
    if st.session_state.selected_dialect:
        st.write(f"Dialecte sélectionné : **{st.session_state.selected_dialect}**")
    else:
        st.warning("Veuillez sélectionner un dialecte avant de traduire.")

    # Section traduction
    if 'french_sentence' not in st.session_state:
        st.session_state.french_sentence = get_french_sentence()

    username = st.text_input("Entrez votre nom d'utilisateur", key="username_input")
    st.write(f"Phrase en français : {st.session_state.french_sentence}")

    if st.button("Actualiser la phrase"):
        st.session_state.french_sentence = get_french_sentence()
        st.rerun()

    comorian_translation = st.text_area("Fasiri shiKomori", value="", key=f"translation_{st.session_state.french_sentence}")

    if st.button('Soumettre'):
        if not username:
            st.error("Veuillez entrer un nom d'utilisateur.")
        elif not comorian_translation:
            st.error("Veuillez entrer une traduction.")
        elif not st.session_state.selected_dialect:
            st.error("Veuillez sélectionner un dialecte.")
        else:
            save_to_mongo(st.session_state.french_sentence, comorian_translation, username, st.session_state.selected_dialect)
            st.success("Traduction soumise avec succès !")
            st.session_state.french_sentence = get_french_sentence()
            st.session_state.selected_dialect = None
            st.rerun()

if __name__ == '__main__':
    main()
