from discord.ext import commands
from discord import app_commands

class Rename(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rename", description="Renommer un message du bot en spécifiant l'ID du message.")
    async def rename(self, interaction: discord.Interaction, message_id: str):
        """Command to rename a bot's message by its ID."""
        try:
            # Récupérer le message à partir de l'ID
            channel = interaction.channel
            if not channel:
                await interaction.response.send_message("Impossible de trouver le canal.", ephemeral=True)
                return

            message = await channel.fetch_message(int(message_id))
            if message.author.id != self.bot.user.id:
                await interaction.response.send_message(
                    "Ce message n'a pas été envoyé par le bot.", ephemeral=True
                )
                return

            # Afficher le modal pour renommer
            class RenameModal(discord.ui.Modal, title="Renommer un message"):
                new_content = discord.ui.TextInput(
                    label="Nouveau contenu",
                    style=discord.TextStyle.paragraph,
                    default=message.content,
                    required=True,
                )

                async def on_submit(self, interaction: discord.Interaction):
                    try:
                        # Modifier le message avec le nouveau contenu
                        await message.edit(content=self.new_content.value)
                        await interaction.response.send_message(
                            "Message renommé avec succès !", ephemeral=True
                        )
                    except discord.HTTPException as e:
                        await interaction.response.send_message(
                            f"Erreur lors de la modification du message : {e}", ephemeral=True
                        )

            await interaction.response.send_modal(RenameModal())

        except discord.NotFound:
            await interaction.response.send_message("Message introuvable.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(
                "Je n'ai pas la permission de modifier ce message.", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Erreur lors de la récupération du message : {e}", ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Rename(bot))
