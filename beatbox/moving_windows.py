#!/usr/bin/env python2

__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2017, Playa Lakes Joint Venture"
__credits__ = "Kyle Taylor"
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"


import os
import re
import numpy
import logging

from scipy import ndimage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    return str(key)+"_"+str(window_size)+"x"+str(window_size)

def generic_filter(r=None, destfile=None, write=True, footprint=None,
                   overwrite=True, function=None, size=None, dtype='uint16'):
    """ wrapper for ndimage.generic_filter that can comprehend a GeoRaster,
    apply a common circular buffer, and writes a numpy array to disk following
    user specifications
    """
    try:
        _WRITE_FILE = ((not os.path.isfile(destfile)) | overwrite) & write \
        & (destfile is not None)
    except TypeError as e:
        _WRITE_FILE = False
    try:
        _FOOTPRINT = footprint if footprint is True else \
        numpy.array(gen_circular_array(nPixels=size//2))
    except TypeError as e:
        raise TypeError("You may have missed a size= or"
                        " footprint= argument to generic_filter()")
    # lazy duck type and apply ndimage filter to user specifications
    try:
        image = r.array
    except AttributeError as e:
        image = r
    # wrap across ndimage.generic_filter
    try:
        image = ndimage.generic_filter(
            input=numpy.array(image, dtype=dtype),
            function=function,
            footprint=_FOOTPRINT
        )
    except RuntimeError as e:
        if re.search(e, "function"):
            raise RuntimeError("function= argument cannot be None")
        else:
            raise RuntimeError("exiting on an unhandled exception")
    except ValueError as e:
        raise ValueError("You may have missed a function= argument "
                         "to generic_filter()")

    # either save to disk or return to user
    if _WRITE_FILE:
        try:

            r.array=image
            r.write(dst_filename = str(destfile))
        except AttributeError as e:
            logger.warning("%s doesn't appear to be a Raster object; "
                           "returning generic_filter result to user", e)

            destfile = destfile.replace(".tif", "") # gdal will append for us
            r.array = image
            r.write(dst_filename=str(destfile))
        except Exception as e:
            logger.warning("%s doesn't appear to be a Raster object; "
                           "returning generic_filter result to user", e)
            return image
    else:
        return image
