import discord
from discord import app_commands
from discord.ext import commands
import random
import logging
import os
from pymongo import MongoClient

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Utilisation d'une variable d'environnement pour sécuriser l'URI MongoDB
        self.mongo_uri = os.getenv("MONGO_URI")
        if not self.mongo_uri:
            logging.error("Erreur : URI MongoDB non configurée dans les variables d'environnement.")
            raise ValueError("La variable d'environnement MONGO_URI est obligatoire.")
        
        try:
            self.client = MongoClient(self.mongo_uri)
            self.db = self.client["discord_bot"]
            self.collection = self.db["xp_data"]
            logging.info("Connexion à MongoDB réussie.")
        except Exception as e:
            logging.error(f"Erreur lors de la connexion à MongoDB : {e}")
            raise

    def get_user_data(self, user_id):
        """Récupère les données d'XP d'un utilisateur depuis MongoDB."""
        try:
            user_data = self.collection.find_one({"user_id": user_id})
            if not user_data:
                user_data = {"user_id": user_id, "xp": 0}
                self.collection.insert_one(user_data)
                logging.info(f"Création de données pour l'utilisateur {user_id}.")
            return user_data
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des données d'utilisateur : {e}")
            return {"user_id": user_id, "xp": 0}

    def update_user_data(self, user_id, xp_amount):
        """Mise à jour des données d'XP d'un utilisateur."""
        try:
            self.collection.update_one(
                {"user_id": user_id},
                {"$inc": {"xp": xp_amount}},
                upsert=True
            )
            logging.info(f"Ajout de {xp_amount} XP pour l'utilisateur {user_id}.")
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour des données d'XP : {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Ajoute de l'XP lorsqu'un utilisateur envoie un message."""
        if message.author.bot:
            return
        xp_gained = random.randint(5, 15)
        self.update_user_data(str(message.author.id), xp_gained)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Ajoute de l'XP lorsqu'un utilisateur réagit à un message."""
        if user.bot:
            return
        xp_gained = random.randint(2, 10)
        self.update_user_data(str(user.id), xp_gained)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Ajoute de l'XP lorsqu'un utilisateur est actif dans un salon vocal."""
        if member.bot:
            return
        if after.channel and not before.channel:
            xp_gained = random.randint(10, 20)
            self.update_user_data(str(member.id), xp_gained)

    @app_commands.command(name="xp", description="Affiche ton XP actuel.")
    async def check_xp(self, interaction: discord.Interaction):
        """Commande slash pour vérifier son propre XP."""
        user_id = str(interaction.user.id)
        user_data = self.get_user_data(user_id)
        xp = user_data.get("xp", 0)
        await interaction.response.send_message(
            f"{interaction.user.mention}, tu as actuellement **{xp} XP** !",
            ephemeral=True
        )

    def cog_unload(self):
        """Appelé lors du déchargement du cog."""
        try:
            self.client.close()
            logging.info("Connexion MongoDB fermée.")
        except Exception as e:
            logging.error(f"Erreur lors de la fermeture de MongoDB : {e}")

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
