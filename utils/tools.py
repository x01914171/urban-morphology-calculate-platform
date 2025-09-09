# -*- coding: utf-8 -*-
# @Time    : 2025/2/17 02:08
# @Author  : WXB
# @File    : tools.py
# @Software: PyCharm

import geopandas as gpd
from shapely.geometry import Polygon, box
import geopandas as gpd
from shapely.ops import unary_union

def create_minimum_bounding_boxes(input_shp, output_shp):
    """
    为输入的多边形 Shapefile 文件创建一个包含所有多边形的总体最小外接矩形，
    并保存为新的 Shapefile 文件。

    参数:
    input_shp (str): 输入的多边形 Shapefile 文件路径。
    output_shp (str): 输出的总体最小外接矩形 Shapefile 文件路径。
    """
    # 读取包含多边形的 Shapefile 文件
    gdf = gpd.read_file(input_shp)

    # 获取所有多边形的总体边界（bounds）
    total_bounds = gdf.total_bounds  # 返回 (minx, miny, maxx, maxy)

    # 创建一个包含所有多边形的总体最小外接矩形
    min_bbox = box(*total_bounds)  # 使用 bounds 创建矩形

    # 创建一个新的 GeoDataFrame 来存储总体最小外接矩形
    bbox_gdf = gpd.GeoDataFrame(geometry=[min_bbox], crs=gdf.crs)

    # 保存为新的 Shapefile 文件
    bbox_gdf.to_file(output_shp)


def generate_bounding_polygon(input_shp_path, output_shp_path=None):
    """
    生成包含所有多边形的连续多边形范围

    参数:
        input_shp_path (str): 输入的 SHP 文件路径。
        output_shp_path (str): 保存的 SHP 文件路径。
    """
    # 1. 读取 SHP 文件
    gdf = gpd.read_file(input_shp_path)
    # 2. 合并所有多边形
    merged_polygon = unary_union(gdf.geometry)

    # 3. 生成凸包（连续的多边形 D）
    convex_hull_polygon = merged_polygon.convex_hull

    # 4. 创建新的 GeoDataFrame 并保存为 SHP 文件
    convex_hull_gdf = gpd.GeoDataFrame(geometry=[convex_hull_polygon], crs=gdf.crs)
    # convex_hull_gdf.to_file(output_shp_path)
    return convex_hull_gdf

