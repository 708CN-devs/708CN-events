import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient #type:ignore
import os
from datetime import datetime, timedelta

OWNER_ID = 463639826361614336

class AbsenceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_uri = os.getenv("MONGO_URI")
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client["discord_bot"]
        self.absence_collection = self.db["absences"]
        self.channel_collection = self.db["absence_channel"]
        self.check_absences.start()
    
    @app_commands.command(name="absence-channel", description="Définit le salon où seront envoyées les absences.")
    async def set_absence_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if interaction.user.guild_permissions.administrator or interaction.user.id == OWNER_ID:
            self.channel_collection.update_one({}, {"$set": {"channel_id": channel.id}}, upsert=True)
            await interaction.response.send_message(f"✅ Salon des absences défini sur {channel.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message("⛔ Seuls les administrateurs peuvent utiliser cette commande.", ephemeral=True)
    
    @app_commands.command(name="absence", description="Déclare une absence.")
    async def absence(self, interaction: discord.Interaction):
        today = datetime.now()
        default_start_date = today.strftime("%d-%m-%Y")
        default_end_date = today.strftime("%d-%m-") + str(today.year)

        class AbsenceModal(discord.ui.Modal, title="Déclarer une absence"):
            start_date = discord.ui.TextInput(label="Date de début (JJ-MM-AAAA)", default=default_start_date)
            end_date = discord.ui.TextInput(label="Date de fin (JJ-MM-AAAA)", default=default_end_date)
            reason = discord.ui.TextInput(label="Raison", style=discord.TextStyle.long)
            
            async def on_submit(self, interaction: discord.Interaction):
                try:
                    start = datetime.strptime(self.start_date.value, "%d-%m-%Y")
                    end = datetime.strptime(self.end_date.value, "%d-%m-%Y")
                    if end < start:
                        await interaction.response.send_message("⚠️ La date de fin doit être après la date de début !", ephemeral=True)
                        return
                    duration = (end - start).days
                    channel_data = interaction.client.get_cog("AbsenceSystem").channel_collection.find_one({})
                    if not channel_data:
                        await interaction.response.send_message("⚠️ Aucun salon d'absence défini.", ephemeral=True)
                        return
                    channel = interaction.guild.get_channel(channel_data["channel_id"])
                    message = await channel.send(f"**Absence de:** {interaction.user.mention}\n**Durée:** {duration} jours ({start.date()} - {end.date()})\n**Raison:** {self.reason.value}")
                    interaction.client.get_cog("AbsenceSystem").absence_collection.insert_one({"user_id": interaction.user.id, "start": start, "end": end, "message_id": message.id})
                    await interaction.response.send_message("✅ Absence enregistrée avec succès !", ephemeral=True)
                except ValueError:
                    await interaction.response.send_message("⚠️ Format de date invalide. Utilisez JJ-MM-AAAA.", ephemeral=True)
        
        await interaction.response.send_modal(AbsenceModal())
    
    @app_commands.command(name="absence-remove", description="Supprime une absence enregistrée.")
    async def remove_absence(self, interaction: discord.Interaction, user: discord.Member = None):
        if user and (interaction.user.id == OWNER_ID or interaction.user.guild_permissions.administrator):
            query_user = user.id
        else:
            query_user = interaction.user.id
        absence = self.absence_collection.find_one({"user_id": query_user})
        if absence:
            self.absence_collection.delete_one({"user_id": query_user})
            await interaction.response.send_message(f"✅ Absence de {user.mention if user else interaction.user.mention} supprimée.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Aucune absence trouvée.", ephemeral=True)
    
    @tasks.loop(minutes=60)
    async def check_absences(self):
        now = datetime.now()
        expired_absences = self.absence_collection.find({"end": {"$lte": now}})
        for absence in expired_absences:
            guild = self.bot.get_guild(absence["guild_id"])
            channel_data = self.channel_collection.find_one({})
            if channel_data:
                channel = guild.get_channel(channel_data["channel_id"])
                try:
                    message = await channel.fetch_message(absence["message_id"])
                    await message.delete()
                except discord.NotFound:
                    pass
                user = guild.get_member(absence["user_id"])
                if user:
                    reminder_msg = await channel.send(f"{user.mention} ton absence est terminée ! Confirme ton retour avec ✅ ou ❌.")
                    await reminder_msg.add_reaction("✅")
                    await reminder_msg.add_reaction("❌")
            self.absence_collection.delete_one({"_id": absence["_id"]})

    @check_absences.before_loop
    async def before_check_absences(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AbsenceSystem(bot))
