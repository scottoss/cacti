# Discord/Red related
# from redbot.core import commands
# from redbot.core.utils.chat_formatting import error

# Local
from abc import ABCMeta

from .abc import MixinMeta


class Listeners(MixinMeta, metaclass=ABCMeta):
    pass
    # @commands.Cog.listener()
    # async def on_member_join(self, member: discord.Member):
    #     await self.challenger(member)
    #
    # @commands.Cog.listener()
    # async def on_member_remove(self, member: discord.Member):
    #     await self.do_possible_cleanup(member)
    #
    # @commands.Cog.listener()
    # async def on_member_captcha_passed(self):
    #     pass
    #
    # @commands.command(name="testing")
    # @commands.is_owner()
    # async def challenge(self, ctx: commands.Context, member: discord.Member):
    #     """Challenge manually an user.
    #
    #     User will be asked to answer captcha.
    #     If he fail, he won't get reinvited by the bot.
    #     """
    #     try:
    #         await self.challenger(member)
    #     except NonEnabledError:
    #         await ctx.send(error("You must enable Captcha before."))
    #
    # @commands.command()
    # @commands.is_owner()
    # async def cancelcap(self, ctx: commands.Context):
    #     await self.temp(ctx.author)
    #     await ctx.tick()
    #
    # async def challenger(self, member: discord.Member):
    #     self.user_challenge_class[str(member.id)] = challenge = Challenge(member)
    #     await challenge.initialize(self.bot)
    #     initied = await challenge.start_challenge()
    #     if not initied:
    #         return
    #     status = await challenge.looper()
    #     if status:
    #         await challenge.handle_role()
    #     await challenge.cleanup()
    #     del self.user_challenge_class[str(member.id)]
    #
    # async def do_possible_cleanup(self, member: discord.Member):
    #     if str(member.id) in self.user_challenge_class:
    #         class_captcha = self.user_challenge_class[str(member.id)]
    #         await class_captcha.cleanup()
    #
    # async def temp(self, member: discord.Member):
    #     if str(member.id) in self.user_challenge_class:
    #         class_captcha = self.user_challenge_class[str(member.id)]
    #         await class_captcha.cancel_tasks()
