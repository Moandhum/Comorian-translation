from pymongo import MongoClient
client = MongoClient("mongodb+srv://moandhum:Mybdd02@cluster0.0kzbcne.mongodb.net/Cluster0?retryWrites=true&w=majority")
db = client["Cluster0"]
collection = db["translations"]
print(client.list_database_names())
collection.insert_one({"test": "connexion réussie"})
print("Insertion réussie")