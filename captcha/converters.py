import discord
from discord.ext.commands import BadArgument
from redbot.core import commands

# A logic from Trusty-Cogs, thank you!
# https://github.com/TrustyJAID/Trusty-cogs/blob/master/roletools/converter.py#L29


class RoleConverter(commands.RoleConverter, discord.Role):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        if not ctx.me.guild_permissions.manage_roles:
            raise BadArgument("I require manage roles permission to use this command.")

        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except commands.BadArgument:
            raise
        if role.managed:
            raise BadArgument(
                "This role is managed (Controlled by an integration) and cannot be used."
            )

        if ctx.author.id == ctx.guild.owner.id:
            return role
        if role.position >= ctx.me.top_role.position:
            raise BadArgument("This role is higher than my highest role in the discord hierarchy.")
        if role.position >= ctx.author.top_role.position:
            raise BadArgument("This role is higher than your own in the discord hierarchy.")

        return role
