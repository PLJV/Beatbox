import sys
import os

sys.path.append("..")

if __name__ == "__main__":
    rasters = [s for s in os.listdir(".") if "_30m_cdls.tif" in s]
    years = []
    for s in rasters:
        years.append(s.replace("_30m_cdls.tif", ""))
    for i, r in enumerate(rasters):
        r = NassCdlRaster(file=r)
        # covariates, as specified by our team
        pasture = r.binary_reclass(match=[62, 176])
        hay_alfalfa = r.binary_reclass(match=[6])
        hay = r.binary_reclass(match=[37])
        small_grains = r.binary_reclass(match=list(range(21, 25)) + [26, 28, 240])
        row_crop = r.binary_reclass(match=[1, 2, 5, 12, 13, 41, 225, 226, 232,
                                           237, 238, 239, 254])

        # define and process our windows
        names = ["pasture", "hay_alfalfa", "hay", "small_grains", "row_crop"]
        windows = [11, 107, 165, 237]
        for j, image in enumerate([pasture, hay_alfalfa, hay, small_grains, row_crop]):
            for k in windows:
                r.raster = ndimage.generic_filter(input=numpy.array(image, dtype='uint16'),
                                                  function=numpy.sum,
                                                  footprint=numpy.array(gen_circular_array(nPixels=k//2),
                                                  dtype='uint16'))
                r.write(dst_filename=years[i]+"_"+names[j]+"_"+str(k)+"x"+str(k)+".tif")
