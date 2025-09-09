 # -*- coding: utf-8 -*-
# @Author  : llc
# @Time    : 2020/10/20 17:45

import os
import json

_here = os.path.dirname(__file__)


def load_config():
    """加载配置文件"""
    config_path = os.path.join(_here, 'config.json')
    if not os.path.exists(config_path):
        # 如果config.json不存在，尝试从example复制
        example_path = os.path.join(_here, 'config.json.example')
        if os.path.exists(example_path):
            import shutil
            shutil.copy(example_path, config_path)
            print(f"已从模板创建配置文件：{config_path}")
            print("请根据您的环境修改config.json中的QGIS路径")
        else:
            raise FileNotFoundError("未找到配置文件config.json和config.json.example")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_qgis_path():
    """获取QGIS安装路径"""
    try:
        config = load_config()
        return config['qgis']['prefix_path']
    except Exception as e:
        print(f"读取QGIS路径配置失败: {e}")
        # 使用默认路径作为后备
        return 'G:/qgis/apps/qgis-ltr'


def setup_env():
    """设置环境变量"""
    try:
        config = load_config()
        paths_config = config.get('paths', {})
        
        # 设置GDAL相关环境变量
        if os.path.exists(os.path.join(_here, 'share')):
            # gdal data
            gdal_data = os.path.join(_here, paths_config.get('gdal_data', 'share/gdal'))
            if os.path.exists(gdal_data):
                os.environ['GDAL_DATA'] = gdal_data
            
            # proj lib
            proj_lib = os.path.join(_here, paths_config.get('proj_lib', 'share/proj'))
            if os.path.exists(proj_lib):
                os.environ['PROJ_LIB'] = proj_lib
            
            # geotiff_csv
            geotiff_csv = os.path.join(_here, paths_config.get('geotiff_csv', 'share/epsg_csv'))
            if os.path.exists(geotiff_csv):
                os.environ['GEOTIFF_CSV'] = geotiff_csv
                
    except Exception as e:
        print(f"设置环境变量时出错: {e}")
        # 使用原有的默认设置作为后备
        if os.path.exists(os.path.join(_here, 'share')):
            os.environ['GDAL_DATA'] = os.path.join(_here, 'share', 'gdal')
            os.environ['PROJ_LIB'] = os.path.join(_here, 'share', 'proj')
            os.environ['GEOTIFF_CSV'] = os.path.join(_here, 'share', 'epsg_csv')
