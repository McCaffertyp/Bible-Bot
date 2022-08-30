import csv
import html as html_helper
import http.client
import random
from urllib.request import urlopen

from discord.ext.commands.context import Context

import channel_interactor as ChannelInteractor
import util.string as StringHelper
from util import logger

#############
# Constants #
#############
BIBLE_DICT_NAME = "Name"
BIBLE_DICT_CHAPTERS = "Chapters"
BIBLE_DICT_TOTAL_VERSES = "Total Verses"
BIBLE_DICT_AVG_VERSES = "Average Verses"
VOTD_BASE_URL = "https://dailyverses.net/"
VERSE_LOOKUP_BASE_URL = "https://www.openbible.info/labs/cross-references/search?q="
KEYWORDS_BASE_URL = "https://www.biblegateway.com/quicksearch/?quicksearch="


async def lookup_verse(context: Context, book: str = None, chapter_verse: str = None, book_num: str = None):
    if book is None:
        await ChannelInteractor.send_message(context, "Unfortunately I cannot look that up. The Book was not provided.")
    elif chapter_verse is None:
        await ChannelInteractor.send_message(context, "Unfortunately I cannot look that up. The Chapter:Verse was not provided.")
    elif ":" not in chapter_verse:
        await ChannelInteractor.send_message(context, "Unfortunately I cannot look that up. The Chapter:Verse was not in the proper format.")
    else:
        if book_num is not None:
            if int(book_num) > 3 or int(book_num) < 1:
                await ChannelInteractor.send_message(context, "Unfortunately I cannot look that up. The entered Book Number does not exist.")
        verse_text = get_verse_from_lookup_url(book.lower(), chapter_verse, book_num)
        if verse_text == "error":
            if book_num is not None:
                logger.w("Verse lookup \"{0} {1} {2}\" is not a valid reference".format(book_num, book, chapter_verse))
                await ChannelInteractor.send_message(context, "Verse lookup \"{0} {1} {2}\" is not a valid reference.".format(book_num, book, chapter_verse))
            else:
                logger.w("Verse lookup \"{0} {1}\" is not a valid reference".format(book, chapter_verse))
                await ChannelInteractor.send_message(context, "Verse lookup \"{0} {1}\" is not a valid reference.".format(book, chapter_verse))
            return
        else:
            await ChannelInteractor.send_message(context, StringHelper.remove_html_tags(verse_text))


async def search_keywords(context: Context, keywords: str = None):
    if keywords is None:
        await ChannelInteractor.send_message(context, "Unfortunately nothing popped up for that, since nothing was entered.")
    else:
        verse_text = get_verse_from_search_url(keywords)
        if verse_text == "error":
            await ChannelInteractor.send_message(context, "Keywords \"{0}\" has 0 good matches.".format(keywords))
        else:
            await ChannelInteractor.send_message(context, StringHelper.remove_html_tags(verse_text))


def get_votd_from_url() -> str:
    lookup_url = "{0}{1}".format(VOTD_BASE_URL, "esv")
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_helper.unescape(html_bytes.decode("utf-8"))

    verse_text_start_search = "<span class=\"v1\">"
    verse_text_start_index = html.find(verse_text_start_search) + len(verse_text_start_search)
    sub_span_style_search = "all-small-caps"
    sub_span_style_start_index = html.find(sub_span_style_search, verse_text_start_index)
    html_span_close_tag = "</span>"
    if sub_span_style_start_index != -1:
        sub_span_style_end_index = html.find(html_span_close_tag, sub_span_style_start_index)
        verse_text_end_index = html.find(html_span_close_tag, (sub_span_style_end_index + len(html_span_close_tag)))
    else:
        verse_text_end_index = html.find(html_span_close_tag, verse_text_start_index)

    verse_ref_start_search = "class=\"vc\">"
    verse_ref_start_index = html.find(verse_ref_start_search) + len(verse_ref_start_search)
    verse_ref_end_index = html.find("</a>", verse_ref_start_index)

    verse_text = StringHelper.remove_html_tags(html[verse_text_start_index:verse_text_end_index])
    reference = html[verse_ref_start_index:verse_ref_end_index]
    return "\"{0}\" - {1} ESV".format(verse_text, reference)


