import streamlit as st
from pymongo import MongoClient

MONGO_URI = st.secrets.get("MONGO_URI")
# Connexion à MongoDB
client = MongoClient(MONGO_URI)
db = client["Cluster0"]
collection = db["translations"]

# Interface Streamlit
st.title("Application MongoDB avec Streamlit")

# Afficher les bases de données
if st.button("Lister les bases de données"):
    dbs = client.list_database_names()
    st.write("Bases de données disponibles :", dbs)

# Formulaire pour insérer un document
with st.form("insert_form"):
    test_value = st.text_input("Valeur à insérer", "connexion réussie")
    submit = st.form_submit_button("Insérer dans MongoDB")
    if submit:
        collection.insert_one({"test": test_value})
        st.success("Insertion réussie !")
