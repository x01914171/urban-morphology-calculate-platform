# -*- coding: utf-8 -*-
# @Author  : llc
# @Time    : 2020/4/21 21:40
import os
import sys

from PyQt5.QtWidgets import QInputDialog, QProgressDialog

from computation.extractByMask import mask_raster_with_vector
from computation.landscape import calculate_landscape_indices_byraster, calculate_landscape_indices_byvector, \
    calculate_landscape_indices_bybuildings
from computation.morphology import calMultiUCP
from utils.vectorPolygonMapTool import vectorPolygonMapTool
from utils.vectorRectangleMapTool import vectorRectangleMapTool

sys.path.append("..")
from qgis.PyQt.QtWidgets import QMainWindow, QFileDialog, QHBoxLayout, QVBoxLayout, QMessageBox
from qgis.core import QgsVectorLayer, QgsProject, QgsLayerTreeModel, QgsRasterLayer
from qgis.gui import QgsMapCanvas, QgsMapToolZoom, QgsMapToolPan, QgsMapToolIdentifyFeature, QgsLayerTreeView, \
    QgsLayerTreeMapCanvasBridge

from ui.mainWindow import Ui_MainWindow
from utils.customMenu import CustomMenuProvider
from Widgets.custom_maptool import RectangleMapTool, PolygonMapTool, PointMapTool, LineMapTool
from computation.morphology_single import calUCP

