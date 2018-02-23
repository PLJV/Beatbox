"""
Various manipulations on georasters.GeoRaster and numpy objects that we use for raster operations
"""

import numpy
import georasters
import gdalnumeric
import gdal
import psutil

from tempfile import mkdtemp

class Raster(georasters.GeoRaster):
    """Raster class is a wrapper meant to extend the functionality of the GeoRaster base class
    :arg file string specifying the full path to a raster file (typically a GeoTIFF)."""
    def __init__(self, *args, **kwargs):
        """Raster constructor."""
        if 'crs' in list(map(str.lower, kwargs.keys())):
            self.array = None
            self.open(kwargs['file'])
        else:
            # assume the array is the first positional arg
            try:
                self.array = None
                self.open(args[0])
            except Exception as e:
                raise e


    def open(self, file=None):
        """Does what it says."""
        self.ndv, self.xsize, self.ysize, self.geot, self.projection, datatype = georasters.get_geo_info(file)
        if self.ndv is None:
            self.ndv = -99999
        self.array = gdalnumeric.LoadFile(file)
        self.y_cell_size = self.geot[1]
        self.x_cell_size = self.geot[5]
        self.array = numpy.ma.masked_array(self.array, mask=self.array == self.ndv, fill_value=self.ndv)

    def write(self, dst_filename=None, format=gdal.GDT_UInt16, driver=gdal.GetDriverByName('GTiff')):
        """Wrapper for georasters create_geotiff that writes a numpy array to disk."""
        georasters.create_geotiff(name=dst_filename, Array=self.array, geot=self.geot, projection=self.projection,
                                  datatype=format, driver=driver, ndv=self.ndv, xsize=self.xsize,
                                  ysize=self.ysize)
    def map_to_disk(self):
        """map the contents of r.array to disk using numpy.memmap"""
        pass

    def to_georaster(self):
        return(georasters.GeoRaster(self.array,
                             self.geot,
                             nodata_value=self.ndv,
                             projection=self.projection,
                             datatype=self.array.dtype))

    def binary_reclass(self, match=None, filter=None, invert=False):
        """ binary reclassification of input data. All cell values in
        self.array are reclassified as uint8(boolean) based on whether they
        match or do not match the values of an input match array.
        """
        return numpy.reshape(numpy.array(numpy.in1d(self.array, match,
            assume_unique=True, invert=invert), dtype='uint8'),
            self.array.shape)

    def mask(self, shape=None):
        """ wrapper for georasters.clip that will preform a crop operation on our input raster"""
        try:
            gr = self.to_georaster()
            self.array = gr.clip(shape)

        except Exception as e:
            raise e

    def merge(self, array=None, **kwargs):
        """Wrapper for georasters.merge that simplifies merging raster segments returned by parallel operations."""
        try:
            array = [georasters.GeoRaster(i, self.geot,
                                          nodata_value=self.ndv,
                                          projection=self.projection,
                                          datatype=self.array.dtype)
                     for i in array]
            self.array = georasters.merge(array)
        except Exception as e:
            raise e


    def split(self, n=None, **kwargs):
        """Stump for numpy.array_split. splits an input array into n (mostly) equal segments,
        possibly for a future parallel operation."""
        return numpy.array_split(numpy.array(self.array,dtype=str(self.array.data.dtype)), n)


class NassCdlRaster(Raster):
    """Inherits the functionality of the GeoRaster class and
    extends its functionality with filters and re-classification tools useful
    for dealing with NASS CDL data.
    :arg file string specifying the full path to a raster file (typically a GeoTIFF)"""
    def __init__(self, **kwargs):
        super(NassCdlRaster, self).__init__(**kwargs)

    def bootstrap(self):
        """ bootstrap selection of NASS cell values for crops using names from
        the Raster Attribute Table
        """
        pass


def _get_free_ram(asGigabytes=True):
    """ determine the amount of free memory available on the current node
    """
    if asGigabytes:
        return psutil.virtual_memory().available * 10**-9
    else:
        return psutil.virtual_memory().available


def _est_ram_usage(dim=None, dtype=None, nOperations=None, asGigabytes=True):
    """ estimate the RAM usage for an array object
    arg dim: can be a Raster object, or a scalar or vector array specifying the dimensions of a numpy array (e.g., n=3;n=[3,2,1])
    """
    try:
        dtype = dim.array.dtype
        dim = dim.array.shape
    except AttributeError as e:
        if 'raster' in str(e):
            try:  # sometimes est_ram_usage will be expected to accept a raw numpy array, rather than a Raster
                dtype = dim.dtype
                dim = dim.shape
            except AttributeError as e:
                pass  # assume this is a scalar
            except Exception as e:
                raise e
    except Exception as e:
        raise e

    try:
        dim = dim ** 2
    except TypeError as e:
        try:
            dim = numpy.prod(dim)  # maybe this is a list?
        except Exception as e:
            raise e
    except Exception as e:
        raise e

    if not nOperations: # exponential heuristic for a wild-assed estimate of ram utilization across n operations
        nOperations=1

    if(asGigabytes):
        asGigabytes = 10**-9
    else:
        asGigabytes = 1

    return (dim * numpy.nbytes[dtype] * asGigabytes) ** nOperations

def ram_sanity_check(r, dtype=None, nOperation=None, asGigabytes=True):
    """check to see if your environment has enough ram to support a complex raster operation. Returns the difference
    between your available ram and your proposed operation(s). Negatives are bad. """
    try:
        dtype = r.array.dtype
    except AttributeError:
        dtype = dtype
    except Exception as e:
        raise e
    return _get_free_ram(asGigabytes=asGigabytes) - \
           _est_ram_usage(r.array.shape, dtype=dtype, nOperations=nOperation, asGigabytes=asGigabytes)
