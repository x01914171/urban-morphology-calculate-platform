# -*- coding: utf-8 -*-
# @Time    : 2025/2/17 19:39
# @Author  : WXB
# @File    : landscape.py
# @Software: PyCharm

import geopandas as gpd
from shapely.geometry import box
import numpy as np
import rasterio
from rasterio.mask import mask
from pylandstats import Landscape
from rasterio.features import rasterize, geometry_mask
import os
from rasterio.io import MemoryFile
from computation.AI_Calculation import AI
from computation.extractByMask import mask_raster_with_vector
from utils.tools import generate_bounding_polygon


def calculate_landscape_indices_byvector(
    vector_boundary_path,  # 矢量边界文件路径
    raster_image_path,     # 栅格图像文件路径
    metrics,               # 需要计算的景观指数（列表）
    output_dir,            # 输出栅格文件目录
    grid_size=1/120,         # 格网大小（默认1km）
    needBoundary = None
):
    """
    根据矢量边界构建格网，计算每个格网的景观指数，并每种指数输出一个栅格文件。

    参数:
        vector_boundary_path (str): 矢量边界文件路径（如 .shp 文件）。
        raster_image_path (str): 栅格图像文件路径（如 .tif 文件）。
        metrics (list): 需要计算的景观指数（如 ['patch_density', 'shannon_diversity_index']）。
        output_dir (str): 输出栅格文件目录。
        grid_size (int): 格网大小（默认1000米）。

    返回:
        None
    """
    try:
       # 1. 读取矢量边界文件
       boundary = gpd.read_file(vector_boundary_path)
       geometry = boundary.geometry.iloc[0]  # 获取多边形边界

       # 2. 裁剪多边形内的栅格
       with rasterio.open(raster_image_path) as src:
           out_image, out_transform = mask(src, [geometry], crop=True)
           out_meta = src.meta

       # 更新裁剪后的栅格元信息
       out_meta.update({
           "height": out_image.shape[1],
           "width": out_image.shape[2],
           "transform": out_transform
       })
       # 将裁剪后的数据写入内存文件
       with MemoryFile() as memfile:
           with memfile.open(**out_meta) as dataset:
               dataset.write(out_image)
           # 3. 构建格网（仅限多边形范围内）
           minx, miny, maxx, maxy = geometry.bounds  # 获取多边形边界范围
           x = np.arange(minx, maxx, grid_size)
           y = np.arange(miny, maxy, grid_size)

           grid = [
               box(xi, yi, xi + grid_size, yi + grid_size)
               for xi in x for yi in y
               if geometry.intersects(box(xi, yi, xi + grid_size, yi + grid_size))
           ]
           # 创建GeoDataFrame
           grid_gdf = gpd.GeoDataFrame(grid, columns=['geometry'], crs=boundary.crs)
           # 4. 用格网裁剪多边形内栅格，并计算景观指数
           landscape_indices = {metric: [] for metric in metrics}  # 为每种指数初始化一个列表
           for idx, row in grid_gdf.iterrows():
               geom = [row['geometry']]
               # 将 out_image 包装为虚拟数据集
               with memfile.open() as src:
                   cell_image, cell_transform = mask(src, geom, crop=True)
               cell_image = cell_image.squeeze()
               if np.any(cell_image >= 0):  # 如果格网内有数据
                   indicators = {}
                   landscape = Landscape(cell_image, res=(grid_size, grid_size),nodata=3)
                   if np.isin(1, cell_image):
                       ai = AI(cell_image, res=(grid_size, grid_size),nodata=3).aggregation_index(class_val=1)
                       indicators['ai'] = ai
                       indicators['largest_patch_index'] = landscape.largest_patch_index(class_val=1)
                       indicators['proportion_of_landscape'] = np.count_nonzero(cell_image == 1) * 100 / (
                                   np.count_nonzero(cell_image == 0) + np.count_nonzero(cell_image == 1))
                       indicators['patch_density'] = landscape.patch_density(class_val=1)
                       indicators['edge_density'] = landscape.edge_density(class_val=1, count_boundary=True)
                       indicators['landscape_shape_index'] = landscape.landscape_shape_index(class_val=1)
                   else:
                       indicators['ai'] = 0
                       indicators['largest_patch_index'] = 0
                       indicators['proportion_of_landscape'] = 0
                       indicators['patch_density'] = 0
                       indicators['edge_density'] = 0
                       indicators['landscape_shape_index'] = 0
                   for metric in metrics:
                       landscape_indices[metric].append(indicators[metric])
               else:
                   for metric in metrics:
                       landscape_indices[metric].append(np.nan)  # 无数据区域填充为NaN

           # 将景观指数添加到GeoDataFrame中
           for metric in metrics:
               grid_gdf[metric] = landscape_indices[metric]

           # 5. 将每种指数保存为单独的栅格文件
           if not os.path.exists(output_dir):
               os.makedirs(output_dir)

           for metric in metrics:
               # 创建景观指数的栅格数据
               rasterized_grid = rasterize(
                   [(geom, value) for geom, value in zip(grid_gdf.geometry, grid_gdf[metric])],
                   out_shape=out_image.shape[1:],
                   transform=out_transform,
                   fill=np.nan,  # 无数据区域填充为NaN
                   dtype=np.float32
               )
               out_meta.update(dtype=rasterio.float32)# 更新元数据
               # 保存栅格文件
               output_path = os.path.join(output_dir, f"{metric}.tif")
               with rasterio.open(output_path, 'w', **out_meta) as dst:
                   dst.write(rasterized_grid, 1)
               if needBoundary: mask_raster_with_vector(needBoundary, output_path)
               print(f"结果已保存至: {output_path}")
    except Exception as e: print(e)


