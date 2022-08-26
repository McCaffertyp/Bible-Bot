# -*- coding: utf-8 -*-
"""
Created on Wed Aug 24 04:35:00 2022

@author: Paul McCafferty
@version: 1.0
"""
import csv
import operator
# bot.py
import os
import random
import discord
import threading
import http.client
import html as html_helper
from util import logger
from discord.ext import commands
from dotenv import load_dotenv
from urllib.request import urlopen

BIBLE_DICT_NAME = "Name"
BIBLE_DICT_CHAPTERS = "Chapters"
BIBLE_DICT_TOTAL_VERSES = "Total Verses"
BIBLE_DICT_AVG_VERSES = "Average Verses"

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_EBC = os.getenv("DISCORD_EBC_GUILD")
GUILD_SQUEEZE = os.getenv("DISCORD_SQUEEZE_GUILD")
use_ebc = True

if use_ebc:
    GUILD = GUILD_EBC
else:
    GUILD = GUILD_SQUEEZE

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"), intents=intents)

# variables
votd_base_url = "https://dailyverses.net/"
verse_lookup_base_url = "https://www.openbible.info/labs/cross-references/search?q="
keyword_search_base_url = "https://www.biblegateway.com/quicksearch/?quicksearch="
swear_words = [line.split("\n")[0] for line in open("swear_words.txt", "r").readlines()]
operators = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv, "^": operator.pow}

in_quiz = {}


# Bot events
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
        if str(message.author) in in_quiz:
            await check_answer(message, message.content)
        elif "bro =" == message.content.lower():
            await send_message(message, "Wassup homie")


# Bot commands
@bot.command(
    name="h",
    help="Provides help on all the commands available by printing out the descriptions for each.",
    brief="Provides help on all the commands available."
)
async def print_help(ctx):
    h_help_text = "$h\nProvides help on all the commands available by printing out the descriptions for each."
    dailyvotd_help_text = "$dailyvotd [time]\nPrints the Verse of the Day every day at a consistent time. Using again while active turns it off."
    votd_help_text = "$votd\nPrints the Verse of the Day that was fetched from online."
    lookup_help_text = "$lookup [book] [chapter:verse] [book_num|optional]\nLooks up and prints out the verse that was searched."
    rlookup_help_text = "$rlookup\nLooks up and prints out a random verse."
    keyword_help_text = "$keyword [word]\nTakes in a singular keyword and searches online for the top related verse to print out as a response."
    quiz_help_text = "$quiz [option]\nSends a random verse with either the reference, a single word, or a sentence missing for the user to solve."
    math_help_text = "$math [number_a] [operator] [number_b]\nProvided two numbers and a method of operation, the bot will produce the result. Supports the following: +, -, *, /"
    help_text = "```{0}\n\n{1}\n\n{2}\n\n{3}\n\n{4}\n\n{5}\n\n{6}\n\n{7}```".format(
        h_help_text, dailyvotd_help_text, votd_help_text, lookup_help_text,
        rlookup_help_text, keyword_help_text, quiz_help_text, math_help_text
    )
    await send_message(ctx, help_text)


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
    await send_message(ctx, remove_html_tags(votd))


@bot.command(
    name="lookup",
    help="Looks up and prints out the verse that was searched.",
    brief="Looks up verse and prints it."
)
async def verse_lookup(ctx, book: str = None, chapter_verse: str = None, book_num: str = None):
    if book is None:
        await send_message(ctx, "Unfortunately I cannot look that up. The Book was not provided.")
    elif chapter_verse is None:
        await send_message(ctx, "Unfortunately I cannot look that up. The Chapter:Verse was not provided.")
    elif ":" not in chapter_verse:
        await send_message(ctx, "Unfortunately I cannot look that up. The Chapter:Verse was not in the proper format.")
    else:
        if book_num is not None:
            if int(book_num) > 3 or int(book_num) < 1:
                await send_message(ctx, "Unfortunately I cannot look that up. The entered Book Number does not exist.")
        verse_text = get_verse_from_lookup_url(book.lower(), chapter_verse, book_num)
        await send_message(ctx, remove_html_tags(verse_text))


