#!/usr/bin/python

import sys
import gdal
import numpy
import math

from scipy import ndimage

class Raster(object):
    def __init__(self, **kwargs):
        """
        Raster base class that allows for nifty array conversions for working between GDAL and NumPy.
        :param kwargs:
        """
        self._wkt = None
        self._geo_transform = None
        self._band = 1
        self._lr_x = None
        self._lr_y = None
        self._ul_x = None
        self._ul_y = None
        self._xres = None
        self._yres = None
        self.array = None
        # process any relevant args
        for i, arg in enumerate(kwargs):
            if arg == "band":
                self._band = kwargs[arg]
            elif arg =="file":
                self.np_open(file_name=kwargs[arg])

    def _world_to_pixel(geoMatrix, x, y):
        """
        Uses a gdal geomatrix (gdal.GetGeoTransform()) to calculate
        the pixel location of a geospatial coordinate
        """
        ulX = geoMatrix[0]
        ulY = geoMatrix[3]
        xDist = geoMatrix[1]
        yDist = geoMatrix[5]
        rtnX = geoMatrix[2]
        rtnY = geoMatrix[4]
        pixel = int((x - ulX) / xDist)
        line = int((ulY - y) / xDist)
        return (pixel, line)

    def np_open(self, file_name=None, ndv=0):
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
        self.array = numpy.ma.masked_equal(b.ReadAsArray(), ndv)

    def np_write(self, dst_filename=None, format=gdal.GDT_Float32):

        driver = gdal.GetDriverByName('GTiff')

        x_pixels = math.ceil(abs(int(self._lr_x - self._ul_x))/abs(self._xres))
        y_pixels = math.ceil(abs(int(self._lr_y - self._ul_y))/abs(self._yres))

        dataset = driver.Create(dst_filename, x_pixels, y_pixels, 1, format)

        dataset.SetGeoTransform(self._geo_transform)
        dataset.SetProjection(self._wkt)
        dataset.GetRasterBand(1).WriteArray(self.array)
        dataset.FlushCache()


def focal(img=None, *args):
    """
    Perform a moving window analysis on a numpy image object
    :param img:
    :param args: integer list specifying the cell-size (x,y) in pixels for the moving window analysis
    :return:
    """
    return ndimage.uniform_filter(img, (args[0], args[1]))

if __name__ == "__main__":
    '''
    MAIN
    '''

    INPUT_RASTER = None
    WINDOW_DIMS = []

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

    # assign binary 1/0 based-on corresponding (2016) NASS CDL values on the raster surface
    print(" -- reclassifying NASS raster input data")
    row_crop = (r.array ==  1 )  | (r.array ==  2 )   | (r.array ==  5 )   | (r.array ==  12 ) | (r.array ==  13 ) | (r.array ==  26 ) | (r.array ==  41 ) | (r.array ==  225 ) | (r.array ==  226 ) | (r.array ==  232 ) | (r.array ==  237 ) | (r.array ==  238 ) | (r.array ==  239 ) | (r.array ==  240 ) | (r.array ==  241 ) | (r.array ==  254 )
    cereal   = (r.array ==  3 )  | (r.array ==  4 )   | (r.array ==  21 )  | (r.array ==  22 ) | (r.array ==  23 ) | (r.array ==  24 ) | (r.array ==  27 ) | (r.array ==  28 ) | (r.array ==  29 ) | (r.array ==  39 ) | (r.array ==  226 ) | (r.array ==  233 ) | (r.array ==  234 ) | (r.array ==  235 ) | (r.array ==  236 ) | (r.array ==  237 ) | (r.array ==  240 ) | (r.array ==  254 )
    grass    = (r.array ==  59 ) | (r.array ==  60 )  | (r.array ==  176 )
    tree     = (r.array ==  63 ) | (r.array ==  70 )  | (r.array ==  71 )  | (r.array ==  141 ) | (r.array ==  142 ) | (r.array ==  143 )
    wetland  = (r.array ==  87 ) | (r.array ==  190 ) | (r.array ==  195 )

    # write to disk
    r.array = row_crop
    r.np_write("2016_row_crop.tif", format=gdal.GDT_Byte)
    r.array = cereal
    r.np_write("2016_cereal.tif", format=gdal.GDT_Byte)
    r.array = grass
    r.np_write("2016_grass.tif", format=gdal.GDT_Byte)
    r.array = tree
    r.np_write("2016_forest.tif", format=gdal.GDT_Byte)
    r.array = wetland
    r.np_write("2016_wetlands.tif", format=gdal.GDT_Byte)

    # moving windows analyses
    for i, j in enumerate(WINDOW_DIMS):
        row_crop = focal(img=row_crop, j, j)