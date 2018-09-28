#!/usr/bin/env python2

__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2017, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Do:
    def __init__(self, *args):
        """
        Do is a dictcomp interface for performing arbitrary spatial tasks with Vector and Raster objects
        :param args:
        """
        self._run = []
        self._what = []
        self._with = []
        try:
            self.run = args[0]
        except AttributeError:
            raise AttributeError("Failed to run Do action. Do assumes that the input provided "
                                 "is an attributed python dictionary. Is the object you passed "
                                 "something else?")

    def _check_backend(self, *args):
        """
        Parse the parameters specified by 'what' to determine whether this should run locally or on
        Earth Engine. Will set optional values for 'with' explicitly
        :param args:
        :return:
        """
        pass

    @property
    def run(self):
        """
        Get method that will call our user-supplied run function
        :param args:
        :return:
        """
        return self._run(self._with)

    @run.setter
    def run(self, *args):
        """
        Set method for our run function. This specifies what we are going to do with our instance
        and does some object checks to determine an appropriate backend based on objects specified
        with the 'what' parameter. The setter will then call the function to perform the user
        specified action
        :param args:
        :return:
        """
        try:
            self._run = args[0]['run']
            self._what = args[0]['what']
            self._with = args[0]['with']  # allow the user to set the backend explicitly
        except Exception as e:
            raise e
        # determine what backend to use (or if the user specified
        # backend is inappropriate for the given data)
        self._check_backend()
        # launch our run function
        return self.run
