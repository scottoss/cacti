from abc import ABC
from redbot.core.commands import Cog


import discord
from redbot.core import Config
from redbot.core.bot import Red


class MixinMeta(ABC):
    def __init__(self):
        self.bot: Red
        self.data: Config
        self.user_challenge_class: dict


class ChallengeMixinMeta(ABC):
    def __init__(self):
        self.initialized: bool
        self.running: bool
        self.member: discord.Member
        self.guild = discord.Guild
        self.data = Config
        self.tasks: list
        self.channel: discord.TextChannel
        self.messages: dict
        self.useless_storage: dict


class CompositeMetaClass(type(Cog), type(ABC)):
    """
    Allows the metaclass used for proper type detection to coexist with discord.py's metaclass.
    Credit to https://github.com/Cog-Creators/Red-DiscordBot (mod cog) for all mixin stuff.
    Credit to the top of the file "base.py".
    """

    pass