def calculate_landscape_indices_byraster(
    grid_raster_path,      # 用于生成格网的栅格文件路径
    landscape_raster_path, # 用于景观计算的栅格文件路径
    metrics,               # 需要计算的景观指标（列表）
    output_dir,            # 保存目录
    needBoundary = None,
):
    """
    根据用于生成格网的栅格文件，定义格网范围，基于用于景观计算的栅格文件计算景观指数，
    并每种指数输出一个栅格文件。

    参数:
        grid_raster_path (str): 用于生成格网的栅格文件路径（如 .tif 文件）。
        landscape_raster_path (str): 用于景观计算的栅格文件路径（如 .tif 文件）。
        metrics (list): 需要计算的景观指标（如 ['patch_density', 'shannon_diversity_index']）。
        output_dir (str): 保存目录。

    返回:
        None
    """
    # 1. 读取用于生成格网的栅格文件
    with rasterio.open(grid_raster_path) as grid_src:
        grid_transform = grid_src.transform
        grid_height, grid_width = grid_src.shape
        grid_crs = grid_src.crs
        grid_meta = grid_src.meta

    # 2. 读取用于景观计算的栅格文件
    with rasterio.open(landscape_raster_path) as landscape_src:
        landscape_transform = landscape_src.transform
        landscape_data = landscape_src.read(1)
        landscape_crs = landscape_src.crs
        landscape_meta = landscape_src.meta

    # 检查两个栅格文件的坐标系是否一致
    if grid_crs != landscape_crs:
        raise ValueError("用于生成格网的栅格文件和用于景观计算的栅格文件的坐标系不一致！")

    # 3. 初始化存储每种景观指数的数组
    landscape_indices = {metric: np.full((grid_height, grid_width), np.nan, dtype=np.float32) for metric in metrics}
    # 4. 遍历每个格网，计算景观指数
    for i in range(grid_height):
        for j in range(grid_width):
            # 获取当前格网的范围
            x_min, y_max = grid_transform * (j, i)
            x_max, y_min = grid_transform * (j + 1, i + 1)

            # 在用于景观计算的栅格文件中裁剪当前格网区域
            row_start, col_start = ~landscape_transform * (x_min, y_max)
            row_end, col_end = ~landscape_transform * (x_max, y_min)
            # 确保 row_start < row_end 和 col_start < col_end
            if row_start > row_end:
                row_start, row_end = row_end, row_start
            if col_start > col_end:
                col_start, col_end = col_end, col_start
            # 将坐标转换为整数
            row_start, row_end = int(row_start), int(row_end)
            col_start, col_end = int(col_start), int(col_end)

            # 确保裁剪区域在范围内
            if row_start >= 0 and col_start >= 0 and row_end < landscape_data.shape[0] and col_end < landscape_data.shape[1]:
                cell_data = landscape_data[row_start:row_end, col_start:col_end]
                if np.any(cell_data >= 0):  # 忽略无数据区域
                    indicators = {}
                    landscape = Landscape(cell_data, res=(abs(landscape_transform.a), abs(landscape_transform.e)))
                    if np.isin(1, cell_data):
                        ai = AI(cell_data,
                                res=(abs(landscape_transform.a), abs(landscape_transform.e))).aggregation_index(
                            class_val=1)
                        indicators['ai'] = ai
                        indicators['largest_patch_index'] = landscape.largest_patch_index(class_val=1)
                        indicators['proportion_of_landscape'] = np.count_nonzero(cell_data == 1) * 100 / (np.count_nonzero(cell_data == 0) + np.count_nonzero(cell_data == 1))
                        indicators['patch_density'] = landscape.patch_density(class_val=1)
                        indicators['edge_density'] = landscape.edge_density(class_val=1,count_boundary=True)
                        indicators['landscape_shape_index'] = landscape.landscape_shape_index(class_val=1)
                    else:
                        indicators['ai'] = 0
                        indicators['largest_patch_index'] = 0
                        indicators['proportion_of_landscape'] = 0
                        indicators['patch_density'] = 0
                        indicators['edge_density'] = 0
                        indicators['landscape_shape_index'] = 0
                    for metric in metrics:
                        landscape_indices[metric][i, j] = indicators[metric]
    # 5. 将每种景观指数保存为单独的栅格文件
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for metric in metrics:
        output_path = os.path.join(output_dir, f"{metric}.tif")
        with rasterio.open(output_path, 'w', **grid_meta) as dst:
            dst.write(landscape_indices[metric], 1)
        if needBoundary: mask_raster_with_vector(needBoundary, output_path)
        print(f"结果已保存至: {output_path}")





