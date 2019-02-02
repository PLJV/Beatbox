#!/usr/bin/python3
"""
__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2017, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor", "Alex Daniels"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"
"""

import sys, os, re
import numpy as np
import argparse as ap
import logging

from beatbox import Raster, moving_windows

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# define handlers for argparse for any arguments passed at runtime

parser = ap.ArgumentParser(
    description='Command-line interfaces for performing moving windows analyses' +
    ' on raster datasets using GDAL and numpy arrays'
)

# parser.add_argument('-h', '--help', help='Print this help message',
#     required=False
# )

parser.add_argument('-r', '--raster', help='Specifies the full path to source'+
    'raster file to use',
    required=True
)

parser.add_argument('-c', '--reclass', help='If we are going to reclassify'+
    'the input raster here are the cell values to match',
    required=False
)

parser.add_argument('-f', '--fun', help='Specifies the function to apply over'+
    ' a moving window. The default function is sum. Sum, mean, and sd are'+
    ' supported.',
    required=False
)

parser.add_argument('-w', '--window-size', help='Specifies the dimensions for'+
    ' our window',
    required=True
)

parser.add_argument('-t', '--target-values', help='Specifies the target values'+
    'we are reclassifying to, if the user asked us to reclassify. Default is'+
    'binary reclassification',
    required=False
)

def cat(string=None):
    ''' print minus the implied \n'''
    sys.stdout.write(string)
    sys.stdout.flush()

def print_usage():
    print(sys.argv[0]," : calculate raster statistics along a user-specified 'roving' windows buffer")
    print("usage:   " + sys.argv[0] + " -r <raster file> --reclass <match array>"
    " -w <window size in pixels> --fun <function name>")
    print("example: " + sys.argv[0] + " -r nass_2016.tif --reclass row_crop=1,2,"
    " 3;wheat=2,7 -w 3,11,33 --fun numpy.sum")
    sys.exit(0)

if __name__ == "__main__":
    # required parameters
    _INPUT_RASTER=None
    _IS_NASS=True
    _FUNCTION=np.sum
    _WINDOW_DIMS=[]
    _MATCH_ARRAYS={}
    _TARGET_RECLASS_VALUE=[1]
    # process runtime arguments
    args = vars(parser.parse_args())
    # -h / --help
    if args['help']:
        print_usage()
    # fix this:
    if len(sys.argv) == 1: print_usage()
    for i, arg in enumerate(sys.argv):
        arg.replace("--", "-")
        if arg == "-h":
            print_usage()
        elif arg == "-r":
            _INPUT_RASTER=sys.argv[i + 1]
        elif arg == "-t":
            _TARGET_RECLASS_VALUE=list(map(int, sys.argv[i + 1].split(',')))
        elif arg == "-function":
            try:
                function = sys.argv[i + 1]
                if re.search(string=function,pattern="\."):
                    function = function.split(".")
                    # assume user wants an explicit function : e.g., "numpy.min"
                    _FUNCTION=getattr(globals()[function[0]],function[1])
                else:
                    _FUNCTION=globals()[function]()
            except Exception as e:
                if re.search(function.lower(), "sum"):
                    _FUNCTION=numpy.sum
                elif re.search(function.lower(), "mean"):
                    _FUNCTION=numpy.mean
                elif re.search(function.lower(), "sd"):
                    _FUNCTION=numpy.std
                else:
                    print("couldn't handle the -function specified at runtime."
                    "see: -u for usage.")
                    raise e
        elif arg == "-mw":
            _WINDOW_DIMS=list(map(int, sys.argv[i + 1].split(',')))
        elif arg == "-reclass":  # e.g., "row_crop=12,34;cereal=2,3;corn=1,10"
            classes=sys.argv[i + 1].split(";")
            for c in classes:
                c=c.split("=")
                _MATCH_ARRAYS[c[0]]=list(map(int, c[1].split(",")))

    # sanity-check user input
    if not _MATCH_ARRAYS:
        _MATCH_ARRAYS['output'] = None
    if not _WINDOW_DIMS:
        raise ValueError("moving window dimensions need to be specified using"
        "the -mw argument at runtime. see -u for usage.")
    elif not _INPUT_RASTER:
        raise ValueError("this analysis requires a NASS input raster specified"
        "with -r argument at runtime. see -u for usage.")

    # process any re-classification requests prior to our filtering if asked
    if _MATCH_ARRAYS:
        r=Raster(file=_INPUT_RASTER)

        cat(" -- performing moving window analyses: ")

        for m in _MATCH_ARRAYS:
            focal=r
            if _MATCH_ARRAYS[m] is not None:
                focal.array=binary_reclassify(raster=focal, match=_MATCH_ARRAYS[m])
            for window in _WINDOW_DIMS:
                filename=str(m+"_"+str(window)+"x"+str(window))
                generic_filter(r = focal, function = _FUNCTION, size=window, \
                destfile = filename)
                cat(".")
