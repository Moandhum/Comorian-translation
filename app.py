import streamlit as st
import requests
from pymongo import MongoClient
import random
from audio_recorder_streamlit import audio_recorder
import speech_recognition as sr
import io
from pydub import AudioSegment
import streamlit.components.v1 as components

# --- Correctif pour le bug du File Watcher de Streamlit avec PyTorch (Whisper) ---
import torch
torch.classes.__path__ = []
# -----------------------------------------------------------------------------------

# Connexion MongoDB (à adapter selon votre configuration)
client = MongoClient("mongodb://localhost:27017/")
db = client["translations_db"]
collection = db["translations"]

# Mots clés par thématique
MOTS_CLES = {
    "salutations": ["bonjour", "salut", "bonsoir", "merci", "aurevoir", "coucou", "ravi", "nom", "appelle", "prénom", "famille"],
    "voyage": ["gare", "aéroport", "train", "bus", "taxi", "billet", "hôtel", "carte", "bateau", "port", "île", "océan", "plage", "voyage"],
    "maison": ["cuisine", "chambre", "salon", "clé", "lampe", "table", "chaise", "maison", "toit", "cour", "bananier", "mangue", "coco", "village"],
    "école": ["classe", "cahier", "stylo", "livre", "professeur", "élève", "examen", "école", "leçon", "apprendre", "étudier", "savoir"],
    "vie_quotidienne": ["marché", "plage", "travail", "sport", "musique", "nourriture", "matin", "poisson", "riz", "manioc", "prière", "mosquée", "fête", "mariage", "soleil", "lagon"]
}

