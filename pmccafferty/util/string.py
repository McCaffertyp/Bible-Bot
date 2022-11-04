import csv

from typing import List

#############
# Constants #
#############
BIBLE_DICT_NAME = "Name"
RETURN_ERROR = "RETURN_ERROR"
NUMBERS_STRING = "0123456789"
ENGLISH_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
SPECIAL_CHARACTERS = "`~!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?“"
HASH_SKIPS = {"0": 13, "1": 8, "2": 1, "3": 42, "4": 27}


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


def get_only_words(word_list: list) -> list:
    words = []
    for word in word_list:
        stripped_word = remove_non_alphabet(word)
        if len(stripped_word) > 0:
            words.append(stripped_word)
    return words


def get_remaining_letters(guessed_letters: str) -> str:
    remaining_letters = ""
    for c in ENGLISH_ALPHABET[:26]:
        if c not in guessed_letters:
            remaining_letters = "{0}, {1}".format(remaining_letters, c.upper())
    return remaining_letters[2:]


def handle_discord_formatting(text: str) -> str:
    discord_formatted = ""
    for c in text:
        if c == "_" or c == "*":
            discord_formatted = "{0}\\{1}".format(discord_formatted, c)
        else:
            discord_formatted = "{0}{1}".format(discord_formatted, c)

    return discord_formatted


def is_banned_word(swear_word: str, check_word: str) -> bool:
    base_word = remove_repeated_letters(check_word)
    return swear_word == base_word


def remove_repeated_letters(word: str) -> str:
    if len(word) <= 1:
        return word

    s: str = word[0]
    c: str = word[0]
    for cc in word[1:]:
        if c == cc:
            continue
        else:
            s = "{0}{1}".format(s, cc)
            c = cc
    return s


def make_valid_firebase_name(s: str) -> str:
    if "𝕁𝕒𝕧𝕒" in s:
        s = s.replace("𝕁𝕒𝕧𝕒", "Java")
    return s.replace(".", "").replace(",", "")


def quick_hash(s: str, loop_count: int, hash_length: int = 25) -> str:
    hashed_string = ""
    words_only = get_only_words(s.split())
    for word in words_only:
        hashed_string = "{0}{1}".format(hashed_string, word)

    while len(hashed_string) < hash_length:
        hashed_string = "{0}{1}".format(hashed_string, hashed_string)

    hashed_string = hashed_string[0:hash_length]

    for i in range(0, loop_count):
        for j in range(0, hash_length):
            c = hashed_string[j]
            hash_skip = HASH_SKIPS[str(i % 5)]
            hash_index = ENGLISH_ALPHABET.find(c) + hash_skip
            if hash_index > 51:
                hash_index -= 52
            elif hash_index < 0:
                hash_index = 0
            hashed_string = "{0}{1}{2}".format(hashed_string[:j], ENGLISH_ALPHABET[hash_index], hashed_string[j + 1:])

    return hashed_string


def remove_html_tags(text: str) -> str:
    has_tag = "<" in text
    while has_tag:
        open_tag_index = text.find("<")
        end_tag_index = text.find(">") + 1
        text = text.replace(text[open_tag_index:end_tag_index], "")
        has_tag = "<" in text
    return text


def remove_non_alphabet(s: str) -> str:
    base_word = ""
    for c in s:
        if c.lower() in ENGLISH_ALPHABET:
            base_word = "{0}{1}".format(base_word, c)
    return base_word


def replace_characters(s: str, c: str, r: str) -> str:
    # Replaces characters c in string s with r
    full_replace_string = ""
    for i in range(0, len(c), len(r)):
        full_replace_string = "{0}\\{1}".format(full_replace_string, r)
    return s.replace(c, "{0}".format(full_replace_string))


def replace_characters_range(s: str, start: int, end: int, r: str) -> str:
    # Replaces characters s[start:end] with r
    full_replace_string = ""
    for i in range(start, end, len(r)):
        full_replace_string = "{0}\\{1}".format(full_replace_string, r)
    return "{0}{1}{2}".format(s[:start], full_replace_string, s[end:])


def replace_words(s: str, w: str, r: str) -> str:
    # Replaces all words w in string s with r
    i = 0
    while i < len(s):
        char = s[i]
        if char.lower() in ENGLISH_ALPHABET:
            word_end_index = i + len(w)
            if word_end_index >= len(s) - 1:
                return s
            word_compare = s[i:word_end_index]
            letter_check = s[word_end_index]
            if word_compare == w and letter_check not in ENGLISH_ALPHABET:
                s = replace_characters_range(s, i, word_end_index, r)
        elif char in SPECIAL_CHARACTERS:
            i += 1
            continue
        i = s.find(" ", i) + 1
    return s


def remove_emojis(s: str) -> str:
    sentence = ""
    for c in s:
        if c.lower() in ENGLISH_ALPHABET or c in SPECIAL_CHARACTERS or c in NUMBERS_STRING or c == " ":
            sentence = "{0}{1}".format(sentence, c)
    return sentence


def contains_characters(check_string: str, check_list: List[str]) -> bool:
    for c in check_list:
        if c in check_string:
            return True
    return False


def is_book_of_the_bible(s: str) -> bool:
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

        return s.lower() in book_names
