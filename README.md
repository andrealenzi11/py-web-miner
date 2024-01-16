# py-web-miner
Extensible Web Miner to extract information from web pages. 

It is based on HTTP Requests library, Beautiful Soup parser, and Selenium WebDriver.


### Usage Example

Use Selenium WebDriver Scraper 
(You must have the ``chromedriver``/``geckodriver`` executable in a folder 
associated to the environment variable ``PATH`` (e.g. ``/usr/local/bin/``):
```python3
from py_web_miner.scraping import SeleniumScraper

scraper_obj = SeleniumScraper(
    random_user_agent_flag=True,
    random_screen_resolution_flag=True,
    browser="chrome",  # "chrome" / "firefox"
    bs4_parser="html.parser",
    proxy=None
)
```

Or, eventually, use Requests Scraper (only HTML parsing, no Javascript execution):
```python3
from py_web_miner.scraping import RequestsScraper

scraper_obj = RequestsScraper(
    random_user_agent_flag=True,
    random_screen_resolution_flag=True,
    bs4_parser="html.parser",
    proxy=None
)
```

Start the scraper, retrieve the HTML source and extract raw text and all external links:
```python3
# start the scraper object
scraper_obj.start()

# retrieve the HTML source
html_body = scraper_obj.retrieve_html(
    url="https://github.com/andrealenzi11",
    wait_seconds=1.0,
    delete_cookies_flag=True
)

# extract the raw text
extracted_text = scraper_obj.extract_text(
    html_body=html_body
)

# extract the links
extracted_links = scraper_obj.extract_links(
    html_body=html_body
)

# quit
scraper_obj.quit()
```