# Fonction pour récupérer une phrase via l’API Tatoeba
def get_french_sentence():
    api_url = 'https://tatoeba.org/en/api_v0/search?from=fra&to=none&query={}&sort=random'
    max_attempts = 10
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
        /* Hover effect for dialect buttons */
        div[data-testid="column"] button:hover {
            opacity: 0.8 !important;
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
          *Exemple* : *macacari* (enfant) au lieu de « matchatchari ».  
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
        label1 = "✅ Shingazidja" if st.session_state.selected_dialect == "Shingazidja" else "Shingazidja"
        if st.button(label1, key="shingazidja"):
            st.session_state.selected_dialect = "Shingazidja"
            st.rerun()
    with col2:
        label2 = "✅ Shindzouani" if st.session_state.selected_dialect == "Shindzouani" else "Shindzouani"
        if st.button(label2, key="shindzouani"):
            st.session_state.selected_dialect = "Shindzouani"
            st.rerun()
    with col3:
        label3 = "✅ Shimwali" if st.session_state.selected_dialect == "Shimwali" else "Shimwali"
        if st.button(label3, key="shimwali"):
            st.session_state.selected_dialect = "Shimwali"
            st.rerun()
    with col4:
        label4 = "✅ Shimaore" if st.session_state.selected_dialect == "Shimaore" else "Shimaore"
        if st.button(label4, key="shimaore"):
            st.session_state.selected_dialect = "Shimaore"
            st.rerun()

    # Injecter JavaScript pour styliser dynamiquement les boutons de dialecte selon leur texte
    components.html(
        """
        <script>
        function styleButtons() {
            const doc = window.parent.document;
            const buttons = Array.from(doc.querySelectorAll('div[data-testid="column"] button'));
            buttons.forEach(btn => {
                const text = btn.textContent || "";
                if (text.includes("Shingazidja")) {
                    btn.style.setProperty("background-color", "#87CEFA", "important");
                    btn.style.setProperty("color", "black", "important");
                    btn.style.setProperty("border", "none", "important");
                    btn.style.setProperty("border-radius", "5px", "important");
                    btn.style.setProperty("width", "100%", "important");
                } else if (text.includes("Shindzouani")) {
                    btn.style.setProperty("background-color", "#FF9999", "important");
                    btn.style.setProperty("color", "black", "important");
                    btn.style.setProperty("border", "none", "important");
                    btn.style.setProperty("border-radius", "5px", "important");
                    btn.style.setProperty("width", "100%", "important");
                } else if (text.includes("Shimwali")) {
                    btn.style.setProperty("background-color", "#FFFF99", "important");
                    btn.style.setProperty("color", "black", "important");
                    btn.style.setProperty("border", "none", "important");
                    btn.style.setProperty("border-radius", "5px", "important");
                    btn.style.setProperty("width", "100%", "important");
                } else if (text.includes("Shimaore")) {
                    btn.style.setProperty("background-color", "#FFFFFF", "important");
                    btn.style.setProperty("color", "black", "important");
                    btn.style.setProperty("border", "1px solid #ccc", "important");
                    btn.style.setProperty("border-radius", "5px", "important");
                    btn.style.setProperty("width", "100%", "important");
                }
            });
        }
        styleButtons();
        setTimeout(styleButtons, 100);
        setTimeout(styleButtons, 500);
        </script>
        """,
        height=0,
        width=0
    )

    # Afficher le dialecte sélectionné
    if st.session_state.selected_dialect:
        st.write(f"Dialecte sélectionné : **{st.session_state.selected_dialect}**")
    else:
        st.warning("Veuillez sélectionner un dialecte avant de traduire.")

    # Section traduction
    if 'french_sentence' not in st.session_state:
        st.session_state.french_sentence = get_french_sentence()

    text_area_key = f"translation_{st.session_state.french_sentence}"

    username = st.text_input("Entrez votre nom d'utilisateur (Optionnel)", key="username_input")
    st.write(f"Phrase en français : {st.session_state.french_sentence}")

    if st.button("Actualiser la phrase"):
        st.session_state.french_sentence = get_french_sentence()
        st.rerun()

    # Section enregistrement audio pour la traduction
    st.markdown("### 🎤 Dicter la traduction en comorien (Optionnel)")
    st.write("*(La transcription phonétique s'affichera dans le champ de texte, vous pourrez ensuite la corriger)*")
    
    transcription_engine = st.radio("Moteur de transcription :", ["Google (Rapide, tranches de 45s)", "Whisper (Local, très précis, sans limite de taille)"])

    lang_options = {
        "Swahili (Tanzanie) - sw-TZ": "sw-TZ",
        "Swahili (Kenya) - sw-KE": "sw-KE",
        "Zoulou (Afrique du Sud) - zu-ZA": "zu-ZA",
        "Français (France) - fr-FR": "fr-FR"
    }
    
    whisper_lang_map = {
        "sw-KE": "sw",
        "sw-TZ": "sw",
        "zu-ZA": "zu",
        "fr-FR": "fr"
    }

    selected_lang_label = st.selectbox("Choisissez une langue de base pour tester la transcription :", list(lang_options.keys()))
    base_lang_code = lang_options[selected_lang_label]

    audio_bytes = None

    tab1, tab2 = st.tabs(["🎤 Enregistrer", "📁 Charger un fichier audio"])
    
    with tab1:
        recorded_audio = audio_recorder(text="Cliquez pour enregistrer", recording_color="#e81c4f", neutral_color="#6aa36f", icon_name="microphone", icon_size="2x", key=f"audio_recorder_{st.session_state.french_sentence}")
        if recorded_audio:
            audio_bytes = recorded_audio

    with tab2:
        uploaded_file = st.file_uploader("Choisissez un fichier audio ou vidéo (formats supportés: WAV, FLAC, AIFF, MP3, MP4, M4A)", type=["wav", "flac", "aiff", "mp3", "mp4", "m4a"], key=f"file_uploader_{st.session_state.french_sentence}")
        if uploaded_file is not None:
            file_extension = uploaded_file.name.split('.')[-1].lower()
            try:
                # On utilise pydub pour charger le fichier, peu importe son format
                # Le format 'm4a' ou 'mp4' est géré par le lecteur ffmpeg sous-jacent
                audio_segment = AudioSegment.from_file(io.BytesIO(uploaded_file.read()))

                # Normaliser l'audio : 1 canal (mono) et 16000 Hz, idéal pour SpeechRecognition
                audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
                
                wav_io = io.BytesIO()
                audio_segment.export(wav_io, format="wav")
                audio_bytes = wav_io.getvalue()
            except Exception as e:
                st.error(f"Erreur lors de la préparation du fichier audio : {e}")
    
    # On re-transcrit si l'audio change OU si la langue change OU si le moteur change
    if audio_bytes:
        if (st.session_state.get('last_audio_bytes') != audio_bytes or 
            st.session_state.get('last_transcription_lang') != base_lang_code or
            st.session_state.get('last_transcription_engine') != transcription_engine):
            
            st.session_state.last_audio_bytes = audio_bytes
            st.session_state.last_transcription_lang = base_lang_code
            st.session_state.last_transcription_engine = transcription_engine
            
            # Transcription
            with st.spinner("Transcription en cours (cela peut prendre du temps avec Whisper)..."):
                try:
                    r = sr.Recognizer()
                    
                    if "Whisper" in transcription_engine:
                        st.info("💡 Premier lancement de Whisper : le téléchargement du modèle (140 Mo) se fait en arrière-plan...")
                        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                            audio_data = r.record(source)
                            whisper_lang = whisper_lang_map.get(base_lang_code, "sw")
                            transcribed_text = r.recognize_whisper(audio_data, language=whisper_lang, model="base")
                            st.session_state[text_area_key] = transcribed_text
                    else:
                        # Moteur GOOGLE avec découpage en tranches
                        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
                        audio_segment = audio_segment.set_channels(1).set_frame_rate(16000)
                        
                        chunk_length_ms = 45000 # 45 secondes
                        chunks = [audio_segment[i:i + chunk_length_ms] for i in range(0, len(audio_segment), chunk_length_ms)]
                        
                        full_text = []
                        progress_bar = st.progress(0)
                        
                        for i, chunk in enumerate(chunks):
                            wav_io = io.BytesIO()
                            chunk.export(wav_io, format="wav")
                            wav_io.seek(0)
                            
                            with sr.AudioFile(wav_io) as source:
                                audio_data = r.record(source)
                                try:
                                    text = r.recognize_google(audio_data, language=base_lang_code)
                                    full_text.append(text)
                                except sr.UnknownValueError:
                                    pass
                            
                            progress_bar.progress((i + 1) / len(chunks))
                            
                        progress_bar.empty()
                        
                        transcribed_text = " ".join(full_text)
                        if not transcribed_text.strip():
                            st.warning("L'audio n'a pas pu être compris ou ne contient que du silence.")
                        else:
                            st.session_state[text_area_key] = transcribed_text
                            
                except sr.RequestError as e:
                    st.error(f"Erreur du service de reconnaissance vocale : {e}")
                except Exception as e:
                    st.error(f"Erreur lors de la transcription : {e}")

    # Afficher l'audio enregistré pour que l'utilisateur puisse se réécouter
    if audio_bytes:
        st.audio(audio_bytes, format="audio/wav")

    # S'assurer que la clé existe pour éviter une erreur
    if text_area_key not in st.session_state:
        st.session_state[text_area_key] = ""

    comorian_translation = st.text_area("Fasiri shiKomori", key=text_area_key)

    if st.button('Soumettre'):
        if not comorian_translation:
            st.error("Veuillez entrer une traduction.")
        elif not st.session_state.selected_dialect:
            st.error("Veuillez sélectionner un dialecte.")
        else:
            final_username = username if username.strip() else "Anonyme"
            save_to_mongo(st.session_state.french_sentence, comorian_translation, final_username, st.session_state.selected_dialect)
            st.success("Traduction soumise avec succès !")
            st.session_state.french_sentence = get_french_sentence()
            st.session_state.selected_dialect = None
            if text_area_key in st.session_state:
                st.session_state[text_area_key] = ""
            if 'last_audio_bytes' in st.session_state:
                del st.session_state['last_audio_bytes']
            st.rerun()

if __name__ == '__main__':
    main()