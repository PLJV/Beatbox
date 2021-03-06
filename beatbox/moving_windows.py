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
import numpy as np
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
        (r, c) = np.mgrid[:n, :n]
        radius = np.sqrt((r-nPixels)**2 + (c-nPixels)**2)
        kernel = (radius <= nPixels).astype(np.uint8)
    return kernel

def _dict_to_mwindow_filename(key=None, window_size=None):
    """ quick kludging to generate a filename from key + window size """
    return str(key)+"_"+str(window_size)+"x"+str(window_size)

def filter(r=None, dest_filename=None, write=True, footprint=None,
           overwrite=True, function=None, size=None, dtype=np.uint16):
    """ wrapper for ndimage.generic_filter that can comprehend a GeoRaster,
    apply a common circular buffer, and optionally writes a numpy array to
    disk following user specifications
    """
    try:
        _WRITE_FILE = ((not os.path.isfile(dest_filename)) | overwrite) & write \
        & (dest_filename is not None)
    except TypeError as e:
        logger.warning("encountered an issue specifying a write file -- ",
                       "filter will return result to user and not write to disc")
        _WRITE_FILE = False
    try:
        _FOOTPRINT = footprint if footprint is True else \
        np.array(gen_circular_array(nPixels=size//2))
    except TypeError as e:
        raise TypeError("Unknown size= or footprint= arguments passed to",
        "filter() :", e)
    # apply ndimage filter to user specifications
    try:
        image = np.array(r.array, dtype=dtype)
    except AttributeError as e:
        image = np.array(r, dtype=dtype)
    # these ndimage filters can be used for the most common functions
    # we may encounter for moving windows analyses
    if function == np.median or function == np.mean:
        image = ndimage.median_filter(
            input=image,
            footprint=_FOOTPRINT
        )
    elif function == sum or function == np.sum:
        image = ndimage.median_filter(
            input = image,
            footprint = _FOOTPRINT
        ) * _FOOTPRINT.size
    elif function == np.max:
        image = ndimage.maximum_filter(
            input = image,
            footprint = _FOOTPRINT
        )
    elif function == np.min:
        image = ndimage.minimum_filter(
            input = image,
            footprint = _FOOTPRINT
        )
    # but, if all else fails, use the (slower) ndimage.generic_filter
    else:
        logger.warning("couldn't find a suitable pre-canned ndimage function",
                       "for your filter operation. Falling back on generic_filter,",
                       "which may be slow")
        try:
            image = ndimage.generic_filter(
                input=np.array(image, dtype=dtype),
                function=function,
                footprint=_FOOTPRINT
            )
        except Exception as e:
                raise RuntimeError("Failed to execute generic_filter using user-specified function. See:", e)
    # either save to disk or return to user
    if _WRITE_FILE:
        try:
            r.array = image
            r.write(dst_filename = str(dest_filename))
        except AttributeError as e:
            dest_filename = dest_filename.replace(".tif", "") # gdal will append for us
            r.array = image
            r.write(dst_filename=str(dest_filename))
        except Exception as e:
            logger.warning("%s doesn't appear to be a Raster object; "
                           "returning result to user", e)
            return image
    else:
        return image
