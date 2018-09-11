# Beatbox
Simple, pythonic hooks for GeoRasters (GDAL) and the Orfeo Toolbox designed to offer a programmable and open alternative to fragstats for calculating landscape metrics, moving windows analyses, and other raster statistics. We are designing the interface so that it can dynamically process large rasters and handle parallelized tasks on multi-core unix machines with a lot of ram : either your home rig -- or an instance on AWS. 

# Installation
From a direct download:
```python3 setup.py install```

From pip:
```bash
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

# Attribution
This work was born out of work related to the [QGIS/LecoS project](http://conservationecology.wordpress.com/lecos-land-cover-statistics/ "LecoS"). If you are looking for a good, open-source GUI for calculating landscape metrics, we recommend it. 
