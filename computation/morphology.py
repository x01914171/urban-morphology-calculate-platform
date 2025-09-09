# coding=utf-8

import os
import shutil

from computation.extractByMask import mask_raster_with_vector
from utils.tools import create_minimum_bounding_boxes

# os.environ['PROJ_LIB'] = r"G:\qgis\apps\Python312\lib\site-packages\rasterio\proj_data\proj.db"
from datetime import datetime as d
import fiona
from shapely.geometry import shape, Polygon
from pyproj import Proj, Transformer
import numpy as np
from itertools import combinations
from pyproj import Geod
from math import cos, sin, radians
from scipy import stats
import rasterio
from rasterio.transform import from_origin
import multiprocessing
from tqdm import tqdm

# 忽略haw计算出现的area=0作分母
np.seterr(divide='ignore', invalid='ignore')
# 定义参考椭球体用于计算投影长度
geod = Geod(ellps='WGS84')
building_min_height=1
building_min_area=5
numberOfEachDegree = 120  # 结果的空间分辨率 -> (1/num)° , 这里的120即最终空间分辨率为1°/120，为0.5‘
# 高度字段
heightField = 'Height'  # 按照shp数据格式更改字段名称
# 区域名称（存放结果的名称）
regionName = 'UCP'

tDict=None
# 获取全部shp文件
def getInitShpList(pathRoot):
    shpPathList = []
    for root, dirs, files in os.walk(pathRoot):
        for file in files:
            if file.endswith('.shp'):
                shpPathList.append(os.path.join(root, file))
    print("读取 {} 个shp文件 当前时间 {}".format(len(shpPathList), d.now().strftime('%m-%d %H:%M:%S')))
    return shpPathList


def create_utm_transformers():  # 60个分带转换器先构建好
    transformers, transformersRev = {}, {}
    for zone in range(1, 61):
        for hemisphere in ['north', 'south']:
            proj_string = f'+proj=utm +zone={zone} {"+south" if hemisphere == "south" else ""} +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
            # Geo to Proj
            transformers[(zone, hemisphere)] = Transformer.from_proj(
                Proj(proj='latlong', datum='WGS84'),
                Proj(proj_string),
                always_xy=True,
            )
            # Proj to Geo
            transformersRev[(zone, hemisphere)] = Transformer.from_proj(
                Proj(proj_string),
                Proj(proj='latlong', datum='WGS84'),
                always_xy=True,
            )
    return transformers, transformersRev


def calcu4ProjLength(coordiList):  # 计算四个方向上的投影长度
    numberOfCombi = (len(coordiList)) * (len(coordiList) - 1) // 2  # to int
    proj4LengthMat = np.zeros([numberOfCombi, 4])  # 开空间存结果
    # 计算建筑物每条边的投影长度
    for count, dotPair in enumerate(combinations(coordiList, 2), 0):
        azimuth1, azimuth2, distance = geod.inv(dotPair[0][0], dotPair[0][1], dotPair[1][0], dotPair[1][1])
        proj4LengthMat[count, 0] = abs(distance * sin(radians((azimuth1 + 360) % 360)))  # fro 0 (东西方向上的投影长度（和北风0°垂直）)
        proj4LengthMat[count, 1] = abs(distance * cos(radians((azimuth1 + 360) % 360)))  # fro 90 (南北方向上的投影长度（和东风90°垂直）)
        proj4LengthMat[count, 2] = abs(
            distance * sin(radians((azimuth1 + 360) % 360 - 45)))  # fro 45 (东南(西北)方向上的投影长度(和东北风45°垂直))
        proj4LengthMat[count, 3] = abs(
            distance * cos(radians((azimuth1 + 360) % 360 - 45)))  # fro 135 (东北(西南)方向上的投影长度(和东南风135°垂直))
    # 返回最大的作为该建筑的投影长度
    return proj4LengthMat.max(axis=0)  # np.array[max(0), max(90), max(45), max(135)]  shape->(4,)


