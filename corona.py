#!/usr/bin/python
# Copyright (C) 2020 fushinari
#
# This file is part of corona.py.
#
# corona.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# corona.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with corona.py.  If not, see <http://www.gnu.org/licenses/>.
"""conora.py is a CLI tool to view statistics of the coronavirus outbreak."""


import argparse
from datetime import datetime, timezone
from functools import lru_cache
import itertools
import json
import locale
import os
import textwrap
import sys

import appdirs
import bs4
from pandas import DataFrame, read_json
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

    def color_red(self, text):
        """Color a string red."""
        return self.RED + text + self.RESET

    def color_blue(self, text):
        """Color a string blue."""
        return self.BLUE + text + self.RESET


locale.setlocale(locale.LC_NUMERIC, '')
PARSER = argparse.ArgumentParser(
    prog="corona.py",
    description="Get up-to-date statistics about the Coronavirus outbreak",
    argument_default=argparse.SUPPRESS
)
PARSER.add_argument("-t", "--table", help="Print the complete table", const='', action="store", nargs='?', type=str)
PARSER.add_argument("--sort", help="Change order of table (used with -t)", default='c', action="store", type=str)
PARSER.add_argument("-n", "--news", help="Print today's news", const='', action="store", nargs='?', type=str)
PARSER.add_argument("-o", "--offline", help="Run in offline mode", action="store_true")
PARSER.add_argument("-l", "--latest", help="Today's incidents", action="store_true")
PARSER.add_argument("-c", "--closed", help="Number of closed cases, closed either by death or by recovery",
                    action="store_true")
PARSER.add_argument("-a", "--active", help="Number of patients in treatment", action="store_true")
PARSER.add_argument("-r", "--recovered", help="Number of recovered patients", action="store_true")
PARSER.add_argument("-d", "--dead", help="Number of deaths that have occurred, in total and today", action="store_true")
PARSER.add_argument("-s", "--serious", help="Number of patients in critical or serious conditions", action="store_true")
PARSER.add_argument("country", nargs='?', type=str, help="Country to show data of; if not given, global stats is shown")
ARGS = PARSER.parse_args()
args_dict = vars(ARGS)
columns, _rows = os.get_terminal_size(0)

cache_dir = appdirs.user_cache_dir('coronapy', appauthor=False)
cache_file_path = os.path.join(cache_dir, 'data.json')


