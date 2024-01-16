import csv
import logging
import os
import random
import re
import sys
import time
from abc import ABC, abstractmethod
from functools import wraps
from typing import Optional, List, Tuple, Literal

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromedriverOptions
from selenium.webdriver.firefox.options import Options as GeckodriverOptions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)


def get_user_agents(filename: str) -> Tuple[List[str], List[float]]:
    """
    This function returns the most common user agents

    :param filename: (*str*) name of the TSV file with the most common user agents
    :return: (list with the user agents strings, list with the user agents weights)
    """
    user_agents_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)
    assert filename.endswith(".tsv")
    assert os.path.isfile(user_agents_filepath)
    with open(file=user_agents_filepath, mode="r", encoding="utf-8") as fr:
        parsed_rows = csv.reader(fr, delimiter="\t", quotechar='"')
        ua_strings, ua_weights = [], []
        for row in parsed_rows:
            assert len(row) == 2
            ua_strings.append(str(row[0]))
            ua_weights.append(float(row[1]))
        return ua_strings, ua_weights


def check_web_driver_decorator(method):
    """
    Decorator to check whether a BaseScraper object has been previously started

    :param method: (*Callable*) method to be called only after the scraper is started
    :return: method output
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.web_driver:
            raise AttributeError(
                "Field 'web_driver' is None! \n"
                "You must execute the 'start()' method after the initialization of your 'BaseScraper' object!"
            )
        return method(self, *args, **kwargs)
    return wrapper


# === source: https://www.useragents.me/#most-common-desktop-useragents-json-csv) === #
MOST_COMMON_USER_AGENTS_FILENAME = "most_common_desktop_user_agents.tsv"

# === Most common user agents for desktop devices === #
MOST_COMMON_USER_AGENTS_STRINGS, MOST_COMMON_USER_AGENTS_WEIGHTS = \
    get_user_agents(filename=MOST_COMMON_USER_AGENTS_FILENAME)

# === Most common screen resolutions for desktop devices === #
MOST_COMMON_SCREEN_RESOLUTIONS = [
    "1920,1080",
    "1366,768",
    "1536,864",
    "1440,900",
    "1600,900",
]


class BaseScraper(ABC):
    """
    Abstract base class representing a generic web scraper that must be implemented in sub-classes
    """

    def __init__(
            self,
            user_agent: Optional[str] = None,
            screen_resolution: Optional[str] = None,
            random_user_agent_flag: bool = True,
            random_screen_resolution_flag: bool = True,
            bs4_parser: str = "html.parser",
            proxy: Optional[str] = None,
    ):
        self.user_agent = user_agent
        self.screen_resolution = screen_resolution
        self.random_user_agent_flag = random_user_agent_flag
        self.random_screen_resolution_flag = random_screen_resolution_flag
        self.bs4_parser = bs4_parser
        # Proxy
        if proxy and len(proxy.split(":")) != 2:
            raise ValueError("Invalid Proxy! Accepted format: 'host:port'")
        self.proxy = proxy
        # User Agent
        if self.random_user_agent_flag:
            self.refresh_user_agent()
        # Screen Resolution
        if self.random_screen_resolution_flag:
            self.refresh_screen_resolution()
        # Initialize Web Driver to None
        self.web_driver = None

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    @check_web_driver_decorator
    def quit(self):
        pass

    @abstractmethod
    @check_web_driver_decorator
    def retrieve_html(
            self,
            url: str,
            wait_seconds: float = 1.0,
            delete_cookies_flag: bool = False,
            **kwargs,
    ) -> str:
        pass

    def refresh_user_agent(self):
        self.user_agent = random.choices(
            MOST_COMMON_USER_AGENTS_STRINGS,
            weights=MOST_COMMON_USER_AGENTS_WEIGHTS,
            k=1,
        )[0]
        logger.info(f"current user agent: {self.user_agent}")

    def refresh_screen_resolution(self):
        self.screen_resolution = random.choice(MOST_COMMON_SCREEN_RESOLUTIONS)
        logger.info(f"current screen resolution: {self.screen_resolution}")

    def format(self, html_body: str) -> str:
        return BeautifulSoup(markup=html_body, features=self.bs4_parser).prettify()

    @staticmethod
    def _process_text(extracted_text: str) -> str:
        extracted_text = re.sub(pattern="\n{5,}", repl="\n\n\n", string=extracted_text)
        extracted_text = re.sub(pattern="\n{4}", repl="\n\n", string=extracted_text)
        extracted_text = re.sub(pattern="\n{2,3}", repl="\n", string=extracted_text)
        return extracted_text

    def extract_text(self, html_body: str) -> str:
        tree = BeautifulSoup(markup=html_body, features=self.bs4_parser)
        if not tree.body:
            return ""
        for tag in tree.body.select("script"):
            tag.decompose()
        for tag in tree.body.select("style"):
            tag.decompose()
        return self._process_text(extracted_text=tree.body.get_text())

    def extract_links(self, html_body: str) -> List[str]:
        tree = BeautifulSoup(markup=html_body, features=self.bs4_parser)
        result = []
        for tag in tree.find_all("a"):
            link = tag.get("href")
            if link and link.startswith("http"):
                result.append(link)
        return result


class SeleniumScraper(BaseScraper):
    """
    Class representing a web scraper based on Selenium.
    You can choose among two browsers: 'chrome' and 'firefox'.
    You must have the 'chromedriver'/'geckodriver' executable in a folder
    associated to the environment variable PATH (e.g. '/usr/local/bin/').
    """

    def __init__(
            self,
            user_agent: Optional[str] = None,
            screen_resolution: Optional[str] = None,
            random_user_agent_flag: bool = True,
            random_screen_resolution_flag: bool = True,
            bs4_parser: str = "html.parser",
            proxy: Optional[str] = None,
            browser: Literal["chrome", "firefox"] = "chrome",
            options: Tuple[str] = (
                    "--headless",
                    "--incognito",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-popup-blocking",
                    "--disable-bundled-ppapi-flash",
                    "--disable-plugins-discovery",
                    "--disable-internal-flash",
                    "--disable-client-side-phishing-detection",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-features=InterestFeedContentSuggestions",
                    "--disable-features=Translate",
                    "--hide-scrollbars",
                    "--mute-audio",
                    "--no-default-browser-check",
                    "--no-first-run",
                    "--ash-no-nudges",
                    "--disable-search-engine-choice-screen",
            ),
    ):
        super().__init__(
            user_agent=user_agent,
            screen_resolution=screen_resolution,
            random_user_agent_flag=random_user_agent_flag,
            random_screen_resolution_flag=random_screen_resolution_flag,
            bs4_parser=bs4_parser,
            proxy=proxy,
        )
        # options
        self.options = list(options)
        if self.screen_resolution:
            self.options.append(f"--window-size={self.screen_resolution}")
        if self.user_agent:
            self.options.append(f"--user-agent={self.user_agent}")
        if self.proxy:
            self.options.append(f"--proxy-server={self.proxy}")
        # browser
        self.browser = browser.lower().strip()
        if self.browser == "chrome":
            self.browser_options_cls = ChromedriverOptions
            self.browser_webdriver_cls = webdriver.Chrome
        elif self.browser == "firefox":
            self.browser_options_cls = GeckodriverOptions
            self.browser_webdriver_cls = webdriver.Firefox
        else:
            raise ValueError(
                f"Invalid browser: '{self.browser}'! \n"
                f"Valid browsers values are: 'chrome' or 'firefox'!"
            )

    def start(self):
        browser_options = self.browser_options_cls()
        for opt in self.options:
            browser_options.add_argument(opt)
        self.web_driver = self.browser_webdriver_cls(options=browser_options)

    @check_web_driver_decorator
    def quit(self):
        self.web_driver.delete_all_cookies()
        self.web_driver.quit()
        del self.web_driver
        self.web_driver = None

    @check_web_driver_decorator
    def retrieve_html(
            self,
            url: str,
            wait_seconds: float = 1.0,
            delete_cookies_flag: bool = False,
            **kwargs,
    ) -> str:
        time.sleep(wait_seconds)
        if delete_cookies_flag:
            self.web_driver.delete_all_cookies()
        self.web_driver.get(url=url)
        return self.format(html_body=self.web_driver.page_source)


class RequestsScraper(BaseScraper):
    """
    Simple Web Scraper based on HTTP 'requests' library
    """

    def start(self):
        self.web_driver = requests.session()
        if self.proxy:
            self.web_driver.proxies = dict()
            self.web_driver.proxies["http"] = f"http://{self.proxy}"
            self.web_driver.proxies["https"] = f"https://{self.proxy}"
        if self.user_agent:
            self.web_driver.headers = dict()
            self.web_driver.headers["User-Agent"] = self.user_agent

    @check_web_driver_decorator
    def quit(self):
        self.web_driver.cookies.clear()
        self.web_driver.close()
        del self.web_driver
        self.web_driver = None

    @check_web_driver_decorator
    def retrieve_html(
            self,
            url: str,
            wait_seconds: float = 1.0,
            delete_cookies_flag: bool = False,
            **kwargs,
    ) -> str:
        if delete_cookies_flag:
            self.web_driver.cookies.clear()
        time.sleep(wait_seconds)
        resp = self.web_driver.get(url=url, **kwargs)
        if resp.status_code == requests.codes.ok:
            cont = resp.text
            if not cont:
                cont = ""
            if ("<html>" not in cont) and ("<body" not in cont):
                return f"<html>\n  <body>\n{cont}\n  </body>\n</html>"
            else:
                return cont
        else:
            resp.raise_for_status()
