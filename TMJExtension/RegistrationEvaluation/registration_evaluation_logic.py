"""
Registration Evaluation Logic - 配准评估模块的业务逻辑
包含 TRE（目标配准误差）和 Mattes MI（互信息）计算
"""
import os
import sys
import logging
import vtk
import slicer
import numpy as np
import threading
from collections import OrderedDict


class MIEvaluationWorker(threading.Thread):
    """
    MI 评估工作线程
    在后台执行 MI 计算，避免阻塞UI
    """
    
    def __init__(self, miRegistrationLogic, fixedNode, movingNode, transformNode, fixedMaskNode):
        super(MIEvaluationWorker, self).__init__()
        self.daemon = True
        self.miRegistrationLogic = miRegistrationLogic
        self.fixedNode = fixedNode
        self.movingNode = movingNode
        self.transformNode = transformNode
        self.fixedMaskNode = fixedMaskNode
        self.miValue = None
        self.success = False
        
    def run(self):
        """线程运行函数"""
        try:
            # 调用同步的 evaluateMutualInformation
            self.miValue = self.miRegistrationLogic.evaluateMutualInformation(
                self.fixedNode, self.movingNode, self.transformNode, self.fixedMaskNode
            )
            self.success = (self.miValue is not None)
        except Exception as e:
            self.success = False
            self.miValue = None