def get_news(soup):
    """Get the latest news from the website data."""
    news_div = soup.find('div', {'id': 'newsdate' + datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    clean_list = {
        '[source]': '',
        '[video]': '',
        '  ': '',
        ' .': '.'
    }
    news_table = []
    for new in news_div.find_all('li'):
        news_text = new.text.replace('\u00a0', ' ').strip()
        if new.find('img', {'alt': 'alert'}):
            news_text = '⚠ ' + news_text
        for to_replace, replace_with in clean_list.items():
            news_text = news_text.replace(to_replace, replace_with)

        news_table.append(news_text)
    return news_table


def zero_checker(integer_string):
    """Return proper integer values from strings containing only integers."""
    if integer_string in ('', 'N/A'):
        return None
    try:
        output = int(integer_string)
        return output
    except ValueError as error:
        print("Something went wrong here. This wasn't supposed to happen...")
        print(error)
        sys.exit(1)


def float_zero_checker(float_string):
    """Return proper float values from strings containing only float values."""
    if float_string in ('', 'N/A'):
        return None
    try:
        output = float(float_string)
        return output
    except ValueError as error:
        print("Something went wrong here. This wasn't supposed to happen...")
        print(error)
        sys.exit(1)


def get_table_row(row_text, length):
    """Return cleaned and converted data from table rows."""
    if length in (0, 12):
        return row_text.text.strip('+ \n')
    if length in (8, 9):
        return float_zero_checker(row_text.text.strip('+ \n').replace(',', ''))
    return zero_checker(row_text.text.strip('+ \n').replace(',', ''))


def get_table(soup):
    """Get the latest news from the website data."""
    rows = soup.find('table').find_all('tr')

    # Prepare a dictionary with all the data needed.
    online_outbreak_list = []

    for table_row in rows:
        table_row_list = []
        for row_text in table_row.find_all('td')[:13]:
            table_row_list.append(get_table_row(row_text, len(table_row_list)))
        if table_row_list:
            if table_row.attrs.get('style', None) == 'background-color:#EAF7D5':
                table_row_list.append('Recovered')
            elif table_row.attrs.get('style', None) == 'background-color:#F0F0F0':
                table_row_list.append('Outcome')
            else:
                table_row_list.append(None)

            if 'total_row' and 'row_continent' in table_row.attrs.get('class', []):
                table_row_list.append('Total')
            else:
                table_row_list.append(None)

            online_outbreak_list.append(table_row_list)

    online_outbreak_dataframe = DataFrame(online_outbreak_list, columns=[
        "Country", "Cases", "New Cases", "Deaths", "New Deaths",
        "Recovered", "Active", "Serious", "Cases/1M", "Deaths/1M",
        "Total Tests", "Tests/1M", "Continent", "State", "Class",
    ])
    online_outbreak_dataframe.sort_values(by='Cases', ascending=False, inplace=True)
    online_outbreak_dataframe.reset_index(drop=True, inplace=True)

    return online_outbreak_dataframe


def get_online_outbreak_data():
    """Get data of the outbreak from the Worldometers.info site."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/70.0.3538.77 Safari/537.36'
        }

        request = requests.get("https://www.worldometers.info/coronavirus", headers=headers)
        soup = bs4.BeautifulSoup(request.text, 'lxml')

        online_outbreak_table = get_table(soup)

        try:
            news_table = get_news(soup)
        except AttributeError:
            news_table = []

        online_outbreak_data = {
            'time': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'news': news_table,
            'table': online_outbreak_table.to_json()
        }

        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        with open(cache_file_path, 'w') as cache_file:
            json.dump(online_outbreak_data, cache_file, indent=4)
        return online_outbreak_data
    except requests.exceptions.ConnectionError:
        print("Network issue detected. Accessing offline data instead.")
        return None


def get_offline_outbreak_data():
    """Get data of the outbreak from local cache, either as fallback or in offline mode."""
    try:
        with open(cache_file_path, 'r') as cache_file:
            offline_outbreak_data = json.load(cache_file)
        print(f"Offline data is from {offline_outbreak_data['time']}.")
        return offline_outbreak_data
    except FileNotFoundError:
        print("No offline data found.")
        return None


def converter(input_string):
    """Convert the input string to slicing integers."""
    if input_string == '':
        return None
    return int(input_string)


if 'news' in args_dict:
    alerts_only = False
    if args_dict['news'] == 'a':
        news_lower_limit = None
        news_upper_limit = None
        alerts_only = True
    else:
        try:
            news_lower_limit = converter(args_dict['news'].rpartition(':')[0])
            if news_lower_limit is not None:
                news_upper_limit = converter(args_dict['news'].rpartition(':')[2]) + 1
            else:
                news_upper_limit = converter(args_dict['news'].rpartition(':')[2])
        except ValueError:
            PARSER.error("Ivalid arguments. '--news' takes arguments in the forms 'm:n', ':n', 'm:' or 'm'.")
            sys.exit(1)

if 'table' in args_dict:
    try:
        table_lower_limit = converter(args_dict['table'].rpartition(':')[0])
        if table_lower_limit is not None:
            table_upper_limit = converter(args_dict['table'].rpartition(':')[2]) + 1
        else:
            table_upper_limit = converter(args_dict['table'].rpartition(':')[2])
    except ValueError:
        PARSER.error("Ivalid arguments. '--table' takes arguments in the forms 'm:n', ':n', 'm:' or 'm'.")
        sys.exit(1)

if 'offline' in args_dict:
    outbreak_data = get_offline_outbreak_data()
    del args_dict['offline']  # Delete dictionary item that has served its purpose.
else:
    outbreak_data = get_online_outbreak_data() or get_offline_outbreak_data()

if outbreak_data is None:
    sys.exit(1)


def get_sorting():
    """Get the currently set sorting order."""
    switch_dict = {
        'n': 'Country',
        'na': 'Country',
        'c': 'Cases',
        'nc': 'New Cases',
        'd': 'Deaths',
        'nd': 'New Deaths',
        'r': 'Recovered',
        'a': 'Active',
        's': 'Serious',
        'c/p': 'Cases/1M',
        'd/p': 'Deaths/1M',
    }
    return switch_dict.get(args_dict['sort'], 'Cases')


sorting = get_sorting()
ascending = bool(args_dict['sort'].endswith('a') and len(args_dict['sort']) > 1)
del args_dict['sort']
table = read_json(outbreak_data['table'])
total_row = table.iloc[0].values


def get_data(input_list, index):
    """Get data from the list."""
    if input_list[index]:
        try:
            if isinstance(input_list[index], float):
                cleaned = '{:n}'.format(input_list[index])
            else:
                cleaned = '{:n}'.format(int(input_list[index]))
        except ValueError:
            cleaned = input_list[index]
        return str(cleaned).strip().replace('nan', '')
    return None


# In the following functions, returning '-' can mean either zero or that there's no information yet.
def get_total_cases(country_row):
    """Get total number of cases."""
    if country_row is not None:
        return get_data(country_row, 1) or '-'
    return get_data(total_row, 1) or '-'


def get_new_cases(country_row):
    """Get number of new cases today."""
    if country_row is not None:
        return get_data(country_row, 2) or '-'
    return get_data(total_row, 2) or '-'


def get_total_deaths(country_row):
    """Get total number of deaths."""
    if country_row is not None:
        return get_data(country_row, 3) or '-'
    return get_data(total_row, 3) or '-'


def get_new_deaths(country_row):
    """Get number of new deaths today."""
    if country_row is not None:
        return get_data(country_row, 4) or '-'
    return get_data(total_row, 4) or '-'


def get_total_recovered(country_row):
    """Get number of total recovered patients."""
    if country_row is not None:
        return get_data(country_row, 5) or '-'
    return get_data(total_row, 5) or '-'


def get_active_cases(country_row):
    """Get number of active cases."""
    if country_row is not None:
        return get_data(country_row, 6) or '-'
    return get_data(total_row, 6) or '-'


def get_serious_cases(country_row):
    """Get number of patients in critical or serious condition."""
    if country_row is not None:
        return get_data(country_row, 7) or '-'
    return get_data(total_row, 7) or '-'


def get_cases_by_pop(country_row):
    """Get the cases by every 1 million population ratio."""
    if country_row is not None:
        return get_data(country_row, 8) or '-'
    return get_data(total_row, 8) or '-'


def get_deaths_by_pop(country_row):
    """Get the deaths by every 1 million population ratio."""
    if country_row is not None:
        return get_data(country_row, 9) or '-'
    return get_data(total_row, 9) or '-'


# This was removed in an update of their site.
# def get_first_case(country_row):
#     """Get the date of first case reported."""
#     if country_row is not None:
#         return get_data(country_row, 10) or '-'
#     return get_data(total_row, 10) or '-'


def get_closed_cases(country_row):
    """Get the number of cases that have been closed, either by death or by recovery."""
    total_cases = get_total_cases(country_row).replace(',', '')
    active_cases = get_active_cases(country_row).replace(',', '')
    return '{:n}'.format(int(total_cases) - int(active_cases))


def get_situation(country_row):
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
        [Colors.LIGHT_GRAY + "Cases/1M Pop: ", get_cases_by_pop(country_row) + Colors.RESET],
        [Colors.LIGHT_RED + "Deaths/1M Pop: ", get_deaths_by_pop(country_row) + Colors.RESET],
        # [Colors.BLUE + "1st Case: ", get_first_case(country_row) + Colors.RESET]
    ]
    return tabulate(overview_data, colalign=("left", "right"))


@lru_cache(maxsize=None)
def get_row(country):
    """Get the country_row that is to be passed as a parameter to other fucntions."""
    if country:
        try:
            return table.loc[table["Country"] == args_dict['country'].title()].values[0]
        except IndexError:
            print("Country not found. So showing overview instead.")
            return total_row
    return total_row


row = get_row(args_dict.get('country'))

if len(args_dict) == 0 or (len(args_dict) == 1 and 'country' in args_dict):
    print(get_situation(row))
    sys.exit()

data = []

if 'active' in args_dict:
    data.append([Colors.PURPLE + "Active Cases: ", get_active_cases(row) + Colors.RESET])

if 'latest' in args_dict:
    data.append([Colors.YELLOW + "New Cases: ", get_new_cases(row) + Colors.RESET])
    data.append([Colors.RED + "New Deaths: ", get_new_deaths(row) + Colors.RESET])

if 'dead' in args_dict:
    data.append([Colors.RED + "Total Deaths: ", get_total_deaths(row) + Colors.RESET])

if 'serious' in args_dict:
    data.append([Colors.ORANGE + "Serious Cases: ", get_serious_cases(row) + Colors.RESET])

if 'recovered' in args_dict:
    data.append([Colors.GREEN + "Total Recovered: ", get_total_recovered(row) + Colors.RESET])

if 'closed' in args_dict:
    data.append([Colors.CYAN + "Closed Cases: ", get_closed_cases(row) + Colors.RESET])

if data:
    print(tabulate(data, colalign=("left", "right")))


def localize(input_data):
    """Localize the data."""
    try:
        if not isinstance(input_data, float):
            output_data = '{:n}'.format(int(input_data))
        else:
            output_data = '{:n}'.format(float(input_data))
    except ValueError:
        output_data = input_data
    return output_data


if 'table' in args_dict:
    na_position = 'first' if ascending else 'last'
    slicer = slice(table_lower_limit, table_upper_limit, 1)
    to_print = table
    for items in to_print.itertuples(name=None):
        if 'Total' in items:
            to_print.drop(items[0], axis=0, inplace=True)
    to_print = to_print.sort_values(
        by=sorting,
        ascending=ascending,
        na_position=na_position
    )[slicer].drop(["State", "Class"], axis=1)
    to_print = to_print.applymap(localize)
    to_print.reset_index(drop=True, inplace=True)
    to_print.index += 1
    print(tabulate(
        to_print,
        tablefmt="fancy_grid", headers='keys',
        colalign=[
            'left', 'left', 'right', 'right', 'right', 'right',
            'right', 'right', 'right', 'right', 'right', 'right'
        ]
    ).replace('nan', '   '))


def wrap(text):
    """Wrap the input text and return as a list."""
    wrapper = textwrap.TextWrapper(columns - 5)
    wrap_list = [wrapper.wrap(line) for line in text.split('\n') if line]
    wrap_list = list(itertools.chain.from_iterable(wrap_list))
    return wrap_list


if 'news' in args_dict:
    if outbreak_data['news']:
        print(f"News from {outbreak_data['time']}")
        slicer = slice(news_lower_limit, news_upper_limit, 1)
        for sentence in outbreak_data['news'][slicer]:
            if not alerts_only or '⚠' in sentence:
                lines = wrap(sentence)
                print(
                    f"{Colors.BOLD} {Colors().color_blue('->')}  "
                    f"{lines[0].replace('⚠', Colors().color_red('⚠'))}"
                )
                for line in lines[1:]:
                    print("     " + line)
    else:
        print("No news available.")
