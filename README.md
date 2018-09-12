# Beatbox
Simple Python 3 wrapper interface for GDAL, GeoRasters, Shapely, and GeoPandas. Beatbox is designed to be a portable interface for working with large spatial datasets on cloud platforms like AWS and Google App Engine. You install it's standard dependencies with anaconda (or miniconda) and/or pip in seconds and produce datasets that can be integrated into distributed computing workflows. 

For an overview of installing the Earth Engine Python API ([RTM](https://developers.google.com/earth-engine/python_install_manual)).

We maintain beatbox and make it publically available so that our collaborators can check our math. It is still very much under active development, so don't use it in production. If you are experimenting with spatial data in Python and would like to get your hands dirty, dive in.

# Installation
From a direct download:
```python3 setup.py install```

From conda / pip:
```bash
conda install gdal numpy fiona shapely seaborn geopandas geoplot
pip install google-api-python-client
pip install earthengine-api
pip uninstall Beatbox
pip install git+git://github.com/PLJV/Beatbox.git
```

# Quickstart
## using ipython
```python
from beatbox import Vector, Raster

some_vector_data = Vector("/path/to/shapefile.shp")
some_raster_data = Raster("/path/to/raster.tif")
```
