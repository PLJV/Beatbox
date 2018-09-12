#!/usr/bin/python3
"""
__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2018, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor", "Alex Daniels", "Meghan Bogaerts", "Stephen Chang"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"
"""

import fiona
import geopandas as gp
import json
import copy
import ee

from shapely.geometry import *

_METERS_TO_DEGREES: int = 111000
_DEGREES_TO_METERS: float = (1 / _METERS_TO_DEGREES)

class Vector:
    def __init__(self, *args, **kwargs):
        """Handles file input/output operations for shapefiles \
        using fiona and shapely built-ins and performs select \
        spatial modifications on vector datasets

        Keyword arguments:
        filename= the full path filename to a vector dataset (typically a .shp file)

        Positional arguments:
        1st= if no filname keyword argument was used, attempt to read the first positional argument
        """

        self._geometries = []
        self._filename = []
        self._schema = []
        self._crs = []
        self._crs_wkt = []

        try:
            self.read(kwargs.get('filename', args[0]))
        except Exception as e:
            raise e

    @property
    def filename(self):
        """ decorated getter for our filename """
        return self._filename

    @filename.setter
    def filename(self, *args):
        """ decorated setter for our filename """
        try:
            self._filename = args[0]
        except Exception as e:
            raise e

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
        except Exception as e:
          raise e

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
            self._schema = self._geometries.schema

    @property
    def geometries(self):
        """ decorated getter for our fiona geometries collection """
        return(self._geometries)

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
        except OSError as e:
            raise e
        # it can't be a string path -- assume is a Collection or Geometry object
        # and pass it on
        except Exception:
            pass
        # is this a full Collection that we need to extract geometries from?
        try:
            self._geometries = [shape(ft['geometry']) for ft in self._geometries]
            if self._schema['geometry'] == 'Polygon':
                self._geometries = MultiPolygon(self._geometries)
                self._schema['geometry'] = 'MultiPolygon'
            elif self._schema['geometry'] == 'Point':
                self._geometries = MultiPoint(self._geometries)
                self._schema['geometry'] = 'MultiPoint'
            elif self._schema['geometry'] == 'Line':
                self._geometries = MultiLineString(self._geometries)
                self._schema['geometry'] = 'MultiLineString'
        # can't read()? assume this is a Geometry and pass it on
        except Exception:
            pass

    def read(self, *args, **kwargs):
        """Short-hand wrapper for fiona.open() that assigns class variables for \
         CRS, geometry, and schema.

        Keyword arguments:
        filename= the full path filename to a vector dataset (typically a .shp file)

        Positional arguments:
        1st = if no filename keyword argument is used, treat the first positional argument\
        as the filename
        """
        try:
            self._filename = kwargs.get('filename', args[0]) if kwargs.get('filename', args[0]) else self._filename
        except Exception as e:
            raise e

        shape_collection = fiona.open(self._filename)

        try:
            self._crs = shape_collection.crs
            self._crs_wkt = shape_collection.crs_wkt
            self._geometries = shape_collection
            self._schema = shape_collection.schema
        except Exception as e:
            raise e

    def write(self, *args, **kwargs):
        """ wrapper for fiona.open that will write in-class geometry data to disk

        (Optional) Keyword arguments:
        filename -- the full path filename to a vector dataset (typically a .shp file)
        (Optional) Positional arguments:
        1st -- if no keyword argument was used, attempt to .read the first pos argument
        """
        try:
            self._filename = kwargs.get('filename', args[0]) if kwargs.get('filename', args[0]) else ''
        except Exception:
            pass # assume we previously defined a _filename to use for our write()

        try:
            # call fiona to write our geometry to disk
            with fiona.open(
                    self._filename,
                    'w',
                    'ESRI Shapefile',
                    crs=self._crs,
                    schema=self._schema) as shape:
                # If there are multiple geometries, put the "for" loop here
                shape.write({
                    'geometry': mapping(self._geometries),
                    'properties': {'id': 123},
                })
        except Exception as e:
            raise e

    def __copy__(self):
        """ simple copy method that creates a new instance of a vector class and assigns \
        default attributes from the parent instance

        Keyword arguments: None

        Positional arguments: None
        """
        _vector_geom = Vector()
        _vector_geom._geometries = self._geometries
        _vector_geom._crs = self._crs
        _vector_geom._crs_wkt = self._crs_wkt
        _vector_geom._schema = self._schema
        _vector_geom._filename = self._filename

        return _vector_geom

    def __deepcopy__(self, memodict={}):
        """ a deep copy is a shallow copy is a deep copy """
        return self.__copy__()

    def to_collection(self):
        """ return a collection of our geometry data """
        return self.geometries

    def to_geopandas(self):
        """ return our spatial data as a geopandas dataframe """
        _gdf = gp.read_file(self._filename)
        # make sure we note our units, because GeoPandas doesn't by default
        _gdf.crs["units"] = ["degrees" if _gdf.geometry[0].wkt.find('.') != -1 else "meters"]
        return _gdf

    def to_ee_feature_collection(self):
        return ee.FeatureCollection(self.to_geojson(stringify=True))

    def to_geojson(self, *args, **kwargs):
        _as_string = False
        try:
            _as_string = True if kwargs.get("stringify", args) else False
        except IndexError:
            _as_string = False
        except Exception as e:
            raise e

        feature_collection = {
            "type": "FeatureCollection",
            "features": [],
            "crs": []
        }

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

        if self._crs:
            feature_collection["crs"].append(self._crs)

        if _as_string:
            feature_collection = json.dumps(feature_collection)

        return feature_collection


def intersection(vector=None, *args, **kwargs):
    """ Returns the intersection of our focal Vector class with another Vector class """
    pass

def over(vector=None, *args, **kwargs):
    """ Returns a boolean vector of overlapping features of our focal Vector class with another Vector class """
    pass


def buffer(*args, **kwargs):
    """Buffer a shapely geometry collection (or the focal Vector class) by some user-specified \
    distance

    Keyword arguments:
    vector= a Vector object with spatial data
    width= a width value to use for our buffering (in projected units of a given geometry \
    -- typically meters or degrees)

    Positional arguments:
    1st= if no width keyword is provided, the first positional argument is treated as the \
    width parameter
    """
    _vector_geom = kwargs.get('vector', args[0]) if kwargs.get('vector', args[0]) is not None else None
    _vector_geom = copy(_vector_geom)  # spec out a new class to store our buffering results
    if 'width' in list(map(str.lower, kwargs.keys())):
        _width = int(kwargs['width'])
    else:
        try:
            _width = int(args[0])
        except Exception as e:
            raise e
    # check and see if we are working in unit meters or degrees
    if _vector_geom._crs_wkt.find('Degree') > 0:
        _width = _DEGREES_TO_METERS * _width
    # build a schema for our buffering operations
    target_schema = _vector_geom.schema
    target_schema['geometry'] = 'MultiPolygon'
    # iterate our feature geometries and cast the output geometry as
    # a MultiPolygon geometry
    _vector_geom.schema = target_schema
    _vector_geom.geometries = MultiPolygon(
        [shape(ft['geometry']).buffer(_width)
         for ft in _vector_geom.geometries])

    return (_vector_geom)
