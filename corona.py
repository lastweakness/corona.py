#!/usr/bin/python

import argparse
from functools import lru_cache
import locale
import json
import os
import sys

import appdirs
import bs4
import requests
from tabulate import tabulate


class Colors:
    """Color the terminal output."""
    RESET = '\033[0m'
    DISABLE = '\033[02m'
    UNDERLINE = '\033[04m'
    REVERSE = '\033[07m'
    STRIKETHROUGH = '\033[09m'
    INVISIBLE = '\033[08m'
    BOLD = '\033[01m'

    BLACK = '\033[30m'
    DARK_GRAY = '\033[90m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    ORANGE = '\033[33m'
    BLUE = '\033[34m'
    PURPLE = '\033[35m'
    CYAN = '\033[36m'
    YELLOW = '\033[93m'
    PINK = '\033[95m'
    LIGHT_GRAY = '\033[37m'
    LIGHT_RED = '\033[91m'
    LIGHT_GREEN = '\033[92m'
    LIGHT_BLUE = '\033[94m'
    LIGHT_CYAN = '\033[96m'


locale.setlocale(locale.LC_ALL, '')
parser = argparse.ArgumentParser(description="Get up-to-date statistics about the Coronavirus outbreak")
mgroup = parser.add_mutually_exclusive_group()
mgroup.add_argument("-o", "--overview", help="Current overview of the outbreak", action="store_true")
mgroup.add_argument("-l", "--latest", help="Today's incidents", action="store_true")
group = parser.add_argument_group('additional arguments',
                                  "these only work when '-o' or '-l' are not being used but can be combined")
group.add_argument("-c", "--closed", help="Number of closed cases, closed either by death or by recovery",
                   action="store_true")
group.add_argument("-a", "--active", help="Number of patients in treatment", action="store_true")
group.add_argument("-r", "--recovered", help="Number of recovered patients", action="store_true")
group.add_argument("-d", "--dead", help="Number of deaths that have occurred, in total and today", action="store_true")
group.add_argument("-s", "--serious", help="Number of patients in critical or serious conditions", action="store_true")
parser.add_argument("country", nargs='?', type=str, help="Country to show data of; if not given, global stats is shown")
args = parser.parse_args()

cache_dir = appdirs.user_cache_dir('coronapy', appauthor=False)
cache_file_path = os.path.join(cache_dir, 'data.json')

try:
    url = "https://www.worldometers.info/coronavirus"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/70.0.3538.77 Safari/537.36'
    }

    r = requests.get(url, headers=headers)
    soup = bs4.BeautifulSoup(r.text, 'lxml')
    table = soup.find('table')
    rows = table.find_all('tr')

    # Prepare a dictionary with all the data needed.
    outbreak_data = {}

    for tr in rows:
        td = tr.find_all('td')
        table_row = [e.text for e in td]
        if table_row:
            outbreak_data.setdefault(table_row[0].lower(), table_row[1:])

    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
    with open(cache_file_path, 'w') as cache_file:
        json.dump(outbreak_data, cache_file)

except requests.exceptions.ConnectionError:
    try:
        with open(cache_file_path, 'r') as cache_file:
            outbreak_data = json.load(cache_file)
        print("Network issue detected. Using cached data.")
    except FileNotFoundError:
        print("Network issue detected. No cached data found. Exiting.")
        exit(1)

total_row = outbreak_data["total:"]


def get_data(input_list: list, index: int) -> str:
    """Get data from the list."""
    if input_list[index]:
        cleaned = input_list[index].strip('+').replace(',', '')
        try:
            cleaned = '{:n}'.format(int(cleaned))
        except ValueError:
            pass
        return cleaned.strip()
    return None


# In the following functions, returning '-' can mean either zero or that there's no information yet.
def get_total_cases(country_row: list = None) -> str:
    """Get total number of cases."""
    if country_row:
        return get_data(country_row, 0) or '-'
    return get_data(total_row, 0) or '-'


def get_new_cases(country_row: list = None) -> str:
    """Get number of new cases today."""
    if country_row:
        return get_data(country_row, 1) or '-'
    return get_data(total_row, 1) or '-'


def get_total_deaths(country_row: list = None) -> str:
    """Get total number of deaths."""
    if country_row:
        return get_data(country_row, 2) or '-'
    return get_data(total_row, 2) or '-'


