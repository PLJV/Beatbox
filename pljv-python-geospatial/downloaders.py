#!/usr/bin/env python
"""
__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2017, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor", "Alex Daniels"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"
"""

import os
import re
import requests
import urllib

from bs4 import BeautifulSoup as bs

BASE = "https://www.nass.usda.gov/Research_and_Science/Cropland/Release/"

class Nass:
    '''
    Nass baseclass
    Handler for NASS web-scraping and downloading NASS imagery
    '''
    def __init__(self, **kargs):
        self._url = None
        self._file = None
        self._bs = None
        self._zips = []
        for i, arg in enumerate(kargs):
            if arg == "url":
                self.base_url(kargs[arg])
                if not self._validate_url():
                    raise ValueError('could not identify any zip files at the URL provided.')

    def _validate_url(self):
        self._bs = bs(self._file.text, "lxml")
        for i, a in enumerate(self._bs.findAll("a")):
            if re.search(string=str(a), pattern="a href.*.zip"):
                return True
        return False

    def base_url(self, args=BASE):
        self._url = args
        self._file = requests.get(self._url)

    def scrape(self, search_str="30m_cdls"):
        for i, a in enumerate(self._bs.findAll("a")):
            if re.search(string=str(a), pattern=search_str):
                self._zips.append(str(self._bs.select("a")[i].attrs['href']))
        if not self._zips:
            raise ValueError('could not parse any zip files from the URL provided: check the search_str argument')

    def download(self):
        if not self._zips:
            self.scrape()
        for i, f in enumerate(self._zips):
            print("downloading zips:")
            if not os.path.exists(self._zips[i].split("/")[-1]):
                print(i+1, end="")
                urllib.request.urlretrieve(f, self._zips[i].split("/")[-1])


class NassClassifiers:
    def __init__(self):
        self.corn = [1, 12, 13, 225, 226, 237, 241]