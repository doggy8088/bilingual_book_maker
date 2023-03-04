import argparse
import pickle
import time
import os

from abc import abstractmethod
from copy import copy
from os import environ as env
from pathlib import Path

import openai
import requests
from bs4 import BeautifulSoup as bs
from ebooklib import epub
from rich import print

NO_LIMIT = False
IS_TEST = False
RESUME = False
LANG = "Traditional Chinese"


class Base:
    def __init__(self, key):
        pass

    @abstractmethod
    def translate(self, text):
        pass


class GPT3(Base):
    def __init__(self, key):
        self.api_key = key
        self.api_url = "https://api.openai.com/v1/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # TODO support more models here
        self.data = {
            "prompt": "",
            "model": "text-davinci-003",
            "max_tokens": 1024,
            "temperature": 1,
            "top_p": 1,
        }
        self.session = requests.session()

    def translate(self, text):
        print(text)
        self.data["prompt"] = f"Please help me to translate the following text to {LANG}: \n\n{text}"
        r = self.session.post(
            self.api_url, headers=self.headers, json=self.data)
        if not r.ok:
            return text
        t_text = r.json().get("choices")[0].get("text", "").strip()
        print(t_text)
        return t_text


class DeepL(Base):
    def __init__(self, session, key):
        super().__init__(session, key)

    def translate(self, text):
        return super().translate(text)


class ChatGPT(Base):
    def __init__(self, key):
        super().__init__(key)
        self.key = key

    def translate(self, text):
        print(text)
        openai.api_key = self.key
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        # english prompt here to save tokens
                        "content": f"Please help me to translate the following text to {LANG}. Please return only translated content not include the origin text. Here is the text: \n\n{text}",
                    }
                ],
            )
            t_text = (
                completion["choices"][0]
                .get("message")
                .get("content")
                .encode("utf8")
                .decode()
            )
            if not NO_LIMIT:
                # for time limit
                time.sleep(3)
        except Exception as e:
            print(str(e), "will sleep 60 seconds")
            # TIME LIMIT for open api please pay
            time.sleep(60)
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "user",
                        "content": f"Please help me to translate the following text to {LANG}. Please return only translated content not include the origin text. Here is the text: \n\n{text}",
                    }
                ],
            )
            t_text = (
                completion["choices"][0]
                .get("message")
                .get("content")
                .encode("utf8")
                .decode()
            )
        print(t_text)
        return t_text


class BEPUB:
    def __init__(self, epub_name, model, key, resume):
        self.epub_name = epub_name
        self.new_epub = epub.EpubBook()
        self.translate_model = model(key)
        self.origin_book = epub.read_epub(self.epub_name)
        self.p_to_save = []
        self.resume = resume
        self.bin_path = f"{Path(epub_name).parent}/.{Path(epub_name).stem}.temp.bin"
        if self.resume:
            self.load_state()

    @staticmethod
    def _is_special_text(text):
        return text.isdigit() or text.isspace()

    def make_bilingual_book(self):
        new_book = epub.EpubBook()
        new_book.metadata = self.origin_book.metadata
        new_book.spine = self.origin_book.spine
        new_book.toc = self.origin_book.toc
        all_items = list(self.origin_book.get_items())
        # we just translate tag p
        all_p_length = sum(
            [len(bs(i.content, "html.parser").findAll("p")) for i in all_items]
        )
        print("TODO need process bar here: " + str(all_p_length))
        index = 0
        p_to_save_len = len(self.p_to_save)
        try:
            for i in self.origin_book.get_items():
                if i.get_type() == 9:
                    soup = bs(i.content, "html.parser")
                    p_list = soup.findAll("p")
                    is_test_done = IS_TEST and index > TEST_NUM
                    for p in p_list:
                        if is_test_done or not p.text or self._is_special_text(p.text):
                            continue
                        new_p = copy(p)
                        # TODO banch of p to translate then combine
                        # PR welcome here
                        if self.resume and index < p_to_save_len:
                            new_p.string = self.p_to_save[index]
                        else:
                            new_p.string = self.translate_model.translate(
                                p.text)
                            self.p_to_save.append(new_p.text)
                        p.insert_after(new_p)
                        index += 1
                        if IS_TEST and index > TEST_NUM:
                            break
                    i.content = soup.prettify().encode()
                new_book.add_item(i)
            name = self.epub_name.split(".")[0]
            epub.write_epub(f"{name}_bilingual.epub", new_book, {})
        except (KeyboardInterrupt, Exception) as e:
            print(e)
            print("you can resume it next time")
            self.save_progress()
            exit(0)

    def load_state(self):
        try:
            with open(self.bin_path, "rb") as f:
                self.p_to_save = pickle.load(f)
        except:
            raise Exception("can not load resume file")

    def save_progress(self):
        try:
            with open(self.bin_path, "wb") as f:
                pickle.dump(self.p_to_save, f)
        except:
            raise Exception("can not save resume file")


