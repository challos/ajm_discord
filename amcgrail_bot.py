import discord
import re
import urllib
from typing import Union
from discord.ext import commands
from discord.commands import Option


class Base_Cog(commands.Cog):
    """
    Intentionally sparse base class.

    Attributes
    ----------
    bot : commands.bot
        The bot the cog will be used in.

    Methods
    -------
    log_resp : discord.Interaction
        Prints and sends a response.
    """

    def __init__(self, bot: commands.bot):
        """
        Parameters
        ----------
        bot : commands.bot
        """
        self.bot = bot

    async def log_resp(
        self,
        ctx: Union[discord.Interaction, discord.ApplicationContext],
        string: str,
        **kwargs,
    ) -> discord.Interaction:
        """Prints and sends a response.
        ctx : discord.ApplicationContext
            The context that should be responded to.
        string : str
            The string to be printed and used for the response.
        **kwargs:
            Any kwargs which will be directly forwarded to ctx.respond.

        Returns
        -------
        discord.Interaction
            Returns the Interaction object from sending the response.
        """
        if isinstance(ctx, discord.ApplicationContext):
            print(string)
            return await ctx.respond(content=string, **kwargs)
        if isinstance(ctx, discord.Interaction):
            print(string)
            return await ctx.channel.send(content=string, **kwargs)


class Listener_Cog(Base_Cog):
    """
    A cog that contains basic listeners.

    Attributes
    ----------
    bot : commands.bot
        The bot the cog will be used in.

    Methods
    -------
    on_ready : None
        Prints a few pieces of info when the bot is ready.
    on_command_error : None
        Method that will occur when there's an error in a command.

    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Method that prints out when the bot is ready for use.
        """
        print("Bot {} is ready.".format(self.bot.user))
        print("Debug guilds", self.bot.debug_guilds)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: discord.ApplicationContext, error):
        """
        Method that occurs when there's an error in a command.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            Context that the command occurred in.
        error
            The error that was raised.
        """
        self.log_resp(ctx, "THERE WAS AN ERROR: {}".format(error))


class Delete_Cog(Base_Cog):
    """
    A cog that things related to delete commands.

    Attributes
    ----------
    bot : commands.bot
        The bot the cog will be used in.

    Methods
    -------
    to_be_deleted : bool
        A method for checking if a message should or should not be deleted.
    purge_thread : None
        Removes messages from a given thread.
    delete_message(ctx, message) : None
        Deletes a message based on a message command.


    """

    def __init__(self, bot: commands.bot):
        """
        Parameters
        ----------
        bot : commands.bot
        """
        self.bot = bot

    def to_be_deleted(
        self, msg: discord.Message, ignore_reactions: bool = True
    ) -> bool:
        """
        Just a helper function to decide if a message was sent by this bot.

        Parameters
        ----------
        msg : discord.Message
            The message to be checked for deletion.

        Returns
        -------
        True if the message should be deleted, False otherwise.

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
        return self.to_be_deleted(msg, False)

    @commands.slash_command(
        name="purge_thread",
        description="Deletes all messages from this bot in a thread.",
    )
    async def purge_thread(self, ctx: Union[discord.ApplicationContext, discord.Interaction]):
        """
        Removes messages from a thread based on to_be_deleted.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The context the slash command was used in.
        """
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
        Deletes a given message that the user chooses in the App dropdown.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The context for the command.
        message : discord.Message
            The message to be deleted.
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


class Text_Cog(Base_Cog):
    """
    Cog for processing text.

    Attributes
    ----------
    bot: commands.bot
        The bot this cog will be used in.

    Methods
    -------
    text_from_text_attachments(msg) : str
        Returns a string based on the text attachments in a message.
    get_good_text(thread, bot_okay) : str
        Retrieves 'good' text from a thread.
    get_embed_text(thread, split_field = True, bot_okay = True) : str/tuple
        Retrieves the text from embeds.
    drive_doc_to_raw_text(drive_doc_link) : str
        Converts a google docs link to raw text.

    """

    def __init__(self, bot: commands.bot):
        self.bot = bot

    @staticmethod
    async def text_from_text_attachments(msg: discord.Message) -> str:
        """
        Retrieves the text from text attachments on a given discord message.

        Parameters
        ----------
        msg : discord.Message
            The message to retrieve text from attachments from.

        Returns
        -------
        str
            The text from attachments.
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
        Retrieves 'good' text from a thread. Which includes text from text attachments, google docs, and regular message text from discord.

        Parameters
        ----------
        thread : discord.Thread
            The thread to retieve good text from.

        Returns
        -------
        str
            All the text from the thread.
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
                attachment_text = await Text_Cog.text_from_text_attachments(message)
                # or a drive file to read from
                drive_doc_text = ""

                if not attachment_text:
                    check = re.findall(
                        r"(https?://docs.google.com/document/d/[^\s]+)", message.content
                    )
                    for link in check:
                        drive_doc_text += Text_Cog.drive_doc_to_raw_text(link)
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
    ):
        """
        Retrieves embed text from a thread.

        Parameters
        ----------
        thread : discord.Thread
            The thread to retrieve embed text from.
        split_field : bool
            Whether or not the embed text should be split into (field names, field values) upon return
        bot_okay : bool
            Whether or not it's okay to retrieve embed text from bots.

        Returns
        -------
        str/tuple
            Returns either a string or a tuple depending on whether or nor split_field is True
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
        Converts a drive link to raw text from the drive document and returns it.

        Parameters
        ----------
        drive_doc_link : str
            The link to the google drive document.

        Returns
        -------
        str
            The raw text of the google drive document.
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
        with open(local_filename, "r") as fp:
            for line in fp:
                text += line

        return text


class Amcgrail_Cog(Listener_Cog, Delete_Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot
