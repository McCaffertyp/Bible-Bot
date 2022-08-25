# -*- coding: utf-8 -*-
"""
Created on Wed Aug 24 04:35:00 2022

@author: Paul McCafferty
@version: 1.0
"""

# bot.py
import os
import discord
import threading
import http.client
from discord.ext import commands
from dotenv import load_dotenv
from urllib.request import urlopen


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"), intents=intents)

# variables
base_url = "https://dailyverses.net/"
swear_words = [
    "anal", "ass", "bitch", "btch", "bullshit", "cock", "cum", "cunt", "damn", "dick", "dicks", "dumbass", "fuck",
    "fucked", "fucking", "fuc", "fuk", "nigga", "nigar", "niggar", "nigger", "penis", "piss", "pissant",
    "pissed", "pissing", "pussy", "shit", "shitting", "thot", "thots", "turdface", "vagina", "vaginal"
]


def get_votd_from_url() -> str:
    lookup_url = "{0}{1}".format(base_url, "esv")
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_bytes.decode("utf-8")

    verse_text_start_search = "<span class=\"v1\">"
    verse_text_start_index = html.find(verse_text_start_search) + len(verse_text_start_search)
    verse_text_end_index = html.find("</span>", verse_text_start_index)

    verse_ref_start_search = "class=\"vc\">"
    verse_ref_start_index = html.find(verse_ref_start_search) + len(verse_ref_start_search)
    verse_ref_end_index = html.find("</a>", verse_ref_start_index)

    verse_text = html[verse_text_start_index:verse_text_end_index]
    reference = html[verse_ref_start_index:verse_ref_end_index]
    return "\"{0}\" - {1} ESV".format(verse_text, reference)


def get_verse_from_lookup_url(book: str, chapter: str, verse: str) -> str:
    lookup_url = "{0}{1}/{2}/{3}/esv".format(base_url, book, chapter, verse)
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_bytes.decode("utf-8")

    verse_text_start_search = "<span class=\"v2\">"
    verse_text_start_index = html.find(verse_text_start_search) + len(verse_text_start_search)
    verse_text_end_index = html.find("</span>", verse_text_start_index)

    verse_ref_start_search = "class=\"vc\">"
    verse_ref_start_index = html.find(verse_ref_start_search) + len(verse_ref_start_search)
    verse_ref_end_index = html.find("</a>", verse_ref_start_index)

    verse_text = html[verse_text_start_index:verse_text_end_index]
    reference = html[verse_ref_start_index:verse_ref_end_index]
    return "\"{0}\" - {1} ESV".format(verse_text, reference)


@bot.event
async def on_ready():
    print('Successfully logged into {0} as {1.user}'.format(GUILD, bot))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.guild.name == GUILD:
        await filter_message(message)

    await bot.process_commands(message)


@bot.command(
    name="dailyvotd",
    help="Prints the Verse of the Day every day at a consistent time. Using again while active turns it off.",
    brief="Puts the bot on a timer for sending the daily VOTD."
)
async def send_daily_verse_of_the_day(ctx, time: str = None):
    if time is None:
        await send_message(ctx, "Please provide a time.")
    else:
        converted_time = convert_twenty_four_to_twelve(time)
        response = "Will now send the VOTD daily at {0}.".format(converted_time)
        await send_message(ctx, response)
        await send_message(ctx, "Oops, it seems this command is not finished yet!\nVerse will not be sent ;-;")


@bot.command(
    name="votd",
    help="Prints the Verse of the Day that was fetched from online.",
    brief="Prints the Verse of the Day."
)
async def send_verse_of_the_day(ctx):
    votd = get_votd_from_url()
    await send_message(ctx, votd)


@bot.command(
    name="lookup",
    help="Looks up and prints out the verse that was searched.",
    brief="Looks up verse and prints it."
)
async def verse_lookup(ctx, book: str = None, chapter: str = None, verse: str = None):
    if book is None or chapter is None or verse is None:
        await send_message(ctx, "Unfortunately I cannot look that up. Check all values were entered.")
    else:
        verse_text = get_verse_from_lookup_url(book.lower(), chapter, verse)
        await send_message(ctx, verse_text)


