# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 QGIS 和 PyQt5 的 3D 建筑形态分析应用程序，用于计算城市形态学参数（Urban Morphology Parameters）。该项目主要分析建筑物的空间分布模式和景观指数。

## 核心架构

### 主要模块结构
- **main.py**: 应用程序入口点，初始化 QGIS 环境和主窗口
- **Widgets/**: 用户界面组件，包含主窗口和自定义地图工具
- **computation/**: 核心计算模块
  - `morphology.py`: 城市形态参数计算（UCP - Urban Coverage Parameters）
  - `landscape.py`: 景观生态学指数计算
  - `AI_Calculation.py`: 聚集指数（Aggregation Index）计算
  - `extractByMask.py`: 栅格掩膜提取功能
- **utils/**: 工具类，包含地图工具和界面辅助功能
- **ui/**: PyQt5 自动生成的UI代码
- **resource/**: 项目资源文件，包含测试数据和配置文件

### 技术栈
- **GUI框架**: PyQt5 + QGIS Python API
- **空间数据处理**: GDAL, Rasterio, Fiona, GeoPandas
- **科学计算**: NumPy, SciPy, pylandstats
- **地理投影**: PyProj

## 运行环境配置

### 启动应用程序
```bash
python main.py
```

### QGIS 环境依赖
- 项目硬编码了 QGIS 安装路径: `G:\qgis\apps\qgis-ltr`
- 需要修改 `main.py:33` 中的 QGIS 路径以适应不同环境
- 环境变量通过 `config.py` 中的 `setup_env()` 函数设置

### 核心计算参数
- 默认空间分辨率: `numberOfEachDegree = 120` (即 0.5' 精度)
- 建筑物最小高度阈值: `building_min_height = 1`
- 建筑物最小面积阈值: `building_min_area = 5`
- 高度字段名称: `heightField = 'Height'`

## 核心功能模块

### 城市形态参数计算 (morphology.py)
- **功能**: 计算多种城市覆盖参数（λb, λp, λf, HAW, DH, MH, STDH等）
- **输入**: 建筑物矢量数据（Shapefile）
- **输出**: 各参数的栅格结果（GeoTIFF）
- **主要函数**: 
  - `calMultiUCP()`: 批量计算多个区域的UCP参数
  - `calUCP()`: 计算单个区域的UCP参数

### 景观指数计算 (landscape.py)
- **功能**: 计算景观生态学指数（patch density, edge density, landscape shape index等）
- **支持三种计算模式**:
  - `calculate_landscape_indices_byraster()`: 基于栅格数据
  - `calculate_landscape_indices_byvector()`: 基于矢量边界
  - `calculate_landscape_indices_bybuildings()`: 基于建筑物数据
- **依赖**: pylandstats 库

### 自定义聚集指数 (AI_Calculation.py)
- **功能**: 扩展 pylandstats.Landscape 类，添加自定义聚集指数计算
- **关键方法**: `get_share_edge()`, `eii` 属性, `max_eii` 属性

## 数据文件组织

### 输入数据位置
- 建筑物矢量: `resource/buildings_GBA/buildings.shp`
- 底图栅格: `resource/GAIA/2020.tif`
- 测试数据: `test_buildings/` 目录

### 输出数据结构
- 结果按参数类型分类存储在 `res/` 和 `resource/result/` 目录
- 每种参数有独立的子目录 (如 `area/`, `count/`, `dh/`, `haw/` 等)
- 文件命名模式: `{建筑物名称}_{网格坐标}_{参数名}.tif`

## 开发注意事项

### 坐标系统处理
- 项目使用 UTM 投影进行精确计算
- `create_utm_transformers()` 预建了60个UTM分带的坐标转换器
- 默认使用 WGS84 椭球体进行距离计算

### 多进程计算
- morphology.py 模块支持多进程并行计算
- 使用 `multiprocessing` 库和 `tqdm` 进度条

### UI自动生成代码
- `ui/mainWindow.py` 是从 `.ui` 文件自动生成的，不要直接编辑
- 修改界面需要编辑 `ui/mainWindow.ui` 文件，然后重新生成Python代码

### 资源文件管理
- 图标和样式文件通过 `myRC.qrc` 资源文件管理
- `myRC_rc.py` 是自动生成的资源模块