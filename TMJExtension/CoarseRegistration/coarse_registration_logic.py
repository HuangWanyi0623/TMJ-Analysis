"""
Coarse Registration Logic - 基于基准点的粗配准业务逻辑
"""
import logging
import vtk
import slicer
import numpy as np


class CoarseRegistrationLogic:
    """
    Coarse Registration 的业务逻辑类
    负责基于基准点的粗配准计算
    """

    def __init__(self, logCallback=None):
        """
        初始化 Coarse Registration Logic
        
        :param logCallback: 日志回调函数
        """
        self.logCallback = logCallback

    def log(self, message):
        """日志输出"""
        logging.info(message)
        if self.logCallback:
            self.logCallback(message)

    def computeSimilarityTransform(self, fixedFiducials, movingFiducials):
        """
        基于对应的基准点对计算相似性变换 (Similarity Transform)
        使用 VTK 的 LandmarkTransform 计算
        
        :param fixedFiducials: Fixed 标注点节点
        :param movingFiducials: Moving 标注点节点
        :return: 变换节点 (如果成功)
        """
        try:
            # 验证输入
            if not fixedFiducials or not movingFiducials:
                raise ValueError("Fixed 和 Moving 标注点都必须存在")
            
            fixedCount = fixedFiducials.GetNumberOfControlPoints()
            movingCount = movingFiducials.GetNumberOfControlPoints()
            
            if fixedCount == 0 or movingCount == 0:
                raise ValueError("标注点数量不能为0")
            
            if fixedCount != movingCount:
                raise ValueError(f"标注点数量不匹配: Fixed={fixedCount}, Moving={movingCount}")
            
            if fixedCount < 3:
                raise ValueError(f"至少需要3个点对来计算相似变换，当前只有{fixedCount}个")
            
            self.log(f"开始计算相似变换，使用{fixedCount}个点对")
            
            # 创建 VTK 点集
            fixedPoints = vtk.vtkPoints()
            movingPoints = vtk.vtkPoints()
            
            for i in range(fixedCount):
                fixedPos = [0, 0, 0]
                movingPos = [0, 0, 0]
                fixedFiducials.GetNthControlPointPosition(i, fixedPos)
                movingFiducials.GetNthControlPointPosition(i, movingPos)
                
                fixedPoints.InsertNextPoint(fixedPos)
                movingPoints.InsertNextPoint(movingPos)
                
                self.log(f"  点对 {i+1}: Fixed{fixedPos} -> Moving{movingPos}")
            
            # 使用 VTK 的 LandmarkTransform 计算相似变换
            landmarkTransform = vtk.vtkLandmarkTransform()
            landmarkTransform.SetSourceLandmarks(movingPoints)  # Moving 点
            landmarkTransform.SetTargetLandmarks(fixedPoints)   # Fixed 点
            landmarkTransform.SetModeToSimilarity()  # 相似变换模式 (平移+旋转+统一缩放)
            landmarkTransform.Update()
            
            # 获取变换矩阵
            transformMatrix = landmarkTransform.GetMatrix()
            
            # 计算变换参数用于日志
            self._logTransformParameters(transformMatrix)
            
            # 创建 MRML 变换节点
            transformNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLinearTransformNode", 
                "CoarseRegistration_Transform"
            )
            transformNode.SetMatrixTransformToParent(transformMatrix)
            
            self.log(f"✓ 相似变换计算成功")
            
            return transformNode
            
        except Exception as e:
            self.log(f"计算相似变换失败: {str(e)}")
            raise

    def _logTransformParameters(self, matrix):
        """
        解析并记录变换参数
        
        :param matrix: 4x4 变换矩阵
        """
        try:
            # 提取平移
            tx = matrix.GetElement(0, 3)
            ty = matrix.GetElement(1, 3)
            tz = matrix.GetElement(2, 3)
            
            # 提取旋转矩阵部分 (3x3)
            R = np.zeros((3, 3))
            for i in range(3):
                for j in range(3):
                    R[i, j] = matrix.GetElement(i, j)
            
            # 计算统一缩放因子 (相似变换)
            scale = np.linalg.norm(R[0, :])  # 第一行的模长
            
            # 归一化旋转矩阵
            R_normalized = R / scale
            
            # 从旋转矩阵计算欧拉角 (XYZ顺序)
            # 注意：这只是近似，对于一般的旋转矩阵可能不精确
            sy = np.sqrt(R_normalized[0, 0]**2 + R_normalized[1, 0]**2)
            
            if sy > 1e-6:
                rx = np.arctan2(R_normalized[2, 1], R_normalized[2, 2])
                ry = np.arctan2(-R_normalized[2, 0], sy)
                rz = np.arctan2(R_normalized[1, 0], R_normalized[0, 0])
            else:
                rx = np.arctan2(-R_normalized[1, 2], R_normalized[1, 1])
                ry = np.arctan2(-R_normalized[2, 0], sy)
                rz = 0
            
            # 转换为角度
            rx_deg = np.degrees(rx)
            ry_deg = np.degrees(ry)
            rz_deg = np.degrees(rz)
            
            self.log("--- 变换参数 ---")
            self.log(f"  平移: X={tx:.2f} mm, Y={ty:.2f} mm, Z={tz:.2f} mm")
            self.log(f"  旋转: X={rx_deg:.2f}°, Y={ry_deg:.2f}°, Z={rz_deg:.2f}°")
            self.log(f"  统一缩放: {scale:.4f}")
            
        except Exception as e:
            self.log(f"解析变换参数时出错: {str(e)}")

    def _computeRegistrationError(self, fixedPoints, movingPoints, transformMatrix):
        """
        计算配准后的 RMS 误差
        
        :param fixedPoints: Fixed 点集
        :param movingPoints: Moving 点集
        :param transformMatrix: 变换矩阵
        :return: RMS 误差 (mm)
        """
        try:
            numPoints = fixedPoints.GetNumberOfPoints()
            squaredErrors = []
            
            for i in range(numPoints):
                # 获取 Moving 点
                movingPos = movingPoints.GetPoint(i)
                movingPos4 = [movingPos[0], movingPos[1], movingPos[2], 1.0]
                
                # 应用变换
                transformedPos = transformMatrix.MultiplyPoint(movingPos4)
                
                # 获取 Fixed 点
                fixedPos = fixedPoints.GetPoint(i)
                
                # 计算欧氏距离的平方
                dx = transformedPos[0] - fixedPos[0]
                dy = transformedPos[1] - fixedPos[1]
                dz = transformedPos[2] - fixedPos[2]
                squaredError = dx*dx + dy*dy + dz*dz
                
                squaredErrors.append(squaredError)
            
            # 计算 RMS
            rms = np.sqrt(np.mean(squaredErrors))
            
            return rms
            
        except Exception as e:
            self.log(f"计算配准误差时出错: {str(e)}")
            return -1.0

    def saveCoarseRegistrationToScene(self, fixedVolume, movingVolume, transformNode,
                                     fixedFiducials, movingFiducials,
                                     mainFolderName, moduleFolderName):
        """
        将粗配准结果保存到场景文件夹中
        
        :param fixedVolume: Fixed volume 节点
        :param movingVolume: Moving volume 节点
        :param transformNode: 计算得到的变换节点
        :param fixedFiducials: Fixed 标注点
        :param movingFiducials: Moving 标注点
        :param mainFolderName: 配准流程总文件夹名称
        :param moduleFolderName: 模块子文件夹名称
        :return: 成功状态
        """
        try:
            # 获取 Subject Hierarchy 节点
            shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
            sceneItemID = shNode.GetSceneItemID()
            
            # 检查总文件夹是否已存在
            mainFolderItemID = shNode.GetItemChildWithName(sceneItemID, mainFolderName)
            
            if mainFolderItemID == 0:  # 不存在，创建新的总文件夹
                mainFolderItemID = shNode.CreateFolderItem(sceneItemID, mainFolderName)
                self.log(f"✓ 创建配准流程总文件夹: {mainFolderName}")
            else:
                self.log(f"✓ 使用已存在的总文件夹: {mainFolderName}")
            
            # 在总文件夹下创建模块子文件夹
            moduleFolderItemID = shNode.CreateFolderItem(mainFolderItemID, moduleFolderName)
            self.log(f"✓ 创建模块子文件夹: {moduleFolderName}")
            
            # 1. 保存变换矩阵
            if transformNode:
                # 重命名变换节点
                transformNode.SetName("CoarseReg_Transform")
                
                # 移动到文件夹
                transformItemID = shNode.GetItemByDataNode(transformNode)
                shNode.SetItemParent(transformItemID, moduleFolderItemID)
                self.log(f"✓ 变换矩阵已保存")
            
            # 2. 创建粗配准后的 Moving Volume (深拷贝 + 应用变换)
            if movingVolume and transformNode:
                movingCopy = slicer.mrmlScene.AddNewNodeByClass(
                    movingVolume.GetClassName(), 
                    "CoarseReg_Moving"
                )
                
                # 深拷贝图像数据
                imageData = vtk.vtkImageData()
                imageData.DeepCopy(movingVolume.GetImageData())
                movingCopy.SetAndObserveImageData(imageData)
                
                # 复制几何属性
                movingCopy.SetOrigin(movingVolume.GetOrigin())
                movingCopy.SetSpacing(movingVolume.GetSpacing())
                
                # 复制方向矩阵
                directionMatrix = vtk.vtkMatrix4x4()
                movingVolume.GetIJKToRASDirectionMatrix(directionMatrix)
                movingCopy.SetIJKToRASDirectionMatrix(directionMatrix)
                
                # 应用粗配准变换
                movingCopy.SetAndObserveTransformNodeID(transformNode.GetID())
                
                # 移动到文件夹
                movingItemID = shNode.GetItemByDataNode(movingCopy)
                shNode.SetItemParent(movingItemID, moduleFolderItemID)
                
                self.log(f"✓ 粗配准后的 Moving Volume 已保存并绑定变换")
            
            # 3. 保存 Fixed Fiducials (红色)
            if fixedFiducials and fixedFiducials.GetNumberOfControlPoints() > 0:
                fixedFidCopy = self._copyFiducials(
                    fixedFiducials, 
                    "CoarseReg_Fixed_Fiducials", 
                    shNode, 
                    moduleFolderItemID
                )
                # 设置为红色
                fidDisplayNode = fixedFidCopy.GetDisplayNode()
                if fidDisplayNode:
                    fidDisplayNode.SetSelectedColor(1.0, 0.0, 0.0)  # 红色
                    fidDisplayNode.SetColor(1.0, 0.0, 0.0)
                    fidDisplayNode.SetGlyphScale(2.5)
                    fidDisplayNode.SetTextScale(2.5)
                self.log(f"✓ Fixed 标注点已保存 (红色, {fixedFiducials.GetNumberOfControlPoints()} 个点)")
            
            # 4. 保存 Moving Fiducials (绿色)
            if movingFiducials and movingFiducials.GetNumberOfControlPoints() > 0:
                movingFidCopy = self._copyFiducials(
                    movingFiducials, 
                    "CoarseReg_Moving_Fiducials", 
                    shNode, 
                    moduleFolderItemID
                )
                # 设置为绿色
                fidDisplayNode = movingFidCopy.GetDisplayNode()
                if fidDisplayNode:
                    fidDisplayNode.SetSelectedColor(0.0, 1.0, 0.0)  # 绿色
                    fidDisplayNode.SetColor(0.0, 1.0, 0.0)
                    fidDisplayNode.SetGlyphScale(2.5)
                    fidDisplayNode.SetTextScale(2.5)
                self.log(f"✓ Moving 标注点已保存 (绿色, {movingFiducials.GetNumberOfControlPoints()} 个点)")
            
            # 5. 删除原始的基准点节点
            if fixedFiducials:
                slicer.mrmlScene.RemoveNode(fixedFiducials)
                self.log(f"✓ 已删除原始 Fixed 基准点")
            
            if movingFiducials:
                slicer.mrmlScene.RemoveNode(movingFiducials)
                self.log(f"✓ 已删除原始 Moving 基准点")
            
            self.log(f"✓ 粗配准结果保存完成")
            self.log(f"  - 保存的体积: CoarseReg_Moving (已应用变换)")
            self.log(f"  - 变换关系: CoarseReg_Moving → CoarseReg_Transform")
            self.log(f"  - 标注点对: {fixedFiducials.GetNumberOfControlPoints() if fixedFiducials else 0} 对")
            
            return True
            
        except Exception as e:
            self.log(f"保存粗配准结果到场景时出错: {str(e)}")
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
        
        # 深拷贝图像数据
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

    def _copyFiducials(self, sourceFiducials, newName, shNode, folderItemID, originalNode=None):
        """
        复制标注点到新节点并放入文件夹
        
        :param sourceFiducials: 源标注点节点
        :param newName: 新标注点名称
        :param shNode: Subject Hierarchy 节点
        :param folderItemID: 文件夹项目 ID
        :param originalNode: 原始节点（用于删除）
        :return: 新创建的标注点节点
        """
        fidCopy = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", newName)
        
        # 复制所有标注点
        for i in range(sourceFiducials.GetNumberOfControlPoints()):
            pos = [0, 0, 0]
            sourceFiducials.GetNthControlPointPosition(i, pos)
            label = sourceFiducials.GetNthControlPointLabel(i)
            fidCopy.AddControlPoint(pos, label)
        
        # 复制显示属性
        sourceDisplayNode = sourceFiducials.GetDisplayNode()
        if sourceDisplayNode:
            targetDisplayNode = fidCopy.GetDisplayNode()
            if targetDisplayNode:
                color = sourceDisplayNode.GetSelectedColor()
                targetDisplayNode.SetSelectedColor(color[0], color[1], color[2])
                targetDisplayNode.SetColor(color[0], color[1], color[2])
                targetDisplayNode.SetGlyphScale(sourceDisplayNode.GetGlyphScale())
                targetDisplayNode.SetTextScale(sourceDisplayNode.GetTextScale())
        
        # 移动到文件夹
        fidItemID = shNode.GetItemByDataNode(fidCopy)
        shNode.SetItemParent(fidItemID, folderItemID)
        
        return fidCopy
