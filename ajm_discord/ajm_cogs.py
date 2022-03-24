from urllib.error import HTTPError
import discord
from typing import Union
from discord.ext import commands
from discord.commands import Option
import re
import urllib


class BaseCog(commands.Cog):
    def __init__(self, bot: commands.bot):
        """
        Initializer.

        Args:
            bot (commands.bot): The Discord bot to be used for this cog.
        """
        self.bot = bot

    async def log_resp(
        self,
        ctx: Union[discord.Interaction, discord.ApplicationContext],
        string: str,
        **kwargs,
    ) -> discord.Interaction:
        """
        Logs a given string in both discord and the command line.

        Args:
            ctx (Union[discord.Interaction, discord.ApplicationContext]): ctx to post the message to
            string (str): string to be both printed to stdout and sent through discord
            **kwargs: args to be passed to

        Returns:
            discord.Interaction: the ctx's interaction after being responded or sent to.
        """
        func = None

        # there's probably more cases that need to be handled but these are two of the major ones
        if isinstance(ctx, discord.ApplicationContext):
            func = ctx.respond
        if isinstance(ctx, discord.Interaction):
            func = ctx.channel.send
        print(string)
        try:
            return await func(string, **kwargs)
        except discord.errors.HTTPException as e:
            print(e.code)
            print(kwargs)
            if e.code == 40005:
                error_files = []
                if "files" in kwargs:
                    for file in kwargs["files"]:
                        error_files.append(file.filename)
                if "file" in kwargs:
                    error_files.append(kwargs[file].filename)

                error_string = "A file attempted to be sent was too large. Please tell your maintainer to look for file(s): {}".format(
                    error_files
                )
                print(error_string)
                await func(error_string)


class ListenerCog(BaseCog):
    def __init__(self, bot: commands.Bot):
        """
        Initializer function.

        Args:
            bot (commands.Bot): the bot to use for this cog
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Prints that the bot is ready, and what guilds are selected to use for the bot.
        """
        print("Bot {} is ready.".format(self.bot.user))
        print("Debug guilds", self.bot.debug_guilds)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: discord.ApplicationContext, error):
        """
        Listener for when there was an error with a command, though I've never seen it trigger.

        Args:
            ctx (discord.ApplicationContext): context for the command that errored.
            error (_type_): the error of the command.
        """
        self.log_resp(ctx, "THERE WAS A COMMAND ERROR: {}".format(error))

    @commands.Cog.listener()
    async def on_error(self, ctx: discord.ApplicationContext, error):
        """
        Listener for when there's an error.

        Args:
            ctx (discord.ApplicationContext): context for the error
            error (_type_): the error given
        """
        self.log_resp(ctx, "THERE WAS AN ERROR: {}".format(error))


class DeleteCog(BaseCog):
    def __init__(self, bot: commands.bot):
        """
        Initalizer function.

        Args:
            bot (commands.bot): the bot to be used for this cog
        """
        self.bot = bot

    def to_be_deleted(
        self, msg: discord.Message, ignore_reactions: bool = True
    ) -> bool:
        """
        Function for deciding what messages should be deleted.

        Args:
            msg (discord.Message): the message to be checked.
            ignore_reactions (bool, optional): Whether or not reactions on the messages should be ignored. Defaults to True.

        Returns:
            bool: whether or not the message is cleated for deletion.
        """
        if ignore_reactions:
            # delete anything done by the bot,
            return msg.author.id == self.bot.user.id

        for reaction in msg.reactions:
            # supposed to be a white check mark
            if reaction.emoji == "✅":
                return False

        return msg.author.id == self.bot.user.id

    # could probably be replaced with a lambda
    def to_be_deleted_alt(
        self, msg: discord.Message, ignore_reactions: bool = False
    ) -> bool:
        """
        Alternate version of the to_be_deleted function, and could probably be replaced.

        Args:
            msg (discord.Message): the message to be checked.
            ignore_reactions (bool, optional): Whether or not reactions on the messages should be ignored. Defaults to False.

        Returns:
            bool: whether or not the message is cleated for deletion.
        """
        return self.to_be_deleted(msg, False)

    @commands.slash_command(
        name="purge_thread",
        description="Deletes all messages from this bot in a thread.",
    )
    async def purge_thread(
        self, ctx: Union[discord.ApplicationContext, discord.Interaction]
    ):
        """
        Removes all (or at least most messages) from a bot in this thread.

        Args:
            ctx (Union[discord.ApplicationContext, discord.Interaction]): the context this command was called in
        """
        # so that it doesn't time out and complain
        if isinstance(ctx, discord.ApplicationContext):
            await ctx.defer()
        channel = self.bot.get_channel(ctx.channel_id)
        if (
            channel.type != discord.ChannelType.public_thread
            and channel.type != discord.ChannelType.private_thread
        ):
            await self.log_resp(
                self,
                "Sorry {}, this can only be done in a thread.".format(
                    ctx.author.display_name
                ),
            )
            return

        await ctx.channel.purge(limit=1000, check=self.to_be_deleted_alt)

    @commands.message_command(
        name="Delete Message", description="Deletes the selected message."
    )
    async def delete_message(
        self, ctx: discord.ApplicationContext, message: discord.Message
    ):
        """
        Deletes a given message.

        Args:
            ctx (discord.ApplicationContext): the context this command was used in
            message (discord.Message): the message to be deleted
        """
        await ctx.defer()
        if self.to_be_deleted(message):
            await ctx.delete()
            await message.delete()
            print("Deleted message by {}'s request.".format(ctx.author.display_name))

        else:
            await self.log_resp(
                ctx,
                "Sorry {}, this message can't be deleted.".format(
                    ctx.author.display_name
                ),
            )


