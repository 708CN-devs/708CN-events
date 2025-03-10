import discord
from discord.ext import commands, tasks
from discord import app_commands
from pymongo import MongoClient
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
        class AbsenceView(discord.ui.View):
            def __init__(self, user):
                super().__init__()
                self.user = user
                self.start_date = None
                self.end_date = None
                self.reason = None

            @discord.ui.button(label="📅 Définir Date de Début", style=discord.ButtonStyle.primary)
            async def set_start_date(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message("🗓️ Sélectionnez votre date de début via le menu déroulant.", ephemeral=True)

            @discord.ui.button(label="📅 Définir Date de Fin", style=discord.ButtonStyle.primary)
            async def set_end_date(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message("🗓️ Sélectionnez votre date de fin via le menu déroulant.", ephemeral=True)

            @discord.ui.button(label="✏️ Saisir Raison", style=discord.ButtonStyle.secondary)
            async def set_reason(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_message("✍️ Veuillez entrer la raison de votre absence.", ephemeral=True)

            @discord.ui.button(label="✅ Confirmer", style=discord.ButtonStyle.success)
            async def confirm_absence(self, interaction: discord.Interaction, button: discord.ui.Button):
                if not self.start_date or not self.end_date or not self.reason:
                    await interaction.response.send_message("⚠️ Merci de remplir tous les champs avant de confirmer.", ephemeral=True)
                    return
                duration = (self.end_date - self.start_date).days
                channel_data = interaction.client.get_cog("AbsenceSystem").channel_collection.find_one({})
                if not channel_data:
                    await interaction.response.send_message("⚠️ Aucun salon d'absence défini.", ephemeral=True)
                    return
                channel = interaction.guild.get_channel(channel_data["channel_id"])
                message = await channel.send(f"**Absence de:** {self.user.mention}\n**Durée:** {duration} jours ({self.start_date.date()} - {self.end_date.date()})\n**Raison:** {self.reason}")
                interaction.client.get_cog("AbsenceSystem").absence_collection.insert_one({"user_id": self.user.id, "start": self.start_date, "end": self.end_date, "message_id": message.id})
                await interaction.response.send_message("✅ Absence enregistrée avec succès !", ephemeral=True)
        
        await interaction.response.send_message("Déclaration d'absence : veuillez sélectionner les informations.", view=AbsenceView(interaction.user), ephemeral=True)
    
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