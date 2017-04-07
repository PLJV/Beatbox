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
import re
from raster import *
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
    WRITE_FILE = ( not os.path.isfile(destfile) | overwrite ) & write & type(destfile) is not None
    FOOTPRINT  = footprint if footprint is True else numpy.array(gen_circular_array(nPixels=size//2))
    # lazy duck type and apply ndimage filter to user specifications
    try:
        image = r.raster
    except AttributeError as e:
        image = r
    # wrap across ndimage.generic_filter
    image = ndimage.generic_filter(input=numpy.array(image, dtype='uint16'),
                                   function=function,
                                   footprint=FOOTPRINT,
                                   dtype='uint16'))
    # either save to disk or return to user
    if WRITE_FILE:
        try:
            r.write(dst_filname=str(destfile))
        except Exception as e:
            print(e)
    else:
        return r


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
        if arg == "-r":
            _INPUT_RASTER=sys.argv[i + 1]
        elif arg == "-t":
            _TARGET_RECLASS_VALUE=list(map(int, sys.argv[i + 1].split(',')))
        elif arg == "-nass":
            IS_NASS=True
        elif arg == "-function":
            if re.search(sys.argv[i + 1].lower(), "sum"):
                FUNCTION=numpy.sum
            elif re.search(sys.argv[i + 1].lower(), "mean"):
                FUNCTION=numpy.mean
            elif re.search(sys.argv[i + 1].lower(), "sd"):
                FUNCTION=numpy.std
        elif arg == "-mw":
            _WINDOW_DIMS=list(map(int, sys.argv[i + 1].split(',')))
        elif arg == "-reclass":  # e.g., "row_crop=12,34;cereal=2,3;corn=1,10"
            classes=sys.argv[i + 1].split(";")
            for c in classes:
                c=c.split("=")
                MATCH_ARRAYS[c[0]]=list(map(int, c[1].split(",")))
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
            for window in WINDOW_DIMS:
                filename=_dict_to_mwindow_filename(key=m, window_size=window)
                generic_filter(r = _MATCH_ARRAYS[m], function = _FUNCTION, destfile = filename)


    # assign binary 1/0 based-on corresponding (2016) NASS CDL values on the raster surface
    # that I bogarted from the 2016 raster using 'R'. We should come-up with an elegant way to
    # code this raster algebra using just the RAT data from the raster file specified at runtime.
    # print(" -- reclassifying NASS raster input data")
    # row_crop = r.binary_reclass(match=[1, 2, 5, 12, 13, 26, 41, 225, 226, 232, 237, 238, 239, 240, 254])
    # cereal   = r.binary_reclass(match=[3, 4, 21, 22, 23, 24, 27, 28, 29, 39, 226, 233, 234, 235, 236, 237, 240, 254])
    # grass    = r.binary_reclass(match=[59, 60, 176])
    # tree     = r.binary_reclass(match=[63, 70, 71, 141, 142, 143])
    # wetland  = r.binary_reclass(match=[87, 190, 195])
