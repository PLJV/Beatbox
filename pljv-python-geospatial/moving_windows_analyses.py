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
import gdal
import numpy
import math

from scipy import ndimage

class Raster(object):
    """The Raster base class provides file read/write and nifty converters for working between GDAL, NumPy, and SciPy"""
    def __init__(self, **kwargs):
        # private extent parameters
        self._lr_x = None
        self._lr_y = None
        self._ul_x = None
        self._ul_y = None
        self._xres = None
        self._yres = None
        # private spatial parameters
        self._wkt = None
        self._geo_transform = None
        # private band data
        self._band = 1
        # a user-facing numpy array object
        self.array = None
        # process any relevant args
        for i, arg in enumerate(kwargs):
            if arg == "band":
                self._band = kwargs[arg]
            elif arg =="file":
                self.open(file_name=kwargs[arg])

    def _world_to_pixel(self, geoMatrix, x, y):
        """Uses a gdal geomatrix (gdal.GetGeoTransform()) to calculate the pixel location of a geospatial coordinate"""
        ulX = geoMatrix[0]
        ulY = geoMatrix[3]
        xDist = geoMatrix[1]
        yDist = geoMatrix[5]
        rtnX = geoMatrix[2]
        rtnY = geoMatrix[4]
        pixel = int((x - ulX) / xDist)
        line = int((ulY - y) / xDist)
        return (pixel, line)

    def open(self, file_name=None, ndv=0, dtype='uint16'):
        src_ds = gdal.Open(file_name, gdal.GA_ReadOnly)
        b = src_ds.GetRasterBand(self._band)
        b_ndv = b.GetNoDataValue()
        # assign our raster extent
        self._ul_x, self._xres, xskew, self._ul_y, yskew, self._yres = src_ds.GetGeoTransform()
        self._lr_x = self._ul_x + (src_ds.RasterXSize * self._xres)
        self._lr_y = self._ul_y + (src_ds.RasterYSize * self._yres)
        self._wkt = src_ds.GetProjection()
        self._geo_transform = src_ds.GetGeoTransform()
        if b_ndv is not None:
            ndv = b_ndv
            self.array = numpy.ma.MaskedArray(b.ReadAsArray(), mask=ndv, dtype=dtype)
        else:
            self.array = numpy.array(b.ReadAsArray(), dtype=dtype)

    def write(self, dst_filename=None, format=gdal.GDT_Float32):

        driver = gdal.GetDriverByName('GTiff')

        x_pixels = math.ceil(abs(int(self._lr_x - self._ul_x))/abs(self._xres))
        y_pixels = math.ceil(abs(int(self._lr_y - self._ul_y))/abs(self._yres))

        dataset = driver.Create(dst_filename, x_pixels, y_pixels, 1, format)

        dataset.SetGeoTransform(self._geo_transform)
        dataset.SetProjection(self._wkt)
        dataset.GetRasterBand(self._band).WriteArray(self.array)
        dataset.FlushCache()


class NassCdlRaster(Raster):
    def __init__(self):
        pass


def mwindow(**kwargs):
    """ Wrapper function that performs a moving window analysis on a numpy image object

    Function allows user to specify an ndimage filter for use on input=array object
    :param input: an integer-based numpy.array object
    :param function: a numpy function to apply to our generic filter (e.g., numpy.sum)
    :param args: integer list specifying the cell-size (x,y) in pixels for the moving window analysis
    :return:
    """

    if type(kwargs['input']) is None:
        raise ValueError("mwindow requires at-least an input= argument specifying an input array")

    size      = 3          # by default let's assume a 3x3 window
    img_array = kwargs['input']
    fun       = numpy.sum  # take the sum of all values by default

    for i,arg in enumerate(kwargs):
        if arg == "size":
            size = kwargs[arg]
        elif arg == "input":
            img_array = kwargs[arg]
        elif arg == "fun":
            fun = kwargs[arg]

    return ndimage.generic_filter(input=img_array, function=fun, size=size)

