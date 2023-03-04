import argparse

from os import environ as env
from file_engine import BEPUB, BText
from translate_engine import GPT3, ChatGPT


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--book_name",
        dest="book_name",
        type=str,
        help="your epub book name",
    )
    parser.add_argument(
        "--openai_key",
        dest="openai_key",
        type=str,
        default="",
        help="openai api key",
    )
    parser.add_argument(
        "--no_limit",
        dest="no_limit",
        action="store_true",
        default=False,
        help="if you pay add it",
    )
    parser.add_argument(
        "--test",
        dest="test",
        action="store_true",
        default=False,
        help="if test we only translat 10 contents you can easily check",
    )
    parser.add_argument(
        "--test_num",
        dest="test_num",
        type=int,
        default=10,
        help="test num for the test",
    )
    parser.add_argument(
        "-m",
        "--model",
        dest="model",
        type=str,
        default="chatgpt",
        choices=["chatgpt", "gpt3"],  # support DeepL later
        help="Use which model",
    )
    parser.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        default=False,
        help="if program accidentally stop you can use this to resume",
    )
    parser.add_argument(
        "--lang",
        dest="lang",
        type=str,
        default="zh-tw",
        choices=["zh-cn", "zh-tw", "jp"],
        help="Choose lang for zh-cn (Simplified Chinese) or zh-tw (Traditional Chinese)",
    )
    options = parser.parse_args()
    return options


if __name__ == "__main__":
    options = get_parser()

    no_limit = options.no_limit
    is_test = options.test
    test_number = options.test_num
    book_name = options.book_name
    resume = options.resume
    open_ai_api_key = options.openai_key or env.get("OPENAI_API_KEY")

    if not open_ai_api_key:
        raise Exception("Need openai API key, please google how to")

    if options.lang == "zh-cn":
        lang = "Simplified Chinese"
    elif options.lang == "zh-tw":
        lang = "Traditional Chinese"
    elif options.lang == "jp":
        lang = "Japanese"
    else:
        lang = "Traditional Chinese"

    if book_name.endswith(".epub"):
        FileEngine = BEPUB
    elif book_name.endswith(".txt"):
        FileEngine = BText
    else:
        raise Exception("Only support epub and txt file")

    if options.model == "gpt3":
        translate_engine_class = GPT3
    else:
        translate_engine_class = ChatGPT

    translate_engine = translate_engine_class(open_ai_api_key, lang, no_limit)
    book = FileEngine(translate_engine, book_name,
                      resume, is_test, test_number)
    book.make_bilingual_book()
