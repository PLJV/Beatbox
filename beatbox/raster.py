"""
Various manipulations on georasters.GeoRaster and numpy objects that we use for raster operations
"""

import numpy
import georasters
import gdalnumeric
import gdal
import psutil
import copy

from tempfile import mkdtemp

class Raster:
    """Raster class is a wrapper meant to extend the functionality of the GeoRaster class
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
        """wrapper for georasters create_geotiff that writes a numpy array to disk."""
        georasters.create_geotiff(name=dst_filename, Array=self.array, geot=self.geot, projection=self.projection,
                                  datatype=format, driver=driver, ndv=self.ndv, xsize=self.xsize,
                                  ysize=self.ysize)

    def map_to_disk(self):
        """map the contents of r.array to disk using numpy.memmap"""
        pass

    def to_georaster(self):
        return(georasters.GeoRaster(
            self.array,
            self.geot,
            nodata_value=self.ndv,
            projection=self.projection,
            datatype=self.array.dtype
        ))

    def to_ee_image(self):
        pass

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


def binary_reclassify(*args, **kwargs):
    """ binary reclassification of input data. All cell values in
    self.array are reclassified as uint8(boolean) based on whether they
    match or do not match the values of an input match array.
    """
    _raster = kwargs.get('raster', args[0]) if kwargs.get('raster', args[0]) is not None else None
    _match = kwargs.get('match', args[1]) if kwargs.get('match', args[1]) is not None else None
    _invert = kwargs.get('invert', args[2]) if kwargs.get('invert', args[2]) is not None else None
    return numpy.reshape(
        numpy.array(
            numpy.in1d(_raster.array, _match, assume_unique=True, invert=_invert),
            dtype='uint8'
        ),
        _raster.array.shape
    )


def reclassify(*args, **kwargs):
    pass


def crop(*args, **kwargs):
    """ wrapper for georasters.clip that will preform a crop operation on our input raster"""
    _raster = kwargs.get('raster', args[0]) if kwargs.get('raster', args[0]) is not None else None
    _shape = kwargs.get('shape', args[1]) if kwargs.get('shape', args[1]) is not None else None
    try:
        return _raster.to_georaster().gr.clip(_shape)
    except Exception as e:
        raise e


def clip(*args, **kwargs):
    """clip is a hold-over from gr that performs a crop operation"""
    _raster = kwargs.get('raster', args[0]) if kwargs.get('raster', args[0]) is not None else None
    _shape = kwargs.get('shape', args[1]) if kwargs.get('shape', args[1]) is not None else None
    return crop(raster=_raster, shape=_shape)


def extract(*args, **kwargs):
    pass


def reproject(*args, **kwargs):
    pass


def merge(*args, **kwargs):
    """Wrapper for georasters.merge that simplifies merging raster segments returned by parallel operations."""
    _rasters = kwargs.get('rasters', args[0]) if kwargs.get('raster', args[0]) is not None else None
    try:
        return georasters.merge(_rasters)
    except Exception as e:
        raise e


def split(*args, **kwargs):
    """Stump for numpy.array_split. splits an input array into n (mostly) equal segments,
    possibly for a future parallel operation."""
    _raster = kwargs.get('raster', args[0]) if kwargs.get('raster', args[0]) is not None else None
    _n = kwargs.get('n', args[1]) if kwargs.get('n', args[1]) is not None else None
    return numpy.array_split(
        numpy.array(_raster.array,dtype=str(_raster.array.data.dtype)),
        _n
    )

def ram_sanity_check(*args, **kwargs):
    """check to see if your environment has enough ram to support a complex raster operation. Returns the difference
    between your available ram and your proposed operation(s). Negatives are bad. """
    _raster = kwargs.get('raster', args[0]) if kwargs.get('raster', args[0]) is not None else None
    _dtype = kwargs.get('dtype', args[1]) if kwargs.get('dtype', args[1]) is not None else None
    _nOperation = kwargs.get('nOperation', args[2]) if kwargs.get('nOperation', args[2]) is not None else None
    _asGigabytes = kwargs.get('asGigabytes', args[3]) if kwargs.get('asGigabytes', args[3]) is not None else True
    try:
        if _dtype is None:
            _dtype = _raster.array.dtype
    except Exception as e:
        raise e
    return _get_free_ram(asGigabytes=_asGigabytes) - _est_ram_usage(
        _raster.array.shape,
        dtype=_dtype,
        nOperations=_nOperation,
        asGigabytes=_asGigabytes
    )


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
