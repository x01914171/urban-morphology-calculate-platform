# -*- coding: utf-8 -*-
# @Time    : 2025/2/16 16:46
# @Author  : WXB
# @File    : vectorRectangleMapTool.py
# @Software: PyCharm
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QProgressDialog
from qgis._core import QgsVectorFileWriter, QgsPoint, QgsRectangle, QgsPointXY
from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsWkbTypes, QgsFields, QgsField
from qgis.PyQt.QtCore import QVariant
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.PyQt.QtWidgets import QPushButton
from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsWkbTypes, QgsFields, QgsField, QgsPointXY
from qgis.PyQt.QtCore import QVariant
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.PyQt.QtWidgets import QPushButton, QMessageBox, QFileDialog, QProgressDialog
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import Qt


class vectorPolygonMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas,calMor):
        super().__init__(canvas)
        self.canvas = canvas
        self.rubber_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)

        # 设置边框颜色为红色
        self.rubber_band.setColor(QColor(255, 0, 0))

        # 设置填充颜色为蓝色，透明度为 50%
        self.rubber_band.setFillColor(QColor(0, 0, 255, 127))

        # 设置边框宽度为 2 像素
        self.rubber_band.setWidth(2)

        self.points = []  # 存储多边形的顶点
        self.is_drawing = False  # 是否正在绘制
        #记录路径
        self.path = None
        self.buildings = None

        self.calMor = calMor

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 左键点击，添加顶点
            point = self.toMapCoordinates(event.pos())
            self.points.append(point)
            self.is_drawing = True
            self.update_rubber_band()
        elif event.button() == Qt.RightButton:
            # 右键点击，结束绘制
            if len(self.points) >= 3:  # 至少需要 3 个点才能构成多边形
                self.complete_polygon()
            else:
                QMessageBox.warning(None, "警告", "至少需要 3 个点才能绘制多边形！")
                self.cancel_drawing()

    def canvasMoveEvent(self, event):
        if self.is_drawing:
            # 实时更新多边形的最后一个边
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            for point in self.points:
                self.rubber_band.addPoint(point)
            # 添加当前鼠标位置作为临时点
            self.rubber_band.addPoint(self.toMapCoordinates(event.pos()))

    def complete_polygon(self):
        # 弹出提示窗，询问用户是否确认绘制
        reply = QMessageBox.question(
            None, "确认", "是否确认绘制多边形？", QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            output_building_path, _ = QFileDialog.getSaveFileName(
                None, "保存建筑物文件", "", "Shapefile (*.shp)"
            )
            # 弹出文件对话框，选择保存路径
            output_polygon_path, _ = QFileDialog.getSaveFileName(
                None, "保存多边形文件", "", "Shapefile (*.shp)"
            )

            if output_polygon_path:
                # 显示进度条
                progress = QProgressDialog("正在保存文件...", "取消", 0, 100, None)
                progress.setWindowTitle("请稍候")
                progress.setModal(True)
                progress.show()

                # 保存文件并加载图层
                self.create_polygon_layer(output_building_path,output_polygon_path, progress)

                # 关闭进度条
                progress.close()
                QMessageBox.information(None, "成功", "文件保存成功并已加载到图层！")
                self.calMor.setEnabled(True)
                self.path = output_polygon_path
                self.buildings = output_building_path
                self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            else:
                QMessageBox.warning(None, "警告", "未选择保存路径！")
                self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        else:
            # 用户选择取消，删除绘制的多边形
            QMessageBox.information(None, "取消", "绘制已取消。")
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        # 恢复鼠标指针
        self.canvas.unsetMapTool(self)

    def cancel_drawing(self):
        # 取消当前绘制
        self.is_drawing = False
        self.points = []
        # 删除绘制的多边形
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        # 恢复鼠标指针
        # 恢复鼠标指针
        self.canvas.unsetMapTool(self)


    def update_rubber_band(self):
        # 更新橡皮筋，显示当前的多边形
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        for point in self.points:
            self.rubber_band.addPoint(point)

    def create_polygon_layer(self, output_building_path, output_polygon_path, progress):
        # 更新进度条
        progress.setValue(10)

        # 创建多边形图层
        polygon_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "polygon", "memory")
        polygon_layer.dataProvider().addAttributes([QgsField("id", QVariant.Int)])
        polygon_layer.updateFields()

        # 创建多边形要素
        polygon_feature = QgsFeature()
        polygon_geometry = QgsGeometry.fromPolygonXY([self.points])  # 创建多边形几何
        polygon_feature.setGeometry(polygon_geometry)
        polygon_feature.setFields(polygon_layer.fields())
        polygon_feature.setAttribute("id", 1)
        polygon_layer.dataProvider().addFeature(polygon_feature)

        # 更新进度条
        progress.setValue(30)

        # 将多边形图层保存为 SHP 文件
        QgsVectorFileWriter.writeAsVectorFormat(
            polygon_layer, output_polygon_path, "UTF-8", polygon_layer.crs(), "ESRI Shapefile"
        )

        # 获取建筑物图层
        building_layer = QgsProject.instance().mapLayersByName("buildings.shp")[0]  # 假设建筑物图层名为 "buildings"

        # 选中矩形内的建筑物
        selected_features = []
        rectangle_geometry = polygon_feature.geometry()
        total_features = building_layer.featureCount()
        for i, feature in enumerate(building_layer.getFeatures()):
            if feature.geometry().intersects(rectangle_geometry):
                selected_features.append(feature)
            # 更新进度条
            progress.setValue(50 + int((i / total_features) * 30))

        # 创建新的建筑物图层
        output_building_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "selected_buildings", "memory")
        output_building_layer.dataProvider().addAttributes(building_layer.fields())
        output_building_layer.updateFields()

        # 将选中的建筑物保存到新的图层
        output_building_layer.dataProvider().addFeatures(selected_features)
        QgsVectorFileWriter.writeAsVectorFormat(
            output_building_layer, output_building_path, "UTF-8", building_layer.crs(), "ESRI Shapefile"
        )

        # # 加载多边形图层到 QGIS
        saved_polygon_layer = QgsVectorLayer(output_polygon_path, "范围", "ogr")
        QgsProject.instance().addMapLayer(saved_polygon_layer)
        # 加载建筑物图层到 QGIS
        saved_building_layer = QgsVectorLayer(output_building_path, "建筑物", "ogr")
        QgsProject.instance().addMapLayer(saved_building_layer)
        # 更新进度条
        progress.setValue(100)


