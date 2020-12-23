from enum import Enum

from redbot.core import commands
from redbot.core.i18n import cog_i18n, Translator
from redbot.core.utils.chat_formatting import warning

from ..abc import MixinMeta

_ = Translator("Captcha", __file__)


@cog_i18n(_)
class OwnerCommands(MixinMeta):
    @commands.group(name="ownersetcaptcha", aliases=["setownercaptcha", "captchasetowner"])
    @commands.is_owner()
    async def ownercmd(self, ctx: commands.GuildContext):
        pass

    @ownercmd.command(name="setlog")
    async def logging_level_setter(self, ctx: commands.Context, logging_level: int):
        if logging_level > 5:
            await ctx.send(_("The logging level cannot be more than 5."))
            return
        if logging_level < 0:
            await ctx.send(_("The logging level cannot be less than 0."))
        value = getattr(LoggingLevels, "Lvl" + str(logging_level)).value
        await self.data.log_level.set(logging_level * 10)
        await ctx.send(
            warning(
                _("The logging level has been set to: {val}, {lev}").format(
                    val=value, lev=logging_level
                )
            )
        )
        await self.initialize()


class LoggingLevels(Enum):
    Lvl5 = "CRITICAL"
    Lvl4 = "ERROR"
    Lvl3 = "WARNING"
    Lvl2 = "INFO"
    Lvl1 = "DEBUG"
    Lvl0 = "NOTSET"
