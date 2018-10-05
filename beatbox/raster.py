#!/usr/bin/env python2

__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2018, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor", "Alex Daniels", "Meghan Bogaerts", "Stephen Chang"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"

import numpy as np
import georasters as gr
import gdalnumeric
import gdal
import psutil
import logging
from copy import copy

from osgeo import gdal_array

_DEFAULT_NA_VALUE = 0
_DEFAULT_PRECISION = np.uint16

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fickle beast handlers for Earth Engine
try:
    import ee
    ee.Initialize()
    _HAVE_EE = True
except Exception:
    _HAVE_EE = False
    logger.warning("Failed to load the Earth Engine API. "
                   "Check your installation. Will continue "
                   "to load but without the EE functionality.")


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
        self.backend = "local" # By default, assume that we are working with raster data locally
        self.array = None
        self.filename = None
        # Public properties for GeoRaster compatibility and exposure to user
        self.ndv = None          # no data value
        self.x_cell_size = None  # cell size of x (meters/degrees)
        self.y_cell_size = None  # cell size of y (meters/degrees)
        self.geot = None         # geographic transformation
        self.projection = None   # geographic projection
        # args[0]/file=
        if kwargs.get('file', None) is not None:
            self.filename = kwargs.get('file')
        else:
            try:
                self.filename = args[0]
            except IndexError:
                pass
        # args[1]/array=
        if kwargs.get('array', None) is not None:
            self.array = kwargs.get('array')
        else:
            try:
                self._array = args[1]
            except IndexError:
                pass
        # args[2]/dtype=
        if kwargs.get('dtype', None) is not None:
            _dtype = kwargs.get('dtype')
        else:
            try:
                _dtype = args[2]
            except IndexError:
                _dtype = _DEFAULT_PRECISION
        # if we were passed a file argument, assume it's a
        # path and try to open it
        if self.filename is not None:
            try:
                self.open(self.filename, dtype=_dtype)
            except OSError:
                raise OSError("couldn't read filename provided")

    def __copy__(self):
        _raster = Raster()
        _raster._array = copy(self._array)
        _raster._backend = copy(self._backend)
        return _raster

    def __deepcopy__(self, memodict={}):
        return self.__copy__()

    @property
    def array(self):
        return self._array

    @array.setter
    def array(self, *args):
        self._array = args[0]

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, *args):
        self._filename = args[0]

    @property
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, *args):
        self._backend = args[0]

    def open(self, *args, **kwargs):
        """
        Open a local file handle for reading and assignment
        :param file:
        :return: None
        """
        # args[0]/file=
        if kwargs.get('file') is not None:
            _file = kwargs.get('file')
        else:
            try:
                _file = args[0]
            except IndexError:
                raise IndexError("invalid file= argument provided")
        # grab raster meta information from GeoRasters
        self.ndv, _x_size, _y_size, self.geot, self.projection, _datatype = \
            gr.get_geo_info(_file)
        # args[1]/dtype=
        if kwargs.get('dtype') is not None:
            _dtype = kwargs.get('dtype')
        else:
            try:
                _dtype = args[1]
            except IndexError:
                _dtype = _datatype
        if self.ndv is None:
            self.ndv = _DEFAULT_NA_VALUE

        self.array = gdalnumeric.LoadFile(
            filename=self.filename,
            buf_type=gdal_array.NumericTypeCodeToGDALTypeCode(_dtype)
        )

        # store array values as a numpy masked array
        self.array = np.ma.masked_array(
            self.array,
            mask=self.array == self.ndv,
            fill_value=self.ndv
        )

    def write(self, dst_filename=None, format=gdal.GDT_UInt16, driver=gdal.GetDriverByName('GTiff')):
        """
        wrapper for georasters create_geotiff that writes a numpy array to disk.
        :param dst_filename:
        :param format:
        :param driver:
        :return:
        """
        return gr.create_geotiff(
            name=dst_filename,
            Array=self.array,
            geot=self.geot,
            projection=self._projection,
            datatype=format,
            driver=driver,
            ndv=self.ndv,
            xsize=self.x_cell_size,
            ysize=self.y_cell_size
        )

    def to_georaster(self):
        return gr.GeoRaster(
            self.array,
            self.geot,
            nodata_value=self.ndv,
            projection=self.projection,
            datatype=self.array.dtype
        )

    def to_ee_image(self):
        return ee.array(self.array)

def extract(*args):
    """
    Extract wrapper function that will accept a series of 'with' arguments
    and use an appropriate backend to perform an extract operation with
    raster data
    :param args:
    :return:
    """

def _local_binary_reclassify(*args, **kwargs):
    """ binary reclassification of input data. All cell values in
    self._array are reclassified as uint8(boolean) based on whether they
    match or do not match the values of an input match array.
    """
    # args[0]/raster=
    try:
        if kwargs.get('raster', None) is not None:
            _raster = kwargs.get('raster')
        else:
            _raster = args[0]
    except IndexError:
        IndexError("invalid raster= argument supplied by user")
    # args[1]/match=
    try:
        if kwargs.get('match', None) is not None:
            _match = kwargs.get('match')
        else:
            _match =  args[1]
    except IndexError:
        IndexError("invalid match= argument supplied by user")
    # args[2]/invert=
    if kwargs.get('invert', None) is not None:
        _invert = kwargs.get('invert')
    else:
        try:
            _invert = args[2]
        except IndexError:
            # this is an optional arg
            _invert = False
    if kwargs.get('dtype', None) is not None:
        _dtype = kwargs.get('dtype')
    else:
        try:
            _dtype = args[3]
        except IndexError:
            _dtype = np.uint8
    return np.reshape(
        np.array(
            np.in1d(_raster.array, _match, assume_unique=True, invert=_invert),
            dtype=_dtype
        ),
        _raster.array.shape
    )