class Text:
    def __init__(self, book_name, model, key, resume):
        self.book_name = book_name
        self.translate_model = model(key)
        self.origin_book = self.load_file(self.book_name).split("\n")
        self.p_to_save = []
        self.resume = resume
        self.bin_path = f"{os.path.abspath(self.book_name)}.bin.temp"
        if self.resume:
            self.load_state()

    @staticmethod
    def _is_special_text(text):
        return text.isdigit() or text.isspace()

    def make_bilingual_book(self):
        new_book = epub.EpubBook()
        all_p_length = len(self.origin_book)
        print("TODO need process bar here: " + str(all_p_length))
        index = 0
        p_to_save_len = len(self.p_to_save)
        try:
            for i in self.origin_book:
                if self._is_special_text(i):
                    continue
                if self.resume and index < p_to_save_len:
                    pass
                else:
                    temp = self.translate_model.translate(i)
                    self.p_to_save.append(temp)
                index += 1
                if IS_TEST and index > TEST_NUM:
                    break
            name = self.book_name.split(".")[0]
            self.save_file(f"{name}_bilingual.txt", self.p_to_save)
        except (KeyboardInterrupt, Exception) as e:
            print(e)
            print("you can resume it next time")
            self.save_progress()
            exit(0)

    def load_file(self, book_path):
        try:
            with open(book_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            raise Exception("can not load file")
    
    def save_file(self, book_path, content):
        try:
            with open(book_path, "w", encoding="utf-8") as f:
                f.write("\n".join(content))
        except:
            raise Exception("can not save file")

    def load_state(self):
        try:
            with open(self.bin_path, "r", encoding="utf-8") as f:
                self.p_to_save = f.read().split("\n")
        except:
            raise Exception("can not load resume file")

    def save_progress(self):
        try:
            with open(self.bin_path, "w") as f:
                f.write("\n".join(self.p_to_save))
        except:
            raise Exception("can not save resume file")


if __name__ == "__main__":
    MODEL_DICT = {"gpt3": GPT3, "chatgpt": ChatGPT}
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
        help="if you pay add it",
    )
    parser.add_argument(
        "--test",
        dest="test",
        action="store_true",
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
    NO_LIMIT = options.no_limit
    IS_TEST = options.test
    TEST_NUM = options.test_num
    if options.lang == "zh-cn":
        LANG = "Simplified Chinese"
    elif options.lang == "zh-tw":
        LANG = "Traditional Chinese"
    elif options.lang == "jp":
        LANG = "Japanese"
    OPENAI_API_KEY = options.openai_key or env.get("OPENAI_API_KEY")
    RESUME = options.resume
    if not OPENAI_API_KEY:
        raise Exception("Need openai API key, please google how to")
    model = MODEL_DICT.get(options.model, "chatgpt")
    if options.book_name.endswith(".epub"):
        book = BEPUB(options.book_name, model, OPENAI_API_KEY, RESUME)
        book.make_bilingual_book()
    elif options.book_name.endswith(".txt"):
        book = Text(options.book_name, model, OPENAI_API_KEY, RESUME)
        book.make_bilingual_book()