class TextCog(BaseCog):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @staticmethod
    async def text_from_text_attachments(msg: discord.Message) -> str:
        """
        Retrieves the text from the attachments of a given discord message.

        Args:
            msg (discord.Message): the message that should have its attachments searched for text

        Returns:
            str: the text found in the attachments
        """
        return_str = ""
        for attachment in msg.attachments:
            # checks MIME type
            if "text/plain" in attachment.content_type:
                raw = await attachment.read()
                return_str = raw.decode()

        return return_str

    @staticmethod
    async def get_good_text(thread: discord.Thread, bot_okay: bool = False) -> str:
        """
        Retrieves 'good' text from a given thread. Which is text only from users, unless bot_okay is True.

        Args:
            thread (discord.Thread): the thread to retrieve text from
            bot_okay (bool, optional): whether or not bot messages in the thread should also be used. Defaults to False.

        Returns:
            str: all of the text found in the thread
        """
        if (
            thread.type != discord.ChannelType.public_thread
            and thread.type != discord.ChannelType.private_thread
        ):
            await thread.send("Error, this must be done in a thread.")
            return ""

        full_history = ""
        async for message in thread.history(limit=None, oldest_first=True):
            # don't retrieve own messages or messages marked not to be taken
            if not message.author.bot or bot_okay:
                # in case there's text files to read from
                attachment_text = await TextCog.text_from_text_attachments(message)
                # or a drive file to read from
                drive_doc_text = ""

                if not attachment_text:
                    # looking specifically for google drive document links
                    check = re.findall(
                        r"(https?://docs.google.com/document/d/[^\s]+)", message.content
                    )
                    for link in check:
                        drive_doc_text += TextCog.drive_doc_to_raw_text(link)
                        # means that there was a drive doc with nothing in it
                        if drive_doc_text == "":
                            await thread.send(
                                "Permissions on drive link denied, please check your sharing settings. Could also be an empty drive document."
                            )
                            return ""

                # means it wasn't just an attachment or a drive link
                if not drive_doc_text and not attachment_text:
                    full_history += message.content + "\n"

                full_history += attachment_text + drive_doc_text

        return full_history

    @staticmethod
    async def get_embed_text(
        thread: discord.Thread, split_field: bool = True, bot_okay: bool = True
    ) -> Union[(str, str), str]:
        """
        Retrieves text from embeds in a thread.

        Args:
            thread (discord.Thread): the thread to retrieve embed text from.
            split_field (bool, optional): whether or not to split the returned embed text upon return into (name, value). Defaults to True.
            bot_okay (bool, optional): whether or not bot embeds should be read. Defaults to True.

        Returns:
            Union((str, str), str): returns either a tuple of two strings with the first field being the text from embed names and the second being the text from embed values, or a string of the embed unsplit.
        """
        if (
            thread.type != discord.ChannelType.public_thread
            and thread.type != discord.ChannelType.private_thread
        ):
            await thread.send("Error, this must be done in a thread.")
            return ""
        name_text = ""
        value_text = ""
        combined_text = ""
        async for message in thread.history(limit=1000):
            if not message.author.bot or bot_okay:
                for embed in message.embeds:
                    for field in embed.fields:
                        name_text += field.name
                        value_text += field.value
                        combined_text += field.name + field.value

        if split_field:
            return (name_text, value_text)

        return combined_text

    @staticmethod
    def drive_doc_to_raw_text(drive_doc_link: str) -> str:
        """
        Converts a drive document link to text.

        Args:
            drive_doc_link (str): the drive document link.

        Returns:
            str: the text from the drive document.
        """
        doc_pattern = re.compile(r"/document/d/([^/\n]*)")
        key = doc_pattern.findall(drive_doc_link)
        if len(key) != 1:
            return ""

        else:
            key = key[0]

        drive_link = "https://docs.google.com/document/d/{}/export?format=txt".format(
            key
        )

        local_filename, headers = urllib.request.urlretrieve(drive_link)

        # check whether or not it's actually been downloaded
        if headers["X-Frame-Options"] == "DENY":
            return ""

        text = ""
        with open(local_filename, "r", encoding="utf-8-sig") as fp:
            for line in fp:
                text += line

        return text
