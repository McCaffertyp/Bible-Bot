import csv
import html as html_helper
import http.client
import random
from urllib.request import urlopen

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
KEYWORD_SEARCH_BASE_URL = "https://www.biblegateway.com/quicksearch/?quicksearch="


def get_votd_from_url() -> str:
    lookup_url = "{0}{1}".format(VOTD_BASE_URL, "esv")
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


def get_verse_from_keyword_url(word) -> str:
    lookup_url = "{0}{1}&version=ESV".format(KEYWORD_SEARCH_BASE_URL, word)
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
