"""
Various manipulations on georasters.GeoRaster and numpy objects that we use for
common raster operations with common geospatial datasets

"""

import numpy
import georasters
import gdalnumeric
import gdal

class Raster(georasters.GeoRaster):
    """ Raster class is a wrapper meant to extend the functionality of the GeoRaster base class
    :arg file string specifying the full path to a raster file (typically a GeoTIFF)
    """
    def __init__(self, file=None, **kwargs):
        self.raster = None
        self.open(file=file)
        # for i, arg in enumerate(kwargs):
        #     pass

    def open(self, file=None):
        self.ndv, self.xsize, self.ysize, self.geot, self.projection, datatype = georasters.get_geo_info(file)
        if self.ndv is None:
            self.ndv = -99999
        self.raster = gdalnumeric.LoadFile(file)
        self.y_cell_size = self.geot[1]
        self.x_cell_size = self.geot[5]
        self.raster = numpy.ma.masked_array(self.raster, mask=self.raster == self.ndv, fill_value=self.ndv)

    def write(self, dst_filename=None, format=gdal.GDT_UInt16, driver=gdal.GetDriverByName('GTiff')):
        georasters.create_geotiff(name=dst_filename, Array=self.raster, geot=self.geot, projection=self.projection,
                                  datatype=format, driver=driver, ndv=self.ndv, xsize=self.xsize,
                                  ysize=self.ysize)

    def merge(self, array=None, **kwargs):
        try:
            for i in range(0, len(array)):
                array[i] = georasters.GeoRaster(array[i], self.geot, nodata_value=self.ndv,
                                                projection=self.projection, datatype=self.raster.dtype)
            self.raster = georasters.merge(array)
        except Exception as e:
            raise e



    def split(self, n=None, **kwargs):
        """ stump for numpy.array_split. splits an input array into n (mostly) equal segments,
        possibly for a future parallel operation """
        return numpy.array_split(numpy.array(self.raster,dtype=str(self.raster.data.dtype)), n)


class NassCdlRaster(Raster):
    """ inherits the functionality of the GeoRaster class and
    extends its functionality with filters and re-classification tools useful
    for dealing with NASS CDL data.
    :arg file string specifying the full path to a raster file (typically a GeoTIFF)
    """
    def __init__(self, **kwargs):
        Raster.__init__(self, kwargs)

    def bootstrap(self):
        """ bootstrap selection of NASS cell values for crops using names from
        the Raster Attribute Table
        """
        pass

    def binary_reclass(self, match_array=None, filter=None, invert=False):
        """ binary reclassification of NASS input data. All cell values in
        self.raster are reclassified as uint8(boolean) based on whether they
        match or do not match the values of an input match array.
        """
        return(numpy.in1d(self.raster, match_array, assume_unique=False, invert=invert).dtype('uint8'))


def get_free_ram():
    """ determine the amount of free memory available on the current node
    """
    pass


def est_ram_usage(dim=None, dtype='int64', asGigabytes=True):
    """ estimate the RAM usage for an array object of dimensions
    arg dim: can be a Raster object, or a scalar or vector array specifying the dimensions of a numpy array (e.g., n=3;n=[3,2,1])
    """
    try:
        dtype = dim.raster.dtype
        dim = dim.raster.shape
    except AttributeError as e:
        if 'raster' in str(e):
            try: # sometimes est_ram_usage will be expected to accept a raw numpy array, rather than a Raster
                dtype = dim.dtype
                dim = dim.shape
            except AttributeError as e:
                pass # assume this is a scalar
            except Exception as e:
                raise e
    except Exception as e:
        raise e

    try:
        dim = dim ** 2
    except TypeError as e:
        try:
            dim = numpy.prod(dim) # maybe this is a list?
        except Exception as e:
            raise e
    except Exception as e:
        raise e

    if(asGigabytes):
        return dim*numpy.nbytes[dtype] * (10**-9)
    else:
        return dim*numpy.nbytes[dtype]