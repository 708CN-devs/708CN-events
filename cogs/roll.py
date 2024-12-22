import random
from discord.ext import commands

class testCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def roll(self, ctx):
        result = random.randint(1,6)
        await ctx.send(f'{ctx.author.name} lance un dès et obtiens : {result}')

async def setup(bot):
    await bot.add_cog(testCog(bot))