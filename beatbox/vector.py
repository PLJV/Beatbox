
#!/usr/bin/env python2

__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2018, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor", "Alex Daniels", "Meghan Bogaerts", "Stephen Chang"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"


import os
import fiona
import geopandas as gp
import pandas as pd
import json

import pyproj

from shapely.geometry import *

import logging

_DEFAULT_EPSG = 2163

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


class Vector(object):
    def __init__(self, *args, **kwargs):
        """Handles file input/output operations for shapefiles \
        using fiona and shapely built-ins and performs select \
        spatial modifications on vector datasets

        Keyword arguments:
        filename= the full path filename to a vector
        dataset (typically a .shp file)
        json=jsonified text
        Positional arguments:
        1st= if no filname keyword argument was used,
        attempt to read the first positional argument
        """
        self._geometries = []
        self._attributes = {}
        self._filename = []
        self._schema = []
        self._crs = []
        self._crs_wkt = []
        # args[0] / filename= / json=
        try:
            # assume it's a filename
            if os.path.exists(args[0]):
                self.filename = args[0]
            # if our read fails, check
            # to see if it's JSON
            elif is_json(args[0]):
                self.read(string=args[0])
        except IndexError:
            if kwargs.get('filename', None) is not None:
                self.filename = kwargs.get('filename')
            elif kwargs.get('json', None) is not None:
                self.read(string=kwargs.get('json'))
            pass  # allow empty specification
        except Exception as e:
            raise e
        # if the user specified a filename, try to open it
        if self.filename:
            self.read(self.filename)

    def __copy__(self):
        """ simple copy method that creates a new instance of a vector class and assigns \
        default attributes from the parent instance
        """
        _vector_geom = Vector()
        _vector_geom._geometries = self._geometries
        _vector_geom._attributes = self._attributes
        _vector_geom._crs = self._crs
        _vector_geom._crs_wkt = self._crs_wkt
        _vector_geom._schema = self._schema
        _vector_geom._filename = self._filename

        return _vector_geom

    def __deepcopy__(self, memodict={}):
        """ copy already is a deep copy """
        return self.__copy__()

    @property
    def filename(self):
        """ decorated getter for our filename """
        return self._filename

    @filename.setter
    def filename(self, *args):
        """ decorated setter for our filename """
        try:
            self._filename = args[0]
        except Exception:
            raise Exception("General error occured while trying to assign filename")

    @property
    def crs(self):
        """ decorated getter for our Coordinate Reference System """
        return self._crs

    @crs.setter
    def crs(self, *args):
        """ decorated setter for our Coordinate Reference System

        Keyword arguments: None

        Positional arguments:
        1st = first positional argument is used to assign our class CRS value
        """
        try:
            self._crs = args[0]
        except Exception:
            raise Exception("General error occurred while trying to assign CRS")

    @property
    def schema(self):
        """ decorated getter for our schema """
        return(self._schema)

    @schema.setter
    def schema(self, *args):
        """ decorated setter for our schema

        Keyword arguments: None

        Positional arguments:
        1st = first positional argument is used to assign our class schema value
        """
        try:
            self._schema = args[0]
        except Exception:
            logger.warning("invalid schema argument provided -- falling back on "
                           "default from our shapely geometries")

    @property
    def geometries(self):
        """ decorated getter for our fiona geometries collection """
        return self._geometries

    @geometries.setter
    def geometries(self, *args):
        try:
            self._geometries = args[0]
        except Exception as e:
            raise e
        # default behavior is to accept shapely geometry as input, but a
        # user may pass a string path to a shapefile and we will handle the input
        # and write it to output -- this is essentially a file copy operation
        try:
            self.read(self._geometries)
        # did you pass an incorrect filename?
        except OSError:
            raise OSError("Unable to read file passed passed by user")
        # it can't be a string path -- assume is a Collection or Geometry object
        # and pass it on
        except Exception:
            self._fiona_to_shapely_geometries(geometries=self._geometries)

    @property
    def attributes(self):
        """ decorated getter for our attributes """
        return(self._attributes)

    @attributes.setter
    def attributes(self, *args):
        """ setter for our attributes """
        self._attributes = args[0]

    def _fiona_to_shapely_geometries(self, geometries=None):
        """
        Cast a list of features as a shapely geometries. This is
        used to assign internal geometries from fiona -> shapely geometries
        :param geometries:
        :return: None
        """
        self._geometries = [shape(ft['geometry']) for ft in list(geometries)]

    def _json_string_to_shapely_geometries(self, string=None):
        """
        Accepts a json string and parses it into a shapely feature collection
        stored internally
        :param string: GeoJSON string containing a feature collection to parse
        :return: None
        """
        # determine if string= is even json
        try:
            _json = json.loads(string)
        except Exception:
            raise Exception("unable to process string= "
                            "argument... is this not a json string?")
        # determine if string= is geojson
        try:
            _type = _json['type']
            _features = _json['features']
        except KeyError:
            raise KeyError("Unable to parse features from json. "
                           "Is this not a GeoJSON string?")
        try:
            self.crs = _json['crs']
        except KeyError:
            # nobody uses CRS with GeoJSON -- but it's default
            # projection is always(?) EPSG:4326
            logger.warning("no crs property defined for json input "
                           "-- assuming EPSG:4326")
            self.crs = {'crs': 'epsg:4326'}
        # listcomp : iterate over our features and convert them
        # to shape geometries
        self._geometries = [shape(ft['geometry']) for ft in _features]

    def read(self, *args, **kwargs):
        """
        Accepts a GeoJSON string or string path to a shapefile that is read
        and used to assign internal class variables for CRS, geometries, and schema

        Keyword arguments:
        filename= the full path filename to a vector dataset (typically a .shp file)
        string= json string that we should assign our geometries from

        Positional arguments:
        1st = either a full path to a file or a geojson string object
        :return: None
        """
        arg_err = "Unable to process first positional argument as a file or geojson string"
        # sandbox for potential input File/JSON data
        _json = None
        _filename = None
        # args[0] / -filename / -string
        try:
            _filename = kwargs.get('filename', args[0])
            if not os.path.exists(_filename):
                if is_json(_filename):
                    _json = _filename
                    _filename = None
                else:
                    raise AttributeError(arg_err)
            else:
                self.filename = _filename
        except IndexError:
            _json = kwargs.get('string', None)
            if not is_json(_json):
                _json = None
        # if this is a json string, parse out our geometry and attribute
        # data accordingly
        if _json is not None:
            self._json_string_to_shapely_geometries(string=_json)
        # otherwise, process this as a file and parse out or data using Fiona
        else:
            _shape_collection = fiona.open(self.filename)
            self._crs = _shape_collection.crs
            self._crs_wkt = _shape_collection.crs_wkt
            # parse our dict of geometries into an actual shapely list
            self._fiona_to_shapely_geometries(geometries=_shape_collection)
            self._schema = _shape_collection.schema
            # process our attributes
            self._attributes = pd.DataFrame(
                [dict(item['properties']) for item in _shape_collection]
            )

    def write(self, *args, **kwargs):
        """ wrapper for fiona.open that will write in-class geometry data to disk

        (Optional) Keyword arguments:
        filename -- the full path filename to a vector dataset (typically a .shp file)
        (Optional) Positional arguments:
        1st -- if no keyword argument was used, attempt to .read the first pos argument
        """
        # args[0] / filename=
        try:
            self.filename = kwargs.get('filename', args[0])
        except IndexError:
            # perhaps we explicitly set our filename elsewhere
            pass
        # args[1] / type=
        try:
            _type = kwargs.get('type', args[1])
        except IndexError:
            _type = 'ESRI Shapefile'  # by default, write as a shapefile
        try:
            # call fiona to write our geometry to disk
            with fiona.open(
                self.filename,
                'w',
                _type,
                crs=self.crs,
                schema=self.schema
            ) as shape:
                # If there are multiple geometries, put the "for" loop here
                shape.write({
                    'geometry': mapping(self.geometries),
                    'properties': {'id': 123},
                })
        except Exception:
            raise Exception("General error encountered trying "
                            "to call fiona.open on the input data. "
                            "Is the file not a shapefile?")

    def to_shapely_collection(self):
        """ return a shapely collection of our geometry data """
        return self.geometries

    def to_geodataframe(self):
        """ return our spatial data as a geopandas dataframe """
        try:
            _gdf = gp.GeoDataFrame({
                "geometry": gp.GeoSeries(self._geometries),
            })
            _gdf.crs = self.crs
            # merge in our attributes
            _gdf = _gdf.join(self._attributes)
        except Exception:
            logger.warning("failed to build a GeoDataFrame from shapely geometries -- "
                           "will try to read from original source file instead")
            _gdf = gp.read_file(self._filename)
        return _gdf

    def to_ee_feature_collection(self):
        return ee.FeatureCollection(self.to_geojson(stringify=True))

    def to_geojson(self, *args, **kwargs):
        """

        :param args:
        :param kwargs:
        :return:
        """
        _as_string = False
        try:
            _as_string = kwargs.get("stringify", args[0])
        except IndexError:
            _as_string = False
        # build a target dictionary
        feature_collection = {
            "type": "FeatureCollection",
            "features": [],
            "crs": [],
            "properties": []
        }
        # iterate over features in our shapely geometries
        # and build-out our feature_collection
        for feature in self._geometries:
            if isinstance(feature, dict):
                feature_collection["features"].append(feature)
            else:
                # assume that json will know what to do with it
                # and raise an error if it doesn't
                try:
                    feature_collection["features"].append(json.loads(feature))
                except Exception as e:
                    raise e
        # note the CRS
        if self._crs:
            feature_collection["crs"].append(self._crs)
        # define our properties (attributes)
        for i in self.attributes.index:
            feature_collection['properties'].append(
                self.attributes.loc[i].to_json()
            )
        # do we want this stringified?
        if _as_string:
            feature_collection = json.dumps(feature_collection)

        return feature_collection


