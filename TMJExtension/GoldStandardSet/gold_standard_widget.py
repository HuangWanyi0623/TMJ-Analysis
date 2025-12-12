"""
Gold Standard Widget - 金标准设置模块的UI界面
"""
import qt
import ctk
import slicer
import vtk
from .gold_standard_logic import GoldStandardLogic


class GoldStandardWidget:
    """
    Gold Standard Set 的UI组件类
    负责手动配准、标注点管理和金标准保存的界面
    """

    def __init__(self, parent, logCallback, getMainFolderNameCallback):
        """
        初始化 Gold Standard Widget
        
        :param parent: 父布局
        :param logCallback: 日志回调函数
        :param getMainFolderNameCallback: 获取主文件夹名称的回调函数
        """
        self.parent = parent
        self.logCallback = logCallback
        self.getMainFolderNameCallback = getMainFolderNameCallback
        self.logic = GoldStandardLogic(logCallback=logCallback)
        
        # UI 组件引用
        self.gsFixedVolumeSelector = None
        self.gsMovingVolumeSelector = None
        self.transformSelector = None
        self.fixedFiducialsSelector = None
        self.movingFiducialsSelector = None
        self.gsModuleFolderNameEdit = None
        self.gsStatusLabel = None
        self.pointPairsTable = None
        self.placePairButton = None
        self.pointAddedObserver = None
        
        # 变换控制滑块
        self.translateXSlider = None
        self.translateYSlider = None
        self.translateZSlider = None
        self.rotateXSlider = None
        self.rotateYSlider = None
        self.rotateZSlider = None
        self.uniformScaleSlider = None
        self.resetTransformButton = None
        
        self.setupUI()

    def setupUI(self):
        """设置 Gold Standard Set 的UI界面"""
        # Gold Standard Set 模块
        goldStandardCollapsibleButton = ctk.ctkCollapsibleButton()
        goldStandardCollapsibleButton.text = "Gold Standard Set"
        goldStandardCollapsibleButton.collapsed = True  # 默认折叠
        self.parent.addWidget(goldStandardCollapsibleButton)
        goldStandardFormLayout = qt.QFormLayout(goldStandardCollapsibleButton)

        # 从场景中选择数据
        selectLabel = qt.QLabel("选择需要配准的数据，一般为Data Manage创建的Fixed_Volume和Moving_Volume:")
        selectLabel.setStyleSheet("font-weight: bold;")
        goldStandardFormLayout.addRow(selectLabel)

        # Fixed Volume 选择器
        self.gsFixedVolumeSelector = slicer.qMRMLNodeComboBox()
        self.gsFixedVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.gsFixedVolumeSelector.selectNodeUponCreation = False
        self.gsFixedVolumeSelector.addEnabled = False
        self.gsFixedVolumeSelector.removeEnabled = False
        self.gsFixedVolumeSelector.noneEnabled = True
        self.gsFixedVolumeSelector.showHidden = False
        self.gsFixedVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.gsFixedVolumeSelector.setToolTip("选择 Fixed Volume(CBCT)")
        goldStandardFormLayout.addRow("Fixed Volume(CBCT): ", self.gsFixedVolumeSelector)

        # Moving Volume 选择器
        self.gsMovingVolumeSelector = slicer.qMRMLNodeComboBox()
        self.gsMovingVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.gsMovingVolumeSelector.selectNodeUponCreation = False
        self.gsMovingVolumeSelector.addEnabled = False
        self.gsMovingVolumeSelector.removeEnabled = False
        self.gsMovingVolumeSelector.noneEnabled = True
        self.gsMovingVolumeSelector.showHidden = False
        self.gsMovingVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.gsMovingVolumeSelector.setToolTip("选择 Moving Volume (MRI)")
        goldStandardFormLayout.addRow("Moving Volume(MRI): ", self.gsMovingVolumeSelector)

        # 手动配准控制
        transformLabel = qt.QLabel("手动配准(请提前使用Volume Rendering体渲染模块将Fixed Volume与Moving Volume渲染成三维图像):")
        transformLabel.setStyleSheet("font-weight: bold; margin-top: 2px;")
        goldStandardFormLayout.addRow(transformLabel)

        # Transform 选择器
        self.transformSelector = slicer.qMRMLNodeComboBox()
        self.transformSelector.nodeTypes = ["vtkMRMLLinearTransformNode"]
        self.transformSelector.selectNodeUponCreation = True
        self.transformSelector.addEnabled = True
        self.transformSelector.removeEnabled = True
        self.transformSelector.noneEnabled = False
        self.transformSelector.showHidden = False
        self.transformSelector.setMRMLScene(slicer.mrmlScene)
        self.transformSelector.setToolTip("选择或创建用于手动配准的空间变换（相似变换）")
        self.transformSelector.baseName = "ManualSimilarityTransform"
        goldStandardFormLayout.addRow("变换节点: ", self.transformSelector)

        transformButtonsLayout = qt.QHBoxLayout()
        self.applyTransformButton = qt.QPushButton("应用变换到浮动图像")
        self.applyTransformButton.toolTip = "将变换应用到Moving Volume，可进行交互式调整"
        self.applyTransformButton.connect('clicked(bool)', self.onApplyTransform)
        transformButtonsLayout.addWidget(self.applyTransformButton)

        self.openTransformsButton = qt.QPushButton("打开 Transforms 模块")
        self.openTransformsButton.toolTip = "打开 Slicer 的 Transforms 模块进行详细调整"
        self.openTransformsButton.connect('clicked(bool)', self.onOpenTransforms)
        transformButtonsLayout.addWidget(self.openTransformsButton)
        goldStandardFormLayout.addRow(transformButtonsLayout)
        
        # 快捷变换控制（相似变换：平移 + 旋转 + 缩放）
        quickTransformLabel = qt.QLabel("快捷变换控制:")
        quickTransformLabel.setStyleSheet("font-style: oblique; color: gray; margin-top: 2px; font-size: 15px;")
        goldStandardFormLayout.addRow(quickTransformLabel)
        
        # 平移控制
        translationGroup = qt.QGroupBox("平移 (Translation)")
        translationLayout = qt.QFormLayout(translationGroup)
        
        self.translateXSlider = ctk.ctkSliderWidget()
        self.translateXSlider.minimum = -200
        self.translateXSlider.maximum = 200
        self.translateXSlider.value = 0
        self.translateXSlider.singleStep = 0.1
        self.translateXSlider.suffix = " mm"
        self.translateXSlider.connect('valueChanged(double)', lambda v: self.onTransformChanged())
        translationLayout.addRow("X:", self.translateXSlider)
        
        self.translateYSlider = ctk.ctkSliderWidget()
        self.translateYSlider.minimum = -200
        self.translateYSlider.maximum = 200
        self.translateYSlider.value = 0
        self.translateYSlider.singleStep = 0.1
        self.translateYSlider.suffix = " mm"
        self.translateYSlider.connect('valueChanged(double)', lambda v: self.onTransformChanged())
        translationLayout.addRow("Y:", self.translateYSlider)
        
        self.translateZSlider = ctk.ctkSliderWidget()
        self.translateZSlider.minimum = -200
        self.translateZSlider.maximum = 200
        self.translateZSlider.value = 0
        self.translateZSlider.singleStep = 0.1
        self.translateZSlider.suffix = " mm"
        self.translateZSlider.connect('valueChanged(double)', lambda v: self.onTransformChanged())
        translationLayout.addRow("Z:", self.translateZSlider)
        
        goldStandardFormLayout.addRow(translationGroup)
        
        # 旋转控制
        rotationGroup = qt.QGroupBox("旋转 (Rotation)")
        rotationLayout = qt.QFormLayout(rotationGroup)
        
        self.rotateXSlider = ctk.ctkSliderWidget()
        self.rotateXSlider.minimum = -180
        self.rotateXSlider.maximum = 180
        self.rotateXSlider.value = 0
        self.rotateXSlider.singleStep = 0.5
        self.rotateXSlider.suffix = " °"
        self.rotateXSlider.connect('valueChanged(double)', lambda v: self.onTransformChanged())
        rotationLayout.addRow("X:", self.rotateXSlider)
        
        self.rotateYSlider = ctk.ctkSliderWidget()
        self.rotateYSlider.minimum = -180
        self.rotateYSlider.maximum = 180
        self.rotateYSlider.value = 0
        self.rotateYSlider.singleStep = 0.5
        self.rotateYSlider.suffix = " °"
        self.rotateYSlider.connect('valueChanged(double)', lambda v: self.onTransformChanged())
        rotationLayout.addRow("Y:", self.rotateYSlider)
        
        self.rotateZSlider = ctk.ctkSliderWidget()
        self.rotateZSlider.minimum = -180
        self.rotateZSlider.maximum = 180
        self.rotateZSlider.value = 0
        self.rotateZSlider.singleStep = 0.5
        self.rotateZSlider.suffix = " °"
        self.rotateZSlider.connect('valueChanged(double)', lambda v: self.onTransformChanged())
        rotationLayout.addRow("Z:", self.rotateZSlider)
        
        goldStandardFormLayout.addRow(rotationGroup)
        
        # 缩放控制（相似变换 - 只有统一缩放）
        scaleGroup = qt.QGroupBox("缩放 (Scale)")
        scaleLayout = qt.QFormLayout(scaleGroup)
        
        self.uniformScaleSlider = ctk.ctkSliderWidget()
        self.uniformScaleSlider.minimum = 0.5
        self.uniformScaleSlider.maximum = 2.0
        self.uniformScaleSlider.value = 1.0
        self.uniformScaleSlider.singleStep = 0.01
        self.uniformScaleSlider.decimals = 3
        self.uniformScaleSlider.suffix = "x"
        self.uniformScaleSlider.setToolTip("统一缩放所有方向，保持形状比例不变")
        self.uniformScaleSlider.connect('valueChanged(double)', lambda v: self.onTransformChanged())
        scaleLayout.addRow("统一缩放:", self.uniformScaleSlider)
        
        goldStandardFormLayout.addRow(scaleGroup)
        
        # 变换控制按钮
        transformControlLayout = qt.QHBoxLayout()
        
        self.resetTransformButton = qt.QPushButton("重置变换")
        self.resetTransformButton.toolTip = "将所有变换参数重置为初始值"
        self.resetTransformButton.connect('clicked(bool)', self.onResetTransform)
        transformControlLayout.addWidget(self.resetTransformButton)
        
        goldStandardFormLayout.addRow(transformControlLayout)

        # Fiducials 点对管理
        fiducialsLabel = qt.QLabel("标注点对管理:")
        fiducialsLabel.setStyleSheet("font-weight: bold; margin-top: 2px;")
        goldStandardFormLayout.addRow(fiducialsLabel)

        # Fixed Fiducials
        self.fixedFiducialsSelector = slicer.qMRMLNodeComboBox()
        self.fixedFiducialsSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.fixedFiducialsSelector.selectNodeUponCreation = True
        self.fixedFiducialsSelector.addEnabled = True
        self.fixedFiducialsSelector.removeEnabled = True
        self.fixedFiducialsSelector.noneEnabled = False
        self.fixedFiducialsSelector.showHidden = False
        self.fixedFiducialsSelector.setMRMLScene(slicer.mrmlScene)
        self.fixedFiducialsSelector.setToolTip("Fixed Volume 上的标注点")
        self.fixedFiducialsSelector.baseName = "Fixed_Fiducials"
        goldStandardFormLayout.addRow("Fixed 标注点: ", self.fixedFiducialsSelector)

        # Moving Fiducials
        self.movingFiducialsSelector = slicer.qMRMLNodeComboBox()
        self.movingFiducialsSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.movingFiducialsSelector.selectNodeUponCreation = True
        self.movingFiducialsSelector.addEnabled = True
        self.movingFiducialsSelector.removeEnabled = True
        self.movingFiducialsSelector.noneEnabled = False
        self.movingFiducialsSelector.showHidden = False
        self.movingFiducialsSelector.setMRMLScene(slicer.mrmlScene)
        self.movingFiducialsSelector.setToolTip("Moving Volume 上的标注点")
        self.movingFiducialsSelector.baseName = "Moving_Fiducials"
        goldStandardFormLayout.addRow("Moving 标注点: ", self.movingFiducialsSelector)

        # 点对操作按钮
        fiducialButtonsLayout = qt.QHBoxLayout()
        
        self.placePairButton = qt.QPushButton("放置点对")
        self.placePairButton.toolTip = "在同一位置同时创建 Fixed 和 Moving 标注点对"
        self.placePairButton.checkable = True
        self.placePairButton.connect('toggled(bool)', self.onPlacePair)
        fiducialButtonsLayout.addWidget(self.placePairButton)

        self.clearPointsButton = qt.QPushButton("清除所有点")
        self.clearPointsButton.toolTip = "清除所有标注点"
        self.clearPointsButton.connect('clicked(bool)', self.onClearPoints)
        fiducialButtonsLayout.addWidget(self.clearPointsButton)

        goldStandardFormLayout.addRow(fiducialButtonsLayout)

        # 点对列表显示
        self.pointPairsTable = qt.QTableWidget()
        self.pointPairsTable.setColumnCount(2)
        self.pointPairsTable.setHorizontalHeaderLabels(["Fixed上点数", "Moving上点数"])
        self.pointPairsTable.setMaximumHeight(80)
        # 设置列宽自适应,让边框显示完整
        self.pointPairsTable.horizontalHeader().setStretchLastSection(True)
        self.pointPairsTable.setColumnWidth(0, 120)  # Fixed 点数列宽度
        goldStandardFormLayout.addRow("点对数量:", self.pointPairsTable)

        # 保存金标准
        saveLabel = qt.QLabel("保存金标准:")
        saveLabel.setStyleSheet("font-weight: bold; margin-top: 2px;")
        goldStandardFormLayout.addRow(saveLabel)

        # Gold Standard 子文件夹名称
        self.gsModuleFolderNameEdit = qt.QLineEdit()
        self.gsModuleFolderNameEdit.text = "Gold Standard Set"
        self.gsModuleFolderNameEdit.setToolTip("Gold Standard 模块在总场景文件夹下的子文件夹名称")
        goldStandardFormLayout.addRow("Gold Standard Set场景子文件夹: ", self.gsModuleFolderNameEdit)

        self.saveGoldStandardButton = qt.QPushButton("保存金标准到场景")
        self.saveGoldStandardButton.toolTip = "将配准后的金标准体积、变换矩阵和标注点保存到场景文件夹"
        self.saveGoldStandardButton.connect('clicked(bool)', self.onSaveGoldStandard)
        goldStandardFormLayout.addRow(self.saveGoldStandardButton)

        # Gold Standard 状态
        self.gsStatusLabel = qt.QLabel("状态: 等待选择数据")
        self.gsStatusLabel.setStyleSheet("color: gray;")
        goldStandardFormLayout.addRow(self.gsStatusLabel)
        
        # 初始化时禁用变换控制
        self.enableTransformControls(False)

        # 添加模块末尾分隔线（黑色粗线）
        separator2 = qt.QFrame()
        separator2.setFrameShape(qt.QFrame.HLine)
        separator2.setFrameShadow(qt.QFrame.Plain)
        separator2.setLineWidth(2)
        separator2.setMidLineWidth(0)
        separator2.setStyleSheet("QFrame { background-color: #000000; max-height: 2px; margin: 15px 0px; }")
        goldStandardFormLayout.addRow(separator2)

    def onApplyTransform(self):
        """将变换应用到 Moving Volume"""
        try:
            movingNode = self.gsMovingVolumeSelector.currentNode()
            transformNode = self.transformSelector.currentNode()

            if not movingNode:
                self.showError("请选择 Moving Volume")
                return

            if not transformNode:
                # 自动创建 Linear Transform（相似变换）
                transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", "ManualSimilarityTransform")
                self.transformSelector.setCurrentNode(transformNode)
                self.logCallback("✓ 已创建相似变换节点")

            # 应用变换
            movingNode.SetAndObserveTransformNodeID(transformNode.GetID())
            
            # 启用快捷控制
            self.enableTransformControls(True)
            
            self.logCallback(f"✓ 变换已应用到 Moving Volume: {movingNode.GetName()}")
            self.logCallback("提示: 使用下方滑块进行平移、旋转和统一缩放调整（相似变换）")
            self.gsStatusLabel.text = "状态: 变换已应用，可使用快捷控制调整"
            self.gsStatusLabel.setStyleSheet("color: green;")

        except Exception as e:
            self.showError(f"应用变换失败: {str(e)}")
    
    def enableTransformControls(self, enabled):
        """启用/禁用变换控制滑块"""
        self.translateXSlider.enabled = enabled
        self.translateYSlider.enabled = enabled
        self.translateZSlider.enabled = enabled
        self.rotateXSlider.enabled = enabled
        self.rotateYSlider.enabled = enabled
        self.rotateZSlider.enabled = enabled
        self.uniformScaleSlider.enabled = enabled
        self.resetTransformButton.enabled = enabled
    
    def onTransformChanged(self):
        """当变换参数改变时更新变换矩阵（相似变换）"""
        try:
            transformNode = self.transformSelector.currentNode()
            if not transformNode:
                return
            
            # 获取当前参数
            tx = self.translateXSlider.value
            ty = self.translateYSlider.value
            tz = self.translateZSlider.value
            
            rx = self.rotateXSlider.value
            ry = self.rotateYSlider.value
            rz = self.rotateZSlider.value
            
            # 相似变换：统一缩放
            scale = self.uniformScaleSlider.value
            
            # 构建变换矩阵: T * Rz * Ry * Rx * S
            # 1. 统一缩放矩阵（相似变换的特征）
            scaleMatrix = vtk.vtkMatrix4x4()
            scaleMatrix.Identity()
            scaleMatrix.SetElement(0, 0, scale)
            scaleMatrix.SetElement(1, 1, scale)
            scaleMatrix.SetElement(2, 2, scale)
            
            # 2. 旋转矩阵 (使用欧拉角，顺序: X -> Y -> Z)
            transform = vtk.vtkTransform()
            transform.PostMultiply()
            transform.RotateX(rx)
            transform.RotateY(ry)
            transform.RotateZ(rz)
            rotationMatrix = transform.GetMatrix()
            
            # 3. 组合缩放和旋转
            combinedMatrix = vtk.vtkMatrix4x4()
            vtk.vtkMatrix4x4.Multiply4x4(rotationMatrix, scaleMatrix, combinedMatrix)
            
            # 4. 添加平移
            combinedMatrix.SetElement(0, 3, tx)
            combinedMatrix.SetElement(1, 3, ty)
            combinedMatrix.SetElement(2, 3, tz)
            
            # 应用变换矩阵
            transformNode.SetMatrixTransformToParent(combinedMatrix)
            
        except Exception as e:
            self.logCallback(f"更新变换失败: {str(e)}")
    
    def onResetTransform(self):
        """重置所有变换参数"""
        try:
            # 断开信号
            self.translateXSlider.blockSignals(True)
            self.translateYSlider.blockSignals(True)
            self.translateZSlider.blockSignals(True)
            self.rotateXSlider.blockSignals(True)
            self.rotateYSlider.blockSignals(True)
            self.rotateZSlider.blockSignals(True)
            self.uniformScaleSlider.blockSignals(True)
            
            # 重置值
            self.translateXSlider.value = 0
            self.translateYSlider.value = 0
            self.translateZSlider.value = 0
            self.rotateXSlider.value = 0
            self.rotateYSlider.value = 0
            self.rotateZSlider.value = 0
            self.uniformScaleSlider.value = 1.0
            
            # 恢复信号
            self.translateXSlider.blockSignals(False)
            self.translateYSlider.blockSignals(False)
            self.translateZSlider.blockSignals(False)
            self.rotateXSlider.blockSignals(False)
            self.rotateYSlider.blockSignals(False)
            self.rotateZSlider.blockSignals(False)
            self.uniformScaleSlider.blockSignals(False)
            
            # 更新变换（恢复到单位矩阵）
            self.onTransformChanged()
            
            self.logCallback("✓ 变换参数已重置")
            
        except Exception as e:
            self.showError(f"重置变换失败: {str(e)}")

    def onOpenTransforms(self):
        """打开 Transforms 模块进行交互式手动配准"""
        try:
            slicer.util.selectModule("Transforms")
            
            # 如果有选中的变换节点,自动选中它
            transformNode = self.transformSelector.currentNode()
            if transformNode:
                # 设置 Transforms 模块的当前变换节点
                transformsWidget = slicer.modules.transforms.widgetRepresentation()
                if transformsWidget:
                    transformSelector = transformsWidget.findChild(slicer.qMRMLNodeComboBox, "TransformNodeSelector")
                    if transformSelector:
                        transformSelector.setCurrentNode(transformNode)
            
            self.logCallback("✓ 已打开 Transforms 模块")
            self.logCallback("提示: 使用 Translation/Rotation sliders 来交互式调整 Moving Volume 位置")
        except Exception as e:
            self.showError(f"打开 Transforms 模块失败: {str(e)}")

    def onPlacePair(self, checked):
        """同步放置点对 - 在同一位置同时创建 Fixed 和 Moving 标注点"""
        try:
            if checked:
                # 确保 Fixed 和 Moving 标注点节点存在
                fixedFiducials = self.fixedFiducialsSelector.currentNode()
                if not fixedFiducials:
                    fixedFiducials = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "Fixed_Fiducials")
                    self.fixedFiducialsSelector.setCurrentNode(fixedFiducials)
                    # 设置 Fixed 标注点的显示属性（红色）
                    displayNode = fixedFiducials.GetDisplayNode()
                    if displayNode:
                        displayNode.SetSelectedColor(1.0, 0.0, 0.0)  # 红色
                        displayNode.SetGlyphScale(2.0)  # 稍大一点
                        displayNode.SetTextScale(2.0)
                
                movingFiducials = self.movingFiducialsSelector.currentNode()
                if not movingFiducials:
                    movingFiducials = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "Moving_Fiducials")
                    self.movingFiducialsSelector.setCurrentNode(movingFiducials)
                    # 设置 Moving 标注点的显示属性（绿色）
                    displayNode = movingFiducials.GetDisplayNode()
                    if displayNode:
                        displayNode.SetSelectedColor(0.0, 1.0, 0.0)  # 绿色
                        displayNode.SetGlyphScale(2.0)  # 稍大一点
                        displayNode.SetTextScale(2.0)
                
                # 如果标注点节点已存在，也设置颜色
                fixedDisplayNode = fixedFiducials.GetDisplayNode()
                if fixedDisplayNode:
                    fixedDisplayNode.SetSelectedColor(1.0, 0.0, 0.0)  # 红色
                    fixedDisplayNode.SetGlyphScale(2.0)
                    fixedDisplayNode.SetTextScale(2.0)
                
                movingDisplayNode = movingFiducials.GetDisplayNode()
                if movingDisplayNode:
                    movingDisplayNode.SetSelectedColor(0.0, 1.0, 0.0)  # 绿色
                    movingDisplayNode.SetGlyphScale(2.0)
                    movingDisplayNode.SetTextScale(2.0)
                
                # 设置为持续放置模式（可以连续放置多个点）
                interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
                interactionNode.SetPlaceModePersistence(1)  # 持续放置模式
                
                # 激活 Fixed 标注点的放置模式
                selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
                selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
                selectionNode.SetActivePlaceNodeID(fixedFiducials.GetID())
                interactionNode.SetCurrentInteractionMode(interactionNode.Place)
                
                # 添加观察者,监听 Fixed 标注点的添加事件
                self.pointAddedObserver = fixedFiducials.AddObserver(
                    slicer.vtkMRMLMarkupsNode.PointPositionDefinedEvent,
                    lambda caller, event: self.onFixedPointAdded(caller)
                )
                
                self.logCallback("✓ 点对放置模式已激活 (持续放置)")
                self.logCallback("提示: Fixed 点显示为红色，Moving 点显示为绿色")
                self.logCallback("提示: 可连续点击放置多个点对，完成后点击按钮退出")
                self.gsStatusLabel.text = "状态: 正在放置点对 (持续模式)"
                self.gsStatusLabel.setStyleSheet("color: blue;")
            else:
                # 取消放置模式
                interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
                interactionNode.SetPlaceModePersistence(0)  # 恢复默认
                interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
                
                # 移除观察者
                fixedFiducials = self.fixedFiducialsSelector.currentNode()
                if fixedFiducials and hasattr(self, 'pointAddedObserver'):
                    fixedFiducials.RemoveObserver(self.pointAddedObserver)
                    del self.pointAddedObserver
                
                self.logCallback("✓ 点对放置模式已关闭")
                self.gsStatusLabel.text = "状态: 就绪"
                self.gsStatusLabel.setStyleSheet("color: gray;")
            
            self.updatePointPairsTable()
            
        except Exception as e:
            self.showError(f"点对放置模式切换失败: {str(e)}")
            self.placePairButton.setChecked(False)
    
    def onFixedPointAdded(self, fixedFiducials):
        """当 Fixed 标注点添加时,在相同位置添加 Moving 标注点"""
        try:
            movingFiducials = self.movingFiducialsSelector.currentNode()
            if not movingFiducials:
                return
            
            # 获取最后添加的 Fixed 点的位置
            numPoints = fixedFiducials.GetNumberOfControlPoints()
            if numPoints > 0:
                lastIndex = numPoints - 1
                pos = [0, 0, 0]
                fixedFiducials.GetNthControlPointPosition(lastIndex, pos)
                fixedLabel = fixedFiducials.GetNthControlPointLabel(lastIndex)
                
                # 修改 Fixed 点的标签，添加 "F-" 前缀
                fixedFiducials.SetNthControlPointLabel(lastIndex, f"F-{numPoints}")
                
                # 在相同位置添加 Moving 点，使用 "M-" 前缀
                movingFiducials.AddControlPoint(pos, f"M-{numPoints}")
                
                self.logCallback(f"✓ 点对 #{numPoints} 已添加: F-{numPoints}(红) 和 M-{numPoints}(绿)")
                self.updatePointPairsTable()
                
        except Exception as e:
            self.showError(f"同步添加 Moving 点失败: {str(e)}")

    def updatePointPairsTable(self):
        """更新点对列表显示"""
        try:
            fixedFiducials = self.fixedFiducialsSelector.currentNode()
            movingFiducials = self.movingFiducialsSelector.currentNode()

            fixedCount = fixedFiducials.GetNumberOfControlPoints() if fixedFiducials else 0
            movingCount = movingFiducials.GetNumberOfControlPoints() if movingFiducials else 0

            self.pointPairsTable.setRowCount(1)
            
            fixedItem = qt.QTableWidgetItem(str(fixedCount))
            movingItem = qt.QTableWidgetItem(str(movingCount))
            
            # 如果点数不匹配,用红色标记
            if fixedCount != movingCount:
                fixedItem.setForeground(qt.QColor(255, 0, 0))
                movingItem.setForeground(qt.QColor(255, 0, 0))
            elif fixedCount > 0:
                fixedItem.setForeground(qt.QColor(0, 128, 0))
                movingItem.setForeground(qt.QColor(0, 128, 0))
            
            self.pointPairsTable.setItem(0, 0, fixedItem)
            self.pointPairsTable.setItem(0, 1, movingItem)

        except Exception as e:
            self.logCallback(f"更新点对表格失败: {str(e)}")

    def onClearPoints(self):
        """清除所有标注点"""
        try:
            reply = qt.QMessageBox.question(
                None,
                "确认清除",
                "确定要清除所有标注点吗？此操作不可撤销。",
                qt.QMessageBox.Yes | qt.QMessageBox.No
            )

            if reply == qt.QMessageBox.Yes:
                fixedFiducials = self.fixedFiducialsSelector.currentNode()
                movingFiducials = self.movingFiducialsSelector.currentNode()

                if fixedFiducials:
                    fixedFiducials.RemoveAllControlPoints()
                    self.logCallback("✓ 已清除 Fixed 标注点")

                if movingFiducials:
                    movingFiducials.RemoveAllControlPoints()
                    self.logCallback("✓ 已清除 Moving 标注点")

                self.updatePointPairsTable()

        except Exception as e:
            self.showError(f"清除标注点失败: {str(e)}")

    def onSaveGoldStandard(self):
        """保存金标准到场景"""
        try:
            # 检查必要的数据
            fixedNode = self.gsFixedVolumeSelector.currentNode()
            movingNode = self.gsMovingVolumeSelector.currentNode()
            transformNode = self.transformSelector.currentNode()
            fixedFiducials = self.fixedFiducialsSelector.currentNode()
            movingFiducials = self.movingFiducialsSelector.currentNode()

            if not fixedNode or not movingNode:
                self.showError("请选择 Fixed 和 Moving Volume")
                return

            if not transformNode:
                self.showError("请选择变换节点")
                return

            # 获取文件夹名称
            mainFolderName = self.getMainFolderNameCallback()
            moduleFolderName = self.gsModuleFolderNameEdit.text

            if not mainFolderName or not moduleFolderName:
                self.showError("请输入文件夹名称")
                return

            self.logCallback(f"正在保存金标准到场景...")
            self.logCallback(f"  总文件夹: {mainFolderName}")
            self.logCallback(f"  Gold Standard 子文件夹: {moduleFolderName}")

            # 调用 Logic 保存金标准
            success = self.logic.saveGoldStandardToScene(
                fixedNode, movingNode, transformNode,
                fixedFiducials, movingFiducials,
                mainFolderName, moduleFolderName
            )

            if success:
                self.logCallback(f"✓ 金标准已保存到场景文件夹")
                self.logCallback(f"  路径: {mainFolderName}/{moduleFolderName}")
                self.gsStatusLabel.text = "状态: 金标准已保存"
                self.gsStatusLabel.setStyleSheet("color: green;")
                
                qt.QMessageBox.information(
                    None,
                    "保存成功",
                    f"金标准已成功保存到场景文件夹:\n{mainFolderName}/{moduleFolderName}"
                )
            else:
                self.showError("保存金标准失败")

        except Exception as e:
            self.showError(f"保存金标准失败: {str(e)}")

    def showError(self, errorMessage):
        """显示错误信息"""
        self.logCallback(f"✗ 错误: {errorMessage}")
        self.gsStatusLabel.text = f"状态: 错误"
        self.gsStatusLabel.setStyleSheet("color: red;")
        slicer.util.errorDisplay(errorMessage)
        import traceback
        self.logCallback(traceback.format_exc())
