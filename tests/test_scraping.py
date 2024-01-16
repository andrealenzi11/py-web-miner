from typing import Literal, Optional

import pytest

from py_web_miner.scraping import SeleniumScraper, RequestsScraper


def check_html_source(html_body: str):
    assert isinstance(html_body, str)
    assert len(html_body) >= 6
    html_body = html_body.strip()
    assert html_body.startswith("<")
    assert html_body.endswith(">")


@pytest.mark.parametrize(
    "url, browser",
    [("https://blog.python.org/", None),
     ("https://pypi.org/", None),
     ("https://github.com/andrealenzi11", None),
     ("https://blog.python.org/", "chrome"),
     ("https://pypi.org/", "chrome"),
     ("https://github.com/andrealenzi11", "chrome"),
     ("https://blog.python.org/", "firefox"),
     ("https://pypi.org/", "firefox"),
     ("https://github.com/andrealenzi11", "firefox")]
)
def test_scraper(url: str,
                 browser: Optional[Literal["chrome", "firefox"]],
                 debug: bool = False):
    if browser:
        scraper_obj = SeleniumScraper(user_agent=None,
                                      screen_resolution=None,
                                      random_user_agent_flag=True,
                                      random_screen_resolution_flag=True,
                                      browser=browser,
                                      proxy=None)
    else:
        scraper_obj = RequestsScraper(user_agent=None,
                                      screen_resolution=None,
                                      random_user_agent_flag=True,
                                      random_screen_resolution_flag=True,
                                      proxy=None)
    assert scraper_obj.web_driver is None
    scraper_obj.start()
    assert scraper_obj.web_driver is not None
    html_body1 = scraper_obj.retrieve_html(url=url,
                                           wait_seconds=1.0,
                                           delete_cookies_flag=True)
    check_html_source(html_body=html_body1)
    extracted_text1 = scraper_obj.extract_text(html_body=html_body1)
    assert isinstance(extracted_text1, str)
    if debug:
        print(f"\n\n{'-' * 80}")
        print(extracted_text1[:50].strip(), "...")
        print(f"{'-' * 80}")
    assert len(extracted_text1) > 10
    extracted_links = scraper_obj.extract_links(html_body=html_body1)
    assert isinstance(extracted_links, list)
    assert all([isinstance(link, str) for link in extracted_links])
    if debug:
        print(extracted_links[:10], "...")
    assert len(extracted_links) > 3
    scraper_obj.quit()
    assert scraper_obj.web_driver is None
