# -*- coding: utf-8 -*-
# @Time    : 2025/2/16 20:08
# @Author  : WXB
# @File    : extractByMask.py
# @Software: PyCharm
import os
import sys

from qgis._analysis import QgsNativeAlgorithms
from qgis._core import QgsVectorLayer, QgsRasterLayer, QgsApplication
from qgis import processing
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
import os
import sys

import rasterio
from rasterio.mask import mask
import geopandas as gpd
import numpy as np
import os

def mask_raster_with_vector(vector_path, raster_path, vector_gpd=None):
    """
    按矢量文件对栅格进行掩膜提取，并用结果覆盖源栅格图层。

    参数:
    vector_path (str): 矢量文件的路径。
    raster_path (str): 栅格文件的路径。
    """
    # 加载矢量数据
    vector_data = gpd.read_file(vector_path)
    if vector_gpd:
        vector_data = vector_gpd
    if vector_data.crs is None:
        raise ValueError("矢量文件未定义坐标系！")

    # 加载栅格数据
    with rasterio.open(raster_path) as src:
        # 确保矢量数据和栅格数据的坐标系一致
        if vector_data.crs != src.crs:
            vector_data = vector_data.to_crs(src.crs)

        # 提取矢量几何
        geometries = vector_data.geometry.tolist()

        # 执行掩膜提取
        out_image, out_transform = mask(src, geometries, crop=True, filled=True, nodata=src.nodata)

        # 获取掩膜后的元数据
        out_meta = src.meta.copy()
        out_meta.update({
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })

        # 定义临时输出文件路径
        temp_output_raster_path = raster_path.replace(".tif", "_masked.tif")

        # 保存掩膜后的栅格数据
        with rasterio.open(temp_output_raster_path, "w", **out_meta) as dest:
            dest.write(out_image)

        print(f"掩膜提取完成，结果已保存到: {temp_output_raster_path}")

        # 覆盖源栅格文件
    os.replace(temp_output_raster_path, raster_path)
    print(f"源栅格文件已覆盖: {raster_path}")