# `corona.py`

A Python script that tries to provide up-to-date data about the Coronavirus outbreak. It scrapes the [Worldometers](https://www.worldometers.info/coronavirus/) site for information. So, the information should be accurate. However, I'm not to be held responsible for any inaccuracies should they exist.

The output is colored, tabulated and easily understood. There is also a basic form of caching so that you get to view previously downloaded statistics even if you have no network access.

![Example of basic usage](screenshot.png)

## Dependencies

`corona.py` depends on:

* python-appdirs : for caching data
* python-beautifulsoup4 : for parsing data
* python-requests : for obtaining data
* python-tabulate : for prettifying data
