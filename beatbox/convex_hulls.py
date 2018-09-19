#!/usr/bin/python3
"""
__author__ = ["Kyle Taylor", "Stephen Chang"]
__copyright__ = "Copyright 2017, Playa Lakes Joint Venture"
__credits__ = ["Stephen Chang", "Kyle Taylor"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"
"""
import logging
import numpy as np
import geopandas as gp

from copy import copy
from scipy.sparse.csgraph import connected_components

from .vector import Vector

_DEFAULT_BUFFER_WIDTH: int = 1000  # default width (in meters) of a geometry for various buffer operations
_METERS_TO_DEGREES: int = 111000
_DEGREES_TO_METERS: float = (1 / _METERS_TO_DEGREES)
_ARRAY_MAX: int = 800 # maximum array length to attempt numpy operations on before chunking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _chunks(*args):
    """
    Hidden function that will accept an array (list) and split it up into
    chunks of an arbitrary length using the Python yield built-in
    :param args:
    :return:
    """
    try:
        _array = args[0]
        _n_chunks = args[1]
    except IndexError as e:
        raise e
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(_array), _n_chunks):
        yield _array[i:i + _n_chunks]

def _units_are_metric(*args):
    """
    Hidden function that will (hackishly) determine whether
    a Shapely or GeoPandas object's Coordinate Reference System
    is using units of meters or degrees. This is needed for
    input data where a 'units' attribute is not set by Fiona
    or GeoPandas when a shapefile is read
    :param args:
    :return:
    """
    return True if args[0].crs['units'].find('meter')\
                   > 0 else False

def _dissolve_overlapping_geometries(*args, **kwargs):
    """
    Hidden function that will accept a GeoDataFrame containing Polygons,
    explode the geometries from single part to multi part, and then dissolve
    geometries that overlap spatially.
    :param args:
    :param kwargs:
    :return:
    """
    # args[0] / buffers=
    try:
        _buffers = args[0]
    except IndexError:
        if kwargs.get('buffers'):
            _buffers = kwargs.get('buffers')
        else:
            raise IndexError("invalid buffers= "
                             "argument provided by user")
    # force casting as a GeoDataFrame
    try:
        _buffers = gp.GeoDataFrame({
            'geometry': _buffers
        })
    except ValueError as e:
        if isinstance(_buffers, gp.GeoDataFrame):
            pass
        else:
            raise ValueError("Invalid buffers= argument input -- failed to"
                             " make a GeoDataFrame from input provided")
    except Exception:
        raise Exception("Unable to cast buffers= argument as a GeoDataFrame.")
    # determine appropriate groupings for our overlapping buffers
    if _buffers.size > _ARRAY_MAX:
        split = int(round(_buffers.size / _ARRAY_MAX) + 1)
        logger.warning("Attempting dissolve operation on a large "
                       "vector dataset -- processing in %s chunks, "
                       "which may lead to artifacts at boundaries", split)
        chunks = list(_chunks(_buffers, split))
        try:
            # listcomp magic : for each geometry, determine whether it overlaps with
            # all other geometries in this chunk
            overlap_matrix = np.concatenate(
                [_buffers.geometry.overlaps(x).values.astype(int)
                 for i, d in enumerate(chunks)
                 for x in d.explode()]
            )
            # free-up our RAM
            del chunks
        except AttributeError:
            raise AttributeError("Encountered an error when checking for overlaps in chunks of buffered input. "
                                 "This shouldn't happen. Consider updating your libraries with conda/pip and try"
                                 " again.")
    else:
        overlap_matrix = np.concatenate(
            [_buffers.geometry.overlaps(x).values.astype(int) for x in _buffers.explode()]
        )
    # merge attributes
    overlap_matrix.shape = (len(_buffers), len(_buffers))
    n, ids = connected_components(overlap_matrix)
    dissolved_buffers = gp.GeoDataFrame({
        'geometry': _buffers.geometry,
        'group': ids
    })
    # call geopandas dissolve with our 'ids' column and
    dissolved_buffers = dissolved_buffers.dissolve(by='group')
    dissolved_buffers.crs = _buffers.crs
    return dissolved_buffers


