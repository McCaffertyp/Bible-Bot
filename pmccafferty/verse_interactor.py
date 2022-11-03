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
LOG_TAG = "verse_interactor"
BOOK_NOT_FOUND_ERROR = "BOOK_NOT_FOUND_ERROR"
CHAPTER_NOT_FOUND_ERROR = "CHAPTER_NOT_FOUND_ERROR"
VERSE_NOT_FOUND_ERROR = "VERSE_NOT_FOUND_ERROR"
VALID_LOOKUP = "VALID_LOOKUP"
BIBLE_DICT_NAME = "Name"
BIBLE_DICT_CHAPTERS = "Chapters"
BIBLE_DICT_TOTAL_VERSES = "Total Verses"
BIBLE_DICT_AVG_VERSES = "Average Verses"
VOTD_BASE_URL = "https://dailyverses.net/"
VERSE_LOOKUP_BASE_URL = "https://www.openbible.info/labs/cross-references/search?q="
KEYWORDS_BASE_URL = "https://www.biblegateway.com/quicksearch/?quicksearch="


async def lookup_verses(context: Context, book_or_book_num: str = None, book_or_chapter_verses: str = None, chapter_verses: str = None):
    if book_or_book_num is None:
        await ChannelInteractor.send_message(context, "Unfortunately I cannot look that up. The Book was not provided.")
    elif book_or_chapter_verses is None:
        await ChannelInteractor.send_message(context, "Unfortunately I cannot look that up. The Chapter:Verse was not provided.")
    elif is_chapter_verses(book_or_chapter_verses) and ":" not in book_or_chapter_verses:
        await ChannelInteractor.send_message(context, "Unfortunately I cannot look that up. The Chapter:Verse was not in the proper format.")
    elif chapter_verses is not None and ":" not in chapter_verses:
        await ChannelInteractor.send_message(context, "Unfortunately I cannot look that up. The Chapter:Verse was not in the proper format.")
    else:
        book_num = -1
        if is_book_num(book_or_book_num):
            book_num = int(book_or_book_num)

        if book_num == -1:
            is_valid_lookup = is_valid_book_chapter_verses(book_or_book_num, book_or_chapter_verses)
            if is_valid_lookup == VALID_LOOKUP:
                verse_text = build_full_lookup_verse_text(book_or_book_num.lower(), book_or_chapter_verses)
            else:
                await ChannelInteractor.send_message(context, "What you tried to lookup does not exist.")
                return
        else:
            is_valid_lookup = is_valid_book_chapter_verses(book_or_chapter_verses, chapter_verses, book_num)
            if is_valid_lookup == VALID_LOOKUP:
                verse_text = build_full_lookup_verse_text(book_or_chapter_verses.lower(), chapter_verses, book_num)
            else:
                await ChannelInteractor.send_message(context, "What you tried to lookup does not exist.")
                return

        if StringHelper.RETURN_ERROR in verse_text:
            if book_num == -1:
                logger.w(LOG_TAG, "Verse lookup \"{0} {1}\" is not a valid reference".format(book_or_book_num, book_or_chapter_verses))
                await ChannelInteractor.send_message(context, "Verse lookup \"{0} {1}\" is not a valid reference.".format(book_or_book_num, book_or_chapter_verses))
            else:
                logger.w(LOG_TAG, "Verse lookup \"{0} {1} {2}\" is not a valid reference".format(book_or_book_num, book_or_chapter_verses, chapter_verses))
                await ChannelInteractor.send_message(context, "Verse lookup \"{0} {1} {2}\" is not a valid reference.".format(book_or_book_num, book_or_chapter_verses, chapter_verses))
            return
        else:
            await ChannelInteractor.send_embedded_message(
                context,
                title="Verse Lookup",
                description=StringHelper.remove_html_tags(verse_text)
            )


def build_full_lookup_verse_text(book: str, chapter_verses: str, book_num: int = -1) -> str:
    full_verse_text = ""
    chapter_verses_split = chapter_verses.split(":")
    chapter = chapter_verses_split[0]
    verses = chapter_verses_split[1]
    if book_num == -1:
        if "-" not in verses:
            return get_verse_from_lookup_url(book.lower(), chapter_verses)
        else:
            verses_split = verses.split("-")
            start_verse_num = int(verses_split[0])
            end_verse_num = int(verses_split[1])
            for i in range(start_verse_num, end_verse_num + 1):
                full_verse_text = "{0} {1}".format(full_verse_text, get_verse_from_lookup_url(book.lower(), "{0}:{1}".format(chapter, str(i)), text_only=True))
                if StringHelper.RETURN_ERROR in full_verse_text:
                    return StringHelper.RETURN_ERROR
            reference = "{0} {1}".format(book.capitalize(), chapter_verses)
            return "\"{0}\" - {1} ESV".format(full_verse_text[1:], reference)
    else:
        if "-" not in verses:
            return get_verse_from_lookup_url(book.lower(), chapter_verses, str(book_num))
        else:
            verses_split = verses.split("-")
            start_verse_num = int(verses_split[0])
            end_verse_num = int(verses_split[1])
            for i in range(start_verse_num, end_verse_num + 1):
                full_verse_text = "{0} {1}".format(full_verse_text, get_verse_from_lookup_url(book.lower(), "{0}:{1}".format(chapter, str(i)), str(book_num), text_only=True))
                if StringHelper.RETURN_ERROR in full_verse_text:
                    return StringHelper.RETURN_ERROR
            reference = "{0} {1} {2}".format(str(book_num), book.capitalize(), chapter_verses)
            return "\"{0}\" - {1} ESV".format(full_verse_text[1:], reference)


