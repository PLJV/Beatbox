#!/usr/bin/env python2

__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2018, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor", "Alex Daniels", "Meghan Bogaerts", "Stephen Chang"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"

import numpy
import georasters as gr
import gdalnumeric
import gdal
import psutil
import logging
from copy import copy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fickle beast handlers for Earth Engine
try:
    import ee
    ee.Initialize()
except Exception:
    logger.warning("Failed to load the Earth Engine API. "
                   "Check your installation. Will continue "
                   "to load but without the EE functionality.")

_DEFAULT_NA_VALUE = -9999


class Raster(object):
    """
    Raster class is a wrapper for generating GeoRasters,
    Numpy arrays, and Earth Engine Image objects. It opens files
    and converts to other formats as needed for various backend
    actions associated with Do.
    :arg file string specifying the full path to a raster
    file (typically a GeoTIFF) or an asset id for earth engine
    :return None
    """
    def __init__(self, *args, **kwargs):
        """Raster constructor."""
        self._backend = "local" # By default, assume that we are working with raster data locally
        self._array = None
        self._filepath = None
        # GeoRaster compatibility handlers
        self._ndv = None          # no data value
        self._x_cell_size = None  # cell size of x (meters/degrees)
        self._y_cell_size = None  # cell size of y (meters/degrees)
        self._geot = None         # geographic transformation
        self._projection = None   # geographic projection
        # It's possible we want to initialize an empty class
        # and our args handlers will pass on relevant exceptions
        try:
            self._filepath = kwargs.get('file', args[0])
        except IndexError:
            pass
        try:
            self._array = kwargs.get('array', args[1])
        except IndexError:
            pass
        try:
            self._array = kwargs.get('array', args[1])
        except IndexError:
            pass
        # if we were passed a file argument, assume it's a
        # path and try to open it
        if self._filepath:
            try:
                self.open(self._filepath)
            except Exception as e:
                raise e

    def __copy__(self):
        _raster = Raster()
        _raster._array = copy(self._array)
        _raster._backend = copy(self._backend)
        return _raster

    def __deepcopy__(self, memodict={}):
        return self.__copy__()

    def open(self, *args, **kwargs):
        """
        Open a local file handle for reading and assignment
        :param file:
        :return: None
        """
        try:
            _file = kwargs.get('file', args[0])
        except IndexError:
            raise
        # grab raster meta information from GeoRasters
        self._ndv, _x_size, _y_size, self._geot, self._projection, datatype = gr.get_geo_info(_file)
        if self._ndv is None:
            self._ndv = _DEFAULT_NA_VALUE

        self._array = gdalnumeric.LoadFile(self._filepath)
        self.y_cell_size = self._geot[1]
        self.x_cell_size = self._geot[5]
        # we store the the actual raw array
        # values as a numpy masked array
        self._array = numpy.ma.masked_array(
            self._array,
            mask=self._array == self._ndv,
            fill_value=self._ndv
        )

    def write(self, dst_filename=None, format=gdal.GDT_UInt16, driver=gdal.GetDriverByName('GTiff')):
        """
        wrapper for georasters create_geotiff that writes a numpy array to disk.
        :param dst_filename:
        :param format:
        :param driver:
        :return:
        """
        gr.create_geotiff(
            name=dst_filename,
            Array=self._array,
            geot=self._geot,
            projection=self._projection,
            datatype=format,
            driver=driver,
            ndv=self._ndv,
            xsize=self._x_cell_size,
            ysize=self._y_cell_size
        )

    def map_to_disk(self):
        """map the contents of r._array to disk using numpy.memmap"""
        pass

    def to_georaster(self):
        return(gr.GeoRaster(
            self._array,
            self._geot,
            nodata_value=self._ndv,
            projection=self._projection,
            datatype=self._array.dtype
        ))

    def to_ee_image(self):
        _array = ee._array(self._array)


def _generic_binary_reclassify(*args, **kwargs):
    """ binary reclassification of input data. All cell values in
    self._array are reclassified as uint8(boolean) based on whether they
    match or do not match the values of an input match array.
    """
    try:
        _raster = kwargs.get('raster', args[0])
    except IndexError:
        IndexError("invalid raster= argument supplied by user")
    try:
        _match = kwargs.get('match', args[1])
    except IndexError:
        IndexError("invalid match= argument supplied by user")
    try:
        _invert = kwargs.get('invert', args[2])
    except IndexError:
        IndexError("invalid invert= argument supplied by user")
    return numpy.reshape(
        numpy._array(
            numpy.in1d(_raster._array, _match, assume_unique=True, invert=_invert),
            dtype='uint8'
        ),
        _raster._array.shape
    )


def _generic_reclassify(*args, **kwargs):
    pass


def _generic_crop(*args, **kwargs):
    """ wrapper for georasters.clip that will preform a crop operation on our input raster"""
    _raster = kwargs.get('raster', args[0]) if kwargs.get('raster', args[0]) is not None else None
    _shape = kwargs.get('shape', args[1]) if kwargs.get('shape', args[1]) is not None else None
    try:
        return _raster.to_georaster().gr.clip(_shape)
    except Exception as e:
        raise e


def _generic_clip(*args, **kwargs):
    """clip is a hold-over from gr that performs a crop operation"""
    _raster = kwargs.get('raster', args[0]) if kwargs.get('raster', args[0]) is not None else None
    _shape = kwargs.get('shape', args[1]) if kwargs.get('shape', args[1]) is not None else None
    return _generic_crop(raster=_raster, shape=_shape)


def _generic_extract(*args, **kwargs):
    """
    generic raster extraction handler
    :param args:
    :param kwargs:
    :return:
    """
    pass


def _ee_extract(*args, **kwargs):
    """
    EE raster extraction handler
    :param args:
    :param kwargs:
    :return:
    """

def _generic_reproject(*args, **kwargs):
    pass


def _generic_merge(*args, **kwargs):
    """Wrapper for georasters.merge that simplifies merging raster segments returned by parallel operations."""
    _rasters = kwargs.get('rasters', args[0]) if kwargs.get('raster', args[0]) is not None else None
    try:
        return gr.merge(_rasters)
    except Exception as e:
        raise e


def _generic_split(*args, **kwargs):
    """Stump for numpy._array_split. splits an input array into n (mostly) equal segments,
    possibly for a future parallel operation."""
    _raster = kwargs.get('raster', args[0]) if kwargs.get('raster', args[0]) is not None else None
    _n = kwargs.get('n', args[1]) if kwargs.get('n', args[1]) is not None else None
    return numpy._array_split(
        numpy._array(_raster._array,dtype=str(_raster._array.data.dtype)),
        _n
    )

def _ram_sanity_check(*args, **kwargs):
    """check to see if your environment has enough ram to support a complex raster operation. Returns the difference
    between your available ram and your proposed operation(s). Negatives are bad. """
    _raster = kwargs.get('raster', args[0]) if kwargs.get('raster', args[0]) is not None else None
    _dtype = kwargs.get('dtype', args[1]) if kwargs.get('dtype', args[1]) is not None else None
    _nOperation = kwargs.get('nOperation', args[2]) if kwargs.get('nOperation', args[2]) is not None else None
    _asGigabytes = kwargs.get('asGigabytes', args[3]) if kwargs.get('asGigabytes', args[3]) is not None else True
    try:
        if _dtype is None:
            _dtype = _raster._array.dtype
    except Exception as e:
        raise e
    return _get_free_ram(asGigabytes=_asGigabytes) - _est_ram_usage(
        _raster._array.shape,
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
        dtype = dim._array.dtype
        dim = dim._array.shape
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
