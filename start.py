import os
from dotenv import load_dotenv
import discord
import time
import math
from discord.ext import commands
from keep_alive import keep_alive
import logging

logging.basicConfig(level=logging.INFO)
logging.info(f"discord.py version: {discord.__version__}")


load_dotenv()
token = os.getenv('DISCORD_TOKEN')

class MyBot(commands.Bot):
    async def setup_hook(self):
        for extension in ['roll','ping','mimir','poke','auto_message','sun','xp_system']:
            await self.load_extension(f'cogs.{extension}')
    async def on_ready(self):
        await bot.tree.sync()
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name =f"{bot.command_prefix}help"))
        print(f'Lancé en tant que {self.user} !')
        print(discord.__version__)

intents = discord.Intents.all()
bot = MyBot(command_prefix='.', intents=intents)

keep_alive()
bot.run(token=token)