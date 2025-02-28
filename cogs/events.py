import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient #type: ignore
import os
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ID de l'utilisateur autorisé (à remplacer par ton ID Discord)
OWNER_ID = 463639826361614336  # Remplace par ton ID

class EventsSystem(commands.Cog):
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
            self.events_collection = self.db["events"]  # Stocke les événements
            self.participants_collection = self.db["event_participants"]  # Stocke les participations
            logging.info("Connexion à MongoDB réussie.")
        except Exception as e:
            logging.error(f"Erreur lors de la connexion à MongoDB : {e}")
            raise
    
    @app_commands.command(name="event-add", description="Ajoute un nouvel événement organisé.")
    async def event_add(self, interaction: discord.Interaction, event_name: str):
        """Ajoute un événement dans la base de données."""
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("⛔ Seul l'administrateur peut utiliser cette commande !", ephemeral=True)
            return
        
        if self.events_collection.find_one({"name": event_name}):
            await interaction.response.send_message("⚠️ Cet événement existe déjà !", ephemeral=True)
            return
        
        self.events_collection.insert_one({"name": event_name})
        await interaction.response.send_message(f"✅ Événement **{event_name}** ajouté avec succès !", ephemeral=True)

    @app_commands.command(name="event-define", description="Ajoute ou retire un utilisateur d'un événement existant.")
    async def event_define(self, interaction: discord.Interaction, user: discord.Member, event_name: str):
        """Ajoute ou retire un utilisateur d'un événement."""
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("⛔ Seul l'administrateur peut utiliser cette commande !", ephemeral=True)
            return
        
        if not self.events_collection.find_one({"name": event_name}):
            await interaction.response.send_message("⚠️ Cet événement n'existe pas !", ephemeral=True)
            return
        
        user_id = str(user.id)
        existing_participation = self.participants_collection.find_one({"user_id": user_id, "event_name": event_name})
        
        if existing_participation:
            self.participants_collection.delete_one({"user_id": user_id, "event_name": event_name})
            await interaction.response.send_message(f"❌ {user.mention} a été retiré de l'événement **{event_name}**.", ephemeral=True)
        else:
            self.participants_collection.insert_one({"user_id": user_id, "event_name": event_name})
            await interaction.response.send_message(f"✅ {user.mention} a été ajouté à l'événement **{event_name}**.", ephemeral=True)
    
    @app_commands.command(name="events", description="Affiche la liste des événements auxquels un utilisateur a participé.")
    async def events(self, interaction: discord.Interaction, member: discord.Member = None):
        """Affiche la liste des événements d'un utilisateur."""
        member = member or interaction.user
        user_id = str(member.id)
        
        events = self.participants_collection.find({"user_id": user_id})
        event_names = [event["event_name"] for event in events]
        
        if event_names:
            event_list = "\n".join(f"- {name}" for name in event_names)
            await interaction.response.send_message(f"📜 **Événements de {member.mention}**:\n{event_list}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {member.mention} n'a participé à aucun événement.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EventsSystem(bot))
