import json
from osgeo import gdal, osr
import numpy
# cCeate a json file from a geotif to be used as input for ploting it as an image using javascript and canvas.
# The json file includes the extent (in wgs84 coordinates), and the native resolution (width and height) of the raster file
def rasterToJSON (infile, outfile, outproj):
    # Open source dataset in wgs84
    src_ds = gdal.Open(infile)
    #get origin in wgs84
    ulcorner = [src_ds.GetGeoTransform()[0], src_ds.GetGeoTransform()[3]]
    lrcorner = [src_ds.GetGeoTransform()[0] + src_ds.GetGeoTransform()[1]*src_ds.RasterXSize,
               src_ds.GetGeoTransform()[3] + src_ds.GetGeoTransform()[5]*src_ds.RasterYSize]

    # Define target SRS
    dst_srs = osr.SpatialReference()
    dst_srs.ImportFromEPSG(outproj)
    dst_wkt = dst_srs.ExportToWkt()
    #define parameters for transformation
    error_threshold = 0.125  # error threshold (the same default value as in gdalwarp)
    resampling = gdal.GRA_NearestNeighbour

    # Call AutoCreateWarpedVRT() to fetch default values for target raster dimensions and geotransform
    tmp_ds = gdal.AutoCreateWarpedVRT( src_ds,
                                       None, # src_wkt : if none it will use the source wtk
                                       dst_wkt,
                                       resampling,
                                       error_threshold )
    #get properties of new raster
    nrows = tmp_ds.RasterYSize
    ncols = tmp_ds.RasterXSize
    band1 = tmp_ds.GetRasterBand(1)
    nodata = band1.GetNoDataValue()
    gdata = band1.ReadAsArray()
    dataType = gdal.GetDataTypeName(band1.DataType)
    #convert to float
    if dataType.startswith('Int'):
        gdata = gdata.astype(numpy.float32, copy=False)
    # new nodata value
    gdata[gdata == nodata] = -9999
    gdata = numpy.concatenate(gdata)
    gdata = gdata.tolist()
    #write to json
    gdataJSON = {'extent': [[ulcorner[0], ulcorner[1]], [lrcorner[0], lrcorner[1]]], 'width': ncols, 'height': nrows, 'data': gdata}

    with open(outfile, 'w') as fp:
        json.dump(gdataJSON, fp)

    del gdata
 