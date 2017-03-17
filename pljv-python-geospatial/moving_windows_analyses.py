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
from raster import *
from scipy import ndimage

def gen_circular_array(nPixels=None):
    """ Make a 2-d array for buffering. It represents a circle of
    radius buffsize pixels, with 1 inside the circle, and zero outside.
    """
    bufferkernel = None
    if nPixels > 0:
        n = 2 * nPixels + 1
        (r, c) = numpy.mgrid[:n, :n]
        radius = numpy.sqrt((r-nPixels)**2 + (c-nPixels)**2)
        bufferkernel = (radius <= nPixels).astype(numpy.uint8)
    return bufferkernel


def mwindow(**kwargs):
    """ Wrapper function that performs a moving window analysis on a numpy image
    object. Function allows user to specify an ndimage filter for use on
    image=array object
    :param image: an integer-based numpy.array object
    :param filter: a string specifying the type of analysis (e.g.,'sum','mean','sd')
    :param size: scalar representing the width of the moving window (e.g., size=3; for a 3x3 window)
    :return: numpy.array object containing the result of the moving window
    """

    if type(kwargs['image']) is None:
        raise ValueError("mwindow requires at-least an image= argument specifying an input array")

    filter    = ndimage.generic_filter
    size      = None
    image     = None
    dtype     = "float64"
    f_kwargs  = dict()

    for i,arg in enumerate(kwargs):
        if arg == "filter": # the default ndimage filters are slow, but accurate. The following are fast, but controversial
            if kwargs[arg] == "sum":
                def filter(kwargs) : ndimage.uniform_filter(image, size=size, mode="constant") * size**2
            if kwargs[arg] == "mean":
                def filter(kwargs) : ndimage.uniform_filter(image, size=size, mode="constant")
            elif kwargs[arg] == "sd":
                # mean of square minus square of mean (requires strict enforcement of precision)
                def filter(kwargs):
                    c1 = ndimage.uniform_filter(image, size=size, mode='constant')
                    c2 = ndimage.uniform_filter(image*image, size=size, mode='constant')
                    return((c2 - (c1*c1)) ** .5)[make_mwindow_buffer]
        elif arg == "size":
            size = kwargs[arg]
        elif arg == "type":
            dtype = kwargs[arg]
        elif arg == "image":
            image = kwargs[arg]
            if not issubclass(type(image), numpy.ndarray):
                raise TypeError("image argument must be a numpy array")
            image = numpy.array(image, dtype=dtype) # bug-fix : on a binary surface, ndimage requires floating point precision for its calculations
        # by default, pass un-handled arguments to ndimage.generic_filter()
        else:
            f_kwargs[arg] = kwargs[arg]

    if size is None:
        raise ValueError("size= argument cannot be null")

    # cast to float64 to force precision (ndimage intermediates will inherit from image's type)
    image = numpy.array(image, dtype=type)

    return filter(f_kwargs)


if __name__ == "__main__":

    INPUT_RASTER = None
    WINDOW_DIMS  = [] # 107 = ~1 km; 237 = ~5 kilometers

    for i, arg in enumerate(sys.argv):
        if arg == "-r":
            INPUT_RASTER = sys.argv[i + 1]
        elif arg == "-t":
            TARGET_RECLASS_VALUE = list(map(int, sys.argv[i + 1].split(',')))
        elif arg == "-mw":
            WINDOW_DIMS = list(map(int, sys.argv[i + 1].split(',')))
    if not WINDOW_DIMS:
        raise ValueError("moving window dimensions need to be specified using the -mw argument at runtime")
    elif not INPUT_RASTER:
        raise ValueError("this analysis requires a NASS input raster specified with -r argument at runtime")

    r = NassCdlRaster(file=INPUT_RASTER)
    r.raster = numpy.array(r.raster, dtype='uint16')

    # assign binary 1/0 based-on corresponding (2016) NASS CDL values on the raster surface
    # that I bogarted from the 2016 raster using 'R'. We should come-up with an elegant way to
    # code this raster algebra using just the RAT data from the raster file specified at runtime.
    print(" -- reclassifying NASS raster input data")
    row_crop = r.binary_reclass(match_array=[1, 2, 5, 12, 13, 26, 41, 225, 226, 232, 237, 238, 239, 240, 254])
    cereal   = r.binary_reclass(match_array=[3, 4, 21, 22, 23, 24, 27, 28, 29, 39, 226, 233, 234, 235, 236, 237, 240, 254])
    grass    = r.binary_reclass(match_array=[59, 60, 176])
    tree     = r.binary_reclass(match_array=[63, 70, 71, 141, 142, 143])
    wetland  = r.binary_reclass(match_array=[87, 190, 195])

    # moving windows analyses
    print(" -- performing moving window analyses")
    for i, j in enumerate(WINDOW_DIMS):
        #row_crop_mw = mwindow(input=row_crop, size=j)
        #r.raster=ndimage.generic_filter(input=numpy.array(r.raster,dtype='uint16'), function=numpy.std, footprint=numpy.array(gen_circular_array(nPixels=11),dtype='uint16'))
        r.raster = ndimage.uniform_filter(numpy.array(row_crop, dtype="float64"), size=j, mode="constant") * j ** 2
        r.write("2016_row_crop_" + str(j) + "x" + str(j), format=gdal.GDT_UInt16)

        #cereal_mw = mwindow(input=cereal, size=j)
        r.raster = ndimage.uniform_filter(numpy.array(cereal,dtype="float64"), size=j, mode="constant") * j ** 2
        r.write("2016_cereal_" + str(j) + "x" + str(j), format=gdal.GDT_UInt16)

        #grass_mw = mwindow(input=grass, size=j)
        r.raster = ndimage.uniform_filter(numpy.array(grass,dtype="float64"), size=j, mode="constant") * j ** 2
        r.write("2016_grass_" + str(j) + "x" + str(j), format=gdal.GDT_UInt16)

        #tree_mw = mwindow(input=tree, size=j)
        r.raster = ndimage.uniform_filter(numpy.array(tree,dtype="float64"), size=j, mode="constant") * j ** 2
        r.write("2016_tree_" + str(j) + "x" + str(j), format=gdal.GDT_UInt16)

        #wetland_mw = mwindow(input=wetland, size=j)
        r.raster = ndimage.uniform_filter(numpy.array(wetland, dtype="float64"), size=j, mode="constant") * j ** 2
        r.write("2016_wetland_" + str(j) + "x" + str(j), format=gdal.GDT_UInt16)
