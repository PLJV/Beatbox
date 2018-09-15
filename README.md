### Beatbox
Simple Python wrapper interface for GDAL, GeoRasters, Shapely, and GeoPandas. Beatbox is designed to be a portable interface for working with large spatial datasets on cloud platforms like AWS and Google App Engine. You install it's standard dependencies with anaconda (or miniconda) and/or pip in seconds and produce datasets that can be integrated into distributed computing workflows. 

For an overview of installing the Earth Engine Python API ([RTM](https://developers.google.com/earth-engine/python_install_manual)).

We maintain beatbox and make it publically available so that our collaborators can check our math. It is still very much under active development, so don't use it in production. If you are experimenting with spatial data in Python and would like to get your hands dirty, dive in.

### Installation
From a direct download:
```python setup.py install```

From conda / pip:
```bash
conda install pyCrypto GDAL numpy pandas fiona shapely geopandas scikit-learn 

pip install google-api-python-client
pip install earthengine-api

pip uninstall Beatbox
pip install git+git://github.com/PLJV/Beatbox.git
```

### Quickstart
##### using ipython
```python
from beatbox import Do, Vector, Raster, fuzzy_convex_hulls

water_raster = Raster("/path/to/water_raster.tif")
spatial_points = Vector("/path/to/spatialpoints.shp")
convex_hulls = fuzzy_convex_hulls(spatial_points, width=1033)

result = Do({
  'what': extract,
  'with': [ convex_hulls, water_raster ]
})

```
