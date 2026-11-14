import discord
from discord.ext import commands
from util.log import log
from dotenv import load_dotenv
import os
import re
import json
import asyncio
from util.inspect_message import save_message_json
from discord.utils import MISSING
from database.queries import (
    init_database,
    save_message,
    save_link,
    find_link,
    save_image,
    find_image,
    add_custom_message,
    get_random_custom_message,
    delete_custom_message,
    list_custom_messages,
)
from discord import app_commands
from util.imageHash import hash_attachment
from util.messageBuilder import build_message

load_dotenv()


URL_PATTERN = re.compile(r"https?://[^\s<>]+")


def return_links(message: str) -> list[str]:
    return [url.rstrip(".,;:!?)]}'\"") for url in URL_PATTERN.findall(message)]


async def handle_duplicate(message: discord.Message, duplicates: list):
    lines = []
    for _, msg_id, channel_id, author_id, created_at, guild_id in duplicates:
        url = f"https://discord.com/channels/{guild_id}/{channel_id}/{msg_id}"
        lines.append(f"{url} (posted by <@{author_id}> at {created_at})")

    try:
        await message.delete()
    except (discord.Forbidden, discord.NotFound):
        pass  # missing Manage Messages permission, or already deleted
    try:
        shame_duration = os.environ.get("SHAME_DURATION")
        delete_after = float(shame_duration) if shame_duration else MISSING

        template = await get_random_custom_message(message.guild.id)
        content = (
            build_message(template, message, duplicates)
            if template
            else f"{message.author.mention} your message was removed because the link was already posted:\n"
            + "\n".join(lines)
        )
        await message.channel.send(content, delete_after=delete_after)
    except discord.Forbidden:
        pass  # user has DMs closed


class SeenIt(commands.Bot):
    async def setup_hook(self):
        await init_database()
        await self.tree.sync()
        log("Database initialized.")


intents = discord.Intents.default()
intents.message_content = True

bot = SeenIt(command_prefix="!", intents=intents)


@bot.tree.command(
    name="addmessage",
    description="Add a custom message shown when a duplicate is removed",
)
@app_commands.describe(
    template="Insert this for placeholder @author.mention @original_author @created_at @channel @original_message @guild"
)
@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
async def addmessage(interaction: discord.Interaction, template: str):
    await add_custom_message(interaction.guild_id, template)
    await interaction.response.send_message("Custom message added.", ephemeral=True)


@bot.tree.command(name="listmessages", description="List the custom duplicate messages")
@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
async def listmessages(interaction: discord.Interaction):
    rows = await list_custom_messages(interaction.guild_id)
    if not rows:
        await interaction.response.send_message(
            "No custom messages yet.", ephemeral=True
        )
        return
    text = "\n".join(f"`{id}` {template[:150]}" for id, template in rows)
    await interaction.response.send_message(text[:2000], ephemeral=True)


@bot.tree.command(
    name="removemessage", description="Remove a custom duplicate message by its ID"
)
@app_commands.describe(id="The ID shown in /listmessages")
@app_commands.default_permissions(manage_guild=True)
@app_commands.guild_only()
async def removemessage(interaction: discord.Interaction, id: int):
    deleted = await delete_custom_message(interaction.guild_id, id)
    await interaction.response.send_message(
        "Removed." if deleted else "No message with that ID.", ephemeral=True
    )


@bot.event
async def on_ready():
    log(f"Logged is as {bot.user}")


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    parsing_url = message.content

    if os.environ.get("USING_EMBED_FIXER") == "True":
        if message.application_id == 770144963735453696:
            parsing_url = " ".join(
                component.url
                for row in message.components
                for component in row.children
                if component.url is not None
            )
            log(f"hehe parsing url : {parsing_url}")
            pass  # Embed Fixer replacement: process it
        else:
            await asyncio.sleep(7)

            try:
                await message.channel.fetch_message(message.id)
            except discord.NotFound:
                return  # Original was deleted by Embed Fixer

    log(f"here is the parsing url : {parsing_url}")
    result = return_links(parsing_url)

    hashes = []
    for attachment in message.attachments:
        image_hash = await hash_attachment(attachment)
        if image_hash:
            hashes.append(image_hash)

    if result or hashes:
        duplicate_links = []
        for link in result:
            match = await find_link(link, message.guild.id, message.channel.id)
            if match:
                duplicate_links.append(match)

        for image_hash in hashes:
            match = await find_image(image_hash, message.guild.id, message.channel.id)
            if match:
                duplicate_links.append(match)

        if duplicate_links:
            await handle_duplicate(message, duplicate_links)
            return

        row_id = await save_message(
            message.guild.id,
            message.channel.id,
            message.id,
            message.author.id,
            message.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

        if row_id:
            for link in result:
                await save_link(row_id, link)
            for image_hash in hashes:
                await save_image(row_id, image_hash)


bot.run(os.environ["BOT_TOKEN"])
