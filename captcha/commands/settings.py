# Builtin or Pip
from typing import Union

# Discord/Red related
import discord
from discord.ext.commands import BadArgument
import redbot.core.utils.chat_formatting as form
from redbot.core import commands
from redbot.core.i18n import Translator, cog_i18n

# Local
from ..abc import MixinMeta
from ..classes import CaptchaType

_ = Translator("Captcha", __file__)


# A logic from Trusty-Cogs, thank you!
# https://github.com/TrustyJAID/Trusty-cogs/blob/master/roletools/converters.py
@cog_i18n(_)
class RoleConverter(commands.RoleConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        if not ctx.me.guild_permissions.manage_roles:
            raise BadArgument(_("I require manage roles permission to use this command."))
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except commands.BadArgument:
            raise
        if role.managed:
            raise BadArgument(
                _("This role is managed (Controlled by an integration) and cannot be used.")
            )
        if ctx.author.id == ctx.guild.owner.id:
            return role
        if role.position >= ctx.me.top_role.position:
            raise BadArgument(
                _("This role is higher than my highest role in the discord hierarchy.")
            )
        if role.position >= ctx.author.top_role.position:
            raise BadArgument(_("This role is higher than your own in the discord hierarchy."))
        return role


class Settings(MixinMeta):
    """
    Commands used for setting up Captcha.
    Those commands are mostly used in a guild.
    """

    @commands.guild_only()
    @commands.admin_or_permissions(manage_roles=True)
    @commands.group(name="setcaptcha", aliases=["captchaset"])
    async def config(self, ctx: commands.GuildContext):
        """Configure Captcha in your server."""
        pass

    @config.command(name="channel", usage="<destination = text_channel_or_'dm'>")
    async def challenge_channel(
        self, ctx: commands.Context, *, destination: Union[discord.TextChannel, str]
    ):
        """Set the channel where the user will be challenged.

        ``destination`` - Discord Text Channel.
        This can also be a string repre
        """
        # Will get modified: channel
        is_text_channel = isinstance(destination, discord.TextChannel)
        if not is_text_channel and destination != "dm":
            await ctx.send_help()
            await ctx.send(
                form.error(
                    form.bold(
                        _(
                            "You can only use 'dm' as the destination if you don't want to use a channel."
                        )
                    )
                )
            )
            return
        await self.data.guild(ctx.guild).channel.set(
            destination.id if is_text_channel else destination
        )
        await ctx.send(
            form.info(
                _(
                    "Destination registered: {dest}.".format(
                        dest=destination.mention if is_text_channel else _("User Private Message")
                    )
                )
            )
        )
        # End of command.

    @config.command(
        name="logschannel",
        aliases=["lchann", "lchannel", "logschan", "logchannel", "logsc"],
    )
    async def logging_channel(
        self, ctx: commands.Context, *, destination: Union[discord.TextChannel, str]
    ):
        """Set a channel where events are registered.

        The following actions will be registered:
        - User join and must answer the captcha.
        - User passed captcha/failed captcha.
        - User got kicked.

        ``destination``: Text channel. You can also use "None" if you wish to remove the logging
         channel.
        """
        # Will get modified: logschannel
        is_text_channel = isinstance(destination, discord.TextChannel)
        if not is_text_channel and destination.lower() == "none":
            await self.data.guild(ctx.guild).logschannel.clear()
            await ctx.send(form.info(_("Logging channel removed.")))
            return
        await self.data.guild(ctx.guild).logschannel.set(destination.id)
        await ctx.send(
            form.info(_("Logging channel registered: {chan}.").format(chan=destination.mention))
        )

    @config.command(name="enable", aliases=["activate"])
    async def activator(self, ctx: commands.Context, state: bool):
        """Enable or disable Captcha security.

        Use `True` (Or `t`) to enable or `False` (r `f`) to disable.
        User won't be challenged and will not receive any temporary role.
        """
        # Will get modified: enabled
        actual_state = await self.data.guild(ctx.guild).enabled()
        if actual_state is state:
            await ctx.send(
                form.warning(form.bold(_("Captcha is already set on {stat}.").format(stat=state)))
            )
            return
        await self.data.guild(ctx.guild).enabled.set(state)
        await ctx.send(
            form.info(form.bold(_("Captcha state registered: {stat}").format(stat=state)))
        )

    @config.command(name="type")
    async def captcha_type_setter(self, ctx: commands.Context, captcha_type: str):
        """
        Change the type of Captcha challenge.

        You choose the following type of Captcha:
        - image: A normal captcha image, hardest to understand.
        - wheezy: A less complex captcha image, easier than image method.
        - plain: Plain text captcha. Easiest to read, cannot be copy/pasted.
        """
        # Will get modified: type
        captcha_type = captcha_type.upper()
        if not hasattr(CaptchaType, captcha_type):
            if captcha_type == "WHEZZY":
                await ctx.send(
                    form.error(
                        _(
                            "Whezzy captcha are not available on this instance. Install `whezzy.captcha` "
                            "first."
                        )
                    )
                )
            await ctx.send_help()
            await ctx.send(
                form.error(
                    form.bold(_("{type} is not a valid type option.").format(type=captcha_type))
                )
            )
            return
        await self.data.guild(ctx.guild).type.set(captcha_type)
        await ctx.send(
            form.warning(form.bold(_("Captcha type registered: {type}").format(type=captcha_type)))
        )

    @config.command(name="timeout", usage="<time_in_minutes>")
    async def timeout_setter(self, ctx: commands.Context, time: int):
        """
        Set the timeout before the bot kick the user if the challenger doesn't give answer.

        Time must be expressed in minutes.
        """
        if time > 15:
            await ctx.send(_("I think 15 minutes is enough, don't you think?"))
        await self.data.guild(ctx.guild).timeout.set(time)
        if time > 1:
            await ctx.send(form.info(_("Timeout registered: {time} minutes.").format(time=time)))
        else:
            await ctx.send(form.info(_("Timeout registered: {time} minute.").format(time=time)))

    @config.command(name="temprole", usage="<temporary_role>")
    async def temporary_role_setter(self, ctx: commands.Context, *, role: RoleConverter):
        """
        Give a temporary role when initilalizing the captcha challenge.
        """
        await self.data.guild(ctx.guild).temprole.set(role.id)
        await ctx.send(
            form.info(form.bold(_("Temporary role registered: {role}").format(role=role.name)))
        )

    # Taken from my logic at
    # https://github.com/SharkyTheKing/Sharky/blob/master/verify/verification.py#L163, thank buddy
    # What the f*ck do you mean I'm lazy? Dude I made 3/4 of the cog and logic in less a week, I
    # deserve understanding what sleep schedule mean!
    @config.group()
    async def autorole(self, ctx: commands.GuildContext):
        pass

    @autorole.command(name="add")
    async def add_roles(self, ctx: commands.Context, *roles: discord.Role):
        """Add a role to give.
        You can give more than one role to add.
        """
        errored = ""
        message = ""
        added = []
        already_added = []
        for role in roles:
            async with self.data.guild(ctx.guild).autoroles() as roles_list:
                if role.id not in roles_list:
                    roles_list.append(role.id)
                    added.append(role.name)
                else:
                    already_added.append(role.name)
        message += errored
        if added:
            message += _("\nAdded role(s): {roles}").format(roles=form.humanize_list(added))
        if already_added:
            message += _("\nRole(s) already added: {roles}").format(
                roles=form.humanize_list(already_added)
            )
        if message:
            for line in form.pagify(message):
                await ctx.send(line)

    @autorole.command(name="remove", aliases=["delete", "rm"])
    async def remove_roles(self, ctx: commands.Context, *roles: RoleConverter):
        """Remove a role to give.
        You can give more than one role to add.
        """
        if not roles:
            return await ctx.send_help()
        message = ""
        removed = []
        not_found = []
        async with self.data.guild(ctx.guild).autoroles() as roles_list:
            for role in roles:
                if role.id in roles_list:
                    roles_list.remove(role.id)
                    removed.append(role.name)
                else:
                    not_found.append(role.name)
        if not_found:
            message += _("\nRole(s) not found in autorole list: {roles}").format(
                roles=form.humanize_list(not_found)
            )
        if removed:
            message += _("\nRole(s) remove from autorole list: {roles}").format(
                roles=form.humanize_list(removed)
            )
        if message:
            for line in form.pagify(message):
                await ctx.send(line)

    @autorole.command(name="list")
    async def list_roles(self, ctx: commands.Context):
        """List all roles that will be given."""
        all_roles = await self.data.guild(ctx.guild).autoroles()
        maybe_not_found = []
        message = ""
        for role in all_roles:
            fetched_role = ctx.guild.get_role(role)
            if not fetched_role:
                maybe_not_found.append(fetched_role.id)
                continue
            message += "- {name} (`{id}`).\n".format(name=fetched_role.name, id=fetched_role.id)
        if maybe_not_found:
            clean_list = list(set(all_roles) - set(maybe_not_found))
            await self.data.guild(ctx.guild).autoroles.set(clean_list)
            message += _("\nSome roles has been removed since I was unable to find them.")
        if message:
            for line in form.pagify(message):
                await ctx.send(line)
        else:
            await ctx.send(_("No role has been added."))
