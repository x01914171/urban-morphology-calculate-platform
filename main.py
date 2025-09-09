# -*- coding: utf-8 -*-
# @Time    : 2025/2/5 22:21
# @Author  : WXB
# @File    : main.py
# @Software: PyCharm

# 程序主要入口，从该文件打开应用
from qgis.PyQt import QtCore
from qgis._analysis import QgsNativeAlgorithms
from qgis.core import QgsApplication
from PyQt5.QtCore import Qt

from config import setup_env, get_qgis_path, load_config
from Widgets.mainWindow import MainWindow
from splash import NewSplashScreen

if __name__ == '__main__':
    try:
        # 设置环境变量
        setup_env()
        
        # 加载配置
        config = load_config()
        
        # 适应高分辨率
        QgsApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        # 设置窗口风格
        QgsApplication.setStyle("Fusion")
        
        # 创建对QgsApplication的引用，第二个参数设置为False将禁用GUI
        qgs = QgsApplication([], True)
        t = QtCore.QTranslator()  # 先新建一个 QTranslator
        
        # 加载翻译文件
        translator_file = config.get('data', {}).get('translator_file', r'.\resource\qgis_zh-Hans.qm')
        t.load(translator_file)
        qgs.installTranslator(t)
        
        # 启动画面
        splash = NewSplashScreen()
        splash.show()

        # 从配置文件获取QGIS路径
        qgis_path = get_qgis_path()
        QgsApplication.setPrefixPath(qgis_path, True)
        QgsApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        
        app = QgsApplication([], True)
        app.initQgis()
        mainWindow = MainWindow()
        
        # 从配置文件加载默认数据
        default_raster = config.get('data', {}).get('default_raster', r'resource/GAIA/2020.tif')
        default_buildings = config.get('data', {}).get('default_buildings', r'resource/buildings_GBA/buildings.shp')
        
        mainWindow.addRaasterLayer(default_raster)
        mainWindow.addVectorLayer(default_buildings)

        # 设置图标
        splash.finish(mainWindow)
        mainWindow.show()
        
        app.exec_()
        app.exitQgis()
        
    except Exception as e:
        print(f"启动应用程序时出错: {e}")
        print("请检查config.json配置文件是否正确设置")
        import traceback
        traceback.print_exc()