def get_verse_from_lookup_url(book: str, chapter_verse: str, book_num: str = None) -> str:
    book = book.capitalize()
    chapter_verse_split = chapter_verse.split(":")
    chapter = chapter_verse_split[0]
    verse = chapter_verse_split[1]
    logger.d("Looking up: book_num={0}, book={1}, chapter={2}, verse={3}".format(book_num, book, chapter, verse))
    if book_num is None:
        lookup_url = "{0}{1}+{2}%3A{3}".format(VERSE_LOOKUP_BASE_URL, book.replace(" ", "+"), chapter, verse)
    else:
        lookup_url = "{0}{1}+{2}+{3}%3A{4}".format(VERSE_LOOKUP_BASE_URL, book_num, book.replace(" ", "+"), chapter, verse)

    logger.d("Using url={0}".format(lookup_url))
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_helper.unescape(html_bytes.decode("utf-8"))

    verse_text_start_search = "<div class=\"crossref-verse\">"
    verse_text_sub_start_search = "<p>"
    verse_text_search_start_index = html.find(verse_text_start_search)
    if verse_text_search_start_index == -1:
        return StringHelper.RETURN_ERROR
    verse_text_start_index = html.find(verse_text_sub_start_search, verse_text_search_start_index) + len(verse_text_sub_start_search)
    verse_text_end_index = html.find("</p>", verse_text_start_index)

    verse_text = html[verse_text_start_index:verse_text_end_index]
    if book_num is None:
        reference = "{0} {1}".format(book, chapter_verse)
    else:
        reference = "{0} {1} {2}".format(book_num, book, chapter_verse)
    return "\"{0}\" - {1} ESV".format(verse_text, reference)


def get_verse_from_search_url(query: str) -> str:
    query_words = StringHelper.get_only_words(query.split())
    search_text = query_words[0]
    for i in range(1, len(query_words)):
        search_text = "{0}+{1}".format(search_text, query_words[i])
    lookup_url = "{0}{1}&version=ESV".format(KEYWORDS_BASE_URL, search_text)
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_helper.unescape(html_bytes.decode("utf-8"))

    verse_text_start_search = "<div class=\"bible-item-text\">"
    verse_text_start_index = html.find(verse_text_start_search)
    if verse_text_start_index == -1:
        verse_text_start_search = "div class=\"bible-item-text col-sm-9\">"
        verse_text_start_index = html.find(verse_text_start_search)
        if verse_text_start_index == -1:
            return StringHelper.RETURN_ERROR
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


def get_random_verse(book: str = None) -> str:
    with open("data/bible_data_esv.csv") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        bible_dict = {}
        book_names = []
        skip_first_row = True
        for row in csv_reader:
            if not skip_first_row:
                skip_first_row = True
            else:
                book_name = row[BIBLE_DICT_NAME].lower()
                bible_dict[book_name] = row
                book_names.append(book_name)

        if book is None:
            book: str = book_names[random.randint(0, (len(book_names) - 1))]
            logger.d("Random book fetched = {0}".format(book))
        else:
            if book.lower() not in bible_dict:
                logger.e("Was unable to fetch provided book: {0}".format(book))
                return "error"
            logger.d("Using user supplied book = {0}".format(book))
        random_book_stats = bible_dict.get(book.lower())
        random_book_chapters = int(random_book_stats[BIBLE_DICT_CHAPTERS])
        logger.d("Random book chapter count = {0}".format(random_book_chapters))
        random_book_chapter = random.randint(1, random_book_chapters)
        logger.d("Random book chapter chosen = {0}".format(random_book_chapter))
        random_book_verses = int(random_book_stats[str(random_book_chapter)])
        logger.d("Random book verse count for selected chapter = {1}".format(random_book_chapter, random_book_verses))
        random_book_verse = random.randint(1, random_book_verses)
        logger.d("Random book verse selected = {0}".format(random_book_verse))
        random_chapter_verse = "{0}:{1}".format(random_book_chapter, random_book_verse)

        if " " in book:
            if "Song" in book:
                verse_text = get_verse_from_lookup_url(book, random_chapter_verse, None)
            else:
                random_book_split = book.split(" ")
                bna = random_book_split[1]
                bnu = random_book_split[0]
                verse_text = get_verse_from_lookup_url(bna, random_chapter_verse, bnu)
        else:
            verse_text = get_verse_from_lookup_url(book, random_chapter_verse, None)

        return StringHelper.remove_html_tags(verse_text)
