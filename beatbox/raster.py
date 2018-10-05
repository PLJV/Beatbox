#!/usr/bin/env python2

__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2018, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor", "Alex Daniels", "Meghan Bogaerts", "Stephen Chang"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"

# mmap file caching and file handling
import sys, os
from tempfile import mkdtemp
from random import randint
# raster manipulation
import numpy as np
import georasters as gr
import gdalnumeric
import gdal
from osgeo import gdal_array
# logging
import logging
# deep copy
from copy import copy
# memory profiling
import types
import psutil

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

str_to_numpy_types = {
  "uint8": np.uint8,
  "int8": np.uint8,
  "byte": np.int8,
  "uint16": np.uint16,
  "int16": np.int16,
  "uint32": np.uint32,
  "int32": np.int32,
  "float32": np.float32,
  "float64": np.float64,
  "complex64": np.complex64,
  "complex128": np.complex128,
}

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
        self._use_disc_caching = None # Use mmcache?
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
        # args[3]/disc_cache=
        if kwargs.get('disc_cache', None) is not None:
            self._use_disc_caching = kwargs.get('disc_cache')
        else:
            try:
                if args[3] is not None:
                    self._use_disc_caching = str(randint(1, 9999999999)) + \
                                             '_np_binary_array.dat'
            except IndexError:
                self._use_disc_caching = None
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
        _raster._filename = copy(self._filename)
        _raster._use_disc_caching = copy(self._filename)
        _raster.ndv = self.ndv
        _raster.x_cell_size = self.x_cell_size
        _raster.y_cell_size = self.y_cell_size
        _raster.geot = self.geot
        _raster.projection = self.projection
        # if we are mem caching, generate a new tempfile
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
        try:
            self.ndv, _x_size, _y_size, self.geot, self.projection, _datatype = \
                gr.get_geo_info(_file)
        except Exception:
            raise AttributeError("problem processing file input -- is this a raster file?")
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
        # low-level call to gdal with explicit type specification
        # that will store in memory or as a disc cache, depending
        # on the state of our _use_disc_caching property
        if self._use_disc_caching is not None:
            self.array = np.memmap(
                self._use_disc_caching, dtype=_dtype, mode='w+', shape=(_x_size, _y_size)
            )
        # self.array here can be either a memmap object or undefined
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
            projection=self.projection,
            datatype=format,
            driver=driver,
            ndv=self.ndv,
            xsize=self.x_cell_size,
            ysize=self.y_cell_size
        )

    def to_numpy_array(self):
        return self.array

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
    # if this is a complete GeoRaster, try
    # to process the whole object
    if isinstance(_raster, gr.GeoRaster):
        return np.reshape(
            np.array(
                np.in1d(_raster.array, _match, assume_unique=True, invert=_invert),
                dtype=_dtype
            ),
            _raster.array.shape
        )
    # if this is a big raster that we've split into chunks
    # process this piece-wise
    elif isinstance(_raster, types.GeneratorType):
        return np.concatenate(
            [np.reshape(
                np.array(
                    np.in1d(d[0], _match, assume_unique=True, invert=_invert),
                    dtype=_dtype
                ),
                (1, d.shape[1]) # array shape tuple e.g., (1,1111)
             )
             for i, d in enumerate(_raster)]
        )
    else:
        raise ValueError("raster= input should be a GeoRaster or Generator that numpy can work with")

def _local_reclassify(*args, **kwargs):
    pass


def _local_crop(*args, **kwargs):
    """ wrapper for georasters.clip that will preform a crop operation on our input raster"""
    # args[0] / raster=
    try:
        if kwargs.get('raster', None) is not None:
            _raster = kwargs.get('raster')
        else:
            _raster = args[0]
    except IndexError:
        raise IndexError("invalid raster= argument specified")
    # args[1] / shape=
    try:
        if kwargs.get('shape', None) is not None:
            _shape = kwargs.get('shape')
        else:
            _shape = args[1]
    except IndexError:
        raise IndexError("invalid shape=argument specified")
   # sanity check and then do our crop operation
   # and return to user
    _enough_ram = _local_ram_sanity_check(_raster.array)
    if not _enough_ram['available'] and not _raster._use_disc_caching:
        logger.warning(" There doesn't apprear to be enough free memory"
                       " available for our raster operation. You should use"
                       "disc caching options with your dataset. Est Megabytes "
                       "needed: %s", -1*_enough_ram['bytes']*0.0000001)
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
    """
    Wrapper for georasters.merge that simplifies merging raster segments returned by parallel operations.
    """
    try:
        if kwargs.get('rasters', None) is not None:
            _rasters = kwargs.get('rasters')
        else:
            _rasters = args[0]
    except IndexError:
        raise IndexError("invalid raster= argument specified")
    return gr.merge(_rasters)



def _local_split(*args, **kwargs):
    """
    Stump for np._array_split. splits an input array into n (mostly) equal segments,
    possibly for a future parallel operation.
    """
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


def _local_ram_sanity_check(*args):
    #args[0] (Raster object, GeoRaster, or numpy array)
    try:
        _array = args[0]
    except IndexError:
        raise IndexError("first pos. argument should be some kind of raster data")

    _cost = _est_free_ram - _est_array_size(_array)

    return {
        'available': bool(_cost>0),
        'bytes': int(_cost)
    }

def _est_free_ram():
    """
    Shorthand for psutil that will determine the amount of free ram
    available for an operation. This is typically used in conjunction
    with _est_array_size() or as a precursor to raising MemoryError
    when working with large raster datasets
    :return: int (free ram measured in bytes)
    """
    return psutil.virtual_memory().free


def _est_array_size(*args, **kwargs):
    """

    :param args:
    :param kwargs:
    :return:
    """
    _obj = args[0]
    _byte_size = None
    # args[0] is a list containing array dimensions
    if isinstance(_obj, list) or isinstance(_obj, tuple):
        _array_len = np.prod(_obj)
    # args[0] is a GeoRaster object
    elif isinstance(_obj, gr.GeoRaster):
        _array_len = np.prod(_obj.shape)
        _byte_size = str_to_numpy_types[_obj.datatype.lower()](1)
    # args[0] is a Raster object
    elif isinstance(_obj, Raster):
        _array_len = np.prod(_obj.array.shape)
        _byte_size = str_to_numpy_types[_obj.array.dtype.lower()](1)
    # args[0] is something else?
    else:
        _array_len = len(_obj)
    # args[1]/dtype= argument was specified
    try:
        _byte_size = str_to_numpy_types[args[1].lower()](1)
    except IndexError:
        if kwargs.get("dtype", None) is not None:
            _byte_size = str_to_numpy_types[kwargs.get("dtype").lower()](1)
        elif _byte_size is None:
            raise IndexError("invalid dtype= argument specified")
    return _array_len * sys.getsizeof(_byte_size)


def _local_process_array_as_blocks(*args):
    """
    Accepts
    :param args:
    :return:
    """
    _array = args[0].raster   # numpy array
    _rows = _array.shape[0]   # rows in array
    _n_chunks = 1             # how many blocks (rows) per chunk?
    """Yield successive n-sized chunks from 0-to-nrow."""
    for i in range(0, _rows, _n_chunks):
        yield _array[i:i + _n_chunks]
