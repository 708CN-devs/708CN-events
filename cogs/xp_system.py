import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import logging
import os
from pymongo import MongoClient
from datetime import datetime, timedelta
import math

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Définition des limites d'XP pour chaque type d'interaction
XP_LIMITS = {
    "message": {"min": 5, "max": 15},  # XP pour les messages
    "vocal": {"min": 10, "max": 20},   # XP pour les salons vocaux
    "reaction": {"min": 2, "max": 8}, # XP pour les réactions
}

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
        
        # Dictionnaire pour suivre les timers des salons vocaux
        self.vocal_timers = {}
        # Dictionnaire pour limiter les gains d'XP par message ou réaction
        self.last_message_xp = {}
        self.reaction_tracking = {}

    def get_user_data(self, user_id):
        """Récupère les données d'XP et de niveau d'un utilisateur depuis MongoDB."""
        try:
            user_data = self.collection.find_one({"user_id": user_id})
            if not user_data:
                user_data = {"user_id": user_id, "xp": 0, "level": 1}
                self.collection.insert_one(user_data)
                logging.info(f"Création de données pour l'utilisateur {user_id}.")
            return user_data
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des données d'utilisateur : {e}")
            return {"user_id": user_id, "xp": 0, "level": 1}

    def update_user_data(self, user_id, xp_amount, source):
        """Mise à jour des données d'XP et de niveau d'un utilisateur."""
        try:
            user_data = self.get_user_data(user_id)
            new_xp = user_data["xp"] + xp_amount
            new_level = self.calculate_level(new_xp)

            # Mise à jour des données d'XP et de niveau
            self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"xp": new_xp, "level": new_level}},
                upsert=True
            )
            logging.info(f"Ajout de {xp_amount} XP pour l'utilisateur {user_id} (source : {source}). Nouveau niveau : {new_level}.")
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour des données d'XP : {e}")

    def calculate_level(self, xp):
        """Calcule le niveau d'un utilisateur en fonction de son XP."""
        # Exemple ajusté : augmenter le taux en utilisant un exposant légèrement inférieur à 0.5
        level = math.floor(0.5 * xp ** 0.6)  # Ajuster ici le diviseur et l'exposant
        return level

    @commands.Cog.listener()
    async def on_message(self, message):
        """Ajoute de l'XP lorsqu'un utilisateur envoie un message."""
        if message.author.bot:
            return
        
        user_id = str(message.author.id)
        now = datetime.utcnow()

        # Ajout d'un délai minimum entre les gains d'XP pour les messages
        if user_id in self.last_message_xp and now - self.last_message_xp[user_id] < timedelta(seconds=60):
            return
        
        self.last_message_xp[user_id] = now
        xp_gained = random.randint(XP_LIMITS["message"]["min"], XP_LIMITS["message"]["max"])
        self.update_user_data(user_id, xp_gained, source="Message")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Ajoute de l'XP lorsqu'un utilisateur réagit à un message."""
        if user.bot:
            return
        
        message_id = str(reaction.message.id)
        user_id = str(user.id)

        # Empêcher de gagner de l'XP plusieurs fois pour la même réaction/message
        if message_id in self.reaction_tracking and user_id in self.reaction_tracking[message_id]:
            return
        
        if message_id not in self.reaction_tracking:
            self.reaction_tracking[message_id] = set()

        self.reaction_tracking[message_id].add(user_id)
        xp_gained = random.randint(XP_LIMITS["reaction"]["min"], XP_LIMITS["reaction"]["max"])
        self.update_user_data(user_id, xp_gained, source="Réaction")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Ajoute de l'XP lorsqu'un utilisateur est actif dans un salon vocal."""
        user_id = str(member.id)
        if member.bot:
            return

        # Si l'utilisateur rejoint un salon vocal
        if after.channel and not before.channel:
            if user_id not in self.vocal_timers:
                # Démarrer un timer pour cet utilisateur
                self.vocal_timers[user_id] = self.start_vocal_timer(member)

        # Si l'utilisateur quitte le salon vocal
        elif not after.channel and before.channel:
            if user_id in self.vocal_timers:
                # Annuler le timer de cet utilisateur
                self.vocal_timers[user_id].cancel()
                del self.vocal_timers[user_id]

    def start_vocal_timer(self, member):
        """Démarre un timer pour ajouter de l'XP toutes les minutes."""
        async def add_vocal_xp():
            while True:
                await discord.utils.sleep_until(datetime.utcnow() + timedelta(seconds=60))
                if not member.voice or not member.voice.channel:  # Vérifie si l'utilisateur est encore en vocal
                    break
                xp_gained = random.randint(XP_LIMITS["vocal"]["min"], XP_LIMITS["vocal"]["max"])
                self.update_user_data(str(member.id), xp_gained, source="Vocal")

        return self.bot.loop.create_task(add_vocal_xp())

    @app_commands.command(name="xp", description="Affiche l'XP et le niveau d'un utilisateur.")
    async def check_xp(self, interaction: discord.Interaction, user: discord.Member = None):
        """Commande slash pour vérifier l'XP et le niveau d'un utilisateur."""
        try:
            # Préviens Discord que la réponse est différée si nécessaire
            await interaction.response.defer(ephemeral=True)

            target_user = user if user else interaction.user
            user_id = str(target_user.id)
            user_data = self.get_user_data(user_id)
            xp = user_data.get("xp", 0)
            level = user_data.get("level", 1)

            # Envoie la réponse finale
            if user:
                await interaction.followup.send(
                    f"L'XP de {target_user.mention} : **{xp} XP** et il est niveau **{level}** !"
                )
            else:
                await interaction.followup.send(
                    f"{interaction.user.mention}, tu as actuellement **{xp} XP** et tu es niveau **{level}** !"
                )
        except discord.errors.NotFound:
            logging.error("L'interaction n'est plus valide ou a expiré.")
        except Exception as e:
            logging.error(f"Erreur lors du traitement de la commande /xp : {e}")

    @app_commands.command(name="xp-add", description="Ajoute de l'XP à un utilisateur.")
    @app_commands.describe(user="L'utilisateur à modifier.", xp_amount="Montant d'XP à ajouter.")
    async def add_xp(self, interaction: discord.Interaction, user: discord.Member, xp_amount: int):
        """Ajoute de l'XP à un utilisateur."""
        try:
            self.update_user_data(
                str(user.id), 
                xp_amount, 
                source=f"Manuel (par {interaction.user.display_name})"
            )
            await interaction.response.send_message(
                f"Ajout de {xp_amount} XP à {user.mention} (par {interaction.user.mention}).", ephemeral=True
            )
        except Exception as e:
            logging.error(f"Erreur lors de l'ajout d'XP : {e}")
            await interaction.response.send_message("Une erreur est survenue lors de l'ajout d'XP.", ephemeral=True)

    @app_commands.command(name="xp-remove", description="Retire de l'XP à un utilisateur.")
    @app_commands.describe(user="L'utilisateur à modifier.", xp_amount="Montant d'XP à retirer.")
    async def remove_xp(self, interaction: discord.Interaction, user: discord.Member, xp_amount: int):
        """Retire de l'XP à un utilisateur."""
        try:
            self.update_user_data(
                str(user.id), 
                -xp_amount, 
                source=f"Manuel (par {interaction.user.display_name})"
            )
            await interaction.response.send_message(
                f"Retrait de {xp_amount} XP à {user.mention} (par {interaction.user.mention}).", ephemeral=True
            )
        except Exception as e:
            logging.error(f"Erreur lors du retrait d'XP : {e}")
            await interaction.response.send_message("Une erreur est survenue lors du retrait d'XP.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
