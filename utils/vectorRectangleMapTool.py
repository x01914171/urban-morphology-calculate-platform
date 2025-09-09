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


class vectorRectangleMapTool(QgsMapToolEmitPoint):
    def __init__(self, canvas,calMor):
        super().__init__(canvas)
        self.canvas = canvas
        self.rubber_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)

        self.start_point = None
        self.end_point = None

        # 设置边框颜色为红色
        self.rubber_band.setColor(QColor(255, 0, 0))
        # 设置填充颜色为蓝色，透明度为 50%
        self.rubber_band.setFillColor(QColor(0, 0, 255, 127))
        # 设置边框宽度为 2 像素
        self.rubber_band.setWidth(2)

        #记录路径
        self.path = None
        self.buildings = None
        self.is_drawing = False  # 是否正在绘制

        self.calMor = calMor

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self.is_drawing:
                # 第一次点击左键，设置起点
                self.start_point = self.toMapCoordinates(event.pos())
                self.is_drawing = True
            else:
                # 第二次点击左键，设置对角点并完成绘制
                self.end_point = self.toMapCoordinates(event.pos())
                self.is_drawing = False
                self.complete_rectangle()
        elif event.button() == Qt.RightButton:
            # 右键点击，取消当前绘制
            self.cancel_drawing()

    def canvasMoveEvent(self, event):
        if self.is_drawing:
            # 实时更新矩形
            self.end_point = self.toMapCoordinates(event.pos())
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self.rubber_band.addPoint(QgsPointXY(self.start_point.x(), self.start_point.y()))
            self.rubber_band.addPoint(QgsPointXY(self.end_point.x(), self.start_point.y()))
            self.rubber_band.addPoint(QgsPointXY(self.end_point.x(), self.end_point.y()))
            self.rubber_band.addPoint(QgsPointXY(self.start_point.x(), self.end_point.y()))
            self.rubber_band.addPoint(QgsPointXY(self.start_point.x(), self.start_point.y()))

    def complete_rectangle(self):
        # 弹出提示窗，询问用户是否确认绘制
        reply = QMessageBox.question(
            None, "确认", "是否确认绘制矩形？", QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # 弹出文件对话框，选择保存路径
            output_building_path, _ = QFileDialog.getSaveFileName(
                None, "保存建筑物文件", "", "Shapefile (*.shp)"
            )
            output_rectangle_path, _ = QFileDialog.getSaveFileName(
                None, "保存矩形文件", "", "Shapefile (*.shp)"
            )

            if output_building_path and output_rectangle_path:
                # 显示进度条
                progress = QProgressDialog("正在保存文件...", "取消", 0, 100, None)
                progress.setWindowTitle("请稍候")
                progress.setModal(True)
                progress.show()

                # 保存文件
                self.create_rectangle_layer(output_building_path, output_rectangle_path, progress)
                # 关闭进度条
                progress.close()
                QMessageBox.information(None, "成功", "文件保存成功！")
                self.calMor.setEnabled(True)
                self.path = output_rectangle_path
                self.buildings = output_building_path
                self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            else:
                QMessageBox.warning(None, "警告", "未选择保存路径！")
                self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        else:
            QMessageBox.information(None, "取消", "绘制已取消。")
            self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)

        # 恢复鼠标指针
        self.canvas.unsetMapTool(self)

    def create_rectangle_layer(self, output_building_path, output_rectangle_path, progress):
        # 更新进度条
        progress.setValue(10)

        # 创建矩形图层
        rectangle_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "rectangle", "memory")
        rectangle_layer.dataProvider().addAttributes([QgsField("id", QVariant.Int)])
        rectangle_layer.updateFields()

        # 创建矩形要素
        rectangle_feature = QgsFeature()
        rectangle_feature.setGeometry(QgsGeometry.fromRect(QgsRectangle(self.start_point, self.end_point)))
        rectangle_feature.setFields(rectangle_layer.fields())
        rectangle_feature.setAttribute("id", 1)
        rectangle_layer.dataProvider().addFeature(rectangle_feature)

        # 更新进度条
        progress.setValue(30)

        # 将矩形图层保存为 SHP 文件
        QgsVectorFileWriter.writeAsVectorFormat(
            rectangle_layer, output_rectangle_path, "UTF-8", rectangle_layer.crs(), "ESRI Shapefile"
        )

        # 更新进度条
        progress.setValue(50)

        # 获取建筑物图层
        building_layer = QgsProject.instance().mapLayersByName("buildings.shp")[0]  # 假设建筑物图层名为 "buildings"

        # 选中矩形内的建筑物
        selected_features = []
        rectangle_geometry = rectangle_feature.geometry()
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

        # 加载矩形图层到 QGIS
        saved_rectangle_layer = QgsVectorLayer(output_rectangle_path, "范围", "ogr")
        QgsProject.instance().addMapLayer(saved_rectangle_layer)
        # 加载建筑物图层到 QGIS
        saved_building_layer = QgsVectorLayer(output_building_path, "建筑物", "ogr")
        QgsProject.instance().addMapLayer(saved_building_layer)

        # 更新进度条
        progress.setValue(100)

    def cancel_drawing(self):
        # 取消当前绘制
        self.is_drawing = False
        self.start_point = None
        self.end_point = None
        self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
        # 恢复鼠标指针
        self.canvas.unsetMapTool(self)