class RegistrationEvaluationLogic:
    """
    配准评估的业务逻辑类
    负责计算 TRE（Target Registration Error）和 Mattes MI（互信息）
    """

    def __init__(self, logCallback=None):
        """
        初始化 Registration Evaluation Logic
        
        :param logCallback: 日志回调函数
        """
        self.logCallback = logCallback if logCallback else print
        
        # 动态导入 TMJRegistration 的 MIRegistrationLogic
        self.miRegistrationLogic = None
        self._miRegistrationLogicInitialized = False

    def _initMIRegistrationLogic(self):
        """初始化 TMJRegistration 的 MIRegistrationLogic"""
        if self._miRegistrationLogicInitialized:
            return
        
        self._miRegistrationLogicInitialized = True
        
        try:
            # 获取 TMJRegistration 模块路径
            import slicer
            modulePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            parentPath = os.path.dirname(modulePath)
            tmjRegPath = os.path.join(parentPath, "TMJRegistration", "MIRegistration")
            
            if tmjRegPath not in sys.path:
                sys.path.insert(0, tmjRegPath)
            
            # 导入 MIRegistrationLogic
            from mi_registration_logic import MIRegistrationLogic
            self.miRegistrationLogic = MIRegistrationLogic(logCallback=self.logCallback)
            self.log("✓ 成功加载 TMJRegistration 后端")
            
        except Exception as e:
            self.log(f"⚠ 无法加载 TMJRegistration 后端: {str(e)}")
            self.log("  MI 计算将不可用")
            self.miRegistrationLogic = None

    def log(self, message):
        """日志输出"""
        logging.info(message)
        if self.logCallback:
            try:
                self.logCallback(message)
            except:
                # 如果回调失败（例如UI还没准备好），只记录到logging
                pass

    # ========================================================================
    # TRE 计算相关
    # ========================================================================

    def computeTRE(self, fixedFiducials, movingFiducials, transformNode=None):
        """
        计算 TRE（Target Registration Error）
        
        TRE = sqrt(1/n * sum((p_fixed - T(p_moving))^2))
        
        :param fixedFiducials: 固定图像上的标注点节点
        :param movingFiducials: 浮动图像上的标注点节点
        :param transformNode: 变换节点（用于变换浮动图像上的点）
        :return: dict 包含 meanTRE, maxTRE, minTRE, stdTRE, pointTREs
        """
        try:
            if not fixedFiducials or not movingFiducials:
                raise ValueError("固定标注点或浮动标注点为空")

            numFixedPoints = fixedFiducials.GetNumberOfControlPoints()
            numMovingPoints = movingFiducials.GetNumberOfControlPoints()

            if numFixedPoints != numMovingPoints:
                raise ValueError(f"点对数量不匹配: 固定点={numFixedPoints}, 浮动点={numMovingPoints}")

            if numFixedPoints == 0:
                raise ValueError("没有标注点")

            # 获取变换矩阵
            transformMatrix = None
            if transformNode:
                transformMatrix = vtk.vtkMatrix4x4()
                transformNode.GetMatrixTransformToParent(transformMatrix)

            # 计算每个点对的 TRE
            pointTREs = []
            for i in range(numFixedPoints):
                # 获取固定点坐标
                fixedPoint = [0.0, 0.0, 0.0]
                fixedFiducials.GetNthControlPointPositionWorld(i, fixedPoint)

                # 获取浮动点坐标
                movingPoint = [0.0, 0.0, 0.0]
                movingFiducials.GetNthControlPointPositionWorld(i, movingPoint)

                # 应用变换到浮动点
                if transformMatrix:
                    movingPointHomogeneous = [movingPoint[0], movingPoint[1], movingPoint[2], 1.0]
                    transformedPoint = transformMatrix.MultiplyPoint(movingPointHomogeneous)
                    transformedMovingPoint = [transformedPoint[0], transformedPoint[1], transformedPoint[2]]
                else:
                    transformedMovingPoint = movingPoint

                # 计算欧氏距离
                distance = np.sqrt(
                    (fixedPoint[0] - transformedMovingPoint[0]) ** 2 +
                    (fixedPoint[1] - transformedMovingPoint[1]) ** 2 +
                    (fixedPoint[2] - transformedMovingPoint[2]) ** 2
                )
                pointTREs.append(distance)

            # 统计计算
            pointTREs = np.array(pointTREs)
            result = {
                'meanTRE': np.mean(pointTREs),
                'maxTRE': np.max(pointTREs),
                'minTRE': np.min(pointTREs),
                'stdTRE': np.std(pointTREs),
                'pointTREs': pointTREs.tolist(),
                'numPoints': numFixedPoints
            }

            self.log(f"TRE 计算完成:")
            self.log(f"  点对数量: {numFixedPoints}")
            self.log(f"  平均 TRE: {result['meanTRE']:.4f} mm")
            self.log(f"  最大 TRE: {result['maxTRE']:.4f} mm")
            self.log(f"  最小 TRE: {result['minTRE']:.4f} mm")
            self.log(f"  标准差: {result['stdTRE']:.4f} mm")

            return result

        except Exception as e:
            self.log(f"TRE 计算失败: {str(e)}")
            raise

    def createFiducialNode(self, name):
        """
        创建新的标注点节点
        
        :param name: 节点名称
        :return: 创建的标注点节点
        """
        try:
            fiducialNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLMarkupsFiducialNode", name)
            fiducialNode.CreateDefaultDisplayNodes()
            
            # 设置默认显示属性
            displayNode = fiducialNode.GetDisplayNode()
            if displayNode:
                displayNode.SetTextScale(3.0)
                displayNode.SetGlyphScale(2.0)
            
            self.log(f"创建标注点节点: {name}")
            return fiducialNode
            
        except Exception as e:
            self.log(f"创建标注点节点失败: {str(e)}")
            raise

    # ========================================================================
    # Mattes MI 计算相关
    # ========================================================================

    def computeMattesMI(self, fixedVolume, movingVolume, transformNode, fixedMaskNode=None):
        """
        计算 Mattes 互信息值（异步执行，避免UI卡顿）
        
        使用 TMJRegistration 后端的 evaluateMutualInformation 接口
        
        :param fixedVolume: 固定图像节点
        :param movingVolume: 浮动图像节点
        :param transformNode: 变换节点
        :param fixedMaskNode: 固定图像掩膜节点（可选）
        :return: bool 是否成功启动计算
        """
        try:
            # 延迟初始化 TMJRegistration 后端
            if not self._miRegistrationLogicInitialized:
                self._initMIRegistrationLogic()
            
            if not self.miRegistrationLogic:
                raise RuntimeError("TMJRegistration 后端未加载，无法计算 MI")
            
            # 简化日志输出
            self.log(f"开始计算 Mattes MI")
            
            # 创建工作线程
            self.miWorker = MIEvaluationWorker(
                self.miRegistrationLogic, fixedVolume, movingVolume, transformNode, fixedMaskNode
            )
            
            # 启动线程
            self.miWorker.start()
            
            # 启动定时器检查状态
            import qt
            self.miCheckTimer = qt.QTimer()
            self.miCheckTimer.timeout.connect(self._checkMIWorkerStatus)
            self.miCheckTimer.start(100)  # 每100ms检查一次
            
            return True
            
        except Exception as e:
            self.log(f"MI 计算启动失败: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            return False
    
    def _checkMIWorkerStatus(self):
        """检查 MI 工作线程状态"""
        if self.miWorker and not self.miWorker.is_alive():
            # 线程已完成
            self.miCheckTimer.stop()
            
            success = self.miWorker.success
            miValue = self.miWorker.miValue
            
            if success and miValue is not None:
                # 构造结果字典（简化输出）
                result = {
                    'MI': miValue,
                    'usedMask': self.miWorker.fixedMaskNode is not None
                }
                
                # 简化日志：只输出最终结果
                self.log(f"MI = {miValue:.6f}")
                
                if hasattr(self, '_miFinishCallback') and self._miFinishCallback:
                    self._miFinishCallback(True, result)
            else:
                self.log("❌ MI 计算失败")
                if hasattr(self, '_miFinishCallback') and self._miFinishCallback:
                    self._miFinishCallback(False, None)
    
    def setMIFinishCallback(self, callback):
        """设置 MI 完成回调"""
        self._miFinishCallback = callback

    # ========================================================================
    # 保存结果到场景
    # ========================================================================

    def saveEvaluationToScene(self, fixedVolume, movingVolume, transformNode,
                              fixedFiducials, movingFiducials,
                              treResult, miResult,
                              mainFolderName, moduleFolderName):
        """
        将评估结果保存到场景文件夹中
        
        :param fixedVolume: 固定图像节点
        :param movingVolume: 浮动图像节点
        :param transformNode: 变换节点
        :param fixedFiducials: 固定标注点节点
        :param movingFiducials: 浮动标注点节点
        :param treResult: TRE 计算结果
        :param miResult: MI 计算结果
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
                self.log(f"✓ 创建配准流程总文件夹: {mainFolderName}")
            else:
                self.log(f"✓ 使用已存在的总文件夹: {mainFolderName}")
            
            # 创建模块子文件夹
            moduleFolderItemID = shNode.CreateFolderItem(mainFolderItemID, moduleFolderName)
            self.log(f"✓ 创建模块子文件夹: {moduleFolderName}")
            
            # 保存变换节点（如果有）
            if transformNode:
                transformCopy = slicer.mrmlScene.AddNewNodeByClass(
                    "vtkMRMLLinearTransformNode", "Eval_Transform")
                transformMatrix = vtk.vtkMatrix4x4()
                transformNode.GetMatrixTransformToParent(transformMatrix)
                transformCopy.SetMatrixTransformToParent(transformMatrix)
                
                transformItemID = shNode.GetItemByDataNode(transformCopy)
                shNode.SetItemParent(transformItemID, moduleFolderItemID)
                self.log(f"✓ 变换节点已保存")
            
            # 保存固定标注点（如果有）
            if fixedFiducials and fixedFiducials.GetNumberOfControlPoints() > 0:
                fixedFidCopy = self._copyFiducials(fixedFiducials, "Eval_Fixed_Fiducials", shNode, moduleFolderItemID)
                displayNode = fixedFidCopy.GetDisplayNode()
                if displayNode:
                    displayNode.SetSelectedColor(1.0, 0.0, 0.0)  # 红色
                    displayNode.SetColor(1.0, 0.0, 0.0)
                self.log(f"✓ 固定标注点已保存 ({fixedFiducials.GetNumberOfControlPoints()} 个点)")
            
            # 保存浮动标注点（如果有）
            if movingFiducials and movingFiducials.GetNumberOfControlPoints() > 0:
                movingFidCopy = self._copyFiducials(movingFiducials, "Eval_Moving_Fiducials", shNode, moduleFolderItemID)
                displayNode = movingFidCopy.GetDisplayNode()
                if displayNode:
                    displayNode.SetSelectedColor(0.0, 1.0, 0.0)  # 绿色
                    displayNode.SetColor(0.0, 1.0, 0.0)
                self.log(f"✓ 浮动标注点已保存 ({movingFiducials.GetNumberOfControlPoints()} 个点)")
            
            # 保存评估结果到表格节点
            tableNode = self._createEvaluationTable(treResult, miResult, shNode, moduleFolderItemID)
            self.log(f"✓ 评估结果表格已保存")
            
            self.log(f"✓ 评估结果保存完成")
            return True
            
        except Exception as e:
            self.log(f"保存评估结果失败: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            raise

    def _copyFiducials(self, sourceFiducials, newName, shNode, folderItemID):
        """复制标注点节点"""
        fiducialNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLMarkupsFiducialNode", newName)
        
        for i in range(sourceFiducials.GetNumberOfControlPoints()):
            pos = [0.0, 0.0, 0.0]
            sourceFiducials.GetNthControlPointPositionWorld(i, pos)
            label = sourceFiducials.GetNthControlPointLabel(i)
            fiducialNode.AddControlPointWorld(pos[0], pos[1], pos[2], label)
        
        fiducialNode.CreateDefaultDisplayNodes()
        
        fiducialItemID = shNode.GetItemByDataNode(fiducialNode)
        shNode.SetItemParent(fiducialItemID, folderItemID)
        
        return fiducialNode

    def _createEvaluationTable(self, treResult, miResult, shNode, folderItemID):
        """创建评估结果表格"""
        tableNode = slicer.mrmlScene.AddNewNodeByClass(
            "vtkMRMLTableNode", "Evaluation_Results")
        
        table = tableNode.GetTable()
        
        # 添加列
        metricColumn = vtk.vtkStringArray()
        metricColumn.SetName("Metric")
        valueColumn = vtk.vtkStringArray()
        valueColumn.SetName("Value")
        
        # 添加 TRE 结果
        if treResult:
            metricColumn.InsertNextValue("TRE - Mean (mm)")
            valueColumn.InsertNextValue(f"{treResult['meanTRE']:.4f}")
            
            metricColumn.InsertNextValue("TRE - Max (mm)")
            valueColumn.InsertNextValue(f"{treResult['maxTRE']:.4f}")
            
            metricColumn.InsertNextValue("TRE - Min (mm)")
            valueColumn.InsertNextValue(f"{treResult['minTRE']:.4f}")
            
            metricColumn.InsertNextValue("TRE - Std (mm)")
            valueColumn.InsertNextValue(f"{treResult['stdTRE']:.4f}")
            
            metricColumn.InsertNextValue("TRE - Num Points")
            valueColumn.InsertNextValue(f"{treResult['numPoints']}")
        
        # 添加 MI 结果
        if miResult:
            metricColumn.InsertNextValue("Mattes MI")
            valueColumn.InsertNextValue(f"{miResult['MI']:.6f}")
            
            metricColumn.InsertNextValue("Mattes MI (negative)")
            valueColumn.InsertNextValue(f"{miResult['negativeMI']:.6f}")
            
            metricColumn.InsertNextValue("MI - Used Mask")
            valueColumn.InsertNextValue("Yes" if miResult.get('usedMask', False) else "No")
            
            metricColumn.InsertNextValue("MI - Method")
            valueColumn.InsertNextValue(miResult.get('method', 'Unknown'))
        
        table.AddColumn(metricColumn)
        table.AddColumn(valueColumn)
        
        tableItemID = shNode.GetItemByDataNode(tableNode)
        shNode.SetItemParent(tableItemID, folderItemID)
        
        return tableNode