PROJECT = QgsProject.instance()


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.first_flag = False
        self.setWindowTitle('城市形态计算')
        # 调整窗口大小
        # 2 初始化图层树
        vl = QVBoxLayout(self.layerContents)
        self.layerTreeView = QgsLayerTreeView(self)
        vl.addWidget(self.layerTreeView)
        # 3 初始化地图画布
        self.mapCanvas = QgsMapCanvas(self)
        hl = QHBoxLayout(self.frame)
        hl.setContentsMargins(0,0,0,0) #设置周围间距
        hl.addWidget(self.mapCanvas)

        # 矩形 包含地址信息
        self.vectorRectangle = None
        self.vectorPolygon = None

        # 绘制矩形
        self.selectRectangle.clicked.connect(self.actionVectorRectangleTriggered)
        # 矩形计算
        self.calMor.clicked.connect(self.actionCalMorTriggered)
        #绘制多边形
        self.selectPolygon.clicked.connect(self.actionSelectPolygonTriggered)
        #多边形计算
        self.calMor_polygon.clicked.connect(self.actionCalMor_polygonTriggered)

        #其他
        self.selectBuildingsDir.clicked.connect(self.actionSelectBuildingsDirTriggered)
        self.selectResultDir.clicked.connect(self.actionSelectResultDirTriggered)
        self.multiCal.clicked.connect(self.actionMultiCalTriggered)

        #选择
        self.allIndicator = [
            self.count, self.sumhei, self.area, self.volume, self.mh, self.stdh, self.haw,
            self.lb, self.lp, self.lf0, self.lf45, self.lf90, self.lf135, self.dh,
            self.pol, self.lpi, self.pd, self.ed, self.si, self.ai]
        self.selectAll.clicked.connect(self.actionSelectAllTriggered)
        self.selectSwitch.clicked.connect(self.actionSelectSwitchTriggered)

        # 建立桥梁
        self.model = QgsLayerTreeModel(PROJECT.layerTreeRoot(), self)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeRename)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeReorder)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility)
        self.model.setFlag(QgsLayerTreeModel.ShowLegendAsTree)
        self.model.setAutoCollapseLegendNodes(10)
        self.layerTreeView.setModel(self.model)
        self.layerTreeBridge = QgsLayerTreeMapCanvasBridge(PROJECT.layerTreeRoot(), self.mapCanvas, self)
        # 显示经纬度
        self.mapCanvas.xyCoordinates.connect(self.showLngLat)

        # 打开工程
        self.actionOpen.triggered.connect(self.actionOpenTriggered)
        # 退出程序
        self.actionQuit.triggered.connect(self.close)

        # 地图工具
        # TODO:放大、缩小没有图标
        self.actionPanTriggered()
        self.actionPan.triggered.connect(self.actionPanTriggered)
        self.actionZoomin.triggered.connect(self.actionZoomInTriggered)
        self.actionZoomout.triggered.connect(self.actionZoomOutTriggered)
        self.actionIdentity.triggered.connect(self.actionIdentifyTriggered)

        # 图层 ->>绑定事件
        self.actionShapefile.triggered.connect(self.actionShapefileTriggered)
        self.actionCsv.triggered.connect(self.actionCsvTriggered)
        # self.actionPostGIS.triggered.connect(self.actionPostGISTriggered)
        self.actionWFS.triggered.connect(self.actionWFSTriggered)

        self.actionGeotiff.triggered.connect(self.actionGeotiffTriggered)
        self.actionXYZ.triggered.connect(self.actionXYZTriggered)

        # 绘图工具
        self.actionPoint.triggered.connect(self.actionPointTriggered)
        self.actionLine.triggered.connect(self.actionLineTriggered)
        self.actionRectangle.triggered.connect(self.actionRectangleTriggered)
        self.actionPolygon.triggered.connect(self.actionPolygonTriggered)

        # 关于Qt
        self.actionAboutQt.triggered.connect(lambda: QMessageBox.aboutQt(self, '关于Qt'))
        self.actionAbout.triggered.connect(lambda: QMessageBox.about(self, '关于', 'PyQGIS二次开发'))

        # self.actionPan.triggered.connect(self.actionPanTriggered)
        # self.actionIdentify.triggered.connect(self.actionIdentifyTriggered)

        # 图层右键菜单
        self.customMenuProvider = CustomMenuProvider(self,self.layerTreeView, self.mapCanvas)
        self.layerTreeView.setMenuProvider(self.customMenuProvider)
        # self.layerTreeRegistryBridge = QgsLayerTreeRegistryBridge(PROJECT.layerTreeRoot(), PROJECT, self)

    def actionOpenTriggered(self):
        """打开工程"""
        data_file, ext = QFileDialog.getOpenFileName(self, '打开', '', '工程文件(*.qgs , *.qgz)')
        if data_file:
            PROJECT.read(data_file)

    def actionPanTriggered(self):
        self.mapTool = QgsMapToolPan(self.mapCanvas)
        self.mapCanvas.setMapTool(self.mapTool)

    def actionZoomInTriggered(self):
        self.mapTool = QgsMapToolZoom(self.mapCanvas, False)
        self.mapCanvas.setMapTool(self.mapTool)

    def actionZoomOutTriggered(self):
        self.mapTool = QgsMapToolZoom(self.mapCanvas, True)
        self.mapCanvas.setMapTool(self.mapTool)

    def actionIdentifyTriggered(self):
        # 设置识别工具
        self.identifyTool = QgsMapToolIdentifyFeature(self.mapCanvas)
        self.identifyTool.featureIdentified.connect(self.showFeatures)
        self.mapCanvas.setMapTool(self.identifyTool)

        # 设置需要识别的图层
        layers = self.mapCanvas.layers()
        if layers:
            # 识别画布中第一个图层
            self.identifyTool.setLayer(layers[0])

    def showFeatures(self, feature):
        print(type(feature))
        QMessageBox.information(self, '信息', ''.join(feature.attributes()))

    def actionAddGroupTriggered(self):
        PROJECT.layerTreeRoot().addGroup('group1')

    def actionShapefileTriggered(self):
        """打开shp"""
        data_file, ext = QFileDialog.getOpenFileName(self, '打开', '', '*.shp')
        if data_file:
            layer = QgsVectorLayer(data_file, os.path.splitext(os.path.basename(data_file))[0], "ogr")
            self.addLayer(layer)

    def actionCsvTriggered(self):
        """加载csv数据"""
        data_file, ext = QFileDialog.getOpenFileName(self, '打开', '', '*.csv')
        if data_file:
            # 去掉盘符，否则图层无效
            print(f'CSV 文件路径: {data_file}')
            data_file = os.path.normpath(data_file)
            data_file = os.path.splitdrive(data_file)[1]
            uri = f'file://{data_file}?type=csv&xField=x&yField=y&crs=EPSG:4326&encoding=UTF-8'
            layer = QgsVectorLayer(uri, 'point', 'delimitedtext')
            if not layer.isValid():
                print(f'图层无效，错误信息: {layer.error().message()}')
            self.addLayer(layer)


    def actionWFSTriggered(self):
        """加载天地图WFS图层"""
        uri = 'http://gisserver.tianditu.gov.cn/TDTService/wfs?' \
              'srsname=EPSG:4326&typename=TDTService:RESA&version=auto&request=GetFeature&service=WFS'
        layer = QgsVectorLayer(uri, "RESA", "WFS")
        self.addLayer(layer)

    def actionGeotiffTriggered(self):
        """加载geotiff"""
        data_file, ext = QFileDialog.getOpenFileName(self, '打开', '', '*.tif')
        if data_file:
            layer = QgsRasterLayer(data_file, os.path.basename(data_file))
            self.addLayer(layer)

    def actionXYZTriggered(self):
        uri = 'type=xyz&' \
              'url=https://www.google.cn/maps/vt?lyrs=s@804%26gl=cn%26x={x}%26y={y}%26z={z}&' \
              'zmax=19&' \
              'zmin=0&' \
              'crs=EPSG3857'
        layer = QgsRasterLayer(uri, 'google', 'wms')
        self.addLayer(layer)

    def addLayer(self, layer):
        if layer.isValid():
            if self.first_flag:
                self.mapCanvas.setDestinationCrs(layer.crs())
                self.mapCanvas.setExtent(layer.extent())
                self.first_flag = False
            PROJECT.addMapLayer(layer)
            layers = [layer] + [PROJECT.mapLayer(i) for i in PROJECT.mapLayers()]
            self.mapCanvas.setLayers(layers)
            self.mapCanvas.refresh()
        else:
            print('图层无效.')

    def actionPointTriggered(self):
        self.pointTool = PointMapTool(self.mapCanvas)
        self.mapCanvas.setMapTool(self.pointTool)

    def actionLineTriggered(self):
        self.lineTool = LineMapTool(self.mapCanvas)
        self.mapCanvas.setMapTool(self.lineTool)

    def actionRectangleTriggered(self):
        self.rectangleTool = RectangleMapTool(self.mapCanvas)
        self.mapCanvas.setMapTool(self.rectangleTool)

    def actionPolygonTriggered(self):
        self.polygonTool = PolygonMapTool(self.mapCanvas)
        self.mapCanvas.setMapTool(self.polygonTool)

    def showLngLat(self, point):
        x = point.x()
        y = point.y()
        self.statusbar.showMessage(f'X: {x},  Y: {y}')

    def addRaasterLayer(self,rasterFilePath):
        layer = QgsRasterLayer(rasterFilePath, os.path.basename(rasterFilePath))
        self.addLayer(layer)

    def addVectorLayer(self,vectorFilePath):
        vectorLayer = QgsVectorLayer(vectorFilePath,os.path.basename(vectorFilePath),"ogr")
        self.addLayer(vectorLayer)

    #选取加计算
    def actionVectorRectangleTriggered(self):
        self.vectorRectangle = vectorRectangleMapTool(self.mapCanvas,self.calMor)
        self.mapCanvas.setMapTool(self.vectorRectangle)
        self.claenLayer()

    def actionCalMorTriggered(self):
        # try:
        twoDptions, threeDptions = self.getSelectedOptions()
        targetFolder = QFileDialog.getExistingDirectory(None, '选择文件夹')
        if targetFolder:
            progress = QProgressDialog("正在计算指标...", "取消", 0, 100, None)
            progress.setWindowTitle("请稍候")
            progress.setModal(True)
            progress.show()
            path = []
            if len(threeDptions)!=0:
                path, progress = calUCP(self.vectorRectangle.buildings, targetFolder, progress,threeDptions)
                for i in path:
                    mask_raster_with_vector(self.vectorRectangle.path, i)
            progress.setValue(90)
            if len(twoDptions)!=0:
                if len(path) != 0:
                    calculate_landscape_indices_byraster(path[0], r'resource/GAIA/2020.tif', twoDptions,
                                                         targetFolder + f'/{os.path.basename(self.vectorRectangle.path).replace('.shp','')}_2D')
                else:
                    calculate_landscape_indices_byvector(self.vectorRectangle.path, r'resource/GAIA/2020.tif',
                                                         twoDptions, targetFolder + f'/{os.path.basename(self.vectorRectangle.path).replace('.shp','')}_2D')
            progress.setValue(100)
            progress.close()
            QMessageBox.information(None, "成功", "计算完成！")

        else:
            QMessageBox.warning(None, "警告", "未选择保存路径！")
        # except Exception as e:
        #     QMessageBox.warning(None, "警告", "建筑物选择有错，请重新选择！")
        #     print(e)

    # 矩形功能区
    def actionSelectPolygonTriggered(self):
        self.vectorPolygon = vectorPolygonMapTool(self.mapCanvas,self.calMor_polygon)
        self.mapCanvas.setMapTool(self.vectorPolygon)
        self.claenLayer()

    def actionCalMor_polygonTriggered(self):
        twoDptions, threeDptions = self.getSelectedOptions()
        # try:
        targetFolder  = QFileDialog.getExistingDirectory(None, '选择文件夹')
        if targetFolder:
            progress = QProgressDialog("正在计算指标...", "取消", 0, 100, None)
            progress.setWindowTitle("请稍候")
            progress.setModal(True)
            progress.show()
            path = []
            if len(threeDptions)!=0:
                path, progress = calUCP(self.vectorPolygon.buildings, targetFolder, progress, threeDptions)
                for i in path:
                    mask_raster_with_vector(self.vectorPolygon.path, i)
            progress.setValue(90)
            if len(twoDptions)!=0:
                if len(path) != 0:
                    calculate_landscape_indices_byraster(path[0], r'resource/GAIA/2020.tif', twoDptions,targetFolder + f'/{os.path.basename(self.vectorPolygon.path).replace('.shp','')}_2D',needBoundary=self.vectorPolygon.path)
                else:
                    calculate_landscape_indices_byvector(self.vectorPolygon.path,r'resource/GAIA/2020.tif',twoDptions,targetFolder + f'/{os.path.basename(self.vectorPolygon.path).replace('.shp','')}_2D',needBoundary=self.vectorPolygon.path)
            QMessageBox.information(None, "成功", "计算完成！")
            progress.setValue(100)
            progress.close()
        else:
            QMessageBox.warning(None, "警告", "未选择保存路径！")
        # except Exception as e:
        #     QMessageBox.warning(None, "警告", "建筑物选择有错，请重新选择！")

    #多边形功能区
    def actionSelectBuildingsDirTriggered(self):
        targetFolder = QFileDialog.getExistingDirectory(None, '选择文件夹')
        if targetFolder:
            self.buildingsDir.setText(targetFolder)
        else:
            QMessageBox.warning(None, "警告", "未选择保存路径！")

    def actionSelectResultDirTriggered(self):
        targetFolder = QFileDialog.getExistingDirectory(None, '选择文件夹')
        if targetFolder:
            self.resultDir.setText(targetFolder)
        else:
            QMessageBox.warning(None, "警告", "未选择保存路径！")

    def actionMultiCalTriggered(self):
        if not self.resultDir or not self.buildingsDir:
            QMessageBox.warning(None, "警告", "未选择路径！")
        if not self.threadNum:
            self.threadNum.setText('6')
        twoDptions, threeDptions = self.getSelectedOptions()
        progress = QProgressDialog("正在计算...", "取消", 0, 100, None)
        progress.setWindowTitle("请稍候")
        progress.setModal(True)
        progress.show()
        threadNum = eval(self.threadNum.text())
        if len(threeDptions)!=0:
            calMultiUCP(self.buildingsDir.text(), self.resultDir.text(), threadNum, progress,threeDptions)
        if len(twoDptions)!=0:
            files = [f for f in os.listdir(self.buildingsDir.text()) if f.endswith('.shp')]
            files = [rf'{self.buildingsDir.text()}/{i}'for i in files]
            for f in files:
                calculate_landscape_indices_bybuildings(f, r'resource/GAIA/2020.tif', twoDptions,
                                                     self.resultDir.text() + f'/{os.path.basename(f).replace('.shp','')}_2D')
        progress.setValue(100)
        progress.close()
        QMessageBox.information(None, "成功", "计算完成！")

    def getSelectedOptions(self):
        # 2d
        twoDptions = []
        # 3d
        threeDptions = []
        #
        # 检查每个复选框的状态
        if self.count.isChecked():threeDptions.append('count')
        if self.sumhei.isChecked():threeDptions.append('sum')
        if self.area.isChecked():threeDptions.append('area')
        if self.volume.isChecked():threeDptions.append('volume')
        if self.mh.isChecked():threeDptions.append('mh')
        if self.stdh.isChecked():threeDptions.append('stdh')
        if self.haw.isChecked():threeDptions.append('haw')
        if self.lb.isChecked():threeDptions.append('lb')
        if self.lp.isChecked():threeDptions.append('lp')
        if self.lf0.isChecked():threeDptions.append('lf0')
        if self.lf45.isChecked():threeDptions.append('lf45')
        if self.lf90.isChecked():threeDptions.append('lf90')
        if self.lf135.isChecked():threeDptions.append('lf135')
        if self.dh.isChecked():threeDptions.append('dh')
        #2D
        if self.pol.isChecked():twoDptions.append('proportion_of_landscape')
        if self.lpi.isChecked():twoDptions.append('largest_patch_index')
        if self.pd.isChecked():twoDptions.append('patch_density')
        if self.ed.isChecked():twoDptions.append('edge_density')
        if self.si.isChecked():twoDptions.append('landscape_shape_index')
        if self.ai.isChecked():twoDptions.append('ai')

        return twoDptions, threeDptions

    # 全选
    def actionSelectAllTriggered(self):
        for checkbox in self.allIndicator:
            checkbox.setChecked(True)

    def actionSelectSwitchTriggered(self):
        for checkbox in self.allIndicator:
            checkbox.setChecked(not checkbox.isChecked())

    def claenLayer(self):
        # 获取所有图层
        layers = PROJECT.mapLayers().values()
        # 遍历图层
        for layer in layers:
            if layer.name() == '建筑物' or layer.name() == '范围':
                # 移除图层
                PROJECT.removeMapLayer(layer.id())


