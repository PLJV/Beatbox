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


class Do(object):
    def __init__(self, *args):
        """
        Do is a dictcomp interface for performing arbitrary spatial tasks with Vector and Raster objects
        :param args:
        """
        self._what = None
        self._with = None
        self._backend = None
        try:
            self.run = args[0]
        except IndexError:
            # allow empty class specification, e.g. for copy() and deepcopy()
            pass

    def _guess_backend(self):
        """
        Parse the parameters specified by 'what' to determine whether this should run locally or on
        Earth Engine.
        :param args:
        :return: None
        """
        pass

    def _unpack_with_arguments(self):
        """
        The what arguments specified by the user can be pass as a dictionary or as a list. This
        method will unpack user-specified 'with' arguments so that they can be handled by a user-specified
        'what' function
        :return: None
        """
        pass

    @property
    def run(self):
        """
        Get method that will call our user-supplied run function
        :param args:
        :return: Result of a what function
        """
        # if we haven't already specified our 'what' and 'with' parameters
        if self._what is None or self._with is None:
            raise AttributeError("'what' and 'with' parameters are undefined.")
        return self._what(self._with)

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
            self._what = args[0]['what']
            self._with = args[0]['with']
        except KeyError or IndexError as e:
            raise KeyError("run= accepts a dict as a single positional argument specifying "
                           "'what' and 'with' keys")
        # determine what backend to use (or if the user specified
        # backend is inappropriate for the given data)
        self._unpack_with_arguments()
        self._guess_backend()
