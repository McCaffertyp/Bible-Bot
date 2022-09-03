#############
# Constants #
#############
RETURN_ERROR = "error"
NUMBERS_STRING = "0123456789"
ENGLISH_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
SPECIAL_CHARACTERS = "`~!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?"
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
    for c in ENGLISH_ALPHABET:
        if c not in guessed_letters:
            remaining_letters = "{0}, {1}".format(remaining_letters, c)
    return remaining_letters[2:]


def handle_discord_formatting(text: str) -> str:
    discord_formatted = ""
    for c in text:
        if c == "_" or c == "*":
            discord_formatted = "{0}\\{1}".format(discord_formatted, c)
        else:
            discord_formatted = "{0}{1}".format(discord_formatted, c)

    return discord_formatted


def is_banned_word(swear_words: list, swear_word: str, sentence: str) -> bool:
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
    # Replaces characters "c" in string "s" with character "r"
    full_replace_string = ""
    for i in range(0, len(c), len(r)):
        full_replace_string = "{0}\\{1}".format(full_replace_string, r)
    return s.replace(c, " {0} ".format(full_replace_string))


def remove_emojis(s: str) -> str:
    sentence = ""
    for c in s:
        if c.lower() in ENGLISH_ALPHABET or c in SPECIAL_CHARACTERS or c in NUMBERS_STRING or c == " ":
            sentence = "{0}{1}".format(sentence, c)
    return sentence
