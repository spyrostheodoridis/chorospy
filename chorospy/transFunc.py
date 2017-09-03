import json
from osgeo import gdal, osr, ogr
import numpy
import subprocess

# Create a json file from a geotif to be used as input for ploting it as an image using javascript and canvas.
# The json file includes the extent (in wgs84 coordinates), and the native resolution (width and height) of the raster file
def transPoint(point, inproj, outproj):
    sr_srs = osr.SpatialReference()
    sr_srs.ImportFromEPSG(inproj)
    dst_srs = osr.SpatialReference()
    dst_srs.ImportFromEPSG(outproj)

    coordTransform = osr.CoordinateTransformation(sr_srs, dst_srs)

    gps_point = ogr.Geometry(ogr.wkbPoint)
    gps_point.AddPoint(point[0], point[1])
    gps_point.Transform(coordTransform)
    x = float(gps_point.ExportToWkt().split()[1].split('(')[1])
    y = float(gps_point.ExportToWkt().split()[2])
    return [x,y]


def rasterToJSON (infile, outfile, outproj):
    #reproject dataset to the desired projection
    subprocess.call(['gdalwarp', '-t_srs', 'EPSG:{}'.format(outproj), infile, 'outReproj.tif', '-overwrite'])
    projRas = gdal.Open('outReproj.tif')
    
    #get properties of new raster
    nrows = projRas.RasterYSize
    ncols = projRas.RasterXSize
    band1 = projRas.GetRasterBand(1)
    nodata = band1.GetNoDataValue()
    gdata = band1.ReadAsArray()
    x0, y0 = projRas.GetGeoTransform()[0], projRas.GetGeoTransform()[3]
    cellX, cellY = projRas.GetGeoTransform()[1], projRas.GetGeoTransform()[5]
    
    #get corners
    ulcorner, llcorner = [x0, y0], [x0, y0 + nrows*cellY]
    urcorner, lrcorner =  [x0 + ncols*cellX, y0], [x0 + ncols*cellX, y0 + nrows*cellY]
    
    dataType = gdal.GetDataTypeName(band1.DataType)
    #convert to float
    if dataType.startswith('Int'):
        gdata = gdata.astype(numpy.float32, copy=False)
    # new nodata value
    gdata[gdata == nodata] = -9999
    gdata = numpy.concatenate(gdata)
    gdata = gdata.tolist()
    #write to json
    gdataJSON = {'upLeft': transPoint(ulcorner, outproj, 4326), 'loLeft': transPoint(llcorner, outproj, 4326),
                 'upRight': transPoint(urcorner, outproj, 4326), 'loRight': transPoint(lrcorner, outproj, 4326),
                 'projEPSG': outproj, 'width': ncols, 'height': nrows, 'data': gdata}

    with open(outfile, 'w') as fp:
        json.dump(gdataJSON, fp)

    del gdata
    subprocess.call(['rm', 'outReproj.tif'])