@bot.command(
    name="rlookup",
    help="Looks up and prints out a random verse.",
    brief="Prints random verse."
)
async def verse_lookup_random(ctx):
    random_verse = get_random_verse()
    await send_message(ctx, random_verse)


@bot.command(
    name="keyword",
    help="Takes in a singular keyword and searches online for the top related verse to print out as a response.",
    brief="Single keyword option to search online."
)
async def search_keyword(ctx, keyword: str = None):
    if keyword is None:
        await send_message(ctx, "Unfortunately nothing popped up for that keyword, since no keyword was entered.")
    else:
        verse_text = get_verse_from_keyword_url(keyword)
        if verse_text == "error":
            await send_message(ctx, "Keyword \"{0}\" has 0 good matches.".format(keyword))
        else:
            await send_message(ctx, remove_html_tags(verse_text))


@bot.command(
    name="quiz",
    help="Sends a random verse with either the reference, a single word, or a sentence missing for the user to solve.",
    brief="Quizzes the user on a random verse."
)
async def bible_quizzing(ctx, option: str = None):
    quizzer = str(ctx.author)
    if option is None:
        username = quizzer.split("#")[0]
        await send_message(ctx, "{0} provided no option. Choosing a random one.".format(username))
        options = ["ref", "word", "sentence"]
        option = options[random.randint(0, 2)]
        await send_message(ctx, "{0} your quizzing option is on: {1}".format(username, option))

    random_verse = get_random_verse()
    verse_text_start = random_verse.find("\"") + 1
    verse_text_end = random_verse.find("\"", verse_text_start)
    verse_text = random_verse[verse_text_start:verse_text_end]

    verse_reference_start_search = "\" - "
    verse_reference_start = random_verse.find(verse_reference_start_search) + len(verse_reference_start_search)
    verse_reference_end = random_verse.find(" ESV")
    verse_reference = random_verse[verse_reference_start:verse_reference_end]

    if option == "ref":
        quiz_verse = replace_characters(random_verse, verse_reference, "_")
        in_quiz[quizzer] = verse_reference
    elif option == "word":
        verse_words = verse_text.split(" ")
        remove_word = verse_words[random.randint(0, (len(verse_words) - 1))].replace(",", "")
        quiz_verse = replace_characters(random_verse, remove_word, "_")
        in_quiz[quizzer] = remove_word
    else:
        verse_words = verse_text.split(" ")
        remove_word_count = random.randint(2, (len(verse_words) - 1))
        remove_start_word_index = random.randint(0, (len(verse_words) - remove_word_count))
        remove_end_word_index = remove_start_word_index + remove_word_count - 1
        remove_start_word = verse_words[remove_start_word_index]
        remove_end_word = verse_words[remove_end_word_index]
        remove_sentence = random_verse[random_verse.find(remove_start_word):(random_verse.find(remove_end_word) + len(remove_end_word))]
        quiz_verse = replace_characters(random_verse, remove_sentence, "_")
        in_quiz[quizzer] = remove_sentence
        # all_words = ""
        # for i in range(remove_start_index, (remove_start_index + remove_word_count)):
        #     remove_word = verse_words[i].replace(",", "")
        #     quiz_verse = replace_characters(quiz_verse, remove_word, "_")
        #     all_words = "{0},{1}".format(all_words, remove_word)
        # in_quiz[quizzer] = all_words[1:(len(all_words) - 1)]

    await send_message(ctx, "{0}, your quiz is:\n{1}".format(ctx.author.mention, quiz_verse))


