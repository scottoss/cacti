# Discord/Red related
import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import error

# Local
from .abc import MixinMeta
from .classes import Challenge
from .errors import NonEnabledError


class Listeners(MixinMeta):
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.challenger(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.do_possible_cleanup(member)

    @commands.command(name="testing")
    @commands.is_owner()
    async def challenge(self, ctx: commands.Context, member: discord.Member):
        """Challenge manually an user.

        User will be asked to answer captcha.
        If he fail, he won't get reinvited by the bot.
        """
        try:
            await self.challenger(member)
        except NonEnabledError:
            await ctx.send(error("You must enable Captcha before."))
        except Exception as e:
            await ctx.send(error("An unexpected error happened: " + str(e)))

    @commands.command()
    @commands.is_owner()
    async def cancelcap(self, ctx: commands.Context):
        await self.temp(ctx.author)
        await ctx.tick()

    async def challenger(self, member: discord.Member):
        self.user_challenge_class[str(member.id)] = challenge = Challenge(member)
        await challenge.initialize(self.bot)
        await challenge.start_challenge()
        status = await challenge.looper()
        if status:
            await challenge.handle_role()
        await challenge.cleanup()
        del self.user_challenge_class[str(member.id)]

    async def do_possible_cleanup(self, member: discord.Member):
        if str(member.id) in self.user_challenge_class:
            class_captcha = self.user_challenge_class[str(member.id)]
            await class_captcha.cleanup()

    async def temp(self, member: discord.Member):
        if str(member.id) in self.user_challenge_class:
            class_captcha = self.user_challenge_class[str(member.id)]
            await class_captcha.cancel_task()
