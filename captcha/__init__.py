from .base import Base


async def setup(bot):
    cog = Base(bot)
    bot.add_cog(cog)
    await cog.initialize()
