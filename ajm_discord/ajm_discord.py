import discord
from typing import Union
from discord.ext import commands
import re
import urllib
from docx import Document
import io


class BaseCog(commands.Cog):
    def __init__(self, bot: commands.bot):
        """
        Cog containing only essentials like logging.

        Parameters
        ----------
        bot : commands.bot
            The bot this cog should be used in.
        """
        self.bot = bot

    @classmethod
    async def log_resp(
        self,
        ctx: Union[discord.Interaction, discord.ApplicationContext],
        string: str,
        **kwargs,
    ) -> discord.Interaction:
        """
        Logs responses both to stdout and to the user.

        Parameters
        ----------
        ctx : Union[discord.Interaction, discord.ApplicationContext]
            The context that log response was used in, could be for either a message
            command, or potentially on a button, etc.
        string : str
            The string that should be output to both stdout and the user.

        Returns
        -------
        discord.Interaction
            The interaction created from this, assuming nothing went wrong.
        """
        func = None

        # there's probably more cases that need to be handled but these are two of the
        # major ones
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

                error_string = (
                    "A file attempted to be sent was too large. Please tell your"
                    " maintainer to look for file(s): {}".format(error_files)
                )
                print(error_string)
                await func(error_string)


class ListenerCog(BaseCog):
    def __init__(self, bot: commands.Bot):
        """
        Contains some basic listeners, although some of them don't quite work for
        whatever reason.

        Parameters
        ----------
        bot : commands.Bot
            The bot this cog should be used in.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Prints that the bot is ready, and what guilds are selected to use for the bot.
        """
        print("Bot {} is ready.".format(self.bot.user))
        print("Debug guilds", self.bot.debug_guilds)