@bot.command(
    name="math",
    help="Provided two numbers and a method of operation, the bot will produce the result.",
    brief="Give two number and an operator, get result."
)
async def do_math(ctx, num_one: float = None, op: str = None, num_two: float = None):
    if num_one is None or op is None or num_two is None:
        await send_message(ctx, "Cannot perform math operations without all the necessary parts.")
    else:
        answer = operators[op](num_one, num_two)
        await send_message(ctx, "Answer: {0}".format(answer))


# Helper functions
# Async
async def filter_message(message):
    for word in swear_words:
        if word in message.content.lower():
            if is_banned_word(word, message.content.lower()):
                await delete_message(message, word)
                break


async def delete_message(message, word):
    await message.delete()
    logger.i("User {0} tried to use the banned word \"{1}\"".format(str(message.author).split("#")[0], word))
    response = "{0} no swearing while I'm around.".format(message.author.mention)
    await send_message(message, response)


async def send_message(message, msg):
    await message.channel.send(msg, allowed_mentions=discord.AllowedMentions().all())


# Non-Async
async def check_answer(message, answer: str):
    if "$quiz" in message.content:
        return
    quizzer = str(message.author)
    username = quizzer.split("#")[0]
    correct_answer: str = in_quiz[quizzer]
    if answer.lower() != correct_answer.lower():
        await send_message(message, "Sorry, {0}, that is incorrect. Was looking for:\n{1}".format(username, correct_answer))
    else:
        await send_message(message, "Congratulations, {0}, that is correct!".format(username))
    in_quiz.__delitem__(quizzer)


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


def get_votd_from_url() -> str:
    lookup_url = "{0}{1}".format(votd_base_url, "esv")
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_helper.unescape(html_bytes.decode("utf-8"))

    verse_text_start_search = "<span class=\"v1\">"
    verse_text_start_index = html.find(verse_text_start_search) + len(verse_text_start_search)
    verse_text_end_index = html.find("</span>", verse_text_start_index)

    verse_ref_start_search = "class=\"vc\">"
    verse_ref_start_index = html.find(verse_ref_start_search) + len(verse_ref_start_search)
    verse_ref_end_index = html.find("</a>", verse_ref_start_index)

    verse_text = html[verse_text_start_index:verse_text_end_index]
    reference = html[verse_ref_start_index:verse_ref_end_index]
    return "\"{0}\" - {1} ESV".format(verse_text, reference)


def get_verse_from_lookup_url(book: str, chapter_verse: str, book_num: str = None) -> str:
    book = book.capitalize()
    chapter_verse_split = chapter_verse.split(":")
    chapter = chapter_verse_split[0]
    verse = chapter_verse_split[1]
    if book_num is None:
        lookup_url = "{0}+{1}+{2}%3A{3}".format(verse_lookup_base_url, book, chapter, verse)
    else:
        lookup_url = "{0}{1}+{2}+{3}%3A{4}".format(verse_lookup_base_url, book_num, book, chapter, verse)

    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_helper.unescape(html_bytes.decode("utf-8"))

    verse_text_start_search = "<div class=\"crossref-verse\">"
    verse_text_sub_start_search = "<p>"
    verse_text_search_start_index = html.find(verse_text_start_search)
    verse_text_start_index = html.find(verse_text_sub_start_search, verse_text_search_start_index) + len(
        verse_text_sub_start_search)
    verse_text_end_index = html.find("</p>", verse_text_start_index)

    verse_text = html[verse_text_start_index:verse_text_end_index]
    if book_num is None:
        reference = "{0} {1}".format(book, chapter_verse)
    else:
        reference = "{0} {1} {2}".format(book_num, book, chapter_verse)
    return "\"{0}\" - {1} ESV".format(verse_text, reference)


