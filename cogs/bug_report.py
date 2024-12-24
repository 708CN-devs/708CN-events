import discord
from discord.ext import commands
from discord import app_commands

class BugReport(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.report_channel_id = 1321162840299540490  # ID de salon persistant

    @app_commands.command(name="report-bug", description="Signaler un bug.")
    @app_commands.describe(bug_name="Nom du bug en quelques mots (exemple : Problème de connexion, Erreur en lobby, etc.)")
    async def report_bug(self, interaction: discord.Interaction, bug_name: str):
        """Ouvre une modal pour signaler un bug."""
        class BugReportModal(discord.ui.Modal, title=f"Signaler un bug: {bug_name}"):
            def __init__(self, cog, bug_name):
                super().__init__()
                self.cog = cog
                self.bug_name = bug_name

                # Champs de la modal
                self.bug_type = discord.ui.TextInput(
                    label="Type de bug",
                    placeholder="Ex: Lobby, Mini-jeu, Hub, ...",
                    style=discord.TextStyle.short,
                    required=True,
                )
                self.reproduction_steps = discord.ui.TextInput(
                    label="Comment réaliser ce bug",
                    placeholder="Décrire étape par étape comment reproduire le bug.",
                    style=discord.TextStyle.paragraph,
                    required=True,
                )
                self.detailed_description = discord.ui.TextInput(
                    label="Description détaillée",
                    placeholder="Ajoutez toutes les informations pertinentes concernant ce bug.",
                    style=discord.TextStyle.paragraph,
                    required=True,
                )

                # Ajout des champs à la modal
                self.add_item(self.bug_type)
                self.add_item(self.reproduction_steps)
                self.add_item(self.detailed_description)

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    # Envoi dans le salon de rapport
                    channel = self.cog.bot.get_channel(self.cog.report_channel_id)
                    if not channel:
                        await interaction.response.send_message("Salon de rapport introuvable.", ephemeral=True)
                        return

                    embed = discord.Embed(
                        title=f"Rapport de bug: {self.bug_name}",
                        color=discord.Color.red(),
                    )
                    embed.add_field(name="Type de bug", value=self.bug_type.value, inline=False)
                    embed.add_field(name="Comment réaliser ce bug", value=self.reproduction_steps.value, inline=False)
                    embed.add_field(name="Description détaillée", value=self.detailed_description.value, inline=False)
                    embed.set_footer(text=f"Signalé par {interaction.user} ({interaction.user.id})")

                    message = await channel.send(embed=embed)

                    # Réagir au message
                    await message.add_reaction("✅")  # Bug résolu
                    await message.add_reaction("⚙️")  # En cours de traitement
                    await message.add_reaction("❓")  # Autre

                    await interaction.response.send_message("Rapport envoyé avec succès !", ephemeral=True)

                except discord.HTTPException as e:
                    await interaction.response.send_message(
                        f"Erreur lors de l'envoi du rapport : {e}", ephemeral=True
                    )

        await interaction.response.send_modal(BugReportModal(self, bug_name))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Modifie le titre du message selon la réaction ajoutée et gère les réactions uniques."""
        if payload.channel_id != self.report_channel_id:
            return  # Ignore les réactions hors du salon de rapport

        if payload.user_id == self.bot.user.id:
            return  # Ignore les réactions du bot

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
            if not message.embeds:
                return  # Ignore les messages sans embed

            embed = message.embeds[0]
            if not embed.title.startswith("Rapport de bug:"):
                return  # Ignore les messages non liés aux rapports de bugs

            # Map des emojis et leurs préfixes
            emoji_map = {
                "✅": "✅",
                "⚙️": "⚙️",
                "❓": "❓",
            }

            emoji = str(payload.emoji)
            if emoji in emoji_map:
                # Supprimer les autres réactions de cet utilisateur
                for reaction in message.reactions:
                    if reaction.me:  # Ne traiter que les réactions où le bot a réagi
                        async for user in reaction.users():
                            if user.id == payload.user_id and str(reaction.emoji) != emoji:
                                await message.remove_reaction(reaction.emoji, user)

                # Modifier le titre de l'embed avec la nouvelle réaction
                new_title = f"[{emoji_map[emoji]}] Rapport de bug: {embed.title.split(':', 1)[1].strip()}"
                embed.title = new_title
                await message.edit(embed=embed)

        except discord.HTTPException:
            pass


    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Gère les cas où une réaction est retirée."""
        if payload.channel_id != self.report_channel_id:
            return  # Ignore les réactions hors du salon de rapport

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
            if not message.embeds:
                return  # Ignore les messages sans embed

            embed = message.embeds[0]
            if not embed.title.startswith("["):
                return  # Ignore les messages sans titre formaté

            # Réinitialiser le titre si toutes les réactions sont retirées
            if all(reaction.count == 1 for reaction in message.reactions if reaction.me):
                original_title = f"Rapport de bug: {embed.title.split(':', 1)[1].strip()}"
                embed.title = original_title
                await message.edit(embed=embed)

        except discord.HTTPException:
            pass

async def setup(bot):
    await bot.add_cog(BugReport(bot))
