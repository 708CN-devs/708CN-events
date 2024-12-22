import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timedelta

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_xp_time = {}  # Dictionnaire pour stocker le dernier gain d'XP de chaque utilisateur
        self.xp_data = {}  # Stockage des XP (à remplacer par un système de base de données si nécessaire)

    async def give_xp(self, user_id, guild_id):
        """
        Attribue un gain d'XP aléatoire à un utilisateur.
        """
        min_xp = 5  # Valeur minimale d'XP
        max_xp = 15  # Valeur maximale d'XP
        xp_gain = random.randint(min_xp, max_xp)

        if guild_id not in self.xp_data:
            self.xp_data[guild_id] = {}

        if user_id not in self.xp_data[guild_id]:
            self.xp_data[guild_id][user_id] = 0

        self.xp_data[guild_id][user_id] += xp_gain

        print(f"User {user_id} in guild {guild_id} gained {xp_gain} XP. Total: {self.xp_data[guild_id][user_id]} XP.")

    def can_gain_xp(self, user_id):
        """
        Vérifie si un utilisateur peut gagner de l'XP (limite d'une fois par minute).
        """
        now = datetime.utcnow()
        if user_id not in self.last_xp_time or now - self.last_xp_time[user_id] >= timedelta(minutes=1):
            self.last_xp_time[user_id] = now
            return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Attribue de l'XP lorsqu'un utilisateur envoie un message texte.
        """
        if message.author.bot:
            return

        if self.can_gain_xp(message.author.id):
            await self.give_xp(message.author.id, message.guild.id)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """
        Attribue de l'XP lorsqu'un utilisateur ajoute une réaction.
        """
        if user.bot:
            return

        if self.can_gain_xp(user.id):
            await self.give_xp(user.id, reaction.message.guild.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Attribue de l'XP lorsqu'un utilisateur rejoint un salon vocal ou change son état vocal.
        """
        if member.bot:
            return

        if self.can_gain_xp(member.id):
            await self.give_xp(member.id, member.guild.id)

    @commands.command(name="xp", help="Affiche le total d'XP d'un utilisateur.")
    async def check_xp(self, ctx, member: discord.Member = None):
        """
        Affiche le total d'XP d'un utilisateur dans la guilde actuelle.
        """
        member = member or ctx.author  # Si aucun membre spécifié, utilise l'auteur de la commande
        guild_id = ctx.guild.id

        total_xp = self.xp_data.get(guild_id, {}).get(member.id, 0)
        await ctx.send(f"{member.mention} a un total de **{total_xp} XP**.")

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
