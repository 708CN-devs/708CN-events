import discord
from discord.ext import commands
from discord import app_commands
from pymongo import MongoClient
import os
import logging

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Events(commands.Cog):
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
            self.events_collection = self.db["events"]
            self.participation_collection = self.db["participations"]
            logging.info("Connexion à MongoDB réussie.")
        except Exception as e:
            logging.error(f"Erreur lors de la connexion à MongoDB : {e}")
            raise
    
    @app_commands.command(name="event-add", description="Ajoute un nouvel événement organisé.")
    @app_commands.checks.has_permissions(administrator=True)
    async def event_add(self, interaction: discord.Interaction, event_name: str):
        if self.events_collection.find_one({"name": event_name}):
            await interaction.response.send_message(f"⚠️ L'événement **{event_name}** existe déjà !", ephemeral=True)
            return
        
        self.events_collection.insert_one({"name": event_name})
        await interaction.response.send_message(f"✅ L'événement **{event_name}** a été ajouté !", ephemeral=True)
    
    @app_commands.command(name="event-remove", description="Supprime un événement existant.")
    @app_commands.checks.has_permissions(administrator=True)
    async def event_remove(self, interaction: discord.Interaction, event_name: str):
        event = self.events_collection.find_one({"name": event_name})
        if not event:
            await interaction.response.send_message(f"⚠️ L'événement **{event_name}** n'existe pas !", ephemeral=True)
            return
        
        self.events_collection.delete_one({"name": event_name})
        self.participation_collection.delete_many({"event": event_name})
        await interaction.response.send_message(f"✅ L'événement **{event_name}** a été supprimé !", ephemeral=True)
    
    @app_commands.command(name="event-define", description="Ajoute ou retire un utilisateur d'un événement.")
    @app_commands.checks.has_permissions(administrator=True)
    async def event_define(self, interaction: discord.Interaction, user: discord.Member, event_name: str):
        event = self.events_collection.find_one({"name": event_name})
        if not event:
            await interaction.response.send_message(f"⚠️ L'événement **{event_name}** n'existe pas !", ephemeral=True)
            return
        
        user_id = str(user.id)
        participation = self.participation_collection.find_one({"user_id": user_id, "event": event_name})
        
        if participation:
            self.participation_collection.delete_one({"user_id": user_id, "event": event_name})
            action = "retiré de"
        else:
            self.participation_collection.insert_one({"user_id": user_id, "event": event_name})
            action = "ajouté à"
        
        await interaction.response.send_message(f"✅ {user.mention} a été {action} l'événement **{event_name}** !", ephemeral=True)
    
    @app_commands.command(name="events", description="Affiche la liste des événements auxquels un utilisateur a participé.")
    async def events(self, interaction: discord.Interaction, user: discord.Member = None):
        user = user or interaction.user
        user_id = str(user.id)
        participations = self.participation_collection.find({"user_id": user_id})
        event_list = [p["event"] for p in participations]
        
        if not event_list:
            message = f"{user.mention} n'a participé à aucun événement."
        else:
            message = f"{user.mention} a participé aux événements suivants :\n- " + "\n- ".join(event_list)
        
        await interaction.response.send_message(message, ephemeral=False)
    
    @event_define.autocomplete("event_name")
    @event_remove.autocomplete("event_name")
    async def event_autocomplete(self, interaction: discord.Interaction, current: str):
        events = self.events_collection.find({"name": {"$regex": f"^{current}", "$options": "i"}})
        return [app_commands.Choice(name=event["name"], value=event["name"]) for event in events][:25]
    
async def setup(bot):
    await bot.add_cog(Events(bot))
