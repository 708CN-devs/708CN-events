import random
from discord.ext import commands

class Random(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="random")
    async def random(self, ctx, min: int = 1, max: int = 6):
        """
        Génère un nombre aléatoire entre des bornes spécifiées.

        Args:
            min (int, optional): La valeur minimale. Par défaut à 1.
            max (int, optional): La valeur maximale. Par défaut à 6.
        """
        # Validation des paramètres
        if min < 0:
            await ctx.send("La valeur minimale (`min`) ne peut pas être négative.")
            return
        if max < min:
            await ctx.send("La valeur maximale (`max`) doit être supérieure ou égale à la valeur minimale (`min`).")
            return
        if max > 10000:
            await ctx.send("La valeur maximale (`max`) ne peut pas dépasser 10 000.")
            return

        # Génération du nombre aléatoire
        result = random.randint(min, max)
        await ctx.send(f'{ctx.author.name} génère un nombre aléatoire entre `{min}` et `{max}` et obtient : `{result}`')

async def setup(bot):
    await bot.add_cog(Random(bot))
