from osgeo import gdal, ogr, osr
import os
import pandas

def makeDensityRaster(speciesOcc, inVector, pixelSize, outRas, noData):
    srcVector = ogr.Open(inVector)
    srcLayer = srcVector.GetLayer()
    srs = srcLayer.GetSpatialRef()
    # if the layer is not wgs84
    if srs.GetAttrValue("AUTHORITY", 1) != '4326':
        print('Layer projection should be WGS84!')
        return

    xMin, xMax, yMin, yMax = srcLayer.GetExtent()

    # Create the destination data source
    xRes = int((xMax - xMin) / pixelSize)
    yRes = int((yMax - yMin) / pixelSize)
    targetRas = gdal.GetDriverByName('GTiff').Create(outRas, xRes, yRes, 1, 6) # 6 == float
    targetRas.SetGeoTransform((xMin, pixelSize, 0, yMax, 0, -pixelSize))
    band = targetRas.GetRasterBand(1)
    band.SetNoDataValue(noData)

    # Rasterize clips the raster band
    gdal.RasterizeLayer(targetRas, [1], srcLayer, None, None, [0], ['ALL_TOUCHED=TRUE'])
    #os.remove(outRas)
    g = band.ReadAsArray()

    for point in speciesOcc.iterrows():
        xi = int((point[1]['x'] - xMin) / pixelSize)
        yi = int((point[1]['y'] - yMax) / -pixelSize)

        try:
            if g[yi,xi] != noData:
                g[yi,xi] += 1
            else:
                print('point ({}, {}) out of bounds'.format(point[1]['x'], point[1]['y']))
        except:
            print('point ({}, {}) out of bounds'.format(point[1]['x'], point[1]['y']))
            pass


    band.WriteArray(g)
    targetRasSRS = osr.SpatialReference()
    targetRasSRS.ImportFromWkt(srs.ExportToWkt())
    targetRas.SetProjection(targetRasSRS.ExportToWkt())
    band.FlushCache()