def loadGeoAndHeightData(shpFileDir):
    transformers, transformersRev = create_utm_transformers()
    areaList, heightList, centerLocationList, perimeterList, proj4Length = [], [], [], [], []
    print(
        "开始加载 {} ，当前时间 {}".format(shpFileDir.split("\\")[-1].split(".")[0], d.now().strftime('%m-%d %H:%M:%S')))
    with fiona.open(shpFileDir, 'r', as_int=True) as shp:
        for feature in tqdm(shp, desc=shpFileDir.split("\\")[-1].split(".")[0], position=0, leave=True):
            geometry = feature['geometry']
            height = feature['properties'][heightField]  # Height or pred_Heigh
            if height < building_min_height or geometry is None:  # 清除高度小于1的记录、缺少几何信息的记录、以及投影面积偏差的记录(数据原因)
                continue

            elif geometry['type'] == 'Polygon':
                # get proj para
                geoCoordi = geometry['coordinates'][0][:-1]  # [1,2,3,4,5,1] 去掉最后一个点
                geoCoordi = [(item[0], item[1]) for item in geoCoordi]
                firstPoint = geoCoordi[0]  # firstPoint
                utm_zone, hemisphere = int((firstPoint[0] + 180) / 6) + 1, 'south' if firstPoint[1] < 0 else 'north'
                transformer = transformers[(utm_zone, hemisphere)]

                # proj and create shape object
                projCoordi = [transformer.transform(lon, lat) for lon, lat in geoCoordi]
                polygonShape = shape(Polygon(projCoordi))
                polyArea = polygonShape.area

                if polyArea <= building_min_area or polyArea >= 400000:  # 清除误差记录
                    continue

                # CenterLocation (Geo)
                centerLocationList.append(transformersRev[(utm_zone, hemisphere)].transform(polygonShape.centroid.x,
                                                                                            polygonShape.centroid.y))  # Geo
                # Area
                areaList.append(polyArea)
                # Perimeter
                perimeterList.append(polygonShape.length)
                # Height
                heightList.append(height)
                # proj4theta
                proj4Length.append(calcu4ProjLength(geoCoordi))


            elif geometry['type'] == 'MultiPolygon':
                for single in geometry['coordinates']:

                    # 这里要处理这个single
                    geoCoordi = single[0][:-1]  # [1,2,3,4,5,1] 去掉最后一个点
                    geoCoordi = [(item[0], item[1]) for item in geoCoordi]
                    firstPoint = geoCoordi[0]  # firstPoint
                    utm_zone, hemisphere = int((firstPoint[0] + 180) / 6) + 1, 'south' if firstPoint[1] < 0 else 'north'
                    transformer = transformers[(utm_zone, hemisphere)]

                    # proj and create shape object
                    projCoordi = [transformer.transform(lon, lat) for lon, lat in geoCoordi]
                    polygonShape = shape(Polygon(projCoordi))
                    polyArea = polygonShape.area
                    if polyArea <= building_min_area or polyArea >= 400000:  # 清除误差记录
                        continue

                    # CenterLocation (Geo)
                    centerLocationList.append(transformersRev[(utm_zone, hemisphere)].transform(polygonShape.centroid.x,
                                                                                                polygonShape.centroid.y))  # Geo
                    # Area
                    areaList.append(polyArea)
                    # Perimeter
                    perimeterList.append(polygonShape.length)
                    # Height
                    heightList.append(height)
                    # proj4theta
                    proj4Length.append(calcu4ProjLength(geoCoordi))

            else:
                print("未定义类型 {} ".format(geometry['type']))
    print(
        "加载 {} 完成，当前时间 {}".format(shpFileDir.split("\\")[-1].split(".")[0], d.now().strftime('%m-%d %H:%M:%S')))

    return np.array(areaList), np.array(heightList), np.array(centerLocationList), np.array(perimeterList), np.array(
        proj4Length)


def calcuWallArea(area, height, perimeter):
    return area + perimeter * height  # 返回一个建筑物的表面积（顶面面积（占地面积）+侧面积（周长*高度））