def get_new_deaths(country_row: list = None) -> str:
    """Get number of new deaths today."""
    if country_row:
        return get_data(country_row, 3) or '-'
    return get_data(total_row, 3) or '-'


def get_total_recovered(country_row: list = None) -> str:
    """Get number of total recovered patients."""
    if country_row:
        return get_data(country_row, 4) or '-'
    return get_data(total_row, 4) or '-'


def get_active_cases(country_row: list = None) -> str:
    """Get number of active cases."""
    if country_row:
        return get_data(country_row, 5) or '-'
    return get_data(total_row, 5) or '-'


def get_serious_cases(country_row: list = None) -> str:
    """Get number of patients in critical or serious condition."""
    if country_row:
        return get_data(country_row, 6) or '-'
    return get_data(total_row, 6) or '-'


def get_cases_by_pop(country_row: list = None) -> str:
    """Get the cases by every 1 million population ratio."""
    if country_row:
        return get_data(country_row, 7) or '-'
    return get_data(total_row, 7) or '-'


def get_closed_cases(country_row: list = None) -> str:
    """Get the number of cases that have been closed, either by death or by recovery."""
    total_cases = get_total_cases(country_row).replace(',', '')
    active_cases = get_active_cases(country_row).replace(',', '')
    return '{:n}'.format(int(total_cases) - int(active_cases))


def get_situation(country_row: list = None) -> str:
    """Get details of the current situation in prettified, printable form."""
    overview_data = [
            [Colors.BOLD + "Total Cases: ", get_total_cases(country_row) + Colors.RESET],
            [Colors.YELLOW + "New Cases: ", get_new_cases(country_row) + Colors.RESET],
            [Colors.RED + "Total Deaths: ", get_total_deaths(country_row) + Colors.RESET],
            [Colors.RED + "New Deaths: ", get_new_deaths(country_row) + Colors.RESET],
            [Colors.GREEN + "Total Recovered: ", get_total_recovered(country_row) + Colors.RESET],
            [Colors.PURPLE + "Active Cases: ", get_active_cases(country_row) + Colors.RESET],
            [Colors.ORANGE + "Serious or Critical: ", get_serious_cases(country_row) + Colors.RESET],
            [Colors.CYAN + "Total Closed Cases: ", get_closed_cases(country_row) + Colors.RESET],
            [Colors.LIGHT_GRAY + "Cases/1M Pop: ", get_cases_by_pop(country_row) + Colors.RESET]
        ]
    return tabulate(overview_data, colalign=("left", "right"))


def get_new_situation(country_row: list = None) -> str:
    """Get details of what changed today, only new cases and new deaths."""
    new_data = [
            [Colors.YELLOW + "New Cases: ", get_new_cases(country_row) + Colors.RESET],
            [Colors.RED + "New Deaths: ", get_new_deaths(country_row) + Colors.RESET],
        ]
    return tabulate(new_data, colalign=("left", "right"))


@lru_cache(maxsize=None)
def get_row(country: str = None) -> list:
    """Get the country_row that is to be passed as a parameter to other fucntions."""
    if country:
        try:
            return outbreak_data[args.country.lower()]
        except KeyError:
            print("Country not found. So showing overview instead.")
            return total_row
    return total_row


row = get_row(args.country)

if args.overview or (args.country and len(sys.argv) == 2) or len(sys.argv) == 1:
    print(get_situation(row))
    exit()

if args.latest:
    print(get_new_situation(row))
    exit()

data = []

if args.active:
    data.append([Colors.PURPLE + "Active Cases: ", get_active_cases(row) + Colors.RESET])
    data.append([Colors.YELLOW + "New Cases: ", get_new_cases(row) + Colors.RESET])

if args.dead:
    data.append([Colors.RED + "Total Deaths: ", get_total_deaths(row) + Colors.RESET])
    data.append([Colors.RED + "New Deaths: ", get_new_deaths(row) + Colors.RESET])

if args.serious:
    data.append([Colors.ORANGE + "Serious Cases: ", get_serious_cases(row) + Colors.RESET])

if args.recovered:
    data.append([Colors.GREEN + "Total Recovered: ", get_total_recovered(row) + Colors.RESET])

if args.closed:
    data.append([Colors.CYAN + "Closed Cases: ", get_closed_cases(row) + Colors.RESET])

if data:
    print(tabulate(data, colalign=("left", "right")))
