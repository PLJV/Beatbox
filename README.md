# Beatbox
Simple, pythonic hooks for GeoRasters (GDAL) and the Orfeo Toolbox designed to offer a programmable and open alternative to fragstats for calculating landscape metrics, moving windows analyses, and other raster statistics. We would like to design the interface so that it can dynamically process large rasters an handle parallelized tasks on multi-core unix machines with a lot of ram : either your home rig -- or an instance on AWS. 

# Installation
From a direct download:
`python3 setup.py install`

From pip:
`pip3 install git+git://github.com/PLJV/Beatbox.git`

This work was born out of work related to the [QGIS/LecoS project](http://conservationecology.wordpress.com/lecos-land-cover-statistics/ "LecoS"). If you are looking for a good, open-source GUI for calculating landscape metrics, we recommend it. 