def getGridTotalArea(latList, lonList):
    transformers, transformersRev = create_utm_transformers()  # 构建UTM投影转换器
    gridTotalArea = np.zeros((len(latList) - 1, len(lonList) - 1))  # 申请空间存放结果数据
    # 计算每个pixel的面积
    for latIndex, (startLat, endLat) in enumerate(zip(latList[:-1], latList[1:]), 0):
        for lonIndex, (startLon, endLon) in enumerate(zip(lonList[:-1], lonList[1:]), 0):
            center = ((startLon + endLon) / 2, (startLat + endLat) / 2)  # 提取中心点以期确定投影分带
            geoGridCorner = [(startLon, startLat), (startLon, endLat), (endLon, endLat),
                             (endLon, startLat)]  # 提取角点构建shapely对象
            utm_zone = int((center[0] + 180) / 6) + 1
            hemisphere = 'south' if center[1] < 0 else 'north'
            projGridCornor = [transformers[(utm_zone, hemisphere)].transform(lon, lat) for lon, lat in
                              geoGridCorner]  # 投影
            gridTotalArea[latIndex, lonIndex] = shape(Polygon(projGridCornor)).area  # 计算面积填进去
    return gridTotalArea


def calcuSingleData(data):
    shpFileDir=data[0]
    folderDict = data[1]
    threeDptions = data[2]
    # 获取城市名称用于保存数据
    cityName = shpFileDir.split("\\")[-1].split(".")[0]

    # 周长面积等基本信息和四个角度的投影长度
    area, height, centerLocation, perimeter, proj4Length = loadGeoAndHeightData(
        shpFileDir)

    # 算体积（帮助算面积加权高度 Haw）
    volume = area * height

    # 算墙面面积（帮助算表面积比率 λb）
    wallArea = calcuWallArea(area, height, perimeter)

    # 计算四个方向上的投影面积
    proj4Area = proj4Length * height.reshape(-1, 1)

    # 提取中心点经纬度为单独的array用来匹配binned_statistic参数类型
    lon = centerLocation[:, 0]
    lat = centerLocation[:, 1]

    # 提取边界的经纬度
    minLon = np.floor(lon.min()).astype('int')
    maxLon = np.ceil( lon.max()).astype('int')
    minLat = np.floor(lat.min()).astype('int')
    maxLat = np.ceil( lat.max()).astype('int')

    # nx, ny =120 都是1°分为120个Grid，numberOfEachDegree 默认是120
    # 注意！！！由于binned_statistic函数要求区间单增，所以经度是反着来的（越往两级纬度越低，后面改代码要当心！！！！！）

    binX = np.linspace(minLon, maxLon, (maxLon - minLon) * numberOfEachDegree + 1)  # 划分bin用于统计
    binY = np.linspace(minLat, maxLat, (maxLat - minLat) * numberOfEachDegree + 1)  # 划分bin用于统计 （注意纬度区间！）
    binZ = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 400        ]          # 计算dh的高度区间划分

    # 计算划分好网格的面积（AT） （这里也是反着的纬度）
    gridTotalArea_AT = getGridTotalArea(binY, binX)

    # 计算部分信息用于拼接后计算全球参数
    # 建筑物总数量
    temp_Count = stats.binned_statistic_2d(lat, lon, height, statistic='count', bins=[binY, binX])[0]
    # 建筑物高度总和
    temp_SumHeight = stats.binned_statistic_2d(lat, lon, height, statistic='sum', bins=[binY, binX])[0]
    # 建筑物总体积和总面积在 areaBuildingGrid_AP 和 volumeBuildingGrid 中

    # 计算下面的UCP参数
    # mean and standard deviation of building height (mh, stdh) --- pixel中的均值和标准差
    para_MeanHeight_mh = stats.binned_statistic_2d(lat, lon, height, statistic='mean', bins=[binY, binX])[0]
    para_stdHeight_stdh = stats.binned_statistic_2d(lat, lon, height, statistic='std', bins=[binY, binX])[0]

    # average building height weighted by building plan area (haw) --- pixel中的面积加权
    areaBuildingGrid_AP = stats.binned_statistic_2d(lat, lon, area, statistic='sum', bins=[binY, binX])[
        0]  # 建筑物总面积（也要保存）
    volumeBuildingGrid = stats.binned_statistic_2d(lat, lon, volume, statistic='sum', bins=[binY, binX])[
        0]  # 建筑物总体积（也要保存）
    para_AverageHeightByPlanArea_haw = volumeBuildingGrid / areaBuildingGrid_AP

    # building plan area fraction (λp)  --- 占地面积比
    para_PlanAreaFraction_λp = areaBuildingGrid_AP / gridTotalArea_AT

    # building surface area to plan area ratio (λb)  --- 表面面积比
    wallAreaGrid = stats.binned_statistic_2d(lat, lon, wallArea, statistic='sum', bins=[binY, binX])[0]
    para_SurfaceAreaToPlanAreaRatio_λb = wallAreaGrid / gridTotalArea_AT

    # frontal area index (λf)  ---  峰向指数
    para_frontal0AreaGrid_λf0 = \
        stats.binned_statistic_2d(lat, lon, proj4Area[:, 0], statistic='sum', bins=[binY, binX])[0] / gridTotalArea_AT
    para_frontal90AreaGrid_λf90 = \
        stats.binned_statistic_2d(lat, lon, proj4Area[:, 1], statistic='sum', bins=[binY, binX])[0] / gridTotalArea_AT
    para_frontal45AreaGrid_λf45 = \
        stats.binned_statistic_2d(lat, lon, proj4Area[:, 2], statistic='sum', bins=[binY, binX])[0] / gridTotalArea_AT
    para_frontal135AreaGrid_λf135 = \
        stats.binned_statistic_2d(lat, lon, proj4Area[:, 3], statistic='sum', bins=[binY, binX])[0] / gridTotalArea_AT

    # Distribution of building heights  ---  高度分布
    para_distributionOfBuildingHeights_Dh = \
        stats.binned_statistic_dd([height, lat, lon], height, statistic='count', bins=[binZ, binY, binX])[0]

    print("计算 {} 完成，当前时间 {}".format(cityName, d.now().strftime('%m-%d %H:%M:%S')))
    # write Geo Tiff
    # binStatic的纬度增下来的，所以这里的点放左下角，纬度增量为负反着向上写（和rasterio的左上区别开）
    transform = from_origin(minLon, minLat, 1 / numberOfEachDegree, -1 / numberOfEachDegree)
    tifHeight, tifWidth = len(binY) - 1, len(binX) - 1

    corner = '_' + str(minLon) + '_' + str(maxLat) + '_'

    # write GeoTiff
    path = []
    if 'count' in threeDptions:
        # 01 count
        with rasterio.open(folderDict['count'] + '\\' + cityName + corner + 'count.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(temp_Count, 1)
        path.append(folderDict['count'] + '\\' + cityName + corner + 'count.tif')
    if 'sum' in threeDptions:
        # 02 sumHei
        with rasterio.open(folderDict['sum'] + '\\' + cityName + corner + 'sumHei.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(temp_SumHeight, 1)
        path.append(folderDict['sum'] + '\\' + cityName + corner + 'sumHei.tif')
    if 'area' in threeDptions:
        # 03 area
        with rasterio.open(folderDict['area'] + '\\' + cityName + corner + 'area.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(areaBuildingGrid_AP, 1)
        path.append(folderDict['area'] + '\\' + cityName + corner + 'area.tif')
    if 'volume' in threeDptions:
        # 04 volume
        with rasterio.open(folderDict['volume'] + '\\' + cityName + corner + 'volume.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(volumeBuildingGrid, 1)
        path.append(folderDict['volume'] + '\\' + cityName + corner + 'volume.tif')
    if 'mh' in threeDptions:
        # 05 mh
        with rasterio.open(folderDict['mh'] + '\\' + cityName + corner + 'mh.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_MeanHeight_mh, 1)
        path.append(folderDict['mh'] + '\\' + cityName + corner + 'mh.tif')
    if 'stdh' in threeDptions:
        # 06 stdh
        with rasterio.open(folderDict['stdh'] + '\\' + cityName + corner + 'stdh.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_stdHeight_stdh, 1)
        path.append(folderDict['stdh'] + '\\' + cityName + corner + 'stdh.tif')
    if 'haw' in threeDptions:
        # 07 haw
        with rasterio.open(folderDict['haw'] + '\\' + cityName + corner + 'haw.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_AverageHeightByPlanArea_haw, 1)
        path.append(folderDict['haw'] + '\\' + cityName + corner + 'haw.tif')
    if 'lb' in threeDptions:
        # 08 λb
        with rasterio.open(folderDict['lb'] + '\\' + cityName + corner + 'λb.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_SurfaceAreaToPlanAreaRatio_λb, 1)
        path.append(folderDict['lb'] + '\\' + cityName + corner + 'λb.tif')
    if 'lp' in threeDptions:
        # 09 λp
        with rasterio.open(folderDict['lp'] + '\\' + cityName + corner + 'λp.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_PlanAreaFraction_λp, 1)
        path.append(folderDict['lp'] + '\\' + cityName + corner + 'λp.tif')
    if 'lf0' in threeDptions:
        # 10 λf0
        with rasterio.open(folderDict['lf0'] + '\\' + cityName + corner + 'λf0.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_frontal0AreaGrid_λf0, 1)
        path.append(folderDict['lf0'] + '\\' + cityName + corner + 'λf0.tif')
    if 'lf135' in threeDptions:
        # 11 λf135
        with rasterio.open(folderDict['lf135'] + '\\' + cityName + corner + 'λf135.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_frontal135AreaGrid_λf135, 1)
        path.append(folderDict['lf135'] + '\\' + cityName + corner + 'λf135.tif')
    if 'lf45' in threeDptions:
        # 12 λf45
        with rasterio.open(folderDict['lf45'] + '\\' + cityName + corner + 'λf45.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_frontal45AreaGrid_λf45, 1)
        path.append(folderDict['lf45'] + '\\' + cityName + corner + 'λf45.tif')
    if 'lf90' in threeDptions:
        # 13 λf90
        with rasterio.open(folderDict['lf90'] + '\\' + cityName + corner + 'λf90.tif', 'w',
                           height=tifHeight, width=tifWidth, count=1,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_frontal90AreaGrid_λf90, 1)
        path.append(folderDict['lf90'] + '\\' + cityName + corner + 'λf90.tif')
    if 'dh' in threeDptions:
        # 14 dh
        with rasterio.open(folderDict['dh'] + '\\' + cityName + corner + 'dh.tif', 'w',
                           height=tifHeight, width=tifWidth, count=15,
                           dtype='float64', crs='EPSG:4326', transform=transform) as dst:
            dst.write(para_distributionOfBuildingHeights_Dh)
        path.append(folderDict['dh'] + '\\' + cityName + corner + 'dh.tif')
    # 判断文件夹是否存在
    if not os.path.exists('./temp'):
        # 创建文件夹
        os.makedirs('./temp')
    create_minimum_bounding_boxes(shpFileDir,fr'./temp/{cityName}.shp')
    for i in path:
        mask_raster_with_vector(fr'./temp/{cityName}.shp', i)
    print("{} 写入tif完成，当前时间 {}".format(cityName, d.now().strftime('%m-%d %H:%M:%S')))

    return


def createFolder(dataPath,paraSaveFolder,threeDptions):
    folderDict = {}
    folderDict['data'] = dataPath
    for para in threeDptions:
        folderDict[para] = os.path.join(paraSaveFolder, para)

    # 提前新建文件夹
    [os.makedirs(folder) for folder in folderDict.values() if not os.path.exists(folder)]
    return folderDict


def multiProcess_CalcuUCP(data,poolSize,progress):
    # shpLIST->[dataList,folderDict]
    print('开始计算UCP 共{}文件 构建进程池尺寸为{} 当前时间 {}'.format(len(data[0]), poolSize,
                                                                       d.now().strftime('%m-%d %H:%M:%S')))
    progress.setValue(30)
    # 进程池实现同步计算
    pool = multiprocessing.Pool(poolSize)  # 构建进程池
    _ = pool.map(calcuSingleData, [[i,data[1],data[2]] for i in data[0]])
    pool.close()
    pool.join()  # 保证全部运行完后运行主程序
    print("计算完成 当前时间 {}".format(d.now().strftime('%m-%d %H:%M:%S')))
    progress.setValue(90)
    return



def calMultiUCP(buildings,target,poolsize,progress,threeDptions):
    # 原始数据路径
    dataPath = buildings
    # 结果存放文件夹
    paraSaveFolder = target
    folderDict = createFolder(dataPath,paraSaveFolder,threeDptions)
    # 获取数据
    dataList = getInitShpList(folderDict['data'])
    # 多进程计算
    multiProcess_CalcuUCP([dataList,folderDict,threeDptions], poolsize, progress)

    print('done!')
    shutil.rmtree(r'./temp')
    return progress


