import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
import os
import logging
import re

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Liste des mots gênants et des points attribués
GENANCE_WORDS = {
    "feur": 5,
    "quoicoubeh": 10,
    "apagnan": 5,
}

class GenanceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Connexion à MongoDB
        self.mongo_uri = os.getenv("MONGO_URI")
        if not self.mongo_uri:
            logging.error("Erreur : URI MongoDB non configurée dans les variables d'environnement.")
            raise ValueError("La variable d'environnement MONGO_URI est obligatoire.")
        
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client["discord_bot"]
            self.collection = self.db["genance_data"]
            logging.info("Connexion à MongoDB réussie.")
        except Exception as e:
            logging.error(f"Erreur lors de la connexion à MongoDB : {e}")
            raise

    def get_user_data(self, user_id):
        """Récupère les données de gênance d'un utilisateur depuis MongoDB."""
        try:
            user_data = self.collection.find_one({"user_id": user_id})
            if not user_data:
                user_data = {"user_id": user_id, "genance_points": 0}
                self.collection.insert_one(user_data)
                logging.info(f"Création de données de gênance pour l'utilisateur {user_id}.")
            return user_data
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des données d'utilisateur : {e}")
            return {"user_id": user_id, "genance_points": 0}

    def update_user_data(self, user_id, points, word):
        """Mise à jour des points de gênance d'un utilisateur."""
        try:
            user_data = self.get_user_data(user_id)
            new_points = user_data["genance_points"] + points
            self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"genance_points": new_points}},
                upsert=True
            )
            logging.info(f"Ajout de {points} points de gênance à l'utilisateur {user_id} pour le mot '{word}'. Total : {new_points}")
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour des points de gênance : {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Ajoute des points de gênance lorsqu'un mot gênant est détecté."""
        if message.author.bot:
            return

        logging.info(f"Message gênant reçu de {message.author}: {message.content}")
        user_id = str(message.author.id)
        content = message.content.lower()

        for word, points in GENANCE_WORDS.items():
            # Recherche du mot exact avec regex pour éviter les faux positifs
            if re.search(rf"\b{re.escape(word)}\b", content):
                self.update_user_data(user_id, points, word)
                response = f"😬 {message.author.mention}, +{points} point(s) de gênance pour avoir dit **{word}** !"
                await message.channel.send(response)
                break  # Arrêter après le premier mot gênant détecté

    @app_commands.command(name="genance", description="Consulte les points de gênance d'un utilisateur.")
    async def genance(self, interaction: discord.Interaction, member: discord.Member = None):
        """Affiche les points de gênance d'un utilisateur via une commande slash."""
        member = member or interaction.user
        user_id = str(member.id)
        user_data = self.get_user_data(user_id)
        points = user_data["genance_points"]
        await interaction.response.send_message(
            f"😬 {member.mention} a accumulé **{points}** point(s) de gênance.",
            ephemeral=True  # Message visible uniquement par l'utilisateur qui a exécuté la commande
        )

async def setup(bot):
    await bot.add_cog(GenanceSystem(bot))
