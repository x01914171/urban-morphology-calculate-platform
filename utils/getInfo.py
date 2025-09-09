# -*- coding: utf-8 -*-
# @Time    : 2025/2/12 20:42
# @Author  : WXB
# @File    : getInfo.py
# @Software: PyCharm
from qgis._core import QgsRasterLayer, QgsRasterDataProvider, QgsCoordinateReferenceSystem, QgsRectangle, \
    QgsVectorLayer, QgsVectorDataProvider, QgsWkbTypes
import os
import os.path as osp


qgisDataTypeDict = {
    0 : "UnknownDataType",
    1 : "Uint8",
    2 : "UInt16",
    3 : "Int16",
    4 : "UInt32",
    5 : "Int32",
    6 : "Float32",
    7 : "Float64",
    8 : "CInt16",
    9 : "CInt32",
    10 : "CFloat32",
    11 : "CFloat64",
    12 : "ARGB32",
    13 : "ARGB32_Premultiplied"
}

def getRasterLayerAttrs(rasterLayer:QgsRasterLayer):

    rdp : QgsRasterDataProvider = rasterLayer.dataProvider()
    crs : QgsCoordinateReferenceSystem = rasterLayer.crs()
    extent: QgsRectangle = rasterLayer.extent()
    resDict = {
        "name" : rasterLayer.name(),
        "source" : rasterLayer.source(),
        "memory" : getFileSize(rasterLayer.source()),
        "extent" : f"min:[{extent.xMinimum():.6f},{extent.yMinimum():.6f}]; max:[{extent.xMaximum():.6f},{extent.yMaximum():.6f}]",
        "width" : f"{rasterLayer.width()}",
        "height" : f"{rasterLayer.height()}",
        "dataType" : qgisDataTypeDict[rdp.dataType(1)],
        "bands" : f"{rasterLayer.bandCount()}",
        "crs" : crs.description()
    }
    return resDict

def getVectorLayerAttrs(vectorLayer:QgsVectorLayer):
    vdp : QgsVectorDataProvider = vectorLayer.dataProvider()
    crs: QgsCoordinateReferenceSystem = vectorLayer.crs()
    extent: QgsRectangle = vectorLayer.extent()
    resDict = {
        "name" : vectorLayer.name(),
        "source" : vectorLayer.source(),
        "memory": getFileSize(vectorLayer.source()),
        "extent" : f"min:[{extent.xMinimum():.6f},{extent.yMinimum():.6f}]; max:[{extent.xMaximum():.6f},{extent.yMaximum():.6f}]",
        "geoType" : QgsWkbTypes.geometryDisplayString(vectorLayer.geometryType()),
        "featureNum" : f"{vectorLayer.featureCount()}",
        "encoding" : vdp.encoding(),
        "crs" : crs.description(),
        "dpSource" : vdp.description()
    }
    return resDict

def getFileSize(filePath):
    fsize = osp.getsize(filePath)  # 返回的是字节大小
    if fsize < 1024:
        return f"{round(fsize, 2)}Byte"
    else:
        KBX = fsize / 1024
        if KBX < 1024:
            return f"{round(KBX, 2)}Kb"
        else:
            MBX = KBX / 1024
            if MBX < 1024:
                return f"{round(MBX, 2)}Mb"
            else:
                return f"{round(MBX/1024,2)}Gb"