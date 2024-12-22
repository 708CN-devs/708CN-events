import discord
from discord.ext import commands, tasks
import random
import json
import os

class XPSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_data = {}  # Dictionnaire pour stocker les données d'XP des utilisateurs
        self.load_xp_data()  # Charge les données d'XP sauvegardées
        self.save_task.start()  # Démarre une tâche d'auto-sauvegarde

    def load_xp_data(self):
        """Charge les données d'XP depuis un fichier JSON."""
        if os.path.exists("xp_data.json"):
            with open("xp_data.json", "r", encoding="utf-8") as file:
                self.xp_data = json.load(file)
        else:
            print("Aucune sauvegarde d'XP trouvée. Création d'une nouvelle base.")

    def save_xp_data(self):
        """Sauvegarde les données d'XP dans un fichier JSON."""
        with open("xp_data.json", "w", encoding="utf-8") as file:
            json.dump(self.xp_data, file, ensure_ascii=False, indent=4)

    @tasks.loop(minutes=5)  # Sauvegarde automatique toutes les 5 minutes
    async def save_task(self):
        self.save_xp_data()
        print("Données d'XP sauvegardées automatiquement.")

    def cog_unload(self):
        """Appelé lors du déchargement du cog pour sauvegarder les données."""
        self.save_xp_data()
        self.save_task.cancel()

    def add_xp(self, user_id, xp_amount):
        """Ajoute de l'XP à un utilisateur."""
        if user_id not in self.xp_data:
            self.xp_data[user_id] = {"xp": 0}
        self.xp_data[user_id]["xp"] += xp_amount
        self.save_xp_data()  # Sauvegarde immédiatement après une mise à jour

    @commands.Cog.listener()
    async def on_message(self, message):
        """Ajoute de l'XP lorsqu'un utilisateur envoie un message."""
        if message.author.bot:
            return  # Ignore les messages des bots

        xp_gained = random.randint(5, 15)  # Gagne entre 5 et 15 XP
        self.add_xp(str(message.author.id), xp_gained)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Ajoute de l'XP lorsqu'un utilisateur réagit à un message."""
        if user.bot:
            return  # Ignore les réactions des bots

        xp_gained = random.randint(2, 10)  # Gagne entre 2 et 10 XP
        self.add_xp(str(user.id), xp_gained)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Ajoute de l'XP lorsqu'un utilisateur est actif dans un salon vocal."""
        if member.bot:
            return  # Ignore les bots

        if after.channel and not before.channel:
            xp_gained = random.randint(10, 20)  # Gagne entre 10 et 20 XP
            self.add_xp(str(member.id), xp_gained)

    @commands.command(name="xp")
    async def check_xp(self, ctx):
        """Commande pour vérifier son propre XP."""
        user_id = str(ctx.author.id)
        xp = self.xp_data.get(user_id, {}).get("xp", 0)
        await ctx.send(f"{ctx.author.mention}, tu as actuellement {xp} XP !")

async def setup(bot):
    await bot.add_cog(XPSystem(bot))
