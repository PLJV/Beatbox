import numpy


class Raster(georasters.GeoRaster):
    """ Raster class is a wrapper meant to extend the functionality of the GeoRaster base class
    :arg file string specifying the full path to a raster file (typically a GeoTIFF)
    """
    def __init__(self, **kwargs):
        self.raster = None
        for i,arg in enumerate(kwargs):
            if arg == "file":
                self.open(file=kwargs[arg])

    def open(self, file=None):
        self.ndv, self.xsize, self.ysize, self.geot, self.projection, datatype = georasters.get_geo_info(file)
        if self.ndv is None :
            self.ndv = -99999
        self.raster = gdalnumeric.LoadFile(file)
        self.y_cell_size = self.geot[1]
        self.x_cell_size = self.geot[5]
        self.raster = numpy.ma.masked_array(self.raster, mask=self.raster == self.ndv, fill_value=self.ndv)

    def write(self, dst_filename=None, format=gdal.GDT_UInt16, driver=gdal.GetDriverByName('GTiff')):
        georasters.create_geotiff(name=dst_filename, Array=self.raster, geot=self.geot, projection=self.projection,
                                  datatype=format,driver=driver, ndv=self.ndv, xsize=self.xsize,
                                  ysize=self.ysize)

    def split(self, extent=Null, n=Null, **kwargs):
        # define our x/y vector ranges
        x = np.empty(n+1)
        x.fill(None)
        y = np.empty(n+1)
        x.fill(None)
        xmin, ymin, xmax, ymax = self.raster.bounds
        # define the x/y range for calculating the size of our extents
        xStep = (xmax-xmin)/n
        yStep = (ymax-ymin)/n
        # assign vertices to our product vectors
        for(i in 1:(multiple+1)){
        x[i] = ifelse(i==1,
                       min(xmin),
                       x[i-1]+xStep)
        y[i] = ifelse(i==1,
                       min(ymin),
                       y[i-1]+yStep)
        }
        # assign our vertices to extent objects
        extents = []
        # iterate over our extents, assigning as we go
        yStart = i = 1
        while i <= n**2:
            for j in 1:n: # stagger our y-values
              extents.append(list(x[j],x[j+1],y[yStart],y[yStart+1]))
              i+=1
            yStart += 1;
        return(extents)

class NassCdlRaster(Raster):
    """ NassCdlRaster inherits the functionality of the GeoRaster class and extends its functionality with
     filters and re-classification tools useful for dealing with NASS CDL data.
    :arg file string specifying the full path to a raster file (typically a GeoTIFF)
    """
    def __init__(self, **kwargs):
        Raster.__init__(self,kwargs)

    def binary_reclass(self, filter=None):
        pass

def prod(i):
    o = 1
    for j in i: o=o*j
    return(o)

def get_free_ram():
    """ determine the amount of free memory available on the current node
    """
    pass

def est_ram_usage(dim=None,dtype=None):
    """ estimate the RAM usage for an array object of dimensions
    arg dim: scalar or vector array specifying the dimensions of a numpy array (e.g., n=3;n=[3,2,1])
    """
    if type(dim) == int:
        dim = dim**2
    else:
        dim = prod(dim)

    return(dim*numpy.nbytes[dtype])
