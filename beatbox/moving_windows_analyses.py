#!/usr/bin/env python3
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

import sys
import os
import re
import numpy
from scipy import ndimage


def gen_circular_array(nPixels=None):
    """ make a 2-d array for buffering. It represents a circle of
    radius buffsize pixels, with 1 inside the circle, and zero outside.
    """
    kernel = None
    if nPixels > 0:
        n = 2 * nPixels + 1
        (r, c) = numpy.mgrid[:n, :n]
        radius = numpy.sqrt((r-nPixels)**2 + (c-nPixels)**2)
        kernel = (radius <= nPixels).astype(numpy.uint8)
    return kernel

def _dict_to_mwindow_filename(key=None, window_size=None):
    """ quick kludging to generate a filename from key + window size """
    return(str(key)+"_"+str(window_size)+"x"+str(window_size))

def generic_filter(r=None, destfile=None, write=True, footprint=None, overwrite=True, function=None, size=None, dtype='uint16'):
    """ wrapper for ndimage.generic_filter that can comprehend a GeoRaster, apply a common circular buffer, and writes a numpy
    array to disk following user specifications
    """
    try:
        _WRITE_FILE = (not os.path.isfile(destfile) | overwrite) & write & type(destfile) is not None
    except TypeError as e:
        _WRITE_FILE = False

    _FOOTPRINT = footprint if footprint is True else numpy.array(gen_circular_array(nPixels=size//2))

    # lazy duck type and apply ndimage filter to user specifications
    try:
        image = r.raster
    except AttributeError as e:
        image = r
    # wrap across ndimage.generic_filter
    try:
        image = ndimage.generic_filter(input=numpy.array(image, dtype=dtype),
                                       function=function,
                                       footprint=_FOOTPRINT)
    except RuntimeError as e:
        if re.search(e, "function"):
            print("function= argument cannot be None")
        else:
            print("exiting on an unhandled exception")
        raise e
    # either save to disk or return to user
    if _WRITE_FILE:
        try:
            r.raster=image
            r.write(dst_filname = str(destfile))
        except Exception as e:
            print(e + "doesn't appear to be a Raster object; returning generic_filter result to user")
            return image
    else:
        return image


if __name__ == "__main__":
    # required parameters
    _INPUT_RASTER=None
    _IS_NASS=True
    _FUNCTION=numpy.sum
    _WINDOW_DIMS=[]
    _MATCH_ARRAYS={}
    _TARGET_RECLASS_VALUE=1
    # process runtime arguments
    for i, arg in enumerate(sys.argv):
        arg.replace("--", "-")
        if arg == "-r":
            _INPUT_RASTER=sys.argv[i + 1]
        elif arg == "-t":
            _TARGET_RECLASS_VALUE=list(map(int, sys.argv[i + 1].split(',')))
        elif arg == "-nass":
            _IS_NASS=True
        elif arg == "-function":
            if re.search(sys.argv[i + 1].lower(), "sum"):
                _FUNCTION=numpy.sum
            elif re.search(sys.argv[i + 1].lower(), "mean"):
                _FUNCTION=numpy.mean
            elif re.search(sys.argv[i + 1].lower(), "sd"):
                _FUNCTION=numpy.std
        elif arg == "-mw":
            _WINDOW_DIMS=list(map(int, sys.argv[i + 1].split(',')))
        elif arg == "-reclass":  # e.g., "row_crop=12,34;cereal=2,3;corn=1,10"
            classes=sys.argv[i + 1].split(";")
            for c in classes:
                c=c.split("=")
                _MATCH_ARRAYS[c[0]]=list(map(int, c[1].split(",")))
    # sanity-check
    if not _WINDOW_DIMS:
        raise ValueError("moving window dimensions need to be specified using the -mw argument at runtime")
    elif not _INPUT_RASTER:
        raise ValueError("this analysis requires a NASS input raster specified with -r argument at runtime")

    # process any re-classification requests prior to our moving windows analysis if asked
    if _MATCH_ARRAYS:
        if _IS_NASS:
            r=NassCdlRaster(file=_INPUT_RASTER)
            r.raster = numpy.array(r.raster, dtype='uint16') # anticipating composition metric calculations ?
        else:
            r=Raster(file=_INPUT_RASTER)

        print(" -- performing moving window analyses")

        for m in _MATCH_ARRAYS:
            _MATCH_ARRAYS[m]=r.binary_reclass(match=_MATCH_ARRAYS[m])
            for window in _WINDOW_DIMS:
                filename=_dict_to_mwindow_filename(key=m, window_size=window)
                generic_filter(r = _MATCH_ARRAYS[m], function = _FUNCTION, destfile = filename)
