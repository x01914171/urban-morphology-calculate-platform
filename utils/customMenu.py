# -*- coding: utf-8 -*-
# @Author  : llc
# @Time    : 2020/10/19 11:38
from PyQt5.QtWidgets import QMessageBox
from qgis.PyQt.QtWidgets import QMenu, QAction
from qgis._core import QgsProject
from qgis.core import QgsLayerTreeNode, QgsLayerTree, QgsMapLayerType
from qgis.gui import QgsLayerTreeViewMenuProvider, QgsLayerTreeView, QgsLayerTreeViewDefaultActions, QgsMapCanvas

from Widgets.attributeDialog import AttributeDialog
PROJECT = QgsProject.instance()

class CustomMenuProvider(QgsLayerTreeViewMenuProvider):
    def __init__(self, mainWindow,layerTreeView: QgsLayerTreeView, mapCanvas: QgsMapCanvas, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layerTreeView = layerTreeView
        self.mapCanvas = mapCanvas
        self.mainWindow = mainWindow

    def createContextMenu(self):
        menu = QMenu()
        actions: QgsLayerTreeViewDefaultActions = self.layerTreeView.defaultActions()
        if not self.layerTreeView.currentIndex().isValid():
            # 不在图层上右键
            self.actionAddGroup = actions.actionAddGroup(menu)
            menu.addAction(self.actionAddGroup)
            menu.addAction('Expand All', self.layerTreeView.expandAll)
            menu.addAction('Collapse All', self.layerTreeView.collapseAll)
            return menu

        node: QgsLayerTreeNode = self.layerTreeView.currentNode()

        if QgsLayerTree.isGroup(node):
            # 图组操作
            print('group')
            pass
        elif QgsLayerTree.isLayer(node):
            print('layer')
            self.actionZoomToLayer = actions.actionZoomToLayer(self.mapCanvas, menu)
            menu.addAction(self.actionZoomToLayer)

            # 图层操作
            layer = self.layerTreeView.currentLayer()
            if layer.type() == QgsMapLayerType.VectorLayer:
                # 矢量图层
                actionOpenAttributeDialog = QAction('open Attribute Table', menu)
                actionOpenAttributeDialog.triggered.connect(lambda: self.openAttributeDialog(layer))
                menu.addAction(actionOpenAttributeDialog)
            else:
                # 栅格图层
                pass

            if len(self.layerTreeView.selectedLayers()) > 1:
                # 添加组
                self.actionGroupSelected = actions.actionGroupSelected()
                menu.addAction(self.actionGroupSelected)

            actionDeleteSelectedLayers = QAction('Remove', menu)
            actionDeleteSelectedLayers.triggered.connect(self.deleteSelectedLayer)
            menu.addAction(actionDeleteSelectedLayers)

        else:
            print('node type is none')

        return menu

    def openAttributeDialog(self, layer):
        self.attributeDialog = AttributeDialog(self.mapCanvas, parent=self.mapCanvas.parent())
        self.attributeDialog.openAttributeDialog(layer)
        self.attributeDialog.show()

    def deleteSelectedLayer(self):
        deleteRes = QMessageBox.question(self.mainWindow, '信息', "确定要删除所选图层？",
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
        if deleteRes == QMessageBox.Yes:
            layers = self.layerTreeView.selectedLayers()
            for layer in layers:
                self.deleteLayer(layer)


    def deleteLayer(self, layer):
        PROJECT.removeMapLayer(layer)
        self.mapCanvas.refresh()
        return 0