def calculate_landscape_indices_bybuildings(
    vector_boundary_path,  # 矢量边界文件路径
    raster_image_path,     # 栅格图像文件路径
    metrics,               # 需要计算的景观指数（列表）
    output_dir,            # 输出栅格文件目录
    grid_size=1/120,         # 格网大小（默认1km）
    needBoundary = None
):
    """
    根据矢量边界构建格网，计算每个格网的景观指数，并每种指数输出一个栅格文件。

    参数:
        vector_boundary_path (str): 矢量边界文件路径（如 .shp 文件）。
        raster_image_path (str): 栅格图像文件路径（如 .tif 文件）。
        metrics (list): 需要计算的景观指数（如 ['patch_density', 'shannon_diversity_index']）。
        output_dir (str): 输出栅格文件目录。
        grid_size (int): 格网大小（默认1000米）。

    返回:
        None
    """
    try:
       # 1. 读取矢量边界文件
       boundary = generate_bounding_polygon(vector_boundary_path)
       geometry = boundary.geometry.iloc[0]  # 获取多边形边界
       # needBoundary = vector_boundary_path
       # 2. 裁剪多边形内的栅格
       with rasterio.open(raster_image_path) as src:
           out_image, out_transform = mask(src, [geometry], crop=True)
           out_meta = src.meta

       # 更新裁剪后的栅格元信息
       out_meta.update({
           "height": out_image.shape[1],
           "width": out_image.shape[2],
           "transform": out_transform
       })
       # 将裁剪后的数据写入内存文件
       with MemoryFile() as memfile:
           with memfile.open(**out_meta) as dataset:
               dataset.write(out_image)
           # 3. 构建格网（仅限多边形范围内）
           minx, miny, maxx, maxy = geometry.bounds  # 获取多边形边界范围
           x = np.arange(minx, maxx, grid_size)
           y = np.arange(miny, maxy, grid_size)

           grid = [
               box(xi, yi, xi + grid_size, yi + grid_size)
               for xi in x for yi in y
               if geometry.intersects(box(xi, yi, xi + grid_size, yi + grid_size))
           ]
           # 创建GeoDataFrame
           grid_gdf = gpd.GeoDataFrame(grid, columns=['geometry'], crs=boundary.crs)
           # 4. 用格网裁剪多边形内栅格，并计算景观指数
           landscape_indices = {metric: [] for metric in metrics}  # 为每种指数初始化一个列表
           for idx, row in grid_gdf.iterrows():
               geom = [row['geometry']]
               # 将 out_image 包装为虚拟数据集
               with memfile.open() as src:
                   cell_image, cell_transform = mask(src, geom, crop=True)
               cell_image = cell_image.squeeze()
               if np.any(cell_image >= 0):  # 如果格网内有数据
                   indicators = {}
                   landscape = Landscape(cell_image, res=(grid_size, grid_size))
                   if np.isin(1, cell_image):
                       ai = AI(cell_image, res=(grid_size, grid_size)).aggregation_index(class_val=1)
                       indicators['ai'] = ai
                       indicators['largest_patch_index'] = landscape.largest_patch_index(class_val=1)
                       indicators['proportion_of_landscape'] = np.count_nonzero(cell_image == 1) * 100 / (
                                   np.count_nonzero(cell_image == 0) + np.count_nonzero(cell_image == 1))
                       indicators['patch_density'] = landscape.patch_density(class_val=1)
                       indicators['edge_density'] = landscape.edge_density(class_val=1, count_boundary=True)
                       indicators['landscape_shape_index'] = landscape.landscape_shape_index(class_val=1)
                   else:
                       indicators['ai'] = 0
                       indicators['largest_patch_index'] = 0
                       indicators['proportion_of_landscape'] = 0
                       indicators['patch_density'] = 0
                       indicators['edge_density'] = 0
                       indicators['landscape_shape_index'] = 0
                   for metric in metrics:
                       landscape_indices[metric].append(indicators[metric])
               else:
                   for metric in metrics:
                       landscape_indices[metric].append(np.nan)  # 无数据区域填充为NaN

           # 将景观指数添加到GeoDataFrame中
           for metric in metrics:
               grid_gdf[metric] = landscape_indices[metric]

           # 5. 将每种指数保存为单独的栅格文件
           if not os.path.exists(output_dir):
               os.makedirs(output_dir)

           for metric in metrics:
               # 创建景观指数的栅格数据
               rasterized_grid = rasterize(
                   [(geom, value) for geom, value in zip(grid_gdf.geometry, grid_gdf[metric])],
                   out_shape=out_image.shape[1:],
                   transform=out_transform,
                   fill=np.nan,  # 无数据区域填充为NaN
                   dtype=np.float32
               )

               # 保存栅格文件
               output_path = os.path.join(output_dir, f"{metric}.tif")
               with rasterio.open(output_path, 'w', **out_meta) as dst:
                   dst.write(rasterized_grid, 1)
               if needBoundary: mask_raster_with_vector(needBoundary, output_path,vector_gpd=boundary)
               print(f"结果已保存至: {output_path}")
    except Exception as e: print(e)

