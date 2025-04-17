import streamlit as st
import random
import requests
import json

# Fonction pour récupérer une phrase aléatoire en français depuis l'API Tatoeba
def get_french_sentence():
    api_url = 'https://tatoeba.org/en/api_v0/search?from=fra&sort=random&limit=1&tags=francais'
    response = requests.get(api_url)
    
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            return data['results'][0]['text']  # Retourne la phrase aléatoire
    return "Erreur: Impossible de récupérer une phrase."

# Fonction pour sauvegarder les traductions dans un fichier JSON
def save_data(french_sentence, comorian_translation):
    data = []

    # Vérifie si le fichier existe déjà
    try:
        with open('translations.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
    except FileNotFoundError:
        pass

    # Ajoute la nouvelle traduction
    data.append({
        'french_sentence': french_sentence,
        'comorian_translation': comorian_translation
    })

    # Sauvegarde les données dans le fichier
    with open('translations.json', 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Interface utilisateur Streamlit
def main():
    # Titre
    st.title('Application de traduction en Comorien')

    # Obtenir une phrase aléatoire en français
    french_sentence = get_french_sentence()

    # Afficher la phrase en français
    st.write(f"Phrase en français : {french_sentence}")

    # Zone pour entrer la traduction en comorien
    comorian_translation = st.text_area("Votre traduction en comorien", "")

    # Bouton pour soumettre la traduction
    if st.button('Soumettre'):
        if comorian_translation:
            # Sauvegarder la traduction et la phrase
            save_data(french_sentence, comorian_translation)
            st.success("Traduction soumise avec succès!")
        else:
            st.error("Veuillez entrer une traduction.")

if __name__ == '__main__':
    main()