if __name__ == "__main__":

    INPUT_RASTER = None
    WINDOW_DIMS  = [107, 237] # 107 = ~1 km; 237 = ~5 kilometers

    for i in range(0, len(sys.argv)):
        if sys.argv[i] == "-r":
            INPUT_RASTER = sys.argv[i + 1]
        elif sys.argv[i] == "-t":
             TARGET_RECLASS_VALUE = list(map(int,sys.argv[i + 1].split(',')))
        elif sys.argv[i] == "-mw":
            WINDOW_DIMS = list(map(int,sys.argv[i + 1].split(',')))
    if not WINDOW_DIMS:
        raise ValueError("moving window dimensions need to be specified using the -mw argument at runtime")
    elif not INPUT_RASTER:
        raise ValueError("this analysis requires a NASS input raster specified with -r argument at runtime")

    r = Raster(file=INPUT_RASTER)
    r.array = numpy.array(r.array,dtype='uint16')

    # assign binary 1/0 based-on corresponding (2016) NASS CDL values on the raster surface
    # that I bogarted from the 2016 raster using 'R'. We should come-up with an elegant way to
    # code this raster algebra using just the RAT data from the raster file specified at runtime.
    print(" -- reclassifying NASS raster input data")
    row_crop = (r.array ==  1 )  | (r.array ==  2 )   | (r.array ==  5 )   | (r.array ==  12 ) | (r.array ==  13 ) | (r.array ==  26 ) | (r.array ==  41 ) | (r.array ==  225 ) | (r.array ==  226 ) | (r.array ==  232 ) | (r.array ==  237 ) | (r.array ==  238 ) | (r.array ==  239 ) | (r.array ==  240 ) | (r.array ==  241 ) | (r.array ==  254 )
    row_crop = numpy.array(row_crop,dtype='uint8')
    #row_crop = numpy.array(row_crop, dtype='uint16')
    cereal   = (r.array ==  3 )  | (r.array ==  4 )   | (r.array ==  21 )  | (r.array ==  22 ) | (r.array ==  23 ) | (r.array ==  24 ) | (r.array ==  27 ) | (r.array ==  28 ) | (r.array ==  29 ) | (r.array ==  39 ) | (r.array ==  226 ) | (r.array ==  233 ) | (r.array ==  234 ) | (r.array ==  235 ) | (r.array ==  236 ) | (r.array ==  237 ) | (r.array ==  240 ) | (r.array ==  254 )
    cereal   = numpy.array(cereal, dtype='uint8')
    grass    = (r.array ==  59 ) | (r.array ==  60 )  | (r.array ==  176 )
    grass    = numpy.array(grass, dtype='uint8')
    tree     = (r.array ==  63 ) | (r.array ==  70 )  | (r.array ==  71 )  | (r.array ==  141 ) | (r.array ==  142 ) | (r.array ==  143 )
    tree     = numpy.array(tree, dtype='uint8')
    wetland  = (r.array ==  87 ) | (r.array ==  190 ) | (r.array ==  195 )
    wetland  = numpy.array(wetland, dtype='uint8')

    # write to disk
    # r.array = row_crop
    # r.np_write("2016_row_crop.tif", format=gdal.GDT_Byte)
    # r.array = cereal
    # r.np_write("2016_cereal.tif", format=gdal.GDT_Byte)
    # r.array = grass
    # r.np_write("2016_grass.tif", format=gdal.GDT_Byte)
    # r.array = tree
    # r.np_write("2016_forest.tif", format=gdal.GDT_Byte)
    # r.array = wetland
    # r.np_write("2016_wetlands.tif", format=gdal.GDT_Byte)

    # moving windows analyses
    print(" -- performing moving window analyses")
    for i, j in enumerate(WINDOW_DIMS):
        #row_crop_mw = mwindow(input=row_crop, size=j)
        #r.array = ndimage.generic_filter(row_crop,function=numpy.sum, size=j)
        r.array = ndimage.uniform_filter(row_crop.astype(float),size=j,mode="constant") * j**2
        r.write("2016_row_crop_" + str(j) + "x" + str(j) + ".tif", format=gdal.GDT_UInt16)

        #cereal_mw = mwindow(input=cereal, size=j)
        #r.array = ndimage.generic_filter(cereal, function=numpy.sum, size=j)
        r.array = ndimage.uniform_filter(cereal.astype(float),size=j,mode="constant") * j**2
        r.write("2016_cereal_" + str(j) + "x" + str(j) + ".tif", format=gdal.GDT_UInt16)

        #grass_mw = mwindow(input=grass, size=j)
        #r.array = ndimage.generic_filter(grass, function=numpy.sum, size=j)
        r.array = ndimage.uniform_filter(grass.astype(float),size=j,mode="constant") * j**2
        r.write("2016_grass_" + str(j) + "x" + str(j) + ".tif", format=gdal.GDT_UInt16)

        #tree_mw = mwindow(input=tree, size=j)
        #r.array = ndimage.generic_filter(tree, function=numpy.sum, size=j)
        r.array = ndimage.uniform_filter(tree.astype(float),size=j,mode="constant") * j**2
        r.write("2016_tree_" + str(j) + "x" + str(j) + ".tif", format=gdal.GDT_UInt16)

        #wetland_mw = mwindow(input=wetland, size=j)
        #r.array = ndimage.generic_filter(wetland, function=numpy.sum, size=j)
        r.array = ndimage.uniform_filter(wetland.astype(float), size=j,mode="constant") * j**2
        r.write("2016_wetland_" + str(j) + "x" + str(j) + ".tif", format=gdal.GDT_UInt16)

