import discord
from discord import app_commands
from discord.ext import commands
import asyncio

class SunGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="soleil", description="Joue à 1, 2, 3, SOLEIL!")
    async def soleil(self, interaction: discord.Interaction):
        """
        Commande /soleil : Affiche un compte à rebours avec l'édition du message.
        """
        await interaction.response.send_message("Préparez-vous... 🌞", ephemeral=False)

        # Récupère le message envoyé en réponse
        message = await interaction.original_response()

        # Étapes du compte à rebours
        steps = ["1", "2", "3", "🌞 SOLEIL ! 🌞"]

        for step in steps:
            await asyncio.sleep(1)  # Pause de 1 seconde entre chaque étape
            await message.edit(content=step)

async def setup(bot):
    await bot.add_cog(SunGame(bot))
