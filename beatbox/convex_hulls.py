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

from beatbox import Vector
from copy import copy
from scipy.sparse.csgraph import connected_components

_DEFAULT_BUFFER_WIDTH: int = 1000  # default width (in meters) of a geometry for various buffer operations
_METERS_TO_DEGREES: int = 111000
_DEGREES_TO_METERS: float = (1 / _METERS_TO_DEGREES)
_ARRAY_MAX: int = 1000 # maximum array length to attempt numpy operations on before chunking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _chunks(*args):
    """
    hidden function
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


def _dissolve_overlapping_geometries(*args, **kwargs):
    """
    hidden function
    :param args:
    :param kwargs:
    :return:
    """
    try:
        _buffers = kwargs.get('buffers', args[0])
    except IndexError:
        raise IndexError("invalid buffers= argument provided by user")
    # force casting as a GeoDataFrame
    try:
        _buffers = gp.GeoDataFrame({
            'geometry': _buffers
        })
    except ValueError as e:
        if isinstance(_buffers, gp.GeoDataFrame):
            pass
        else:
            raise e
    except Exception as e:
        raise e
    # determine appropriate groupings for our overlapping buffers
    if _buffers.size > _ARRAY_MAX:
        split = int(round(_buffers.size / _ARRAY_MAX) + 1)
        logger.warning("Attempting dissolve operation on a large vector dataset -- processing in %s chunks, "
                       "which may lead to artifacts at boundaries", split)
        chunks = list(_chunks(_buffers, split))
        # listcomp magic : for each geometry, determine whether it overlaps with all other geometries in this chunk
        chunks = [_buffers.geometry.overlaps(x).values.astype(int) for i, d in enumerate(chunks) for x in d.explode()]
        overlap_matrix = np.concatenate(chunks)
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
    hidden function that will use the group attribute from polygon features to classify
    point geometries -- this is intended to be used as a 'fuzzy' point
    classifier for point features entering a convex hull
    :param args:
    :param kwargs:
    :return:
    """
    try:
        _buffers = kwargs.get('buffers', args[0])
    except IndexError:
        raise IndexError("invalid buffers= argument provided by user")
    try:
        _points = kwargs.get('points', args[1])
    except IndexError:
        raise IndexError("invalid points= argument provided by user")
    # dissolve-by explode
    gdf_out = _dissolve_overlapping_geometries(_buffers)
    # return the right-sided spatial join
    return gp.\
        sjoin(_points, gdf_out, how='inner', op='intersects').\
        rename(columns={'index_right': 'clst_id'})


def convex_hull(*args, **kwargs):
    """
    accepts point features as a GeoDataFrame and uses geopandas to
    calulate a convex hull from the geometries
    :param args:
    :param kwargs:
    :return: GeoDataFrame
    """
    # try and handle our lone 'points' argument
    attr_err_msg = "points= input is invalid. try passing" \
                   " a GeoDataFrame or Vector object."
    try:
        _points = kwargs.get('points', args[0])
        if isinstance(_points, gp.GeoDataFrame):
            pass
        elif isinstance(_points, Vector):
            _points = _points.to_geodataframe()
        else:
            raise AttributeError(attr_err_msg)
    except AttributeError:
        raise AttributeError(attr_err_msg)
    except Exception as e:
        raise e

    return _points.convex_hull()

def fuzzy_convex_hulls(*args, **kwargs):
    """
    accepts geopandas datatframe as SpatialPoints, buffers the point geometries by some distance,
    and than builds a convex hull feature collection from clusters of points
    :param args:
    :param kwargs:
    :return:
    """
    try:
        _points = kwargs.get('points', args[0])
    except IndexError:
        raise IndexError("invalid points= argument passed by user")
    try:
        _width = kwargs.get('width', args[1])
    except IndexError:
        _width = _DEFAULT_BUFFER_WIDTH
    # drop our points features into a gdf if they aren't already
    if not isinstance(_points, gp.GeoDataFrame):
        _points = _points.to_geodataframe()
    # generate circular point buffers around our SpatialPoints features
    try:
        _point_buffers = copy(_points)
        if _point_buffers.crs['units'].find('meter') > 0:
            _point_buffers = _point_buffers.buffer(_width)
        else:
            _point_buffers = _point_buffers.buffer(_width / _METERS_TO_DEGREES)
    # assume AttributeErrors are due to args[0] not being a GeoPandas object
    except AttributeError as e:
        # if this is a string, assume that it is a path
        # and try and open it -- otherwise raise an error
        if isinstance(_points, str):
            _points = Vector(_points).to_geodataframe()
            _point_buffers = copy(_points)
            if _point_buffers.crs['units'].find('meter') > 0:
                _point_buffers = _point_buffers.buffer(_width)
            else:
                _point_buffers = _point_buffers.buffer(_width/_METERS_TO_DEGREES)
        else:
            raise e
    except Exception as e:
        raise e
    # dissolve our buffered geometries
    point_clusters = _attribute_by_overlap(_point_buffers, _points)
    # drop any strange columns (i.e., not our clst_id or geometries)
    cols_to_remove = list(point_clusters.columns)
    cols_to_remove.remove('clst_id')
    cols_to_remove.remove('geometry')
    for col in cols_to_remove:
        del point_clusters[col]
    # return our convex hulls as a GeoDataFrame
    gdf = gp.GeoDataFrame({'geometry': point_clusters.convex_hull})
    gdf.crs = point_clusters.crs
    return(gdf)


if __name__ == "__main__":
    pass