async def search_keywords(context: Context, keywords: str = None):
    if keywords is None:
        await ChannelInteractor.send_message(context, "Unfortunately nothing popped up for that, since nothing was entered.")
    else:
        verse_text = get_verse_from_search_url(keywords)
        if verse_text == StringHelper.RETURN_ERROR:
            await ChannelInteractor.send_message(context, "Keywords \"{0}\" has 0 good matches.".format(keywords))
        else:
            await ChannelInteractor.send_embedded_message(
                context,
                title="Keyword Search",
                description=StringHelper.remove_html_tags(verse_text)
            )


def get_votd_from_url() -> str:
    lookup_url = "{0}{1}".format(VOTD_BASE_URL, "esv")
    logger.d(LOG_TAG, "VOTD lookup_url={0}".format(lookup_url))
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


def get_verse_from_lookup_url(book: str, chapter_verse: str, book_num: str = None, text_only: bool = False) -> str:
    book = book.capitalize()
    chapter_verse_split = chapter_verse.split(":")
    chapter = chapter_verse_split[0]
    verse = chapter_verse_split[1]
    logger.d(LOG_TAG, "Looking up: book_num={0}, book={1}, chapter={2}, verse={3}".format(book_num, book, chapter, verse))
    if book_num is None:
        lookup_url = "{0}{1}+{2}%3A{3}".format(VERSE_LOOKUP_BASE_URL, book.replace(" ", "+"), chapter, verse)
    else:
        lookup_url = "{0}{1}+{2}+{3}%3A{4}".format(VERSE_LOOKUP_BASE_URL, book_num, book.replace(" ", "+"), chapter, verse)

    logger.d(LOG_TAG, "Using url={0}".format(lookup_url))
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

    if text_only:
        return verse_text
    else:
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
            logger.d(LOG_TAG, "Random book fetched = {0}".format(book))
        else:
            if book.lower() not in bible_dict:
                logger.e(LOG_TAG, "Was unable to fetch provided book: {0}".format(book))
                return StringHelper.RETURN_ERROR
            logger.d(LOG_TAG, "Using user supplied book = {0}".format(book))
        random_book_stats = bible_dict.get(book.lower())
        random_book_chapters = int(random_book_stats[BIBLE_DICT_CHAPTERS])
        logger.d(LOG_TAG, "Random book chapter count = {0}".format(random_book_chapters))
        random_book_chapter = random.randint(1, random_book_chapters)
        logger.d(LOG_TAG, "Random book chapter chosen = {0}".format(random_book_chapter))
        random_book_verses = int(random_book_stats[str(random_book_chapter)])
        logger.d(LOG_TAG, "Random book verse count for selected chapter = {1}".format(random_book_chapter, random_book_verses))
        random_book_verse = random.randint(1, random_book_verses)
        logger.d(LOG_TAG, "Random book verse selected = {0}".format(random_book_verse))
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


####################
# Helper Functions #
####################

#############
# Non-Async #
#############
def is_valid_book_chapter_verses(book: str, chapter_verses: str, book_num: int = -1) -> str:
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

        book_check = book
        if book_num != -1:
            book_check = "{0} {1}".format(book_num, book_check)

        if book_check.lower() not in bible_dict:
            logger.e(LOG_TAG, "Was unable to fetch provided book: {0}".format(book_check))
            return BOOK_NOT_FOUND_ERROR

        book_check_stats = bible_dict.get(book_check.lower())

        chapter_verses_split = chapter_verses.split(":")
        book_check_chapter = chapter_verses_split[0]
        book_check_chapter_count = int(book_check_stats[BIBLE_DICT_CHAPTERS])
        if int(book_check_chapter) > book_check_chapter_count:
            logger.e(LOG_TAG, "Provided chapter is out of scope of the book provided. Book={0}, Chapter={1}".format(book_check, book_check_chapter))
            return CHAPTER_NOT_FOUND_ERROR

        book_check_verses = chapter_verses_split[1]
        book_check_verse_count = int(book_check_stats[str(book_check_chapter)])
        if "-" in book_check_verses:
            verses_split = book_check_verses.split("-")
            start_verse = int(verses_split[0])
            end_verse = int(verses_split[1])
            if start_verse > book_check_verse_count or end_verse > book_check_verse_count:
                logger.e(LOG_TAG, "Provided verse range is out of scope of the book and chapter provided. Book={0}, Chapter={1}, Verses={2}".format(book_check, book_check_chapter, book_check_verses))
                return VERSE_NOT_FOUND_ERROR
        else:
            if int(book_check_verses) > book_check_verse_count:
                logger.e(LOG_TAG, "Provided verse range is out of scope of the book and chapter provided. Book={0}, Chapter={1}, Verses={2}".format(book_check, book_check_chapter, book_check_verses))
                return VERSE_NOT_FOUND_ERROR

    return VALID_LOOKUP


def is_book_num(book_or_book_num: str) -> bool:
    try:
        int(book_or_book_num)
        return True
    except Exception as error:
        logger.d(LOG_TAG, error)
        return False


def is_chapter_verses(book_or_chapter_verses: str) -> bool:
    if ":" in book_or_chapter_verses:
        return True
    else:
        return not StringHelper.contains_characters(book_or_chapter_verses, StringHelper.ENGLISH_ALPHABET)
