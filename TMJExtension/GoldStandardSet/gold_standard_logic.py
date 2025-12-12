"""
Gold Standard Set Logic - 金标准设置模块的业务逻辑
"""
import logging
import vtk
import slicer


class GoldStandardLogic:
    """
    Gold Standard Set 的业务逻辑类
    负责手动配准、标注点管理和金标准保存
    """

    def __init__(self, logCallback=None):
        """
        初始化 Gold Standard Logic
        
        :param logCallback: 日志回调函数
        """
        self.logCallback = logCallback

    def log(self, message):
        """日志输出"""
        logging.info(message)
        if self.logCallback:
            self.logCallback(message)

    def saveGoldStandardToScene(self, fixedVolume, movingVolume, transformNode, 
                                fixedFiducials, movingFiducials,
                                mainFolderName, moduleFolderName):
        """
        将金标准数据保存到场景文件夹中
        
        :param fixedVolume: Fixed volume 节点
        :param movingVolume: Moving volume 节点  
        :param transformNode: 变换节点
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
            
            if mainFolderItemID == 0:  # 不存在,创建新的总文件夹
                mainFolderItemID = shNode.CreateFolderItem(sceneItemID, mainFolderName)
                self.log(f"✓ 创建配准流程总文件夹: {mainFolderName}")
            else:
                self.log(f"✓ 使用已存在的总文件夹: {mainFolderName}")
            
            # 在总文件夹下创建模块子文件夹
            moduleFolderItemID = shNode.CreateFolderItem(mainFolderItemID, moduleFolderName)
            self.log(f"✓ 创建模块子文件夹: {moduleFolderName}")
            
            # 1. 保存配准后的 Fixed Volume (原始的,不需要变换)
            if fixedVolume:
                fixedCopy = self._createVolumeInFolder(fixedVolume, "GoldStandard_Fixed", shNode, moduleFolderItemID)
                self.log(f"✓ Fixed Volume 已保存")
            
            # 2. 先保存变换矩阵（因为后面要用）
            transformCopy = None
            if transformNode:
                transformCopy = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", "GoldStandard_Transform")
                
                # 复制变换矩阵
                transformMatrix = vtk.vtkMatrix4x4()
                transformNode.GetMatrixTransformToParent(transformMatrix)
                transformCopy.SetMatrixTransformToParent(transformMatrix)
                
                # 移动到文件夹
                transformItemID = shNode.GetItemByDataNode(transformCopy)
                shNode.SetItemParent(transformItemID, moduleFolderItemID)
                self.log(f"✓ 变换矩阵已保存")
            
            # 3. 保存 Moving Volume（深拷贝创建完全独立的副本）
            movingCopy = None
            if movingVolume:
                # 使用深拷贝创建独立副本
                movingCopy = slicer.mrmlScene.AddNewNodeByClass(movingVolume.GetClassName(), "GoldStandard_Moving")
                
                # 深拷贝图像数据（确保完全独立）
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
                
                # 确保新副本没有任何变换绑定
                movingCopy.SetAndObserveTransformNodeID(None)
                
                # 绑定到新的 GoldStandard_Transform
                if transformCopy:
                    movingCopy.SetAndObserveTransformNodeID(transformCopy.GetID())
                    self.log(f"✓ GoldStandard_Moving 已绑定到 GoldStandard_Transform")
                
                # 移动到文件夹
                movingItemID = shNode.GetItemByDataNode(movingCopy)
                shNode.SetItemParent(movingItemID, moduleFolderItemID)
                
                self.log(f"✓ Moving Volume 已深拷贝保存为 GoldStandard_Moving（完全独立）")
            
            # 4. 保存 Fixed Fiducials（金标准参考 - 红色）
            if fixedFiducials and fixedFiducials.GetNumberOfControlPoints() > 0:
                fixedFidCopy = self._copyFiducials(fixedFiducials, "GoldStandard_Fixed_Fiducials", shNode, moduleFolderItemID)
                # 设置为红色（金标准参考）
                fidDisplayNode = fixedFidCopy.GetDisplayNode()
                if fidDisplayNode:
                    fidDisplayNode.SetSelectedColor(1.0, 0.0, 0.0)  # 红色
                    fidDisplayNode.SetColor(1.0, 0.0, 0.0)
                self.log(f"✓ Fixed 标注点已保存为金标准参考 (红色, {fixedFiducials.GetNumberOfControlPoints()} 个点)")
            
            # 5. 保存 Moving Fiducials（金标准参考 - 绿色，应该和 Fixed 重叠）
            # 注意：这里直接复制坐标，不应用变换，因为标注点是在手动配准后的位置标的
            # 手动配准后，Moving 已经和 Fixed 对齐，所以 Moving 上的点应该和 Fixed 上的点重叠
            if movingFiducials and movingFiducials.GetNumberOfControlPoints() > 0:
                # 直接复制，不应用变换
                movingFidCopy = self._copyFiducials(movingFiducials, "GoldStandard_Moving_Fiducials", shNode, moduleFolderItemID)
                # 设置为绿色（金标准参考）
                fidDisplayNode = movingFidCopy.GetDisplayNode()
                if fidDisplayNode:
                    fidDisplayNode.SetSelectedColor(0.0, 1.0, 0.0)  # 绿色
                    fidDisplayNode.SetColor(0.0, 1.0, 0.0)
                self.log(f"✓ Moving 标注点已保存为金标准参考 (绿色, 与红色重叠, {movingFiducials.GetNumberOfControlPoints()} 个点)")
            
            # 6. 验证点对数量
            fixedCount = fixedFiducials.GetNumberOfControlPoints() if fixedFiducials else 0
            movingCount = movingFiducials.GetNumberOfControlPoints() if movingFiducials else 0
            
            if fixedCount == movingCount and fixedCount > 0:
                self.log(f"✓ 点对验证通过: {fixedCount} 对点")
            elif fixedCount == 0 and movingCount == 0:
                self.log(f"⚠ 警告: 未保存标注点")
            else:
                self.log(f"⚠ 警告: 点对数量不匹配 (Fixed: {fixedCount}, Moving: {movingCount})")
            
            # 7. 保留原始标注点，使其跟随体积移动（用于后续配准误差计算）
            self._setupOriginalFiducialsForTracking(fixedFiducials, movingFiducials, fixedVolume, movingVolume, transformCopy, mainFolderName)
            
            # 8. 只删除临时变换节点（保留标注点用于跟踪）
            self._cleanupTemporaryTransform(transformNode, movingVolume)
            
            self.log(f"✓ 金标准数据保存完成")
            self.log(f"  - 保存的体积: GoldStandard_Fixed, GoldStandard_Moving")
            self.log(f"  - 变换关系: GoldStandard_Moving → GoldStandard_Transform")
            self.log(f"  - 标注点对: {min(fixedCount, movingCount)} 对")
            
            return True
            
        except Exception as e:
            self.log(f"保存金标准到场景时出错: {str(e)}")
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

    def _copyFiducials(self, sourceFiducials, newName, shNode, folderItemID):
        """
        复制标注点到新节点并放入文件夹
        
        :param sourceFiducials: 源标注点节点
        :param newName: 新标注点名称
        :param shNode: Subject Hierarchy 节点
        :param folderItemID: 文件夹项目 ID
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
        self._copyDisplayProperties(sourceFiducials, fidCopy)
        
        # 移动到文件夹
        fidItemID = shNode.GetItemByDataNode(fidCopy)
        shNode.SetItemParent(fidItemID, folderItemID)
        
        return fidCopy

    def _copyFiducialsWithTransform(self, sourceFiducials, movingVolume, newName, shNode, folderItemID):
        """
        复制标注点并应用变换后放入文件夹
        
        :param sourceFiducials: 源标注点节点
        :param movingVolume: Moving Volume (用于获取变换)
        :param newName: 新标注点名称
        :param shNode: Subject Hierarchy 节点
        :param folderItemID: 文件夹项目 ID
        :return: 新创建的标注点节点
        """
        fidCopy = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", newName)
        
        # 复制所有标注点(应用变换)
        for i in range(sourceFiducials.GetNumberOfControlPoints()):
            pos = [0, 0, 0]
            sourceFiducials.GetNthControlPointPosition(i, pos)
            
            # 如果 Moving 有变换,应用变换
            if movingVolume and movingVolume.GetTransformNodeID():
                transformNode = slicer.mrmlScene.GetNodeByID(movingVolume.GetTransformNodeID())
                if transformNode:
                    pos4 = [pos[0], pos[1], pos[2], 1.0]
                    transformMatrix = vtk.vtkMatrix4x4()
                    transformNode.GetMatrixTransformToParent(transformMatrix)
                    transformedPos = transformMatrix.MultiplyPoint(pos4)
                    pos = [transformedPos[0], transformedPos[1], transformedPos[2]]
            
            label = sourceFiducials.GetNthControlPointLabel(i)
            fidCopy.AddControlPoint(pos, label)
        
        # 复制显示属性
        self._copyDisplayProperties(sourceFiducials, fidCopy)
        
        # 移动到文件夹
        fidItemID = shNode.GetItemByDataNode(fidCopy)
        shNode.SetItemParent(fidItemID, folderItemID)
        
        return fidCopy

    def _copyDisplayProperties(self, sourceFiducials, targetFiducials):
        """
        复制标注点的显示属性
        
        :param sourceFiducials: 源标注点节点
        :param targetFiducials: 目标标注点节点
        """
        sourceDisplayNode = sourceFiducials.GetDisplayNode()
        if sourceDisplayNode:
            targetDisplayNode = targetFiducials.GetDisplayNode()
            if targetDisplayNode:
                # 复制颜色
                color = sourceDisplayNode.GetSelectedColor()
                targetDisplayNode.SetSelectedColor(color[0], color[1], color[2])
                targetDisplayNode.SetColor(color[0], color[1], color[2])
                
                # 复制大小
                targetDisplayNode.SetGlyphScale(sourceDisplayNode.GetGlyphScale())
                targetDisplayNode.SetTextScale(sourceDisplayNode.GetTextScale())
                
                # 复制透明度
                targetDisplayNode.SetOpacity(sourceDisplayNode.GetOpacity())

    def _setupOriginalFiducialsForTracking(self, fixedFiducials, movingFiducials, fixedVolume, movingVolume, goldStandardTransform, mainFolderName):
        """
        设置原始 Moving 标注点用于跟踪配准误差
        
        关键理解:
        - 应用金标准变换的逆矩阵，使 Moving 标注点回到初始位置
        - 这样它们对应 Moving_Volume 的初始位置
        - 后续配准时，可以比较配准后的位置与金标准位置的差异
        
        :param fixedFiducials: Fixed 标注点（原始，不再需要保留，冗余）
        :param movingFiducials: Moving 标注点（原始，在手动配准时的位置）
        :param fixedVolume: Fixed Volume
        :param movingVolume: Moving Volume（原始的，将要回到初始位置）
        :param goldStandardTransform: 金标准变换节点
        :param mainFolderName: Data Manager 主文件夹名称
        """
        self.log("--- 设置原始标注点用于配准误差跟踪 ---")
        
        # Fixed 标注点是冗余的，直接删除
        if fixedFiducials:
            slicer.mrmlScene.RemoveNode(fixedFiducials)
            self.log(f"✓ 删除 Fixed 原始标注点 (冗余，与金标准重复)")
        
        if movingFiducials and goldStandardTransform:
            # 关键：应用金标准变换的逆矩阵，使点回到初始位置
            movingFiducials.SetName("Moving_Fiducials")
            
            # 获取金标准变换矩阵
            transformMatrix = vtk.vtkMatrix4x4()
            goldStandardTransform.GetMatrixTransformToParent(transformMatrix)
            
            # 计算逆矩阵
            inverseMatrix = vtk.vtkMatrix4x4()
            vtk.vtkMatrix4x4.Invert(transformMatrix, inverseMatrix)
            
            # 对每个标注点应用逆变换
            for i in range(movingFiducials.GetNumberOfControlPoints()):
                # 获取当前位置（世界坐标，配准后）
                pos = [0, 0, 0]
                movingFiducials.GetNthControlPointPosition(i, pos)
                
                # 应用逆变换：配准后位置 -> 初始位置
                pos4 = [pos[0], pos[1], pos[2], 1.0]
                newPos = inverseMatrix.MultiplyPoint(pos4)
                
                # 更新标注点位置
                movingFiducials.SetNthControlPointPosition(i, newPos[0], newPos[1], newPos[2])
            
            self.log(f"✓ Moving 标注点已应用逆变换，回到初始位置")
            
            # 修改显示属性（蓝色）
            movingDisplayNode = movingFiducials.GetDisplayNode()
            if movingDisplayNode:
                movingDisplayNode.SetSelectedColor(0.0, 0.5, 1.0)  # 蓝色
                movingDisplayNode.SetColor(0.0, 0.5, 1.0)
                movingDisplayNode.SetOpacity(0.8)
                movingDisplayNode.SetGlyphScale(1.8)
            
            # 移动到 Data Manager 文件夹下
            shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
            sceneItemID = shNode.GetSceneItemID()
            mainFolderItemID = shNode.GetItemChildWithName(sceneItemID, mainFolderName)
            
            if mainFolderItemID != 0:
                # 找到 Data Manager 子文件夹
                dataManagerFolderID = shNode.GetItemChildWithName(mainFolderItemID, "Data Manager")
                if dataManagerFolderID != 0:
                    # 移动标注点到 Data Manager 文件夹
                    fidItemID = shNode.GetItemByDataNode(movingFiducials)
                    shNode.SetItemParent(fidItemID, dataManagerFolderID)
                    self.log(f"✓ Moving_Fiducials 已移动到 Data Manager 文件夹")
                else:
                    self.log(f"⚠️ 未找到 Data Manager 文件夹，标注点保持在根目录")
            
            self.log(f"✓ 保留 Moving 标注点 (蓝色) - 已应用逆变换，位于初始位置")
        
        self.log("✓ 标注点系统设置完成:")
        self.log("  🔴 GoldStandard_Fixed (红色): 金标准参考 - 固定不动")
        self.log("  🟢 GoldStandard_Moving (绿色): 金标准参考 - 与红色重叠")
        self.log("  🔵 Moving_Fiducials (蓝色): 标注点 - 已回到初始位置，存放在 Data Manager 文件夹")
    
    def _cleanupTemporaryTransform(self, transformNode, movingVolume):
        """
        删除临时变换节点，使 Moving Volume 和 Moving Fiducials 一起回到初始位置
        
        :param transformNode: 临时变换节点（ManualRegistration_Transform）
        :param movingVolume: Moving Volume（原始的，将要回到初始位置）
        """
        self.log("--- 清理临时变换节点 ---")
        
        # 1. 解除 Moving Volume 的临时变换绑定，使其回到初始位置
        if movingVolume:
            currentTransformID = movingVolume.GetTransformNodeID()
            if currentTransformID:
                currentTransform = slicer.mrmlScene.GetNodeByID(currentTransformID)
                if currentTransform:
                    self.log(f"✓ 解除 {movingVolume.GetName()} 的变换绑定: {currentTransform.GetName()}")
            
            # 解除变换，Moving Volume 回到初始位置
            movingVolume.SetAndObserveTransformNodeID(None)
            self.log(f"✓ {movingVolume.GetName()} 已回到初始位置")
        
        # 2. 删除手动配准使用的临时变换节点
        if transformNode:
            slicer.mrmlScene.RemoveNode(transformNode)
            self.log(f"✓ 删除临时变换节点: {transformNode.GetName()}")
        
        self.log("✓ 清理完成:")
        self.log(f"  - Moving_Volume: 已回到初始位置（无变换）")
        self.log(f"  - Moving_Fiducials: 已通过逆变换回到初始位置，存放在 Data Manager 文件夹")
        self.log(f"  - 后续配准时可使用 Moving_Fiducials 计算配准误差")
