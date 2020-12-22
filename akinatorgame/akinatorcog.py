import asyncio

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.predicates import MessagePredicate
from redbot.core.utils.chat_formatting import humanize_list
from redbot.core.utils.embed import randomize_colour

from akinator.async_aki import Akinator
from akinator import CantGoBackAnyFurther, InvalidLanguageError

import discord

__author__ = ["Predeactor"]
__version__ = "Beta v0.6.2"


class AkinatorCog(commands.Cog, name="Akinator"):
    """
    The genius, Akinator, will guess your mind and find who you are thinking of, go challenge him!
    """

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.ongoing_games = {}

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """
        This will put some text at the top of the main help. ([p]help Akinator)
        Thank to Sinbad.
        """
        pre_processed = super().format_help_for_context(ctx)
        return "{pre_processed}\n\nAuthor: {authors}\nVersion: {version}".format(
            pre_processed=pre_processed,
            authors=humanize_list(__author__),
            version=__version__,
        )

    @commands.group()
    async def akinator(self, ctx: commands.GuildContext):
        """
        Answer Akinator's question and get challenged!
        """

    @akinator.command()
    async def start(self, ctx: commands.Context):
        """
        Begin a game session with Aikanator.

        To answer a question, you can use the following terms:
        - "yes" OR "y" OR "0" for answering "Yes".
        - "no" OR "n" OR "1" for answer "No".
        - "i" OR "idk" OR "i dont know" OR "i don't know" OR "2" for answer "I don't know".
        - "probably" OR "p" OR "3" for answering "Probably".
        - "probably not" OR "pn" OR "4" for answering "Probably not".

        You can also say "b" or "back" to change your last question.
        """

        await ctx.send_help()
        await ctx.send("Are you ready to answer Akinator's questions? (y/n)")
        check = MessagePredicate.yes_or_no(ctx=ctx)
        await self.bot.wait_for("message", timeout=60, check=check)
        if not check.result:
            await ctx.send("See you later then! \N{WAVING HAND SIGN}")
            return
        await ctx.send("Let's go!")
        game_class = UserGame(ctx.author, ctx.channel, self.bot)
        self.ongoing_games[ctx.author.id] = game_class
        await ctx.send(
            "Do you wish to set a specific language? If so, please specify it now (Find all "
            "available language at <https://github.com/NinjaSnail1080/akinator.py#functions>) else "
            "just say 'no'."
        )
        try:
            res = await self.bot.wait_for(
                "message", timeout=60, check=MessagePredicate.same_context(ctx=ctx)
            )
        except asyncio.TimeoutError:
            await ctx.send("You didn't answered in time... \N{PENSIVE FACE}")
            return
        res = res.content.lower()
        lang = res if res not in ("no", "n") else "en"
        await game_class.start_akinator_game(language=lang)
        try:
            del self.ongoing_games[ctx.author.id]
        except KeyError:
            pass

    @akinator.command()
    async def cancel(self, ctx: commands.Context):
        """Cancel your game with Akinator."""
        if ctx.author.id not in self.ongoing_games:
            await ctx.send("You're not running any game!")
            return
        game_class: UserGame = self.ongoing_games[ctx.author.id]
        game_class.task.cancel()
        self.ongoing_games.pop(ctx.author.id)
        await ctx.tick()


class UserGame:
    def __init__(self, user: discord.User, channel: discord.TextChannel, bot: Red):
        self.user = user
        self.channel = channel
        self.bot = bot
        self.akinator = Akinator()
        self.task = None
        self.question = None
        self.prog = 80
        self.count = 1

    async def ask_question(self):
        await self.channel.send("Question #{num}: ".format(num=self.count) + str(self.question))
        received = await self.wait_for_input()
        return received

    async def wait_for_input(self):
        valid_answer = False
        done = None  # Linters are lovely
        answer = [
            "yes",
            "y",
            "no",
            "n",
            "i",
            "idk",
            "i don't know",
            "i dont know",
            "probably",
            "p",
            "probably not",
            "pn",
            "0",
            "1",
            "2",
            "3",
            "4",
            "b",
        ]
        while valid_answer is not True:
            self.task = asyncio.create_task(
                self.bot.wait_for(
                    "message",
                    check=MessagePredicate.lower_contained_in(
                        collection=answer, user=self.user, channel=self.channel
                    ),
                    timeout=60,
                )
            )
            try:
                done = await self.task
            except (asyncio.TimeoutError, asyncio.CancelledError):
                return None
            valid_answer = True
        return done.content

    async def start_akinator_game(self, language: str):
        if not self.question:
            try:
                self.question = await self.akinator.start_game(
                    language=language, child_mode=True if self.channel.nsfw else False
                )
            except InvalidLanguageError:
                await self.channel.send("Invalid language! Be sure it's written correctly.")
                return None

        answer = await self.answer_questions()

        if answer:
            await self.determine_win()

    async def answer_questions(self):
        """A while loop."""
        user_prompt = None
        while self.akinator.progression <= self.prog:
            user_prompt = await self.ask_question()
            if not user_prompt:
                await self.channel.send("This is the end of the game.")
                return None

            if user_prompt in ("b", "back"):
                await self.go_back()
                continue

            self.question = await self.akinator.answer(user_prompt)
            self.count += 1
        return user_prompt

    async def go_back(self) -> str:
        """Go back to the latest question."""
        try:
            self.question = await self.akinator.back()
            self.count -= 1
        except CantGoBackAnyFurther:
            await self.channel.send(
                "Cannot go back any further! You will have to answer my question."
            )
        return self.question

    async def determine_win(self):
        await self.akinator.win()
        await self.channel.send(embed=await self.make_guess_embed())
        check = MessagePredicate.yes_or_no(channel=self.channel, user=self.user)
        self.task = asyncio.create_task(self.bot.wait_for("message", check=check, timeout=60))
        try:
            await self.task
        except (asyncio.TimeoutError, asyncio.CancelledError):
            await self.channel.send("I hope I won then, at least. \N{WEARY FACE}")
            return
        if check.result:
            await self.channel.send("I won! I'm so glad I guessed your mind!")
            return True
        await self.channel.send(
            "Awh, that's bad... But feel free to ask me for another person, I " "don't mind you."
        )
        return False

    async def make_guess_embed(self):
        embed = discord.Embed(
            title="Hmm... I think I've guessed...",
            description="Is it {name}? The description is {desc}.".format(
                name=self.akinator.first_guess["name"],
                desc=self.akinator.first_guess["description"],
            ),
        )
        embed = randomize_colour(embed)
        embed.set_image(url=self.akinator.first_guess["absolute_picture_path"])
        embed.set_footer(
            icon_url=self.user.avatar_url,
            text=(
                "Game running for {name}. I asked over {num} questions! (Cog version {ver})"
            ).format(
                name=self.user.name, num=self.count, ver=__version__
            ),
        )
        return embed