async def filter_message(message):
    for word in swear_words:
        if word in message.content.lower():
            if is_banned_word(word, message.content.lower()):
                await delete_message(message)
                break


def is_banned_word(swear_word: str, sentence: str) -> bool:
    start_index_of_swear_word = sentence.find(swear_word)
    end_index_of_swear_word = start_index_of_swear_word + len(swear_word)
    word = sentence[start_index_of_swear_word:end_index_of_swear_word]

    left = start_index_of_swear_word - 1
    right = end_index_of_swear_word

    while left > -1 and sentence[left] != " ":
        word = "{0}{1}".format(sentence[left], word)
        left -= 1

    while right < len(sentence) and sentence[right] != " ":
        word = "{0}{1}".format(word, sentence[right])
        right += 1

    return word in swear_words


async def delete_message(message):
    await message.delete()
    response = "{0} no swearing while I'm around.".format(message.author.mention)
    await send_message(message, response)


async def send_message(message, msg):
    await message.channel.send(msg, allowed_mentions=discord.AllowedMentions().all())


def convert_twenty_four_to_twelve(time: str) -> str:
    time_split = time.split(":")
    hour = int(time_split[0])
    minute = int(time_split[1])

    if minute > 59:
        minute = 59

    if hour < 12:
        return "{0}:{1} AM".format(hour, minute)
    elif 12 <= hour < 25:
        return "{0}:{1} PM".format(hour - 12, minute)
    else:
        return "{0}:{1} PM".format(23, minute)


bot.run(TOKEN)

# verse_lookup_url_base = "https://www.biblegateway.com/passage/?search="
# verse_lookup_url_base = "https://www.bible.com/bible/59/"
# book_names_abbreviations = {
#     "GENESIS": "GEN", "EXODUS": "EXO", "LEVITICUS": "LEV", "NUMBERS": "NUM",
#     "DEUTERONOMY": "DEU", "JOSHUA": "JOS", "JUDGES": "JDG", "RUTH": "RUT",
#     "1 SAMUEL": "1SA", "2 SAMUEL": "2SA", "1 KINGS": "1KI", "2 KINGS": "2KI",
#     "1 CHRONICLES": "1CH", "2 CHRONICLES": "2CH", "EZRA": "EZR", "NEHEMIAH": "NEH",
#     "ESTHER": "EST", "JOB": "JOB", "PSALM": "PSA", "PROVERBS": "PRO",
#     "ECCLESIASTES": "ECC", "SONG OF SOLOMON": "SNG", "ISAIAH": "ISA", "JEREMIAH": "JER",
#     "LAMENTATIONS": "LAM", "EZEKIEL": "EZK", "DANIEL": "DAN", "HOSEA": "HOS",
#     "JOEL": "JOL", "AMOS": "AMO", "OBADIAH": "OBA", "JONAH": "JON",
#     "MICAH": "MIC", "NAHUM": "NAM", "HABAKKUK": "HAB", "ZEPHANIAH": "ZEP",
#     "HAGGAI": "HAG", "ZECHARIAH": "ZEC", "MALACHI": "MAL",
#     "MATTHEW": "MAT", "MARK": "MRK", "LUKE": "LUK", "JOHN": "JHN",
#     "ACTS": "ACT", "ROMANS": "ROM", "1 CORINTHIANS": "1CO", "2 CORINTHIANS": "2CO",
#     "GALATIANS": "GAL", "EPHESIANS": "EPH", "PHILIPPIANS": "PHP", "COLOSSIANS": "COL",
#     "1 THESSALONIANS": "1TH", "2 THESSALONIANS": "2TH", "1 TIMOTHY": "1TI", "2 TIMOTHY": "2TI",
#     "TITUS": "TIT", "PHILEMON": "PHM", "HEBREWS": "HEB", "JAMES": "JAS",
#     "1 PETER": "1PE", "2 PETER": "2PE", "1 JOHN": "1JN", "2 JOHN": "2JN",
#     "3 JOHN": "3JN", "JUDE": "JUD", "REVELATIONS": "REV"
# }