class DeleteCog(BaseCog):
    def __init__(self, bot: commands.bot):
        """
        Contains basic delete methods.

        Parameters
        ----------
        bot : commands.bot
            The bot this cog should be used in.
        """
        self.bot = bot

    def to_be_deleted(
        self, msg: discord.Message, ignore_reactions: bool = True
    ) -> bool:
        """
        A function for checking whether or not a message should be deleted

        Parameters
        ----------
        msg : discord.Message
            The message to be checked
        ignore_reactions : bool, optional
            Whether or not reactions should be ignored, as they can allow certain
            messages that would otherwise would be deleted to stay, by default True

        Returns
        -------
        bool
            Returns true if the message should be deleted, and false otherwise
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
        Alternate version of to_be_deleted, could probably be replaced with a lambda.
        Parameters
        ----------
        msg : discord.Message
            The message to be checked
        ignore_reactions : bool, optional
            Whether or not reactions should be ignored, as they can allow certain
            messages that would otherwise would be deleted to stay, by default True

        Returns
        -------
        bool
            Returns true if the message should be deleted, and false otherwise
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
        Purges the thread this command was run in.

        Parameters
        ----------
        ctx : Union[discord.ApplicationContext, discord.Interaction]
            The context this thread was run in
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

        await channel.purge(limit=1000, check=self.to_be_deleted_alt)

    @commands.message_command(
        name="Delete Message", description="Deletes the selected message."
    )
    async def delete_message(
        self, ctx: discord.ApplicationContext, message: discord.Message
    ):
        """
        Deletes a given message

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The context of that delete message was used in.
        message : discord.Message
            The message to delete.
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
        """
        Initializes the TextCog.

        Parameters
        ----------
        bot : commands.bot
            The bot this cog should be used in.
        """
        self.bot = bot

    @staticmethod
    async def text_from_text_attachments(msg: discord.Message) -> str:
        """
        Gathers text from plain text attachments (.txts).

        Parameters
        ----------
        msg : discord.Message
            The message to look for plain text attachments in.

        Returns
        -------
        str
            All text gathered from any plain text attachments in the message.
        """
        return_str = ""
        for attachment in msg.attachments:
            # checks MIME type
            if "text/plain" in attachment.content_type:
                raw = await attachment.read()
                return_str = raw.decode()

        return return_str

    @staticmethod
    async def text_from_word_attachments(msg: discord.Message) -> str:
        """
        Gathers text from word attachments (.docxs).

        Parameters
        ----------
        msg : discord.Message
            The message to look for word document attachments in.

        Returns
        -------
        str
            All text gathered from any word document attachments in the message.
        """
        return_str = ""
        for attachment in msg.attachments:
            # check MIME type
            if (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                in attachment.content_type
            ):
                bytes = await attachment.read()
                reader = io.BytesIO(bytes)
                raw = reader
                document = Document(raw)
                for paragraph in document.paragraphs:
                    return_str += paragraph.text + "\n"

        return return_str

    @staticmethod
    async def text_from_image_attachments(msg: discord.Message) -> str:
        """
        Converts image links to markdown text. Does not do OCR on images or anything of
        the sort.

        Parameters
        ----------
        msg : discord.Message
            The message to be checked for image attachments.

        Returns
        -------
        str
            A string of concatenated attachment urls in markdown form.
        """
        return_str = ""
        for attachment in msg.attachments:
            # check MIME type
            if attachment.content_type in ["image/jpeg", "image/jpg", "image/png"]:
                return_str += "![]({})".format(attachment.url)

        return return_str

    @staticmethod
    async def get_good_text(
        thread: discord.Thread, bot_okay: bool = False, images_to_markdown: bool = False
    ) -> str:
        """
        Retrieves the 'good' text from a thread, classified as any text inside the
        thread, which includes messages (usually not sent by the bot), attachments, and
        links.

        Parameters
        ----------
        thread : discord.Thread
            The thread to retrieve text from
        bot_okay : bool, optional
            Whether or not bot messages should be counted as text, by default False
        images_to_markdown : bool, optional
            Whether or not image links should be converted to markdown style text

        Returns
        -------
        str
            The 'good' text from the thread.
        """
        if (
            thread.type != discord.ChannelType.public_thread
            and thread.type != discord.ChannelType.private_thread
        ):
            await thread.send("Error, this must be done in a thread.")
            return ""

        docs_pattern = re.compile(r"(https?://docs.google.com/document/d/[^\s]+)")

        full_history = ""
        async for message in thread.history(limit=None, oldest_first=True):
            # don't retrieve own messages or messages marked not to be taken
            if not message.author.bot or bot_okay:
                # in case there's text files to read from
                attachment_text = ""
                attachment_text += await TextCog.text_from_text_attachments(message)
                attachment_text += await TextCog.text_from_word_attachments(message)
                if images_to_markdown:
                    attachment_text += await TextCog.text_from_image_attachments(
                        message
                    )
                # or a drive file to read from
                drive_doc_text = ""

                # looking specifically for google drive document links
                check = docs_pattern.findall(message.content)
                for link in check:
                    drive_doc_text += TextCog.drive_doc_to_raw_text(link)
                    # means that there was a drive doc with nothing in it
                    if drive_doc_text == "":
                        await thread.send(
                            "Permissions on drive link denied, please check your"
                            " sharing settings. Could also be an empty drive"
                            " document."
                        )
                        return ""

                full_history += (
                    message.content + "\n" + attachment_text + "\n" + drive_doc_text
                )

        # remove all drive links, other links can stay if they exist
        full_history = docs_pattern.sub("", full_history)

        return full_history

    @staticmethod
    async def get_embed_text(
        thread: discord.Thread, split_field: bool = True, bot_okay: bool = True
    ):
        """
        Retrieves text from embeds in a thread.

        Parameters
        ----------
        thread : discord.Thread
            The thread to retrieve embed text from
        split_field : bool, optional
            Whether or not to split the returned embed text return into (name, value),
            by default True
        bot_okay : bool, optional
            Whether or not bot embeds should be read, by default True

        Returns
        -------
        Union((str, str), str)
            Returns either a tuple of two strings with the first field being the text
            from embed names and the second being the text from embed values, or a
            string of the embed unsplit.
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
        Converts a drive document link to raw text.

        Parameters
        ----------
        drive_doc_link : str
            The link for the drive document

        Returns
        -------
        str
            The text from the drive document
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
