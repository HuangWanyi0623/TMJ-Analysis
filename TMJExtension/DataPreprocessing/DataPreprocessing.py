"""
Data Preprocessing - 独立模块入口
用于CBCT和MRI数据的预处理
"""
import os
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *


class DataPreprocessing(ScriptedLoadableModule):
    """独立模块入口类"""

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Data Preprocessing"
        self.parent.categories = ["TMJ Analysis"]
        self.parent.dependencies = []
        self.parent.contributors = ["Feng"]
        self.parent.helpText = """
Data Preprocessing 模块用于辅助CBCT和MRI数据的预处理，
为TransMorph仿射配准准备数据。
"""
        self.parent.acknowledgementText = """
This module was developed for TMJ research.
"""
