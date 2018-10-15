#!/usr/bin/env python3

__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2018, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor", "Alex Daniels", "Meghan Bogaerts",
               "Stephen Chang"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"

# mmap file caching and file handling
import sys
from random import randint
# raster manipulation
import numpy as np
from georasters import GeoRaster, get_geo_info, create_geotiff, merge
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

# short-hand string identifiers for numpy
# types. Int, float, and byte will be the
# most relevant for raster arrays, but the
# gang is all here
NUMPY_TYPES = {
  "uint8": np.uint8,
  "int8": np.uint8,
  "int": np.intc,
  "byte": np.int8,
  "uint16": np.uint16,
  "int16": np.int16,
  "uint32": np.uint32,
  "int32": np.int32,
  "float": np.single,
  "float32": np.float32,
  "float64": np.float64,
  "complex64": np.complex64,
  "complex128": np.complex128
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

    def __init__(self, filename=None, array=None, dtype=None,
                 disc_caching=None):
        self.backend = "local"
        self.array = None
        self.filename = None
        self._using_disc_caching = None  # Use mmcache?
        # Public properties for GeoRaster compatibility and exposure to user
        self.ndv = None          # no data value
        self.x_cell_size = None  # cell size of x (meters/degrees)
        self.y_cell_size = None  # cell size of y (meters/degrees)
        self.geot = None         # geographic transformation
        self.projection = None   # geographic projection
        # args[0]/file=
        self.filename = filename
        # args[1]/array=
        self.array = array
        # args[2]/dtype=
        if dtype is None:
            dtype = _DEFAULT_PRECISION
        # args[3]/disc_cache=
        if disc_caching is not None:
            self._using_disc_caching = str(randint(1, 9999999999)) + \
                                       '_np_binary_array.dat'
        # if we were passed a file argument, assume it's a
        # path and try to open it
        if self.filename is not None:
            try:
                self.open(self.filename, dtype=dtype)
            except OSError:
                raise OSError("couldn't open the filename provided")

    def __copy__(self):
        _raster = Raster()
        _raster._array = copy(self._array)
        _raster._backend = copy(self._backend)
        _raster._filename = copy(self._filename)
        _raster._using_disc_caching = copy(self._filename)
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

    def open(self, file=None, dtype=None):
        """
        Open a local file handle for reading and assignment
        :param file:
        :return: None
        """
        # args[0]/file=
        if file is None:
            raise IndexError("invalid file= argument provided")
        # grab raster meta information from GeoRasters
        try:
            self.ndv, _x_size, _y_size, self.geot, self.projection, _dtype = \
                get_geo_info(file)
        except Exception:
            raise AttributeError("problem processing file input -- is this",
                                 "a raster file?")
        # args[1]/dtype=
        if dtype is None:
            # use our shadow'd value from GeoRasters if
            # nothing was specified by the user
            dtype = _dtype
        # re-cast our datatype as a numpy type
        dtype = NUMPY_TYPES[dtype.lower()]
        if self.ndv is None:
            self.ndv = _DEFAULT_NA_VALUE
        # low-level call to gdal with explicit type specification
        # that will store in memory or as a disc cache, depending
        # on the state of our _using_disc_caching property
        if self._using_disc_caching is not None:
            # create a cache file
            self.array = np.memmap(
                self._using_disc_caching, dtype=_dtype, mode='w+', shape=(_x_size, _y_size)
            )
            # load file contents into the cache
            self.array[:] = gdalnumeric.LoadFile(
                filename=self.filename,
                buf_type=gdal_array.NumericTypeCodeToGDALTypeCode(_dtype)
            )[:]
        # by default, load the whole file into memory
        else:
            self.array = gdalnumeric.LoadFile(
                filename=self.filename,
                buf_type=gdal_array.NumericTypeCodeToGDALTypeCode(_dtype)
            )
        # make sure we honor our no data value
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
        return create_geotiff(
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
        """

        :return:
        """
        return GeoRaster(
            self.array,
            self.geot,
            nodata_value=self.ndv,
            projection=self.projection,
            datatype=self.array.dtype
        )

    def to_ee_image(self):
        return ee.array(self.array)


def crop(*args):
    return _local_crop(args)


def extract(*args):
    """
    Extract wrapper function that will accept a series of 'with' arguments
    and use an appropriate backend to perform an extract operation with
    raster data
    :param args:
    :return:
    """

def binary_reclassify(*args, array=None, match=None):
    """
    Generalized version of binary_reclassify that can accomodate
    a local numpy array or processing on EE
    :param args:
    :return:
    """
    _backend = 'local'
    # args[0]/array=
    if array is None:
        raise IndexError("invalid raster= argument provided by user")
    # args[1]/match=
    if match is None:
        raise IndexError("invalid match= argument provided by user")
    if not _is_number(match):
        logger.warning(" One or more values in your match array are "
                       "not integers -- the reclass operation may produce "
                       "unexpected results")
    # process our array using the appropriate backend,
    # currently only local operations are supported
    if isinstance(array, Raster):
        _backend = 'local'
        array = array.to_georaster()
    elif isinstance(array, GeoRaster):
        _backend = 'local'
    elif isinstance(array, np.array):
        _backend = 'local'
    else:
        _backend = 'unknown'

    if _backend == "local":
        return _local_binary_reclassify(array, match)
    else:
        raise NotImplementedError("Currently only local binary "
                                  "reclassification is supported")


def _local_binary_reclassify(raster=None, match=None, invert=None,
                             dtype=np.uint8):
    """ binary reclassification of input data. All cell values in
    a numpy array are reclassified as uint8 (boolean) based on
    whether they match or do not match the values of an input match
    array.
    :param: args0 : a Raster, GeoRaster, or related generator object
    :param: args1 : a list object of integers specifying match values for
    :param: raster : keyword version of args0
    :param: match : keyword version of args1
    """
    # args[0]/raster=
    if raster is None:
        raise IndexError("invalid raster= argument supplied by user")
    # args[1]/match=
    if match is None:
        raise IndexError("invalid match= argument supplied by user")
    # args[2]/invert=
    if invert is None:
        # this is an optional arg
        invert = False
    # if this is a Raster object, just drop
    # raster down to a GeoRaster and pass on
    if isinstance(raster, Raster):
        raster = raster.to_georaster()
    # if this is a complete GeoRaster, try
    # to process the whole object
    if isinstance(raster, GeoRaster):
        raster = raster.raster
        return np.reshape(
            np.array(
                np.in1d(raster, match, assume_unique=True, invert=invert),
                dtype=dtype
            ),
            raster.shape
        )
    # if this is a big raster that we've split into chunks
    # process this piece-wise
    elif isinstance(raster, types.GeneratorType):
        return np.concatenate(
            [np.reshape(
                np.array(
                    np.in1d(d[0], match, assume_unique=True, invert=invert),
                    dtype=dtype
                ),
                (1, d.shape[1])  # array shape tuple e.g., (1,1111)
             )
             for i, d in enumerate(raster)]
        )
    else:
        raise ValueError("raster= input should be a Raster, GeoRaster, or",
                         "Generator that numpy can work with")


def _local_reclassify(*args):
    pass


def _local_crop(*args, raster=None, shape=None):
    """ wrapper for georasters.clip that will preform a crop operation on our input raster"""
    # args[0] / raster=
    if raster is None:
        raise IndexError("invalid raster= argument specified")
    # args[1] / shape=
    if shape is None:
        raise IndexError("invalid shape=argument specified")
    # sanity check and then do our crop operation
    # and return to user
    _enough_ram = _local_ram_sanity_check(raster.array)
    if not _enough_ram['available'] and not raster._using_disc_caching:
        logger.warning(" There doesn't apprear to be enough free memory"
                       " available for our raster operation. You should use"
                       "disc caching options with your dataset. Est Megabytes "
                       "needed: %s", -1*_enough_ram['bytes']*0.0000001)
    return raster.to_georaster().clip(shape)



def _local_clip(raster=None, shape=None):
    """clip is a hold-over from gr that performs a crop operation"""
    # args[0]/raster=
    if raster is None:
        raise IndexError("invalid raster= argument specified")
    # args[1]/shape=
    if shape is None:
        raise IndexError("invalid shape= argument specified")
    return _local_crop(raster=raster, shape=shape)

def _ee_extract(*args):
    """
    Earth Engine extract handler
    :param args:
    :return:
    """
    pass

def _local_extract(*args):
    """
    local raster extraction handler
    :param args:
    :return:
    """
    pass


def _ee_extract(*args):
    """
    EE raster extraction handler
    :param args:
    :return:
    """
    if not _HAVE_EE:
        raise AttributeError("Requested Earth Engine functionality, "
                             "but we failed to load and initialize the ee package.")


def _local_reproject(*args):
    pass


def _local_merge(rasters=None):
    """
    Wrapper for georasters.merge that simplifies merging raster segments
    returned by parallel operations.
    """
    if rasters is None:
        raise IndexError("invalid raster= argument specified")
    return merge(rasters)



def _local_split(raster=None, n=None):
    """
    Stump for np._array_split. splits an input array into n (mostly) equal segments,
    possibly for a future parallel operation.
    """
    # args[0]/raster=
    if raster is None:
        raise IndexError("invalid raster= argument specified")
    #args[1]/n=
    if n is None:
        raise IndexError("invalid n= argument specified")
    return np.array_split(
        np.array(raster.array, dtype=str(raster.array.data.dtype)),
        n
    )


def _local_ram_sanity_check(array=None):
    # args[0] (Raster object, GeoRaster, or numpy array)
    if array is None:
        raise IndexError("first pos. argument should be some kind of "
                         "raster data")

    _cost = _est_free_ram() - _est_array_size(array)
    return {
        'available': bool(_cost > 0),
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


def _est_array_size(obj=None, byte_size=None, dtype=None):
    """

    :param args:
    :return:
    """
    # args[0] is a list containing array dimensions
    if isinstance(obj, list) or isinstance(obj, tuple):
        _array_len = np.prod(obj)
    # args[0] is a GeoRaster object
    elif isinstance(obj, GeoRaster):
        dtype = obj.datatype
        _array_len = np.prod(obj.shape)
        _byte_size = NUMPY_TYPES[obj.datatype.lower()](1)
    # args[0] is a Raster object
    elif isinstance(obj, Raster):
        dtype = obj.array.dtype
        _array_len = np.prod(obj.array.shape)
        _byte_size = NUMPY_TYPES[obj.array.dtype.lower()](1)
    # args[0] is something else?
    else:
        _array_len = len(obj)
    # args[1]/dtype= argument was specified
    if dtype is not None:
        _byte_size = NUMPY_TYPES[dtype.lower()](1)
    else:
        raise IndexError("couldn't assign a default data type and an invalid ",
                         "dtype= argument specified")
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


def _is_number(num_list=None):
    """
    Shorthand listcomp function that will determine whether any
    item in a list is not a number.
    :param args[0]: a python list object
    :return: True on all integers,
    """
    try:
        if np.sum([not(isinstance(i, int) or isinstance(i, float))
                   for i in num_list]) > 0:
            return False
        else:
            return True
    except ValueError:
        return False
