#!/usr/bin/env python3
"""A Simple Script for Extracting Data from a Webpage
This script allows the user to extract data from a webapge
and then export the data to a csv file with column(s).
modified from:
https://medium.com/analytics-vidhya/a-super-easy-python-script-for-web-scraping-that-anybody-can-use-d3bd6ab86c89
"""

__import__("viv").activate("requests", "bs4", "rich")  # noqa

import requests
from bs4 import BeautifulSoup
from rich import box
from rich.console import Console
from rich.table import Table

# Put your URL here
url = "https://www.nytimes.com/books/best-sellers/combined-print-and-e-book-nonfiction/"

# Fetching the html
r = requests.get(url)

# Parsing the html
parse = BeautifulSoup(r.content, "html.parser")

# Provide html elements' attributes to extract the data
text1 = list(
    e.get_text().strip() for e in parse.find_all("h3", attrs={"class": "css-5pe77f"})
)
text2 = list(
    e.get_text().strip().replace("by ", "")
    for e in parse.find_all("p", attrs={"class": "css-hjukut"})
)
max_len = max((len(txt) for txt in text1))

print()
table = Table(title="NY Times Best Sellers", box=box.ROUNDED, title_justify="left")
table.add_column(
    "Title",
    justify="right",
    style="cyan",
    no_wrap=True,
)
table.add_column("Author", style="magenta")

for col1, col2 in zip(text1, text2):
    table.add_row(col1, col2)

console = Console()
console.print(table)
