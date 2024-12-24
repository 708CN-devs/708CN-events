import discord
from discord.ext import commands
from discord import app_commands
import json

class BugReport(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.report_channel_id = None
        self.load_report_channel()

    def load_report_channel(self):
        """Charge l'ID du salon de rapport depuis un fichier JSON."""
        try:
            with open("report_channel.json", "r") as f:
                data = json.load(f)
                self.report_channel_id = data.get("channel_id")
        except FileNotFoundError:
            self.report_channel_id = None

    def save_report_channel(self, channel_id):
        """Sauvegarde l'ID du salon de rapport dans un fichier JSON."""
        with open("report_channel.json", "w") as f:
            json.dump({"channel_id": channel_id}, f)

    @app_commands.command(name="report-bug-channel", description="Définir le salon pour les rapports de bugs.")
    async def set_report_channel(self, interaction: discord.Interaction, id: str):
        """Définit l'ID du salon où les rapports de bugs seront envoyés."""
        try:
            channel = self.bot.get_channel(int(id))
            if not channel:
                await interaction.response.send_message("Salon introuvable. Vérifiez l'ID.", ephemeral=True)
                return

            self.save_report_channel(channel.id)
            self.report_channel_id = channel.id
            await interaction.response.send_message(f"Salon défini pour les rapports de bugs : {channel.mention}", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("ID de salon invalide.", ephemeral=True)

    @app_commands.command(name="report-bug", description="Signaler un bug.")
    async def report_bug(self, interaction: discord.Interaction, bug_name: str):
        """Ouvre une modal pour signaler un bug."""
        if not self.report_channel_id:
            await interaction.response.send_message(
                "Le salon de rapport de bugs n'a pas été défini. Utilisez `/report-bug-channel id:` pour le définir.",
                ephemeral=True,
            )
            return

        class BugReportModal(discord.ui.Modal, title=f"Signaler un bug: {bug_name}"):
            bug_type = discord.ui.TextInput(
                label="Type de bug",
                placeholder="Ex: Lobby, Mini-jeu, Hub, ...",
                style=discord.TextStyle.short,
                required=True,
            )
            reproduction_steps = discord.ui.TextInput(
                label="Comment réaliser ce bug",
                placeholder="Décrire étape par étape comment reproduire le bug.",
                style=discord.TextStyle.paragraph,
                required=True,
            )
            detailed_description = discord.ui.TextInput(
                label="Description détaillée",
                placeholder="Ajoutez toutes les informations pertinentes concernant ce bug.",
                style=discord.TextStyle.paragraph,
                required=True,
            )

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    # Envoi dans le salon de rapport
                    channel = self.bot.get_channel(self.bot.get_cog("BugReport").report_channel_id)
                    if not channel:
                        await interaction.response.send_message("Salon de rapport introuvable.", ephemeral=True)
                        return

                    embed = discord.Embed(
                        title=f"Rapport de bug: {bug_name}",
                        color=discord.Color.red(),
                    )
                    embed.add_field(name="Type de bug", value=self.bug_type.value, inline=False)
                    embed.add_field(name="Comment réaliser ce bug", value=self.reproduction_steps.value, inline=False)
                    embed.add_field(name="Description détaillée", value=self.detailed_description.value, inline=False)
                    embed.set_footer(text=f"Signalé par {interaction.user} ({interaction.user.id})")

                    await channel.send(embed=embed)
                    await interaction.response.send_message("Rapport envoyé avec succès !", ephemeral=True)

                except discord.HTTPException as e:
                    await interaction.response.send_message(
                        f"Erreur lors de l'envoi du rapport : {e}", ephemeral=True
                    )

        await interaction.response.send_modal(BugReportModal())

async def setup(bot):
    await bot.add_cog(BugReport(bot))