def get_verse_from_keyword_url(word) -> str:
    lookup_url = "{0}{1}&version=ESV".format(keyword_search_base_url, word)
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_helper.unescape(html_bytes.decode("utf-8"))

    verse_text_start_search = "<div class=\"bible-item-text\">"
    verse_text_start_index = html.find(verse_text_start_search)
    if verse_text_start_index == -1:
        verse_text_start_search = "div class=\"bible-item-text col-sm-9\">"
        verse_text_start_index = html.find(verse_text_start_search)
        if verse_text_start_index == -1:
            return "error"
    verse_text_end_index = html.find("<div class=\"bible-item-extras\">", verse_text_start_index)

    verse_ref_start_search = "<a class=\"bible-item-title\""
    verse_ref_sub_start_search = ">"
    verse_ref_search_start_index = html.find(verse_ref_start_search)
    verse_ref_start_index = html.find(verse_ref_sub_start_search, verse_ref_search_start_index) + len(
        verse_ref_sub_start_search)
    verse_ref_end_index = html.find("</a>", verse_ref_start_index)

    verse_text_adjusted_start_index = verse_text_start_index + len(verse_text_start_search)
    verse_text = html[verse_text_adjusted_start_index:verse_text_end_index]
    if "<h3>" in verse_text:
        verse_text_start_search = "</h3>"
        verse_text_start_index = verse_text.find(verse_text_start_search) + len(verse_text_start_search)
        verse_text_end_index = verse_text.find("<div class=\"bible-item-extras\">", verse_text_start_index)
        verse_text = verse_text[verse_text_start_index:verse_text_end_index]
    reference = html[verse_ref_start_index:verse_ref_end_index]

    while verse_text[0] == "\n":
        verse_text = verse_text[1:]

    return "\"{0}\" - {1} ESV".format(verse_text, reference)


def get_random_verse() -> str:
    with open("books_of_the_bible.csv") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        bible_dict = {}
        book_names = []
        skip_first_row = True
        for row in csv_reader:
            if not skip_first_row:
                skip_first_row = True
            else:
                book_name = row[BIBLE_DICT_NAME]
                bible_dict[book_name] = row
                book_names.append(book_name)

        random_book: str = book_names[random.randint(0, (len(book_names) - 1))]
        while random_book == "Song of Solomon":
            random_book: str = book_names[random.randint(0, (len(book_names) - 1))]
        logger.d("Random book fetched = {0}".format(random_book))
        random_book_stats = bible_dict.get(random_book)
        random_book_chapters = int(random_book_stats[BIBLE_DICT_CHAPTERS])
        logger.d("Random book chapter count = {0}".format(random_book_chapters))
        random_book_chapter = random.randint(1, random_book_chapters)
        logger.d("Random book chapter chosen = {0}".format(random_book_chapter))
        random_book_verses = int(random_book_stats[str(random_book_chapter)])
        logger.d("Random book verse count for selected chapter = {1}".format(random_book_chapter, random_book_verses))
        random_book_verse = random.randint(1, random_book_verses)
        logger.d("Random book verse selected = {0}".format(random_book_verse))
        random_chapter_verse = "{0}:{1}".format(random_book_chapter, random_book_verse)

        if " " in random_book:
            random_book_split = random_book.split(" ")
            bna = random_book_split[1]
            bnu = random_book_split[0]
            verse_text = get_verse_from_lookup_url(bna, random_chapter_verse, bnu)
        else:
            verse_text = get_verse_from_lookup_url(random_book, random_chapter_verse, None)

        return remove_html_tags(verse_text)


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


def remove_html_tags(text: str) -> str:
    has_tag = "<" in text
    while has_tag:
        open_tag_index = text.find("<")
        end_tag_index = text.find(">") + 1
        text = text.replace(text[open_tag_index:end_tag_index], "")
        has_tag = "<" in text
    return text


def replace_characters(s: str, c: str, r: str) -> str:
    # Replaces characters "c" in string "s" with character "r"
    full_replace_string = ""
    for i in range(0, len(c), len(r)):
        full_replace_string = "{0}\\{1}".format(full_replace_string, r)
    return s.replace(c, full_replace_string)


bot.run(TOKEN)
