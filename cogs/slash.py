from discord.ext import commands


class CogName(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot


    @commands.command(name = "slash",
                        usage="<usage>",
                        description = "description")
    @commands.guild_only()
    @commands.has_permissions()
    @commands.cooldown(1, 2, commands.BucketType.member)
    async def slash(self, ctx:commands.Context):
        await ctx.send("Slash test command")


def setup(bot:commands.Bot):
    bot.add_cog(CogName(bot))