def _local_reclassify(*args, **kwargs):
    pass


def _local_crop(*args, **kwargs):
    """ wrapper for georasters.clip that will preform a crop operation on our input raster"""
    try:
        if kwargs.get('raster', None) is not None:
            _raster = kwargs.get('raster')
        else:
            _raster = args[0]
    except IndexError:
        raise IndexError("invalid raster= argument specified")
    try:
        if kwargs.get('shape', None) is not None:
            _shape = kwargs.get('shape')
        else:
            _shape = args[1]
    except IndexError:
        raise IndexError("invalid shape=argument specified")
    return _raster.to_georaster().gr.clip(_shape)



def _local_clip(*args, **kwargs):
    """clip is a hold-over from gr that performs a crop operation"""
    try:
        if kwargs.get('raster', None) is not None:
            _raster = kwargs.get('raster')
        else:
            _raster = args[0]
    except IndexError:
        raise IndexError("invalid raster= argument specified")
    try:
        if kwargs.get('shape', None) is not None:
            _shape = kwargs.get('shape')
        else:
            _shape = args[1]
    except IndexError:
        raise IndexError("invalid shape= argument specified")
    return _local_crop(raster=_raster, shape=_shape)

def _ee_extract(*args, **kwargs):
    """
    Earth Engine extract handler
    :param args:
    :param kwargs:
    :return:
    """

def _local_extract(*args, **kwargs):
    """
    local raster extraction handler
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
    if not _HAVE_EE:
        raise AttributeError("Requested Earth Engine functionality, "
                             "but we failed to load and initialize the ee package.")


def _local_reproject(*args, **kwargs):
    pass


def _local_merge(*args, **kwargs):
    """Wrapper for georasters.merge that simplifies merging raster segments returned by parallel operations."""
    try:
        if kwargs.get('rasters', None) is not None:
            _rasters = kwargs.get('rasters')
        else:
            _rasters = args[0]
    except IndexError:
        raise IndexError("invalid raster= argument specified")
    return gr.merge(_rasters)



def _local_split(*args, **kwargs):
    """Stump for np._array_split. splits an input array into n (mostly) equal segments,
    possibly for a future parallel operation."""
    try:
        if kwargs.get('raster', None) is not None:
            _raster = kwargs.get('raster')
        else:
            _raster = args[0]
    except IndexError:
        raise IndexError("invalid raster= argument specified")
    try:
        if kwargs.get('n', None) is not None:
            _n = kwargs.get('n')
        else:
            _n = args[1]
    except IndexError:
        raise IndexError("invalid n= argument specified")
    return np.array_split(
        np.array(_raster.array, dtype=str(_raster.array.data.dtype)),
        _n
    )

def _ram_sanity_check(*args, **kwargs):
    """check to see if your environment has enough ram to support a complex raster operation. Returns the difference
    between your available ram and your proposed operation(s). Negatives are bad. """
    try:
        if kwargs.get('raster', None) is not None:
            _raster = kwargs.get('raster')
        else:
            _raster = args[0]
    except IndexError:
        raise IndexError("invalid raster= argument specified")
    try:
        if kwargs.get('dtype', None) is not None:
            _dtype = kwargs.get('dtype')
        else:
            _dtype = args[1]
    except IndexError:
        raise IndexError("invalid dtype= argument specified")
    try:
        if kwargs.get('n_operation', None) is not None:
            _n_operations = kwargs.get('n_operations')
        else:
            _n_operations = args[2]
    except IndexError:
        raise IndexError("invalid n_operation= argument specified")
    try:
        if kwargs.get('as_gigabytes', None) is not None:
            _as_gigabytes = kwargs.get('as_gigabytes')
        else:
            _as_gigabytes = args[3]
    except IndexError:
        raise IndexError("invalid as_gigabytes= argument specified")
    try:
        if _dtype is None:
            _dtype = _raster.array.dtype
    except Exception as e:
        raise e
    return _get_free_ram(as_gigabytes=_as_gigabytes) - _est_ram_usage(
        _raster.array.shape,
        dtype=_dtype,
        n_operations=_n_operations,
        as_gigabytes=_as_gigabytes
    )


def _get_free_ram(as_gigabytes=True):
    """ determine the amount of free memory available on the current node
    """
    if as_gigabytes:
        return psutil.virtual_memory().available * 10**-9
    else:
        return psutil.virtual_memory().available


def _est_ram_usage(dim=None, dtype=None, n_operations=None, as_gigabytes=True):
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
            dim = np.prod(dim)  # maybe this is a list?
        except Exception as e:
            raise e
    except Exception as e:
        raise e

    if not n_operations: # exponential heuristic for a wild-assed estimate of ram utilization across n operations
        n_operations=1

    if as_gigabytes:
        as_gigabytes = 10**-9
    else:
        as_gigabytes = 1

    return (dim * np.nbytes[dtype] * as_gigabytes) ** n_operations
