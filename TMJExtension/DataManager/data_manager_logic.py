"""
Data Manager Logic - 负责数据加载、导出和场景管理的业务逻辑
"""
import os
import json
import logging
import vtk
import slicer
import numpy as np
from datetime import datetime


class DataManagerLogic:
    """
    Data Manager 的业务逻辑类
    负责体积数据的加载、导出和场景文件夹管理
    """

    def __init__(self, logCallback=None):
        """
        初始化 Data Manager Logic
        
        :param logCallback: 日志回调函数
        """
        self.logCallback = logCallback

    def log(self, message):
        """日志输出"""
        logging.info(message)
        if self.logCallback:
            self.logCallback(message)

    def loadVolume(self, filePath, nodeName=None):
        """
        加载体积文件,保留原始数据(不重采样,不改变spacing/direction)
        
        :param filePath: 文件路径
        :param nodeName: 节点名称
        :return: 加载的体积节点
        """
        try:
            if not os.path.exists(filePath):
                raise ValueError(f"文件不存在: {filePath}")

            self.log(f"加载文件: {filePath}")

            # 使用 Slicer 的加载函数,这会保留原始数据
            loadedNode = slicer.util.loadVolume(filePath, returnNode=True)[1]
            
            if not loadedNode:
                raise ValueError("加载体积失败")

            # 设置节点名称
            if nodeName:
                loadedNode.SetName(nodeName)
            
            self.log(f"体积加载成功: {loadedNode.GetName()}")
            self.log(f"  - 维度: {loadedNode.GetImageData().GetDimensions()}")
            self.log(f"  - 间距: {loadedNode.GetSpacing()}")
            self.log(f"  - 原点: {loadedNode.GetOrigin()}")
            
            return loadedNode

        except Exception as e:
            self.log(f"加载体积时出错: {str(e)}")
            raise

    def loadDataToScene(self, fixedVolume, movingVolume, mainFolderName, moduleFolderName, roiVolumes=None):
        """
        将配准数据加载到场景文件夹中(两层结构)
        
        :param fixedVolume: Fixed volume 节点
        :param movingVolume: Moving volume 节点
        :param mainFolderName: 配准流程总文件夹名称
        :param moduleFolderName: 模块子文件夹名称
        :param roiVolumes: ROI高分辨率MRI字典 {internalName: volumeNode}
        :return: 成功状态
        """
        try:
            # 获取 Subject Hierarchy 节点
            shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
            sceneItemID = shNode.GetSceneItemID()
            
            # 检查总文件夹是否已存在
            mainFolderItemID = shNode.GetItemChildWithName(sceneItemID, mainFolderName)
            
            if mainFolderItemID == 0:  # 不存在,创建新的总文件夹
                mainFolderItemID = shNode.CreateFolderItem(sceneItemID, mainFolderName)
                self.log(f"✓ 创建配准流程总文件夹: {mainFolderName}")
            else:
                self.log(f"✓ 使用已存在的总文件夹: {mainFolderName}")
            
            # 在总文件夹下创建模块子文件夹
            moduleFolderItemID = shNode.CreateFolderItem(mainFolderItemID, moduleFolderName)
            self.log(f"✓ 创建模块子文件夹: {moduleFolderName}")
            
            # 将 Fixed Volume 复制到模块子文件夹中
            if fixedVolume:
                fixedCopy = self._createVolumeInFolder(fixedVolume, "Fixed_Volume", shNode, moduleFolderItemID)
                self.log(f"✓ Fixed Volume 已添加到 {moduleFolderName}")
            
            # 将 Moving Volume 复制到模块子文件夹中
            if movingVolume:
                movingCopy = self._createVolumeInFolder(movingVolume, "Moving_Volume", shNode, moduleFolderItemID)
                self.log(f"✓ Moving Volume 已添加到 {moduleFolderName}")
            
            # 将 ROI Volumes 复制到模块子文件夹中
            if roiVolumes:
                for internalName, roiVolume in roiVolumes.items():
                    if roiVolume:
                        roiCopy = self._createVolumeInFolder(roiVolume, internalName, shNode, moduleFolderItemID)
                        self.log(f"✓ {internalName} 已添加到 {moduleFolderName}")
            
            return True
            
        except Exception as e:
            self.log(f"加载数据到场景时出错: {str(e)}")
            raise

    def _createVolumeInFolder(self, sourceVolume, newName, shNode, folderItemID):
        """
        创建体积的深度副本并将其放入指定的场景文件夹中
        
        :param sourceVolume: 源体积节点
        :param newName: 新体积的名称
        :param shNode: Subject Hierarchy 节点
        :param folderItemID: 文件夹项目 ID
        :return: 新创建的体积节点
        """
        # 创建新的体积节点
        volumeNode = slicer.mrmlScene.AddNewNodeByClass(sourceVolume.GetClassName(), newName)
        
        # 深拷贝图像数据（创建独立的图像数据副本）
        imageData = vtk.vtkImageData()
        imageData.DeepCopy(sourceVolume.GetImageData())
        volumeNode.SetAndObserveImageData(imageData)
        
        # 复制其他属性
        volumeNode.SetOrigin(sourceVolume.GetOrigin())
        volumeNode.SetSpacing(sourceVolume.GetSpacing())
        
        # 复制方向矩阵
        directionMatrix = vtk.vtkMatrix4x4()
        sourceVolume.GetIJKToRASDirectionMatrix(directionMatrix)
        volumeNode.SetIJKToRASDirectionMatrix(directionMatrix)
        
        # 设置名称
        volumeNode.SetName(newName)
        
        # 将新节点移动到文件夹中
        volumeItemID = shNode.GetItemByDataNode(volumeNode)
        shNode.SetItemParent(volumeItemID, folderItemID)
        
        return volumeNode

    def exportData(self, fixedVolume, movingVolume, outputDir, folderName, sceneFolderName, fileFormat="nrrd"):
        """
        导出体积数据和元数据,并在场景中创建文件夹节点来组织管理
        
        :param fixedVolume: Fixed volume 节点
        :param movingVolume: Moving volume 节点
        :param outputDir: 输出目录
        :param folderName: 输出文件夹名称
        :param sceneFolderName: 场景中的文件夹名称
        :param fileFormat: 文件格式 ('nrrd' 或 'nii.gz')
        :return: (成功状态, 文件夹节点)
        """
        try:
            # 1. 在场景中创建文件夹节点
            self.log("创建场景文件夹节点...")
            folderNode = slicer.vtkMRMLFolderDisplayNode()
            folderNode = slicer.mrmlScene.AddNode(slicer.vtkMRMLSubjectHierarchyNode())
            shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
            
            # 创建文件夹在场景根目录下
            sceneItemID = shNode.GetSceneItemID()
            folderItemID = shNode.CreateFolderItem(sceneItemID, sceneFolderName)
            self.log(f"✓ 场景文件夹已创建: {sceneFolderName}")
            
            # 2. 创建磁盘输出文件夹
            outputFolder = os.path.join(outputDir, folderName)
            if not os.path.exists(outputFolder):
                os.makedirs(outputFolder)
                self.log(f"创建输出文件夹: {outputFolder}")

            metadata = {
                "export_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "file_format": fileFormat,
                "resampled": False,
                "scene_folder": sceneFolderName,
                "volumes": {}
            }

            # 3. 处理 Fixed Volume
            if fixedVolume:
                self.log("导出 Fixed Volume...")
                fixedPath = os.path.join(outputFolder, f"fixed_volume.{fileFormat}")
                
                # 创建该体积的副本并放入场景文件夹
                fixedCopy = self._createVolumeInFolder(fixedVolume, "fixed_volume", shNode, folderItemID)
                
                # 导出到磁盘
                self._exportVolume(fixedCopy, fixedPath, fileFormat)
                metadata["volumes"]["fixed"] = self._extractVolumeMetadata(fixedCopy)
                self.log(f"✓ Fixed Volume 已保存: {fixedPath}")
                self.log(f"✓ Fixed Volume 已添加到场景文件夹")

            # 4. 处理 Moving Volume
            if movingVolume:
                self.log("导出 Moving Volume...")
                movingPath = os.path.join(outputFolder, f"moving_volume.{fileFormat}")
                
                # 创建该体积的副本并放入场景文件夹
                movingCopy = self._createVolumeInFolder(movingVolume, "moving_volume", shNode, folderItemID)
                
                # 导出到磁盘
                self._exportVolume(movingCopy, movingPath, fileFormat)
                metadata["volumes"]["moving"] = self._extractVolumeMetadata(movingCopy)
                self.log(f"✓ Moving Volume 已保存: {movingPath}")
                self.log(f"✓ Moving Volume 已添加到场景文件夹")

            # 5. 保存 metadata.json
            metadataPath = os.path.join(outputFolder, "metadata.json")
            with open(metadataPath, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            self.log(f"✓ 元数据已保存: {metadataPath}")

            return True, shNode

        except Exception as e:
            self.log(f"导出数据时出错: {str(e)}")
            raise

    def _exportVolume(self, volumeNode, outputPath, fileFormat):
        """
        导出单个体积,保留原始数据
        
        :param volumeNode: 体积节点
        :param outputPath: 输出路径
        :param fileFormat: 文件格式
        """
        try:
            # 使用 Slicer 的保存功能,保留原始数据
            properties = {}
            if fileFormat == "nii.gz":
                properties["useCompression"] = 1
            
            success = slicer.util.saveNode(volumeNode, outputPath, properties)
            
            if not success:
                raise ValueError(f"保存体积失败: {outputPath}")

        except Exception as e:
            raise ValueError(f"导出体积时出错: {str(e)}")

    def _extractVolumeMetadata(self, volumeNode):
        """
        提取体积的元数据
        
        :param volumeNode: 体积节点
        :return: 元数据字典
        """
        try:
            imageData = volumeNode.GetImageData()
            
            # 获取基本信息
            dimensions = imageData.GetDimensions()
            spacing = volumeNode.GetSpacing()
            origin = volumeNode.GetOrigin()
            
            # 获取方向矩阵
            directionMatrix = vtk.vtkMatrix4x4()
            volumeNode.GetIJKToRASDirectionMatrix(directionMatrix)
            direction = []
            for i in range(3):
                row = []
                for j in range(3):
                    row.append(directionMatrix.GetElement(i, j))
                direction.append(row)

            # 获取数组数据用于统计
            import vtk.util.numpy_support as vtk_np
            imageArray = vtk_np.vtk_to_numpy(imageData.GetPointData().GetScalars())
            
            # 计算统计信息
            stats = {
                "min": float(np.min(imageArray)),
                "max": float(np.max(imageArray)),
                "mean": float(np.mean(imageArray)),
                "std": float(np.std(imageArray)),
                "median": float(np.median(imageArray))
            }

            # 检测数据类型 (CT通常是 HU 值,范围约 -1000 到 3000)
            dataType = "MR"
            if stats["min"] < -500 and stats["max"] > 1000:
                dataType = "CT"
                self.log(f"  检测到 CT 数据 (HU 值范围: {stats['min']:.1f} 到 {stats['max']:.1f})")
            else:
                self.log(f"  检测到 MR 数据 (强度范围: {stats['min']:.1f} 到 {stats['max']:.1f})")

            metadata = {
                "name": volumeNode.GetName(),
                "data_type": dataType,
                "dimensions": list(dimensions),
                "spacing": list(spacing),
                "origin": list(origin),
                "direction": direction,
                "scalar_type": imageData.GetScalarTypeAsString(),
                "number_of_components": imageData.GetNumberOfScalarComponents(),
                "intensity_statistics": stats,
                "resampled": False,
                "notes": f"Original {'HU' if dataType == 'CT' else 'intensity'} values preserved"
            }

            return metadata

        except Exception as e:
            self.log(f"提取元数据时出错: {str(e)}")
            raise
