"""
ROI Mask Set Logic - 业务逻辑处理
基于高分辨率ROI浮动图像的物理范围自动生成固定图像的ROI掩膜
"""
import vtk
import slicer
import numpy as np
import qt


class ROIMaskSetLogic:
    """
    ROI Mask Set 的业务逻辑类
    负责根据浮动图像的物理范围生成固定图像的ROI掩膜
    """

    def __init__(self, logCallback=None):
        """
        初始化 ROI Mask Set Logic
        
        :param logCallback: 日志回调函数
        """
        self.logCallback = logCallback if logCallback else print
        
        # 异步处理相关
        self.timer = None
        self.asyncData = None

    def generateROIMask(self, fixedVolume, roiMovingVolume, transformNode=None, expansionMm=5.0):
        """
        根据ROI MRI生成LabelMap Volume掩膜
        步骤1：基于ROI MRI创建LabelMap，所有值为1，尺寸=ROI MRI + 扩张部分
        
        :param fixedVolume: 固定图像 (CBCT)
        :param roiMovingVolume: 高分辨率ROI浮动图像 (局部MRI)
        :param transformNode: 粗配准变换节点
        :param expansionMm: 向外扩张量(毫米)，默认5mm
        :return: 生成的LabelMap Volume节点
        """
        try:
            if not roiMovingVolume:
                raise ValueError("ROI Moving Volume 不能为空")

            self.logCallback(f"步骤1: 根据ROI MRI生成LabelMap Volume")
            self.logCallback(f"  ROI MRI: {roiMovingVolume.GetName()}")
            self.logCallback(f"  扩张量: {expansionMm} mm")

            # 获取ROI MRI的几何信息
            roiImageData = roiMovingVolume.GetImageData()
            roiDims = roiImageData.GetDimensions()
            roiSpacing = roiMovingVolume.GetSpacing()
            
            self.logCallback(f"  原始尺寸: {roiDims[0]} x {roiDims[1]} x {roiDims[2]}")
            self.logCallback(f"  体素间距: {roiSpacing[0]:.2f} x {roiSpacing[1]:.2f} x {roiSpacing[2]:.2f} mm")
            
            # 计算扩张的体素数（每个方向）
            expandVoxels = [
                int(np.ceil(expansionMm / roiSpacing[0])),
                int(np.ceil(expansionMm / roiSpacing[1])),
                int(np.ceil(expansionMm / roiSpacing[2]))
            ]
            
            self.logCallback(f"  扩张体素数: {expandVoxels[0]}, {expandVoxels[1]}, {expandVoxels[2]}")
            
            # 新的尺寸 = 原始尺寸 + 2*扩张体素数（每个方向两侧都扩张）
            newDims = [
                roiDims[0] + 2 * expandVoxels[0],
                roiDims[1] + 2 * expandVoxels[1],
                roiDims[2] + 2 * expandVoxels[2]
            ]
            
            self.logCallback(f"  新尺寸: {newDims[0]} x {newDims[1]} x {newDims[2]}")
            
            # 创建新的ImageData，全部填充为1
            newImageData = vtk.vtkImageData()
            newImageData.SetDimensions(newDims)
            newImageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
            
            # 使用numpy填充为1
            import vtk.util.numpy_support as vtk_np
            newArray = vtk_np.vtk_to_numpy(newImageData.GetPointData().GetScalars())
            newArray[:] = 1
            newImageData.GetPointData().GetScalars().Modified()
            
            # 创建LabelMap Volume节点
            labelMapVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "ROI_Mask")
            labelMapVolume.SetAndObserveImageData(newImageData)
            labelMapVolume.SetSpacing(roiSpacing)
            
            # 获取ROI MRI的IJK到RAS变换矩阵
            ijkToRasMatrix = vtk.vtkMatrix4x4()
            roiMovingVolume.GetIJKToRASMatrix(ijkToRasMatrix)
            
            # 在IJK空间中，新的origin在(-expandVoxels[0], -expandVoxels[1], -expandVoxels[2])
            # 将这个IJK坐标转换到RAS空间
            ijkOrigin = [-expandVoxels[0], -expandVoxels[1], -expandVoxels[2], 1.0]
            rasOrigin = ijkToRasMatrix.MultiplyPoint(ijkOrigin)
            
            newOrigin = [rasOrigin[0], rasOrigin[1], rasOrigin[2]]
            labelMapVolume.SetOrigin(newOrigin)
            
            roiOrigin = roiMovingVolume.GetOrigin()
            self.logCallback(f"  ROI MRI Origin: ({roiOrigin[0]:.2f}, {roiOrigin[1]:.2f}, {roiOrigin[2]:.2f})")
            self.logCallback(f"  LabelMap Origin: ({newOrigin[0]:.2f}, {newOrigin[1]:.2f}, {newOrigin[2]:.2f})")
            
            # 复制方向矩阵
            directionMatrix = vtk.vtkMatrix4x4()
            roiMovingVolume.GetIJKToRASDirectionMatrix(directionMatrix)
            labelMapVolume.SetIJKToRASDirectionMatrix(directionMatrix)
            
            # 创建显示节点
            labelMapVolume.CreateDefaultDisplayNodes()
            displayNode = labelMapVolume.GetDisplayNode()
            if displayNode:
                displayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeLabels")
                displayNode.SetOpacity(0.5)
            
            self.logCallback(f"✓ LabelMap Volume生成成功")
            
            # 步骤2: 应用粗配准变换（如果提供）
            if transformNode:
                self.logCallback(f"步骤2: 应用粗配准变换")
                self.logCallback(f"  变换节点: {transformNode.GetName()}")
                
                # 将LabelMap设置为可变换的（设置其父变换）
                labelMapVolume.SetAndObserveTransformNodeID(transformNode.GetID())
                self.logCallback(f"  ✓ 变换已应用到LabelMap")
                
                # 同时将变换应用到ROI MRI
                roiMovingVolume.SetAndObserveTransformNodeID(transformNode.GetID())
                self.logCallback(f"  ✓ 变换已应用到ROI MRI")
                
                self.logCallback(f"✓ 粗配准变换应用完成")
                self.logCallback(f"  注意: LabelMap和ROI MRI现在处于变换状态，未重采样")
            
            # 统计信息
            totalVoxels = newDims[0] * newDims[1] * newDims[2]
            self.logCallback(f"  总体素数: {totalVoxels}")
            self.logCallback(f"  所有体素值: 1")

            # 步骤3: 生成针对CBCT的ROI LabelMap
            if fixedVolume:
                self.logCallback(f"步骤3: 生成针对CBCT的ROI LabelMap")
                
                # 3.1 准备坐标变换
                self.logCallback(f"  正在准备坐标变换...")
                
                # CBCT的IJK到RAS变换
                cbctIjkToRas = vtk.vtkMatrix4x4()
                fixedVolume.GetIJKToRASMatrix(cbctIjkToRas)
                
                # ROI LabelMap的RAS到IJK变换
                roiRasToIjk = vtk.vtkMatrix4x4()
                labelMapVolume.GetRASToIJKMatrix(roiRasToIjk)
                
                # 如果有变换，需要先应用变换
                if transformNode:
                    # 获取变换矩阵
                    transformMatrix = vtk.vtkMatrix4x4()
                    transformNode.GetMatrixTransformToParent(transformMatrix)
                    
                    # 组合变换: CBCT IJK -> RAS -> Transform -> ROI RAS -> ROI IJK
                    rasToIjkWithTransform = vtk.vtkMatrix4x4()
                    
                    # 先应用变换的逆矩阵
                    inverseTransform = vtk.vtkMatrix4x4()
                    vtk.vtkMatrix4x4.Invert(transformMatrix, inverseTransform)
                    
                    vtk.vtkMatrix4x4.Multiply4x4(roiRasToIjk, inverseTransform, rasToIjkWithTransform)
                    roiRasToIjk.DeepCopy(rasToIjkWithTransform)
                
                # 3.2 创建与CBCT几何完全一致的LabelMap
                self.logCallback(f"  正在创建CBCT ROI LabelMap...")
                
                cbctImageData = fixedVolume.GetImageData()
                cbctDims = cbctImageData.GetDimensions()
                roiDims = labelMapVolume.GetImageData().GetDimensions()
                
                # 创建新的ImageData，初始化为0
                cbctLabelMapData = vtk.vtkImageData()
                cbctLabelMapData.SetDimensions(cbctDims)
                cbctLabelMapData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
                
                import vtk.util.numpy_support as vtk_np
                cbctLabelMapArray = vtk_np.vtk_to_numpy(cbctLabelMapData.GetPointData().GetScalars())
                cbctLabelMapArray[:] = 0  # 初始化为0
                
                # 3.3 遍历CBCT体素，检查是否在ROI LabelMap内
                self.logCallback(f"  正在填充ROI区域...")
                roiVoxelCount = 0
                
                for k in range(cbctDims[2]):
                    for j in range(cbctDims[1]):
                        for i in range(cbctDims[0]):
                            # 将CBCT的IJK坐标转换为RAS物理坐标
                            cbctIjkPoint = [i, j, k, 1.0]
                            rasPoint = cbctIjkToRas.MultiplyPoint(cbctIjkPoint)
                            
                            # 将RAS坐标转换到ROI LabelMap的IJK坐标
                            roiIjkPoint = roiRasToIjk.MultiplyPoint(rasPoint)
                            
                            # 检查是否在ROI LabelMap的范围内
                            if (0 <= roiIjkPoint[0] < roiDims[0] and
                                0 <= roiIjkPoint[1] < roiDims[1] and
                                0 <= roiIjkPoint[2] < roiDims[2]):
                                # 在ROI LabelMap范围内，标记为1
                                idx = i + j * cbctDims[0] + k * cbctDims[0] * cbctDims[1]
                                cbctLabelMapArray[idx] = 1
                                roiVoxelCount += 1
                
                cbctLabelMapData.GetPointData().GetScalars().Modified()
                
                # 3.4 创建CBCT ROI LabelMap节点
                cbctROILabelMap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "Fixed_ROI_Mask")
                cbctROILabelMap.SetAndObserveImageData(cbctLabelMapData)
                cbctROILabelMap.CopyOrientation(fixedVolume)
                cbctROILabelMap.CreateDefaultDisplayNodes()
                
                # 3.5 设置显示颜色: 0=浅蓝色, 1=浅紫色，透明度1
                displayNode = cbctROILabelMap.GetDisplayNode()
                if displayNode:
                    # 创建自定义颜色表
                    colorTable = slicer.mrmlScene.CreateNodeByClass("vtkMRMLColorTableNode")
                    colorTable.SetTypeToUser()
                    colorTable.SetNumberOfColors(2)
                    colorTable.SetColor(0, "Background", 0.6, 0.8, 1.0, 1.0)  # 浅蓝色，完全不透明
                    colorTable.SetColor(1, "ROI", 0.8, 0.6, 1.0, 1.0)         # 浅紫色，完全不透明
                    colorTable.SetName("ROI_Mask_Colors")
                    slicer.mrmlScene.AddNode(colorTable)
                    
                    displayNode.SetAndObserveColorNodeID(colorTable.GetID())
                
                # 3.6 删除临时的ROI_Mask
                self.logCallback(f"  清理临时节点...")
                slicer.mrmlScene.RemoveNode(labelMapVolume)
                self.logCallback(f"  ✓ ROI_Mask已删除")
                
                # 统计
                totalCBCTVoxels = cbctDims[0] * cbctDims[1] * cbctDims[2]
                roiPercentage = (roiVoxelCount / totalCBCTVoxels) * 100
                
                self.logCallback(f"✓ CBCT ROI LabelMap生成成功")
                self.logCallback(f"  CBCT尺寸: {cbctDims[0]} x {cbctDims[1]} x {cbctDims[2]}")
                self.logCallback(f"  ROI体素数: {roiVoxelCount}/{totalCBCTVoxels} ({roiPercentage:.2f}%)")
                
                return cbctROILabelMap
            else:
                self.logCallback(f"  未提供Fixed Volume，跳过CBCT ROI LabelMap生成")
                return labelMapVolume

        except Exception as e:
            self.logCallback(f"✗ 生成LabelMap Volume失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return None

    def saveROIMaskToScene(self, fixedVolume, roiMovingVolume, maskVolume, 
                           mainFolderName, moduleFolderName):
        """
        将ROI掩膜结果保存到场景文件夹
        
        :param fixedVolume: Fixed Volume节点
        :param roiMovingVolume: ROI Moving Volume节点
        :param maskVolume: 生成的掩膜节点
        :param mainFolderName: 总文件夹名称
        :param moduleFolderName: ROI Mask Set模块子文件夹名称
        :return: 保存是否成功
        """
        try:
            self.logCallback(f"开始保存ROI掩膜到场景...")
            
            # 1. 获取Subject Hierarchy节点
            shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
            sceneItemID = shNode.GetSceneItemID()
            
            # 2. 查找或创建主文件夹
            mainFolderItemID = shNode.GetItemChildWithName(sceneItemID, mainFolderName)
            if not mainFolderItemID:
                mainFolderItemID = shNode.CreateFolderItem(sceneItemID, mainFolderName)
                self.logCallback(f"✓ 创建主文件夹: {mainFolderName}")
            else:
                self.logCallback(f"  使用已存在的主文件夹: {mainFolderName}")
            
            # 3. 查找或创建模块子文件夹
            moduleFolderItemID = shNode.GetItemChildWithName(mainFolderItemID, moduleFolderName)
            if moduleFolderItemID:
                # 删除旧文件夹内容
                self.logCallback(f"  删除旧的 {moduleFolderName} 文件夹内容...")
                shNode.RemoveItem(moduleFolderItemID)
            
            moduleFolderItemID = shNode.CreateFolderItem(mainFolderItemID, moduleFolderName)
            self.logCallback(f"✓ 创建模块子文件夹: {moduleFolderName}")
            
            # 4. 将掩膜节点添加到场景文件夹（创建深拷贝,保持原名称）
            self.logCallback(f"  正在添加掩膜到场景文件夹...")
            maskName = maskVolume.GetName()  # 使用掩膜的实际名称
            maskCopy = self._createVolumeInFolder(maskVolume, maskName, shNode, moduleFolderItemID)
            self.logCallback(f"✓ 掩膜已添加到场景: {maskCopy.GetName()}")
            
            self.logCallback(f"✓ ROI掩膜已成功保存到场景文件夹")
            self.logCallback(f"  路径: {mainFolderName}/{moduleFolderName}/{maskName}")
            
            return True

        except Exception as e:
            self.logCallback(f"✗ 保存ROI掩膜失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return False
    
    def _createVolumeInFolder(self, sourceVolume, newName, shNode, folderItemID):
        """
        在指定的场景文件夹中创建volume的深拷贝
        
        :param sourceVolume: 源volume节点
        :param newName: 新节点名称
        :param shNode: SubjectHierarchy节点
        :param folderItemID: 目标文件夹ID
        :return: 新创建的volume节点
        """
        # 创建新的volume节点
        if sourceVolume.IsA("vtkMRMLLabelMapVolumeNode"):
            newVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", newName)
        else:
            newVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", newName)
        
        # 深拷贝图像数据
        newImageData = vtk.vtkImageData()
        newImageData.DeepCopy(sourceVolume.GetImageData())
        newVolume.SetAndObserveImageData(newImageData)
        
        # 复制几何信息
        newVolume.CopyOrientation(sourceVolume)
        
        # 复制显示信息
        if sourceVolume.GetDisplayNode():
            newVolume.CreateDefaultDisplayNodes()
            newDisplayNode = newVolume.GetDisplayNode()
            sourceDisplayNode = sourceVolume.GetDisplayNode()
            
            # 复制颜色表
            if sourceDisplayNode.GetColorNode():
                newDisplayNode.SetAndObserveColorNodeID(sourceDisplayNode.GetColorNode().GetID())
        
        # 将新节点添加到指定文件夹
        volumeItemID = shNode.GetItemByDataNode(newVolume)
        shNode.SetItemParent(volumeItemID, folderItemID)
        
        return newVolume
    
    # ========== 异步生成掩膜方法 ==========
    
    def generateROIMaskAsync(self, fixedVolume, roiMovingVolume, transformNode=None, 
                            expansionMm=5.0, maskName="Fixed_ROI_Mask", 
                            progressCallback=None, completedCallback=None):
        """
        异步生成ROI掩膜 - 不阻塞UI
        
        :param fixedVolume: 固定图像 (CBCT)
        :param roiMovingVolume: 高分辨率ROI浮动图像 (局部MRI)
        :param transformNode: 粗配准变换节点 (可选)
        :param expansionMm: 向外扩张量(毫米), 默认5mm
        :param maskName: 掩膜名称, 默认"Fixed_ROI_Mask"
        :param progressCallback: 进度回调函数 progressCallback(percent, message)
        :param completedCallback: 完成回调函数 completedCallback(maskVolume)
        """
        try:
            self.logCallback(f"===== 开始异步生成 ROI 掩膜 =====")
            
            # 步骤1-2: 生成ROI MRI LabelMap并应用变换（这部分很快）
            if progressCallback:
                progressCallback(10, "正在创建ROI LabelMap...")
            
            # 复用同步方法的步骤1-2
            labelMapVolume = self._generateROIMRILabelMap(roiMovingVolume, transformNode, expansionMm)
            
            if not labelMapVolume:
                if completedCallback:
                    completedCallback(None)
                return
            
            if progressCallback:
                progressCallback(30, "ROI LabelMap创建完成，准备生成CBCT掩膜...")
            
            # 步骤3: 异步生成CBCT掩膜（这部分最耗时）
            if fixedVolume:
                self._generateCBCTMaskAsync(
                    fixedVolume, labelMapVolume, transformNode, maskName,
                    progressCallback, completedCallback
                )
            else:
                self.logCallback(f"  未提供Fixed Volume，跳过CBCT ROI LabelMap生成")
                if completedCallback:
                    completedCallback(labelMapVolume)
        
        except Exception as e:
            self.logCallback(f"✗ 异步生成掩膜失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            if completedCallback:
                completedCallback(None)
    
    def _generateROIMRILabelMap(self, roiMovingVolume, transformNode, expansionMm):
        """
        生成步骤1-2: ROI MRI LabelMap（同步处理，速度较快）
        
        :param roiMovingVolume: ROI浮动图像
        :param transformNode: 粗配准变换节点
        :param expansionMm: 扩张量(毫米)
        :return: LabelMap Volume节点
        """
        try:
            if not roiMovingVolume:
                raise ValueError("ROI Moving Volume 不能为空")

            self.logCallback("步骤1: 根据ROI MRI生成LabelMap Volume")
            
            # 获取ROI MRI的几何信息
            roiImageData = roiMovingVolume.GetImageData()
            roiDims = roiImageData.GetDimensions()
            roiSpacing = roiMovingVolume.GetSpacing()
            
            # 计算扩张的体素数（每个方向向外扩张）
            expandVoxels = [
                int(np.ceil(expansionMm / roiSpacing[0])),
                int(np.ceil(expansionMm / roiSpacing[1])),
                int(np.ceil(expansionMm / roiSpacing[2]))
            ]
            
            # 新的尺寸 = 原始尺寸 + 2×扩张体素数（每个方向两侧都扩张）
            newDims = [
                roiDims[0] + 2 * expandVoxels[0],
                roiDims[1] + 2 * expandVoxels[1],
                roiDims[2] + 2 * expandVoxels[2]
            ]
            
            # 创建新的ImageData，全部填充为1
            newImageData = vtk.vtkImageData()
            newImageData.SetDimensions(newDims)
            newImageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
            
            # 使用numpy填充为1
            import vtk.util.numpy_support as vtk_np
            newArray = vtk_np.vtk_to_numpy(newImageData.GetPointData().GetScalars())
            newArray[:] = 1
            newImageData.GetPointData().GetScalars().Modified()
            
            # 创建LabelMap Volume节点
            labelMapVolume = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLabelMapVolumeNode", "ROI_Mask_Temp"
            )
            labelMapVolume.SetAndObserveImageData(newImageData)
            labelMapVolume.SetSpacing(roiSpacing)
            
            # 计算新的Origin（考虑扩张后的偏移）
            ijkToRasMatrix = vtk.vtkMatrix4x4()
            roiMovingVolume.GetIJKToRASMatrix(ijkToRasMatrix)
            ijkOrigin = [-expandVoxels[0], -expandVoxels[1], -expandVoxels[2], 1.0]
            rasOrigin = ijkToRasMatrix.MultiplyPoint(ijkOrigin)
            labelMapVolume.SetOrigin([rasOrigin[0], rasOrigin[1], rasOrigin[2]])
            
            # 复制方向矩阵
            directionMatrix = vtk.vtkMatrix4x4()
            roiMovingVolume.GetIJKToRASDirectionMatrix(directionMatrix)
            labelMapVolume.SetIJKToRASDirectionMatrix(directionMatrix)
            
            # 创建显示节点
            labelMapVolume.CreateDefaultDisplayNodes()
            
            # 步骤2: 应用粗配准变换（如果提供）
            if transformNode:
                self.logCallback("步骤2: 应用粗配准变换")
                labelMapVolume.SetAndObserveTransformNodeID(transformNode.GetID())
                roiMovingVolume.SetAndObserveTransformNodeID(transformNode.GetID())
                self.logCallback("  ✓ 变换已应用")
            
            return labelMapVolume
            
        except Exception as e:
            self.logCallback(f"✗ 生成ROI MRI LabelMap失败: {str(e)}")
            return None
    
    def _generateCBCTMaskAsync(self, fixedVolume, labelMapVolume, transformNode, 
                              maskName, progressCallback, completedCallback):
        """
        异步生成CBCT掩膜 - 使用QTimer分块处理
        
        :param fixedVolume: 固定图像 (CBCT)
        :param labelMapVolume: 临时LabelMap
        :param transformNode: 粗配准变换节点
        :param maskName: 掩膜名称
        :param progressCallback: 进度回调
        :param completedCallback: 完成回调
        """
        try:
            self.logCallback("步骤3: 异步生成针对CBCT的ROI LabelMap")
            
            # 准备坐标变换矩阵
            cbctIjkToRas = vtk.vtkMatrix4x4()
            fixedVolume.GetIJKToRASMatrix(cbctIjkToRas)
            
            roiRasToIjk = vtk.vtkMatrix4x4()
            labelMapVolume.GetRASToIJKMatrix(roiRasToIjk)
            
            # 如果有变换，组合变换矩阵
            if transformNode:
                transformMatrix = vtk.vtkMatrix4x4()
                transformNode.GetMatrixTransformToParent(transformMatrix)
                inverseTransform = vtk.vtkMatrix4x4()
                vtk.vtkMatrix4x4.Invert(transformMatrix, inverseTransform)
                rasToIjkWithTransform = vtk.vtkMatrix4x4()
                vtk.vtkMatrix4x4.Multiply4x4(roiRasToIjk, inverseTransform, rasToIjkWithTransform)
                roiRasToIjk.DeepCopy(rasToIjkWithTransform)
            
            cbctImageData = fixedVolume.GetImageData()
            cbctDims = cbctImageData.GetDimensions()
            roiDims = labelMapVolume.GetImageData().GetDimensions()
            
            cbctLabelMapData = vtk.vtkImageData()
            cbctLabelMapData.SetDimensions(cbctDims)
            cbctLabelMapData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
            
            import vtk.util.numpy_support as vtk_np
            cbctLabelMapArray = vtk_np.vtk_to_numpy(cbctLabelMapData.GetPointData().GetScalars())
            cbctLabelMapArray[:] = 0
            
            # 准备异步处理数据
            self.asyncData = {
                'cbctDims': cbctDims,
                'roiDims': roiDims,
                'cbctIjkToRas': cbctIjkToRas,
                'roiRasToIjk': roiRasToIjk,
                'cbctLabelMapArray': cbctLabelMapArray,
                'cbctLabelMapData': cbctLabelMapData,
                'maskName': maskName,  # 添加掩膜名称
                'fixedVolume': fixedVolume,
                'labelMapVolume': labelMapVolume,
                'roiVoxelCount': 0,
                'currentK': 0,  # 当前K层
                'currentJ': 0,  # 当前J行
                'rowsPerChunk': 10,  # 每次处理10行
                'progressCallback': progressCallback,
                'completedCallback': completedCallback,
                'cancelled': False  # 取消标志
            }
            
            # 创建并启动计时器
            self.timer = qt.QTimer()
            self.timer.timeout.connect(self._processNextChunk)
            self.timer.start(1)  # 1ms间隔，尽快处理但保持响应
            
        except Exception as e:
            self.logCallback(f"✗ 启动异步处理失败: {str(e)}")
            if completedCallback:
                completedCallback(None)
    
    def _processNextChunk(self):
        """
        处理下一块数据（由QTimer调用）
        每次处理若干行以保持UI响应性
        """
        try:
            data = self.asyncData
            
            # 检查是否用户取消
            if data.get('cancelled', False):
                self.logCallback("✗ 用户取消了掩膜生成")
                self.timer.stop()
                slicer.mrmlScene.RemoveNode(data['labelMapVolume'])
                if data['completedCallback']:
                    data['completedCallback'](None)
                self.asyncData = None
                return
            
            cbctDims = data['cbctDims']
            roiDims = data['roiDims']
            currentK = data['currentK']
            currentJ = data['currentJ']
            rowsPerChunk = data['rowsPerChunk']
            
            # 处理当前块（若干行）
            endJ = min(currentJ + rowsPerChunk, cbctDims[1])
            
            # 遍历当前块的所有体素
            for j in range(currentJ, endJ):
                for i in range(cbctDims[0]):
                    # CBCT IJK -> RAS -> ROI IJK
                    cbctIjkPoint = [i, j, currentK, 1.0]
                    rasPoint = data['cbctIjkToRas'].MultiplyPoint(cbctIjkPoint)
                    roiIjkPoint = data['roiRasToIjk'].MultiplyPoint(rasPoint)
                    
                    # 检查是否在ROI范围内
                    if (0 <= roiIjkPoint[0] < roiDims[0] and
                        0 <= roiIjkPoint[1] < roiDims[1] and
                        0 <= roiIjkPoint[2] < roiDims[2]):
                        idx = i + j * cbctDims[0] + currentK * cbctDims[0] * cbctDims[1]
                        data['cbctLabelMapArray'][idx] = 1
                        data['roiVoxelCount'] += 1
            
            # 检查是否完成当前层
            if endJ >= cbctDims[1]:
                # 当前层完成，进入下一层
                data['currentK'] += 1
                data['currentJ'] = 0
                
                # 更新进度（每完成一层更新一次）
                progress = int((data['currentK'] / cbctDims[2]) * 100)
                if data['progressCallback']:
                    data['progressCallback'](
                        progress, 
                        f"正在生成Fixed ROI 掩膜... {data['currentK']}/{cbctDims[2]} 层"
                    )
            else:
                # 继续当前层的下一块
                data['currentJ'] = endJ
            
            # 处理UI事件，保持响应性
            slicer.app.processEvents()
            
            # 检查是否完全完成
            if data['currentK'] >= cbctDims[2]:
                # 完成处理
                self.timer.stop()
                self._finalizeCBCTMask(data)
                
        except Exception as e:
            self.logCallback(f"✗ 处理数据块失败: {str(e)}")
            self.timer.stop()
            if self.asyncData and self.asyncData['completedCallback']:
                self.asyncData['completedCallback'](None)
            self.asyncData = None
    
    def _finalizeCBCTMask(self, data):
        """
        完成CBCT掩膜生成，创建最终节点
        
        :param data: 异步处理数据
        """
        try:
            if data['progressCallback']:
                data['progressCallback'](90, "正在完成掩膜生成...")
            
            data['cbctLabelMapData'].GetPointData().GetScalars().Modified()
            
            # 创建最终节点（使用用户指定的名称）
            maskName = data.get('maskName', 'Fixed_ROI_Mask')
            cbctROILabelMap = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLabelMapVolumeNode", maskName
            )
            cbctROILabelMap.SetAndObserveImageData(data['cbctLabelMapData'])
            cbctROILabelMap.CopyOrientation(data['fixedVolume'])
            cbctROILabelMap.CreateDefaultDisplayNodes()
            
            # 设置自定义颜色表
            displayNode = cbctROILabelMap.GetDisplayNode()
            if displayNode:
                colorTable = slicer.mrmlScene.CreateNodeByClass("vtkMRMLColorTableNode")
                colorTable.SetTypeToUser()
                colorTable.SetNumberOfColors(2)
                colorTable.SetColor(0, "Background", 0.6, 0.8, 1.0, 1.0)  # 浅蓝色
                colorTable.SetColor(1, "ROI", 0.8, 0.6, 1.0, 1.0)  # 浅紫色
                colorTable.SetName("ROI_Mask_Colors")
                slicer.mrmlScene.AddNode(colorTable)
                displayNode.SetAndObserveColorNodeID(colorTable.GetID())
            
            # 删除临时节点
            slicer.mrmlScene.RemoveNode(data['labelMapVolume'])
            
            # 统计信息
            totalCBCTVoxels = data['cbctDims'][0] * data['cbctDims'][1] * data['cbctDims'][2]
            roiPercentage = (data['roiVoxelCount'] / totalCBCTVoxels) * 100
            
            self.logCallback("✓ CBCT ROI LabelMap生成成功")
            self.logCallback(f"  掩膜名称: {maskName}")
            self.logCallback(
                f"  ROI体素数: {data['roiVoxelCount']}/{totalCBCTVoxels} "
                f"({roiPercentage:.2f}%)"
            )
            
            if data['progressCallback']:
                data['progressCallback'](100, "掩膜生成完成！")
            
            if data['completedCallback']:
                data['completedCallback'](cbctROILabelMap)
            
            self.asyncData = None
            
        except Exception as e:
            self.logCallback(f"✗ 完成掩膜生成失败: {str(e)}")
            if data['completedCallback']:
                data['completedCallback'](None)
    
    def cancelAsyncGeneration(self):
        """
        取消正在进行的异步掩膜生成
        """
        if self.asyncData:
            self.asyncData['cancelled'] = True
            self.logCallback("正在取消掩膜生成...")
