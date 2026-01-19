"""
Data Preprocessing Logic - 业务逻辑处理
用于CBCT和MRI数据的预处理操作
"""
import vtk
import slicer
import numpy as np
import qt


class DataPreprocessingLogic:
    """
    Data Preprocessing 的业务逻辑类
    负责CBCT和MRI数据的预处理，为TransMorph仿射配准准备数据
    """

    def __init__(self, logCallback=None):
        """
        初始化 Data Preprocessing Logic
        
        :param logCallback: 日志回调函数
        """
        self.logCallback = logCallback if logCallback else print
        
        # 异步处理相关
        self.timer = None
        self.asyncData = None

    def getVolumeInfo(self, volumeNode):
        """
        获取体数据的详细信息
        
        :param volumeNode: 体数据节点
        :return: 包含体数据信息的字典
        """
        if not volumeNode:
            return None
        
        imageData = volumeNode.GetImageData()
        dims = imageData.GetDimensions()
        spacing = volumeNode.GetSpacing()
        origin = volumeNode.GetOrigin()
        
        # 获取方向矩阵
        directionMatrix = vtk.vtkMatrix4x4()
        volumeNode.GetIJKToRASDirectionMatrix(directionMatrix)
        
        # 计算物理尺寸
        physicalSize = [dims[i] * spacing[i] for i in range(3)]
        
        return {
            'name': volumeNode.GetName(),
            'dimensions': dims,
            'spacing': spacing,
            'origin': origin,
            'physicalSize': physicalSize,
            'directionMatrix': directionMatrix
        }

    def setOriginToZero(self, volumeNode):
        """
        将体数据的原点设置为(0, 0, 0)
        
        :param volumeNode: 输入体数据节点
        :return: 处理后的体数据节点
        """
        try:
            if not volumeNode:
                raise ValueError("体数据节点不能为空")
            
            oldOrigin = volumeNode.GetOrigin()
            self.logCallback(f"原始原点: ({oldOrigin[0]:.3f}, {oldOrigin[1]:.3f}, {oldOrigin[2]:.3f})")
            
            volumeNode.SetOrigin(0, 0, 0)
            self.logCallback(f"已将 {volumeNode.GetName()} 原点设置为 (0, 0, 0)")
            return volumeNode
                
        except Exception as e:
            self.logCallback(f"设置原点失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return None

    def createROIFromVolume(self, volumeNode, roiName=None):
        """
        根据体数据创建ROI标注框
        
        :param volumeNode: 体数据节点
        :param roiName: ROI名称
        :return: 创建的ROI节点
        """
        try:
            if not volumeNode:
                raise ValueError("体数据节点不能为空")
            
            # 获取体数据边界
            bounds = [0] * 6
            volumeNode.GetRASBounds(bounds)
            
            # 计算中心和半径
            center = [(bounds[i*2] + bounds[i*2+1]) / 2 for i in range(3)]
            radius = [(bounds[i*2+1] - bounds[i*2]) / 2 for i in range(3)]
            
            # 创建ROI节点
            if roiName is None:
                roiName = f"{volumeNode.GetName()}_ROI"
            
            roiNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsROINode", roiName)
            roiNode.SetCenter(center)
            roiNode.SetSize([r * 2 for r in radius])
            
            self.logCallback(f"创建ROI: {roiName}")
            self.logCallback(f"  中心: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f})")
            self.logCallback(f"  尺寸: ({radius[0]*2:.2f}, {radius[1]*2:.2f}, {radius[2]*2:.2f}) mm")
            
            return roiNode
            
        except Exception as e:
            self.logCallback(f"创建ROI失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return None

    def updateROISizeByDimensions(self, roiNode, volumeNode, targetDimensions):
        """
        根据目标体素尺寸更新ROI大小
        
        :param roiNode: ROI节点
        :param volumeNode: 参考体数据节点（用于获取间距）
        :param targetDimensions: 目标尺寸 [x, y, z]（体素数）
        """
        try:
            spacing = volumeNode.GetSpacing()
            newSize = [targetDimensions[i] * spacing[i] for i in range(3)]
            roiNode.SetSize(newSize)
            
            self.logCallback(f"更新ROI尺寸:")
            self.logCallback(f"  目标体素: {targetDimensions}")
            self.logCallback(f"  物理尺寸: ({newSize[0]:.2f}, {newSize[1]:.2f}, {newSize[2]:.2f}) mm")
            
        except Exception as e:
            self.logCallback(f"更新ROI尺寸失败: {str(e)}")

    def padVolumeToTargetSize(self, volumeNode, targetDimensions, fillValue=-1000):
        """
        填充体数据到目标尺寸（用于解决裁剪后的尺寸偏差）
        
        :param volumeNode: 输入体数据节点
        :param targetDimensions: 目标尺寸 [x, y, z]
        :param fillValue: 填充值（默认-1000，CT数据的最小值）
        :return: 填充后的体数据节点（修改原节点）
        """
        try:
            currentDims = volumeNode.GetImageData().GetDimensions()
            
            # 检查是否需要填充
            needsPadding = any(currentDims[i] != targetDimensions[i] for i in range(3))
            
            if not needsPadding:
                self.logCallback(f"尺寸已匹配 {currentDims}，无需填充")
                return volumeNode
            
            self.logCallback(f"填充体数据到目标尺寸:")
            self.logCallback(f"  当前尺寸: {currentDims}")
            self.logCallback(f"  目标尺寸: {targetDimensions}")
            self.logCallback(f"  填充值: {fillValue}")
            
            # 计算填充范围
            padFilter = vtk.vtkImageConstantPad()
            padFilter.SetInputData(volumeNode.GetImageData())
            padFilter.SetConstant(fillValue)
            
            # 设置输出范围 [xMin, xMax, yMin, yMax, zMin, zMax]
            padFilter.SetOutputWholeExtent(
                0, targetDimensions[0] - 1,
                0, targetDimensions[1] - 1,
                0, targetDimensions[2] - 1
            )
            
            padFilter.Update()
            paddedImageData = padFilter.GetOutput()
            
            # 更新体数据
            volumeNode.SetAndObserveImageData(paddedImageData)
            
            # 验证结果
            resultDims = volumeNode.GetImageData().GetDimensions()
            self.logCallback(f"  填充后尺寸: {resultDims}")
            
            if resultDims == tuple(targetDimensions):
                self.logCallback(f"  ✓ 尺寸精确匹配目标")
            else:
                self.logCallback(f"  ⚠ 警告: 填充后尺寸仍不匹配!")
            
            return volumeNode
            
        except Exception as e:
            self.logCallback(f"填充体数据失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return volumeNode
    
    def cropVolumeWithROI(self, volumeNode, roiNode, outputVolumeName=None):
        """
        使用ROI裁剪体数据（完全模拟Crop Volume插件的行为）
        
        :param volumeNode: 输入体数据节点
        :param roiNode: ROI节点
        :param outputVolumeName: 输出体数据名称
        :return: 裁剪后的体数据节点
        """
        try:
            if not volumeNode or not roiNode:
                raise ValueError("体数据节点和ROI节点不能为空")
            
            # 获取原始体数据信息
            originalSpacing = volumeNode.GetSpacing()
            originalDims = volumeNode.GetImageData().GetDimensions()
            originalOrigin = volumeNode.GetOrigin()
            
            self.logCallback(f"原始体数据信息:")
            self.logCallback(f"  尺寸: {originalDims}")
            self.logCallback(f"  间距: ({originalSpacing[0]:.4f}, {originalSpacing[1]:.4f}, {originalSpacing[2]:.4f})")
            self.logCallback(f"  原点: ({originalOrigin[0]:.4f}, {originalOrigin[1]:.4f}, {originalOrigin[2]:.4f})")
            
            # 获取ROI信息
            center = [0, 0, 0]
            roiNode.GetCenter(center)
            size = roiNode.GetSize()
            
            self.logCallback(f"ROI裁剪参数:")
            self.logCallback(f"  中心: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f})")
            self.logCallback(f"  尺寸: ({size[0]:.2f}, {size[1]:.2f}, {size[2]:.2f}) mm")
            
            # 使用Crop Volume模块 - 完全按照插件的默认行为
            cropVolumeLogic = slicer.modules.cropvolume.logic()
            
            # 创建参数节点
            cropVolumeParameterNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLCropVolumeParametersNode")
            cropVolumeParameterNode.SetInputVolumeNodeID(volumeNode.GetID())
            cropVolumeParameterNode.SetROINodeID(roiNode.GetID())
            
            # 关键设置：使用VoxelBased模式 = 纯裁剪，不重采样
            cropVolumeParameterNode.SetVoxelBased(True)
            
            # 执行裁剪
            cropVolumeLogic.Apply(cropVolumeParameterNode)
            
            # 获取输出
            croppedVolume = cropVolumeParameterNode.GetOutputVolumeNode()
            
            if croppedVolume:
                outputDims = croppedVolume.GetImageData().GetDimensions()
                outputSpacing = croppedVolume.GetSpacing()
                outputOrigin = croppedVolume.GetOrigin()
                
                self.logCallback(f"裁剪完成:")
                self.logCallback(f"  输出尺寸: {outputDims}")
                self.logCallback(f"  输出间距: ({outputSpacing[0]:.4f}, {outputSpacing[1]:.4f}, {outputSpacing[2]:.4f})")
                self.logCallback(f"  输出原点: ({outputOrigin[0]:.4f}, {outputOrigin[1]:.4f}, {outputOrigin[2]:.4f})")
                
                # 验证间距是否保持不变
                spacingMatch = all(abs(originalSpacing[i] - outputSpacing[i]) < 0.0001 for i in range(3))
                if spacingMatch:
                    self.logCallback(f"  ✓ 间距保持不变")
                else:
                    self.logCallback(f"  ⚠ 警告: 间距发生变化!")
                
                if outputVolumeName:
                    croppedVolume.SetName(outputVolumeName)
            else:
                self.logCallback("错误: 裁剪未生成输出体数据")
            
            # 清理参数节点
            slicer.mrmlScene.RemoveNode(cropVolumeParameterNode)
            
            return croppedVolume
            
        except Exception as e:
            self.logCallback(f"ROI裁剪失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return None

    def createTemplateVolume(self, referenceVolume, outputVolumeName, targetSpacing):
        """
        创建模板图像（空白图像，用于后续MRI配准和重采样的参考）
        直接根据参考体数据的尺寸和目标间距创建，不进行重采样
        
        :param referenceVolume: 参考体数据节点（用于获取尺寸）
        :param outputVolumeName: 输出模板名称
        :param targetSpacing: 目标间距 [x, y, z]
        :return: 模板体数据节点
        """
        try:
            if not referenceVolume:
                raise ValueError("参考体数据节点不能为空")
            
            # 获取参考体数据信息
            refDims = referenceVolume.GetImageData().GetDimensions()
            refSpacing = referenceVolume.GetSpacing()
            
            self.logCallback(f"创建模板图像:")
            self.logCallback(f"  参考体数据: {referenceVolume.GetName()}")
            self.logCallback(f"  参考尺寸: {refDims}")
            self.logCallback(f"  参考间距: ({refSpacing[0]:.4f}, {refSpacing[1]:.4f}, {refSpacing[2]:.4f})")
            self.logCallback(f"  目标间距: ({targetSpacing[0]:.4f}, {targetSpacing[1]:.4f}, {targetSpacing[2]:.4f})")
            
            # 计算模板尺寸（保持物理大小不变）
            templateDims = [int(round(refDims[i] * refSpacing[i] / targetSpacing[i])) for i in range(3)]
            self.logCallback(f"  模板尺寸: {templateDims}")
            
            # 创建空白ImageData
            imageData = vtk.vtkImageData()
            imageData.SetDimensions(templateDims[0], templateDims[1], templateDims[2])
            imageData.AllocateScalars(vtk.VTK_SHORT, 1)  # 使用SHORT类型，与CT数据一致
            
            # 填充固定值（1000，显示为白色，方便查看模板范围）
            fillValue = 1000
            imageData.GetPointData().GetScalars().Fill(fillValue)
            
            self.logCallback(f"  填充值: {fillValue}（白色显示）")
            
            # 创建输出节点
            templateVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", outputVolumeName)
            templateVolume.SetAndObserveImageData(imageData)
            templateVolume.SetSpacing(targetSpacing)
            templateVolume.SetOrigin(0, 0, 0)  # 模板原点固定为(0, 0, 0)
            
            # 复制方向矩阵
            directionMatrix = vtk.vtkMatrix4x4()
            referenceVolume.GetIJKToRASDirectionMatrix(directionMatrix)
            templateVolume.SetIJKToRASDirectionMatrix(directionMatrix)
            
            # 设置显示属性（白色显示）
            displayNode = templateVolume.GetDisplayNode()
            if not displayNode:
                templateVolume.CreateDefaultDisplayNodes()
                displayNode = templateVolume.GetDisplayNode()
            
            if displayNode:
                # 设置窗口/窗宽以白色显示
                displayNode.SetAutoWindowLevel(0)  # 关闭自动窗宽
                displayNode.SetWindowLevel(2000, 500)  # 同时设置窗口和窗宽
                displayNode.Modified()  # 触发显示更新
                
            # 强制更新场景显示
            slicer.app.processEvents()
            
            # 验证结果
            resultDims = templateVolume.GetImageData().GetDimensions()
            resultSpacing = templateVolume.GetSpacing()
            resultOrigin = templateVolume.GetOrigin()
            scalarRange = templateVolume.GetImageData().GetScalarRange()
            
            self.logCallback(f"模板创建完成: {outputVolumeName}")
            self.logCallback(f"  实际尺寸: {resultDims}")
            self.logCallback(f"  实际间距: ({resultSpacing[0]:.4f}, {resultSpacing[1]:.4f}, {resultSpacing[2]:.4f})")
            self.logCallback(f"  实际原点: ({resultOrigin[0]:.4f}, {resultOrigin[1]:.4f}, {resultOrigin[2]:.4f})")
            self.logCallback(f"  标量范围: [{scalarRange[0]:.2f}, {scalarRange[1]:.2f}]")
            
            return templateVolume
            
        except Exception as e:
            self.logCallback(f"创建模板失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return None
    
    def normalizeCBCT(self, volumeNode, clipMin=-1000, clipMax=1000):
        """
        CBCT强度归一化：截断后归一化到[0, 1]
        
        :param volumeNode: CBCT体数据节点
        :param clipMin: 截断下限（默认-1000 HU）
        :param clipMax: 截断上限（默认1000 HU）
        :return: 归一化后的体数据节点
        """
        try:
            if not volumeNode:
                raise ValueError("体数据节点不能为空")
            
            import vtk.util.numpy_support as vtk_np
            
            # 获取图像数据
            imageData = volumeNode.GetImageData()
            scalarArray = imageData.GetPointData().GetScalars()
            
            # 转换为numpy数组
            numpyArray = vtk_np.vtk_to_numpy(scalarArray)
            originalRange = (numpyArray.min(), numpyArray.max())
            
            self.logCallback(f"CBCT强度归一化:")
            self.logCallback(f"  原始范围: [{originalRange[0]:.2f}, {originalRange[1]:.2f}]")
            self.logCallback(f"  截断范围: [{clipMin}, {clipMax}]")
            
            # 步骤1: 截断到指定范围
            numpyArray = np.clip(numpyArray, clipMin, clipMax)
            
            # 步骤2: 归一化到[0, 1]
            normalizedArray = (numpyArray - clipMin) / (clipMax - clipMin)
            
            newRange = (normalizedArray.min(), normalizedArray.max())
            self.logCallback(f"  归一化后范围: [{newRange[0]:.4f}, {newRange[1]:.4f}]")
            
            # 更新图像数据
            vtk_np.numpy_to_vtk(normalizedArray, deep=1, array_type=vtk.VTK_FLOAT)
            newScalarArray = vtk_np.numpy_to_vtk(normalizedArray.astype(np.float32), deep=1, array_type=vtk.VTK_FLOAT)
            imageData.GetPointData().SetScalars(newScalarArray)
            imageData.Modified()
            
            # 更新显示节点的窗宽窗位（关键：适配[0,1]范围）
            displayNode = volumeNode.GetDisplayNode()
            if not displayNode:
                volumeNode.CreateDefaultDisplayNodes()
                displayNode = volumeNode.GetDisplayNode()
            
            if displayNode:
                # 关闭自动窗宽窗位
                displayNode.SetAutoWindowLevel(0)
                # 设置适合[0,1]范围的窗宽窗位：window=1.0, level=0.5
                displayNode.SetWindowLevel(1.0, 0.5)
                displayNode.Modified()
                self.logCallback(f"  ✓ 已更新显示窗宽窗位: Window=1.0, Level=0.5")
            
            # 强制刷新显示
            slicer.app.processEvents()
            
            self.logCallback(f"  ✓ CBCT归一化完成")
            return volumeNode
            
        except Exception as e:
            self.logCallback(f"CBCT归一化失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return volumeNode
    
    def normalizeMRI(self, volumeNode, lowerPercentile=1.0, upperPercentile=99.0):
        """
        MRI强度归一化：百分位数截断后归一化到[0, 1]
        
        :param volumeNode: MRI体数据节点
        :param lowerPercentile: 下百分位数（默认1%）
        :param upperPercentile: 上百分位数（默认99%）
        :return: 归一化后的体数据节点
        """
        try:
            if not volumeNode:
                raise ValueError("体数据节点不能为空")
            
            import vtk.util.numpy_support as vtk_np
            
            # 获取图像数据
            imageData = volumeNode.GetImageData()
            scalarArray = imageData.GetPointData().GetScalars()
            
            # 转换为numpy数组
            numpyArray = vtk_np.vtk_to_numpy(scalarArray)
            originalRange = (numpyArray.min(), numpyArray.max())
            
            self.logCallback(f"MRI强度归一化:")
            self.logCallback(f"  原始范围: [{originalRange[0]:.2f}, {originalRange[1]:.2f}]")
            
            # 步骤1: 计算百分位数
            lowerBound = np.percentile(numpyArray, lowerPercentile)
            upperBound = np.percentile(numpyArray, upperPercentile)
            
            self.logCallback(f"  {lowerPercentile}%分位数: {lowerBound:.2f}")
            self.logCallback(f"  {upperPercentile}%分位数: {upperBound:.2f}")
            
            # 步骤2: 截断到百分位数范围
            numpyArray = np.clip(numpyArray, lowerBound, upperBound)
            
            # 步骤3: 归一化到[0, 1]
            if upperBound > lowerBound:
                normalizedArray = (numpyArray - lowerBound) / (upperBound - lowerBound)
            else:
                self.logCallback(f"  ⚠ 警告: 上下界相同，跳过归一化")
                normalizedArray = numpyArray
            
            newRange = (normalizedArray.min(), normalizedArray.max())
            self.logCallback(f"  归一化后范围: [{newRange[0]:.4f}, {newRange[1]:.4f}]")
            
            # 更新图像数据
            newScalarArray = vtk_np.numpy_to_vtk(normalizedArray.astype(np.float32), deep=1, array_type=vtk.VTK_FLOAT)
            imageData.GetPointData().SetScalars(newScalarArray)
            imageData.Modified()
            
            # 更新显示节点的窗宽窗位（适配[0,1]范围）
            displayNode = volumeNode.GetDisplayNode()
            if not displayNode:
                volumeNode.CreateDefaultDisplayNodes()
                displayNode = volumeNode.GetDisplayNode()
            
            if displayNode:
                displayNode.SetAutoWindowLevel(0)
                displayNode.SetWindowLevel(1.0, 0.5)
                displayNode.Modified()
                self.logCallback(f"  ✓ 已更新显示窗宽窗位: Window=1.0, Level=0.5")
            
            # 强制刷新显示
            slicer.app.processEvents()
            
            self.logCallback(f"  ✓ MRI归一化完成")
            return volumeNode
            
        except Exception as e:
            self.logCallback(f"MRI归一化失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return volumeNode
    
    def replaceVolumeData(self, targetVolume, sourceVolume):
        """
        用源体数据替换目标体数据的内容（保留目标节点）
        
        :param targetVolume: 目标体数据节点（将被替换内容）
        :param sourceVolume: 源体数据节点（提供新内容）
        :return: 成功返回True，否则False
        """
        try:
            if not targetVolume or not sourceVolume:
                raise ValueError("目标和源体数据节点不能为空")
            
            originalName = targetVolume.GetName()
            
            self.logCallback(f"替换前 - 目标体数据 {originalName}:")
            self.logCallback(f"  尺寸: {targetVolume.GetImageData().GetDimensions()}")
            self.logCallback(f"  间距: {targetVolume.GetSpacing()}")
            self.logCallback(f"  原点: {targetVolume.GetOrigin()}")
            
            self.logCallback(f"源体数据:")
            self.logCallback(f"  尺寸: {sourceVolume.GetImageData().GetDimensions()}")
            self.logCallback(f"  间距: {sourceVolume.GetSpacing()}")
            self.logCallback(f"  原点: {sourceVolume.GetOrigin()}")
            
            # 深拷贝图像数据
            newImageData = vtk.vtkImageData()
            newImageData.DeepCopy(sourceVolume.GetImageData())
            targetVolume.SetAndObserveImageData(newImageData)
            
            # 复制空间信息
            targetVolume.SetSpacing(sourceVolume.GetSpacing())
            targetVolume.SetOrigin(sourceVolume.GetOrigin())
            
            # 复制方向矩阵
            mat = vtk.vtkMatrix4x4()
            sourceVolume.GetIJKToRASDirectionMatrix(mat)
            targetVolume.SetIJKToRASDirectionMatrix(mat)
            
            # 恢复原始名称
            targetVolume.SetName(originalName)
            
            self.logCallback(f"替换后 - 目标体数据 {originalName}:")
            self.logCallback(f"  尺寸: {targetVolume.GetImageData().GetDimensions()}")
            self.logCallback(f"  间距: {targetVolume.GetSpacing()}")
            self.logCallback(f"  原点: {targetVolume.GetOrigin()}")
            
            self.logCallback(f"✓ 已用处理后的数据替换原始 {originalName}")
            return True
            
        except Exception as e:
            self.logCallback(f"替换体数据失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return False

    def processCBCT(self, cbctVolume, roiNode, targetSpacing, targetDimensions=None,
                    replaceOriginal=True, createTemplateVolume=True):
        """
        完整的CBCT预处理流程
        
        :param cbctVolume: 原始CBCT体数据节点
        :param roiNode: ROI节点（用于裁剪）
        :param targetSpacing: 目标间距 [x, y, z]（mm），用于模板图像
        :param targetDimensions: 目标尺寸 [x, y, z]（voxels），用于精确控制裁剪尺寸
        :param replaceOriginal: 是否用处理后的数据替换原始CBCT
        :param createTemplateVolume: 是否创建模板图像（原点归零+裁剪+重采样）
        :return: (fixedVolume, templateVolume) 元组
        """
        try:
            baseName = cbctVolume.GetName()
            self.logCallback("=" * 50)
            self.logCallback(f"开始CBCT预处理: {baseName}")
            self.logCallback("=" * 50)
            
            # 记录原始信息
            originalInfo = self.getVolumeInfo(cbctVolume)
            self.logCallback(f"\n原始CBCT信息:")
            self.logCallback(f"  尺寸: {originalInfo['dimensions']}")
            self.logCallback(f"  间距: {originalInfo['spacing']}")
            self.logCallback(f"  原点: {originalInfo['origin']}")
            
            fixedVolume = None
            templateVolume = None
            
            # 步骤1: 使用ROI裁剪（完全模拟Crop Volume插件）
            self.logCallback("\n[步骤1] ROI裁剪...")
            croppedVolume = self.cropVolumeWithROI(cbctVolume, roiNode, f"{baseName}_Cropped_Temp")
            
            if not croppedVolume:
                raise RuntimeError("ROI裁剪失败，未生成输出")
            
            # 验证裁剪结果
            if not croppedVolume.GetImageData():
                raise RuntimeError("ROI裁剪输出的ImageData为空")
            
            croppedInfo = self.getVolumeInfo(croppedVolume)
            self.logCallback(f"裁剪后体数据信息:")
            self.logCallback(f"  尺寸: {croppedInfo['dimensions']}")
            self.logCallback(f"  间距: {croppedInfo['spacing']}")
            self.logCallback(f"  原点: {croppedInfo['origin']}")
            
            # 检查裁剪后数据的标量范围
            scalarRange = croppedVolume.GetImageData().GetScalarRange()
            self.logCallback(f"  标量范围: [{scalarRange[0]:.2f}, {scalarRange[1]:.2f}]")
            
            # 步骤1.5: 如果指定了目标尺寸，填充到精确尺寸
            if targetDimensions:
                self.logCallback(f"\n[步骤1.5] 填充到目标尺寸 {targetDimensions}...")
                croppedVolume = self.padVolumeToTargetSize(croppedVolume, targetDimensions, fillValue=-1000)
            
            # 步骤2: 处理原始CBCT
            if replaceOriginal:
                self.logCallback("\n[步骤2] 用裁剪后的数据替换原始CBCT...")
                success = self.replaceVolumeData(cbctVolume, croppedVolume)
                if success:
                    fixedVolume = cbctVolume
                    self.logCallback(f"✓ 原始CBCT已更新: {cbctVolume.GetName()}")
                else:
                    self.logCallback("✗ 替换失败，使用裁剪后的体数据作为Fixed Volume")
                    croppedVolume.SetName(f"{baseName}_Fixed")
                    fixedVolume = croppedVolume
            else:
                # 重命名裁剪后的体数据作为Fixed Volume
                croppedVolume.SetName(f"{baseName}_Fixed")
                fixedVolume = croppedVolume
            
            # 步骤2.5: 原点归零（在重采样之前执行）
            self.logCallback("\n[步骤2.5] 原点归零...")
            if fixedVolume:
                self.setOriginToZero(fixedVolume)
                self.logCallback(f"✓ Fixed Volume原点已归零")
            
            # 步骤2.6: CBCT强度归一化
            self.logCallback("\n[步骤2.6] CBCT强度归一化...")
            if fixedVolume:
                self.normalizeCBCT(fixedVolume, clipMin=-1000, clipMax=1000)
            
            # 步骤3: 创建Template Volume（空白模板图像）
            if createTemplateVolume and targetSpacing:
                self.logCallback("\n[步骤3] 创建Template Volume...")
                templateVolumeName = f"{baseName}_Template"
                
                # 使用fixedVolume作为参考创建空白模板
                templateVolume = self.createTemplateVolume(fixedVolume, templateVolumeName, targetSpacing)
                
                if templateVolume:
                    self.logCallback(f"✓ Template Volume创建成功")
                else:
                    self.logCallback("✗ Template Volume创建失败")
            
            # 清理临时节点（只在成功替换后删除）
            if replaceOriginal and croppedVolume and croppedVolume.GetID() != fixedVolume.GetID():
                self.logCallback(f"\n清理临时节点: {croppedVolume.GetName()}")
                slicer.mrmlScene.RemoveNode(croppedVolume)
            
            self.logCallback("\n" + "=" * 50)
            self.logCallback("CBCT预处理完成!")
            if fixedVolume:
                info = self.getVolumeInfo(fixedVolume)
                self.logCallback(f"Fixed Volume: {info['name']}")
                self.logCallback(f"  尺寸: {info['dimensions']}")
                self.logCallback(f"  间距: {info['spacing']}")
                self.logCallback(f"  原点: {info['origin']}")
            if templateVolume:
                info = self.getVolumeInfo(templateVolume)
                self.logCallback(f"Template Volume: {info['name']}")
                self.logCallback(f"  尺寸: {info['dimensions']}")
                self.logCallback(f"  间距: {info['spacing']}")
                self.logCallback(f"  原点: {info['origin']}")
            self.logCallback("=" * 50)
            
            return fixedVolume, templateVolume
            
        except Exception as e:
            self.logCallback(f"CBCT预处理失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return None, None

    def resampleMRIToTemplate(self, mriVolume, templateVolume, transformNode=None, outputVolumeName=None):
        """
        将MRI重采样到模板空间（使用BRAINSResample模块）
        
        :param mriVolume: 输入MRI节点
        :param templateVolume: 模板体数据节点（定义目标空间）
        :param transformNode: （可选）初始变换节点（如粗配准变换）
        :param outputVolumeName: 输出体数据名称
        :return: 重采样后的体数据节点
        """
        try:
            if not mriVolume or not templateVolume:
                raise ValueError("MRI和模板节点不能为空")
            
            # 获取原始MRI信息
            mriInfo = self.getVolumeInfo(mriVolume)
            templateInfo = self.getVolumeInfo(templateVolume)
            
            self.logCallback(f"\n原始MRI信息:")
            self.logCallback(f"  尺寸: {mriInfo['dimensions']}")
            self.logCallback(f"  间距: ({mriInfo['spacing'][0]:.4f}, {mriInfo['spacing'][1]:.4f}, {mriInfo['spacing'][2]:.4f})")
            self.logCallback(f"  原点: ({mriInfo['origin'][0]:.2f}, {mriInfo['origin'][1]:.2f}, {mriInfo['origin'][2]:.2f})")
            
            self.logCallback(f"\n目标模板空间:")
            self.logCallback(f"  尺寸: {templateInfo['dimensions']}")
            self.logCallback(f"  间距: ({templateInfo['spacing'][0]:.4f}, {templateInfo['spacing'][1]:.4f}, {templateInfo['spacing'][2]:.4f})")
            self.logCallback(f"  原点: ({templateInfo['origin'][0]:.2f}, {templateInfo['origin'][1]:.2f}, {templateInfo['origin'][2]:.2f})")
            
            # 创建输出节点
            if outputVolumeName is None:
                outputVolumeName = f"{mriVolume.GetName()}_Resampled"
            
            outputVolume = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLScalarVolumeNode", 
                outputVolumeName
            )
            
            # 配置重采样参数
            parameters = {
                'inputVolume': mriVolume.GetID(),
                'referenceVolume': templateVolume.GetID(),
                'outputVolume': outputVolume.GetID(),
                'interpolationMode': 'Linear',  # 三线性插值
                'pixelType': 'short',            # 输出类型（MRI通常是short）
                'defaultValue': 0                # 边界外默认值
            }
            
            # 如果有初始变换，应用它
            if transformNode:
                parameters['warpTransform'] = transformNode.GetID()
                self.logCallback(f"  应用初始变换: {transformNode.GetName()}")
            else:
                self.logCallback(f"  无初始变换")
            
            self.logCallback(f"\n开始重采样MRI（三线性插值）...")
            
            # 同步执行重采样
            cliNode = slicer.cli.runSync(slicer.modules.brainsresample, None, parameters)
            
            # 检查执行状态
            if cliNode.GetStatus() & cliNode.Completed:
                if cliNode.GetStatus() & cliNode.ErrorsMask:
                    self.logCallback("错误: MRI重采样失败")
                    # 清理失败的输出节点
                    slicer.mrmlScene.RemoveNode(outputVolume)
                    return None
                else:
                    self.logCallback(f"重采样完成: {outputVolumeName}")
                    
                    # 验证输出
                    outputInfo = self.getVolumeInfo(outputVolume)
                    self.logCallback(f"  输出尺寸: {outputInfo['dimensions']}")
                    self.logCallback(f"  输出间距: ({outputInfo['spacing'][0]:.4f}, {outputInfo['spacing'][1]:.4f}, {outputInfo['spacing'][2]:.4f})")
                    self.logCallback(f"  输出原点: ({outputInfo['origin'][0]:.2f}, {outputInfo['origin'][1]:.2f}, {outputInfo['origin'][2]:.2f})")
                    
                    # 验证是否与模板一致
                    dimsMatch = outputInfo['dimensions'] == templateInfo['dimensions']
                    spacingMatch = all(abs(outputInfo['spacing'][i] - templateInfo['spacing'][i]) < 0.0001 for i in range(3))
                    
                    if dimsMatch and spacingMatch:
                        self.logCallback(f"  ✓ 输出空间与模板完全一致")
                    else:
                        self.logCallback(f"  ⚠ 警告: 输出空间与模板不一致")
                    
                    # 清理CLI节点
                    slicer.mrmlScene.RemoveNode(cliNode)
                    
                    return outputVolume
            else:
                self.logCallback("错误: 重采样未完成")
                slicer.mrmlScene.RemoveNode(outputVolume)
                return None
                
        except Exception as e:
            self.logCallback(f"MRI重采样失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return None

    def processMRI(self, mriVolume, templateVolume, transformNode=None, replaceOriginal=True):
        """
        完整的MRI预处理流程
        
        :param mriVolume: 原始MRI体数据节点
        :param templateVolume: 模板体数据节点（由CBCT预处理生成）
        :param transformNode: （可选）初始空间变换节点（如粗配准变换）
        :param replaceOriginal: 是否用处理后的数据替换原始MRI
        :return: 处理后的MRI节点
        """
        try:
            baseName = mriVolume.GetName()
            self.logCallback("=" * 50)
            self.logCallback(f"开始MRI预处理: {baseName}")
            self.logCallback("=" * 50)
            
            # 步骤1: 重采样到模板空间
            self.logCallback("\n[步骤1] 重采样MRI到Template空间...")
            resampledVolume = self.resampleMRIToTemplate(
                mriVolume, 
                templateVolume, 
                transformNode,
                f"{baseName}_Resampled_Temp"
            )
            
            if not resampledVolume:
                raise RuntimeError("MRI重采样失败，未生成输出")
            
            # 验证重采样结果
            if not resampledVolume.GetImageData():
                raise RuntimeError("MRI重采样输出的ImageData为空")
            
            scalarRange = resampledVolume.GetImageData().GetScalarRange()
            self.logCallback(f"  标量范围: [{scalarRange[0]:.2f}, {scalarRange[1]:.2f}]")
            
            # 步骤1.5: MRI强度归一化
            self.logCallback("\n[步骤1.5] MRI强度归一化...")
            self.normalizeMRI(resampledVolume, lowerPercentile=1.0, upperPercentile=99.0)
            
            # 步骤2: 处理原始MRI
            movingVolume = None
            if replaceOriginal:
                self.logCallback("\n[步骤2] 用重采样后的数据替换原始MRI...")
                success = self.replaceVolumeData(mriVolume, resampledVolume)
                if success:
                    movingVolume = mriVolume
                    self.logCallback(f"✓ 原始MRI已更新: {mriVolume.GetName()}")
                else:
                    self.logCallback("✗ 替换失败，使用重采样后的体数据作为Moving Volume")
                    resampledVolume.SetName(f"{baseName}_Moving")
                    movingVolume = resampledVolume
            else:
                # 重命名重采样后的体数据作为Moving Volume
                resampledVolume.SetName(f"{baseName}_Moving")
                movingVolume = resampledVolume
            
            # 清理临时节点（只在成功替换后删除）
            if replaceOriginal and resampledVolume and resampledVolume.GetID() != movingVolume.GetID():
                self.logCallback(f"\n清理临时节点: {resampledVolume.GetName()}")
                slicer.mrmlScene.RemoveNode(resampledVolume)
            
            self.logCallback("\n" + "=" * 50)
            self.logCallback("MRI预处理完成!")
            if movingVolume:
                info = self.getVolumeInfo(movingVolume)
                self.logCallback(f"Moving Volume: {info['name']}")
                self.logCallback(f"  尺寸: {info['dimensions']}")
                self.logCallback(f"  间距: {info['spacing']}")
                self.logCallback(f"  原点: {info['origin']}")
            self.logCallback("=" * 50)
            
            return movingVolume
            
        except Exception as e:
            self.logCallback(f"MRI预处理失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return None

    def savePreprocessingResults(self, roiNode, templateVolume, fixedVolume, movingVolume,
                                  mainFolderName, moduleFolderName):
        """
        保存预处理结果到场景文件夹
        
        :param roiNode: ROI节点
        :param templateVolume: 模板体数据节点
        :param fixedVolume: 固定图像节点（预处理后的CBCT）
        :param movingVolume: 浮动图像节点（预处理后的MRI）
        :param mainFolderName: 主文件夹名称
        :param moduleFolderName: 模块子文件夹名称
        :return: 成功状态
        """
        try:
            # 获取 Subject Hierarchy 节点
            shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
            sceneItemID = shNode.GetSceneItemID()
            
            # 检查总文件夹是否已存在
            mainFolderItemID = shNode.GetItemChildWithName(sceneItemID, mainFolderName)
            
            if mainFolderItemID == 0:
                mainFolderItemID = shNode.CreateFolderItem(sceneItemID, mainFolderName)
                self.logCallback(f"✓ 创建总文件夹: {mainFolderName}")
            else:
                self.logCallback(f"✓ 使用已有总文件夹: {mainFolderName}")
            
            # 创建模块子文件夹
            moduleFolderItemID = shNode.CreateFolderItem(mainFolderItemID, moduleFolderName)
            self.logCallback(f"✓ 创建模块子文件夹: {moduleFolderName}")
            
            # 保存ROI节点
            if roiNode:
                roiItemID = shNode.GetItemByDataNode(roiNode)
                if roiItemID:
                    shNode.SetItemParent(roiItemID, moduleFolderItemID)
                    self.logCallback(f"✓ ROI已保存: {roiNode.GetName()}")
                    
                    # 取消ROI显示
                    roiNode.SetDisplayVisibility(0)
                    self.logCallback(f"✓ ROI已隐藏")
            
            # 保存Template Volume
            if templateVolume:
                templateItemID = shNode.GetItemByDataNode(templateVolume)
                if templateItemID:
                    shNode.SetItemParent(templateItemID, moduleFolderItemID)
                    self.logCallback(f"✓ Template已保存: {templateVolume.GetName()}")
            
            # 设置Slice视图的前景和背景
            if fixedVolume and movingVolume:
                self._setSliceCompositeNodes(fixedVolume, movingVolume)
                self.logCallback(f"✓ Slice视图已设置: 背景=固定图像(CBCT), 前景=浮动图像(MRI)")
            
            self.logCallback(f"✓ 预处理结果保存完成")
            return True
            
        except Exception as e:
            self.logCallback(f"保存预处理结果失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return False
    
    def _setSliceCompositeNodes(self, backgroundVolume, foregroundVolume):
        """
        设置所有Slice视图的前景和背景
        
        :param backgroundVolume: 背景体数据节点
        :param foregroundVolume: 前景体数据节点
        """
        try:
            # 获取所有Slice视图的CompositeNode
            layoutManager = slicer.app.layoutManager()
            if not layoutManager:
                return
            
            sliceViewNames = layoutManager.sliceViewNames()
            for sliceViewName in sliceViewNames:
                compositeNode = layoutManager.sliceWidget(sliceViewName).mrmlSliceCompositeNode()
                if compositeNode:
                    compositeNode.SetBackgroundVolumeID(backgroundVolume.GetID())
                    compositeNode.SetForegroundVolumeID(foregroundVolume.GetID())
                    compositeNode.SetForegroundOpacity(0.5)  # 设置前景透明度为50%
            
            # 刷新显示
            slicer.app.processEvents()
            
        except Exception as e:
            self.logCallback(f"设置Slice视图失败: {str(e)}")

    def preprocessVolume(self, volumeNode):
        """
        预处理体数据（兼容旧接口，显示信息）
        
        :param volumeNode: 待预处理的体数据节点
        :return: 预处理结果
        """
        try:
            if not volumeNode:
                raise ValueError("体数据节点不能为空")
            
            self.logCallback(f"开始预处理: {volumeNode.GetName()}")
            info = self.getVolumeInfo(volumeNode)
            self.logCallback(f"  尺寸: {info['dimensions']}")
            self.logCallback(f"  间距: {info['spacing']}")
            self.logCallback(f"  原点: {info['origin']}")
            
            self.logCallback("预处理完成")
            return True
            
        except Exception as e:
            self.logCallback(f"预处理失败: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
            return False
