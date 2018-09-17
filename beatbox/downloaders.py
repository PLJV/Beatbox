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
import logging

from bs4 import BeautifulSoup as bs

_CDL_BASE_URL: str = "https://www.nass.usda.gov/Research_and_Science/Cropland/\
Release/"
_PROBABLE_PLAYAS_BASE_URL: str = "https://pljv.org/for-habitat-partners/maps\
-and-data/maps-of-probable-playas/"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HttpDownload:
    def __init__(self, *args, **kwargs):
        """
        Default web scraping interface for BeautifulSoup that will scrape
        a user-specified URL for A HREF tags and then download files that match
        some filename pattern using regular expressions (e.g., [.]zip).
        :param args:
        :param kwargs:
        """
        self._re_pattern = None
        self._url = None
        self._html = None
        self._soup = None
        self._files = []
        try:
            self.url = kwargs.get('url', args[0])
        except IndexError:
            pass # allow instantiation without specifying a default URL
        try:
            self._re_pattern = kwargs.get('pattern', args[1])
            if not self._validate_url():
                raise ValueError("Could not identify any target files at the "
                                 "URL provided using your search pattern.")
        except IndexError:
            pass  # allow instantiation without specifying an re search filter

    def _validate_url(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        _pattern = self._re_pattern
        try:
            # if the user passed a filename pattern argument, use it,
            # otherwise just use the default pattern specified
            # by _re_pattern
            _pattern = self._re_pattern = kwargs.get('pattern', args[0])
        except IndexError:
            pass
        self._soup = bs(self._html.text, "lxml")
        for i, a in enumerate(self._soup.findAll("a")):
            if re.search(string=str(a), pattern="a href.*" + _pattern):
                return True
        return False

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, *args):
        try:
            self._url = args[0]
        except IndexError:
            raise IndexError("url assignment requires a single str argument")
        self._html = requests.get(self._url)

    def scrape(self, *args, **kwargs):
        try:
            _dir_search_str = kwargs.get('search_str', args[0])
        except IndexError:
            _dir_search_str = None
        for i, a in enumerate(self._soup.findAll("a")):
            if re.search(string=str(a), pattern=_dir_search_str):
                self._files.append(
                    # by default, use the filename specified by our a hrefs
                    str(self._soup.select("a")[i].attrs['href'])
                )
        if not self._files:
            raise ValueError("could not parse any target files from the URL "
                             "provided: check the search_str argument")

    def download(self):
        if not self._files:
            self.scrape()
        for i, f in enumerate(self._files):
            if not os.path.exists(self._files[i].split("/")[-1]):
                print(i+1, end="")
                urllib.request.urlretrieve(f, self._files[i].split("/")[-1])


class Nass(HttpDownload):
    def __init__(self, *args, **kwargs):
        super().__init__(url=_CDL_BASE_URL, pattern=".zip")


class ProbablePlayas(HttpDownload):
    def __init__(self, *args, **kwargs):
        super().__init__(url=_PROBABLE_PLAYAS_BASE_URL, pattern=".zip")