def _attribute_by_overlap(*args, **kwargs):
    """
    Hidden function that will use the group attribute from polygon features to classify
    point geometries -- this is intended to be used as a classifier for overlapping
    geometries
    :param args:
    :param kwargs:
    :return:
    """
    # args[0] / buffers=
    try:
        _buffers = args[0]
    except IndexError:
        if kwargs.get('buffers'):
            _buffers = kwargs.get('buffers')
        else:
           raise IndexError("invalid buffers= argument provided by user")
    # args[1] / points=
    try:
        _points = args[1]
    except IndexError:
        if kwargs.get('points'):
            _points = kwargs.get('points')
        else:
            raise IndexError("invalid points= argument provided by user")
    # dissolve-by explode
    gdf_out = _dissolve_overlapping_geometries(_buffers)
    # return the right-sided spatial join
    return gp.\
        sjoin(_points, gdf_out, how='inner', op='intersects').\
        rename(columns={'index_right': 'clst_id'})


def convex_hull(*args, **kwargs):
    """
    Accepts point features as a GeoDataFrame and uses geopandas to
    calulate a convex hull from the geometries
    :param args:
    :param kwargs:
    :return: GeoDataFrame
    """
    try:
        _points = args[0]
    except IndexError:
        if kwargs.get('points'):
            _points = kwargs.get('points')
        else:
            raise IndexError("invalid points= argument provided by user")
    # try and process our lone 'points' argument
    attr_err_msg = "points= input is invalid. try passing" \
                   " a GeoDataFrame or Vector object."
    if isinstance(_points, gp.GeoDataFrame):
        pass
    elif isinstance(_points, Vector):
        _points = _points.to_geodataframe()
    else:
        raise AttributeError(attr_err_msg)
    # GeoPandasDataframe->convex_hull()
    return _points.convex_hull()

def fuzzy_convex_hulls(*args, **kwargs):
    """
    Accepts a GeoDataFrame containing points, buffers the point geometries by some distance,
    and than builds convex hulls from point clusters
    :param args:
    :param kwargs:
    :return:
    """
    # args[0] / points=
    try:
        _points = args[0]
    except IndexError:
        if kwargs.get('points'):
            _points = kwargs.get('points')
        else:
            raise IndexError("invalid points= argument passed by user")
    # args[1] / width=
    try:
        _width = args[1]
    except IndexError:
        if kwargs.get('width'):
            _width = kwargs.get('width')
        else:
            _width = _DEFAULT_BUFFER_WIDTH
    # cast our points features as a gdf (if they aren't already)
    if not isinstance(_points, gp.GeoDataFrame):
        _points = _points.to_geodataframe()
    # generate circular point buffers around our SpatialPoints features
    try:
        _point_buffers = copy(_points)
        # adjust the width= parameter based on the projection
        # of our point buffers
        if _units_are_metric(_point_buffers):
            _point_buffers = _point_buffers.buffer(_width)
        else:
            logger.warning("Points dataframe is projected in degrees. Will convert to meters using a"
                           " scalar that is error-prone if you are far removed from the equator. "
                           "Try projecting in meters.")
            _point_buffers = _point_buffers.buffer(_width / _METERS_TO_DEGREES)
    # assume AttributeErrors are due to args[0] not being a GeoPandas object
    except AttributeError as e:
        # if this is a string, assume that it is a path
        # and try and open it -- otherwise raise an error
        if isinstance(_points, str):
            _points = Vector(_points).to_geodataframe()
            _point_buffers = copy(_points)
            if _units_are_metric(_point_buffers):
                _point_buffers = _point_buffers.buffer(_width)
            else:
                logger.warning("Points dataframe is projected in degrees. Will convert to meters using a"
                               " scalar that is error-prone if you are far removed from the equator. "
                               "Try projecting in meters.")
                _point_buffers = _point_buffers.buffer(_width/_METERS_TO_DEGREES)
        else:
            raise e
    except Exception as e:
        raise e
    # dissolve overlapping buffered geometries
    point_clusters = _attribute_by_overlap(_point_buffers, _points)
    # drop any strange columns lurking in our data (i.e., not our clst_id or geometries)
    cols_to_remove = list(point_clusters.columns).remove('clst_id').remove('geometry')
    for col in cols_to_remove:
        del point_clusters[col]
    # return our convex hulls as a GeoDataFrame
    gdf = gp.GeoDataFrame({'geometry': point_clusters.convex_hull})
    gdf.crs = point_clusters.crs
    return(gdf)