def _geom_units(*args):
    # args[0]
    try:
        _gdf = args[0]
    except IndexError:
        raise IndexError("1st positional argument should either "
                         "be a Vector or GeoDataFrame object")
    if isinstance(_gdf, Vector):
        _gdf = _gdf.to_geodataframe()
    # by default, there should be a units key
    # associated with the CRS dict object. Prefer
    # to use that units entry
    try:
        return _gdf['crs']['units']
    # otherwise, let's hackishly lean on pyproj to figure out
    # units from the full PROJ.4 string
    except KeyError:
        proj_4_string = pyproj.Proj(
            "+init=EPSG:"+str(_gdf.crs['init'].split(":")[1])
        )
        _units = proj_4_string.srs.split("+units=")[1].split(" +")[0]
        if _units.find("m") != -1:
            return "m"
        else:
            return _units


def _local_rebuild_crs(*args):
    _gdf = args[0]
    _gdf.crs = fiona.crs.from_epsg(int(_gdf.crs['init'].split(":")[1]))
    return _gdf


def rebuild_crs(*args, **kwargs):
    """
    Build a CRS dict for a user-specified Vector or GeoDataFrame object
    :param args:
    :param kwargs:
    :return:
    """
    try:
        _backend = args[1]
    except IndexError:
        _backend = kwargs.get('backend', 'local')
    if _backend.lower().find('local') != -1:
        return _local_rebuild_crs(*args)
    elif _backend.lower().find('ee') != -1:
        raise BaseException("Currently only local operations for this function are supported")
    else:
        raise BaseException("Unknown backend type specified")

def is_json(*args, **kwargs):
    try:
        _string = kwargs.get("string", args[0])
    except IndexError:
        raise IndexError("invalid string= argument passed by user")
    # sneakily use json.loads() to test whether this is
    # a valid json string
    try:
        _string = json.loads(_string)
        return True
    except Exception:
        return False

