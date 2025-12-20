"""
Registration Evaluation Widget - 配准评估模块的UI界面
包含 TRE（目标配准误差）和 Mattes MI（互信息）评估
"""
import qt
import ctk
import slicer
from .registration_evaluation_logic import RegistrationEvaluationLogic


class RegistrationEvaluationWidget:
    """
    Registration Evaluation 的UI组件类
    负责配准结果评估界面
    """

    def __init__(self, parent, logCallback, getMainFolderNameCallback):
        """
        初始化 Registration Evaluation Widget
        
        :param parent: 父布局
        :param logCallback: 日志回调函数
        :param getMainFolderNameCallback: 获取主文件夹名称的回调函数
        """
        self.parent = parent
        self.logCallback = logCallback
        self.getMainFolderNameCallback = getMainFolderNameCallback
        self.logic = RegistrationEvaluationLogic(logCallback=logCallback)
        
        # UI 组件引用
        self.evalFixedVolumeSelector = None
        self.evalMovingVolumeSelector = None
        self.evalFixedMaskSelector = None
        self.evalTransformSelector = None
        self.fixedFiducialsSelector = None
        self.movingFiducialsSelector = None
        
        # TRE 相关
        self.createFixedFiducialsButton = None
        self.createMovingFiducialsButton = None
        self.computeTREButton = None
        self.treResultLabel = None
        self.treDetailTable = None
        
        # MI 相关
        self.miHistogramBinsSlider = None
        self.miSamplingSlider = None
        self.computeMIButton = None
        self.miResultLabel = None
        
        # 保存相关
        self.evalModuleFolderNameEdit = None
        self.saveEvalResultButton = None
        self.evalStatusLabel = None
        
        # 存储计算结果
        self.treResult = None
        self.miResult = None
        
        # 标注点观察者
        self.fixedObserverTag = None
        self.movingObserverTag = None
        
        # 标记点对组是否为新建（用于保存时决定是否删除原始节点）
        self.createdFixedFiducials = None
        self.createdMovingFiducials = None
        
        self.setupUI()

    def setupUI(self):
        # Registration Evaluation 模块 (容器)
        evalCollapsibleButton = ctk.ctkCollapsibleButton()
        evalCollapsibleButton.text = "Registration Evaluation"
        evalCollapsibleButton.collapsed = True
        self.parent.addWidget(evalCollapsibleButton)
        evalFormLayout = qt.QFormLayout(evalCollapsibleButton)
        # 更紧凑的整体间距
        try:
            evalFormLayout.setSpacing(6)
            evalFormLayout.setContentsMargins(6, 4, 6, 4)
        except Exception:
            pass

        # 数据选择区
        selectLabel = qt.QLabel("选择配准数据:")
        selectLabel.setStyleSheet("font-weight: bold;")
        evalFormLayout.addRow(selectLabel)

        # Fixed / Moving / Mask / Transform selectors
        self.evalFixedVolumeSelector = slicer.qMRMLNodeComboBox()
        self.evalFixedVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.evalFixedVolumeSelector.selectNodeUponCreation = False
        self.evalFixedVolumeSelector.addEnabled = False
        self.evalFixedVolumeSelector.removeEnabled = False
        self.evalFixedVolumeSelector.noneEnabled = True
        self.evalFixedVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.evalFixedVolumeSelector.setToolTip("选择固定图像 (CBCT)")
        evalFormLayout.addRow("Fixed Volume: ", self.evalFixedVolumeSelector)

        self.evalMovingVolumeSelector = slicer.qMRMLNodeComboBox()
        self.evalMovingVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.evalMovingVolumeSelector.selectNodeUponCreation = False
        self.evalMovingVolumeSelector.addEnabled = False
        self.evalMovingVolumeSelector.removeEnabled = False
        self.evalMovingVolumeSelector.noneEnabled = True
        self.evalMovingVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.evalMovingVolumeSelector.setToolTip("选择浮动图像 (MRI)")
        evalFormLayout.addRow("Moving Volume: ", self.evalMovingVolumeSelector)

        self.evalFixedMaskSelector = slicer.qMRMLNodeComboBox()
        self.evalFixedMaskSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode"]
        self.evalFixedMaskSelector.selectNodeUponCreation = False
        self.evalFixedMaskSelector.addEnabled = False
        self.evalFixedMaskSelector.removeEnabled = False
        self.evalFixedMaskSelector.noneEnabled = True
        self.evalFixedMaskSelector.setMRMLScene(slicer.mrmlScene)
        self.evalFixedMaskSelector.setToolTip("选择固定图像掩膜（可选，用于 MI 计算）")
        evalFormLayout.addRow("Fixed Mask (可选): ", self.evalFixedMaskSelector)

        self.evalTransformSelector = slicer.qMRMLNodeComboBox()
        self.evalTransformSelector.nodeTypes = ["vtkMRMLTransformNode"]
        self.evalTransformSelector.selectNodeUponCreation = False
        self.evalTransformSelector.addEnabled = False
        self.evalTransformSelector.removeEnabled = False
        self.evalTransformSelector.noneEnabled = True
        self.evalTransformSelector.setMRMLScene(slicer.mrmlScene)
        self.evalTransformSelector.setToolTip("选择配准得到的空间变换")
        evalFormLayout.addRow("空间变换: ", self.evalTransformSelector)

        # TRE 折叠面板（默认折叠）
        treCollapsible = ctk.ctkCollapsibleButton()
        treCollapsible.text = "TRE (目标配准误差)"
        treCollapsible.collapsed = True
        # 紧凑折叠头样式
        try:
            treCollapsible.setContentsMargins(2, 2, 2, 2)
            treCollapsible.setStyleSheet("QLabel { font-size: 12px; padding: 2px; }")
        except Exception:
            pass
        evalFormLayout.addRow(treCollapsible)
        treFormLayout = qt.QFormLayout(treCollapsible)
        # 紧凑 TRE 面板
        try:
            treFormLayout.setSpacing(6)
            treFormLayout.setContentsMargins(6, 4, 6, 4)
        except Exception:
            pass

        # 标注点对管理
        fiducialGroupBox = qt.QGroupBox(" 选择或创建标注点对组")
        fiducialGroupLayout = qt.QVBoxLayout(fiducialGroupBox)
        fiducialGroupBox.setStyleSheet("QGroupBox { color: gray; }")
        # 紧凑点对组内部布局
        try:
            fiducialGroupLayout.setSpacing(6)
            fiducialGroupLayout.setContentsMargins(4, 4, 4, 4)
        except Exception:
            pass
        treFormLayout.addRow(fiducialGroupBox)

        fixedFidLayout = qt.QHBoxLayout()
        fixedLabel = qt.QLabel("Fixed Points: ")
        fixedFidLayout.addWidget(fixedLabel)

        self.fixedFiducialsSelector = slicer.qMRMLNodeComboBox()
        self.fixedFiducialsSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.fixedFiducialsSelector.selectNodeUponCreation = True
        self.fixedFiducialsSelector.noneEnabled = True
        self.fixedFiducialsSelector.setMRMLScene(slicer.mrmlScene)
        self.fixedFiducialsSelector.setToolTip("选择固定图像上的标注点")
        fixedFidLayout.addWidget(self.fixedFiducialsSelector, 1)

        self.placeFixedButton = qt.QPushButton("放置 Fixed")
        self.placeFixedButton.setCheckable(True)
        self.placeFixedButton.connect('toggled(bool)', self.onPlaceFixedToggled)
        fixedFidLayout.addWidget(self.placeFixedButton)
        fiducialGroupLayout.addLayout(fixedFidLayout)

        movingFidLayout = qt.QHBoxLayout()
        movingLabel = qt.QLabel("Moving Points:")
        movingFidLayout.addWidget(movingLabel)

        self.movingFiducialsSelector = slicer.qMRMLNodeComboBox()
        self.movingFiducialsSelector.nodeTypes = ["vtkMRMLMarkupsFiducialNode"]
        self.movingFiducialsSelector.selectNodeUponCreation = True
        self.movingFiducialsSelector.noneEnabled = True
        self.movingFiducialsSelector.setMRMLScene(slicer.mrmlScene)
        self.movingFiducialsSelector.setToolTip("选择浮动图像上的对应标注点")
        movingFidLayout.addWidget(self.movingFiducialsSelector, 1)

        self.placeMovingButton = qt.QPushButton("放置 Moving")
        self.placeMovingButton.setCheckable(True)
        self.placeMovingButton.connect('toggled(bool)', self.onPlaceMovingToggled)
        movingFidLayout.addWidget(self.placeMovingButton)
        fiducialGroupLayout.addLayout(movingFidLayout)

        # 标注点列表
        listLabel = qt.QLabel("标注点列表:")
        fiducialGroupLayout.addWidget(listLabel)

        self.fiducialListTable = qt.QTableWidget()
        self.fiducialListTable.setColumnCount(2)
        self.fiducialListTable.setHorizontalHeaderLabels(["From Fiducials (Fixed)", "To Fiducials (Moving)"])
        # 让两列均分可用宽度，避免第一列挤成一团
        header = self.fiducialListTable.horizontalHeader()
        try:
            if hasattr(header, 'setSectionResizeMode'):
                header.setSectionResizeMode(0, qt.QHeaderView.Stretch)
                header.setSectionResizeMode(1, qt.QHeaderView.Stretch)
            elif hasattr(header, 'setResizeMode'):
                header.setResizeMode(0, qt.QHeaderView.Stretch)
                header.setResizeMode(1, qt.QHeaderView.Stretch)
            else:
                # 备用：仍然保证最后一列拉伸
                self.fiducialListTable.horizontalHeader().setStretchLastSection(True)
        except Exception:
            # 保持兼容，不抛异常
            try:
                self.fiducialListTable.horizontalHeader().setStretchLastSection(True)
            except Exception:
                pass

        # 略微减小表格高度以节省空间
        self.fiducialListTable.setMaximumHeight(120)
        self.fiducialListTable.setMinimumHeight(80)
        self.fiducialListTable.setSelectionBehavior(qt.QTableWidget.SelectRows)
        fiducialGroupLayout.addWidget(self.fiducialListTable)

        # 点对管理按钮
        pairButtonsLayout = qt.QHBoxLayout()
        try:
            pairButtonsLayout.setSpacing(6)
            pairButtonsLayout.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass
        self.createPairButton = qt.QPushButton("新建点对组")
        self.createPairButton.connect('clicked(bool)', self.onCreateFiducialPair)
        pairButtonsLayout.addWidget(self.createPairButton)

        self.deleteLastPairButton = qt.QPushButton("删除最后一对点")
        self.deleteLastPairButton.connect('clicked(bool)', self.onDeleteLastPair)
        pairButtonsLayout.addWidget(self.deleteLastPairButton)

        self.clearAllPairsButton = qt.QPushButton("清除所有点")
        self.clearAllPairsButton.connect('clicked(bool)', self.onClearAllPairs)
        pairButtonsLayout.addWidget(self.clearAllPairsButton)

        fiducialGroupLayout.addLayout(pairButtonsLayout)

        self.pairStatusLabel = qt.QLabel("点对状态: 无标注点")
        self.pairStatusLabel.setStyleSheet("color: gray; font-size: 12px; padding: 0px;")
        fiducialGroupLayout.addWidget(self.pairStatusLabel)

        # 计算 TRE 按钮
        self.computeTREButton = qt.QPushButton("计算 TRE")
        self.computeTREButton.toolTip = "根据选择的标注点对和变换计算 TRE"
        self.computeTREButton.enabled = False
        self.computeTREButton.setStyleSheet("QPushButton { padding: 3px; font-weight: 500; }")
        self.computeTREButton.connect('clicked(bool)', self.onComputeTRE)
        treFormLayout.addRow(self.computeTREButton)

        # TRE 结果显示
        self.treResultLabel = qt.QLabel("TRE：未计算")
        self.treResultLabel.setStyleSheet("color: gray; padding: 5px; background-color: #f0f0f0;")
        self.treResultLabel.setWordWrap(True)
        treFormLayout.addRow(self.treResultLabel)

        # TRE 详细结果表格
        self.treDetailTable = qt.QTableWidget()
        self.treDetailTable.setColumnCount(2)
        self.treDetailTable.setHorizontalHeaderLabels(["点对", "TRE (mm)"])
        self.treDetailTable.horizontalHeader().setStretchLastSection(True)
        self.treDetailTable.setMaximumHeight(150)
        self.treDetailTable.hide()  # 初始隐藏
        treFormLayout.addRow(self.treDetailTable)

        # Mattes MI 折叠面板
        miCollapsible = ctk.ctkCollapsibleButton()
        miCollapsible.text = "Mattes MI (互信息)"
        miCollapsible.collapsed = True  # 默认折叠
        try:
            miCollapsible.setContentsMargins(2, 2, 2, 2)
            miCollapsible.setStyleSheet("QLabel { font-size: 12px; padding: 2px; }")
        except Exception:
            pass
        miFormLayout = qt.QFormLayout(miCollapsible)
        # 紧凑 MI 面板
        try:
            miFormLayout.setSpacing(6)
            miFormLayout.setContentsMargins(6, 4, 6, 4)
        except Exception:
            pass
        evalFormLayout.addRow(miCollapsible)

        # 计算 MI 按钮
        self.computeMIButton = qt.QPushButton("计算 Mattes MI")
        self.computeMIButton.toolTip = "根据选择的图像和变换计算互信息"
        self.computeMIButton.connect('clicked(bool)', self.onComputeMI)
        self.computeMIButton.setStyleSheet("QPushButton { padding: 3px; font-weight: 500; }")
        miFormLayout.addRow(self.computeMIButton)

        # MI 结果显示
        self.miResultLabel = qt.QLabel("MI：未计算")
        self.miResultLabel.setStyleSheet("color: gray; padding: 5px; background-color: #f0f0f0;")
        self.miResultLabel.setWordWrap(True)
        miFormLayout.addRow(self.miResultLabel)

        # =====================================================================
        # 保存结果区域
        # =====================================================================
        saveLabel = qt.QLabel("保存评估结果:")
        saveLabel.setStyleSheet("font-weight: bold; ")
        evalFormLayout.addRow(saveLabel)

        # 模块子文件夹名称
        self.evalModuleFolderNameEdit = qt.QLineEdit()
        self.evalModuleFolderNameEdit.text = "Registration Evaluation"
        self.evalModuleFolderNameEdit.setToolTip("评估结果在总场景文件夹下的子文件夹名称")
        evalFormLayout.addRow("场景子文件夹:", self.evalModuleFolderNameEdit)

        # 保存按钮
        self.saveEvalResultButton = qt.QPushButton("保存评估结果到场景")
        self.saveEvalResultButton.toolTip = "将评估结果保存到场景文件夹"
        self.saveEvalResultButton.enabled = False
        self.saveEvalResultButton.connect('clicked(bool)', self.onSaveResult)
        evalFormLayout.addRow(self.saveEvalResultButton)

        # 状态标签
        self.evalStatusLabel = qt.QLabel("状态: 等待选择数据")
        self.evalStatusLabel.setStyleSheet("color: gray;")
        evalFormLayout.addRow(self.evalStatusLabel)

        # 添加模块末尾分隔线
        separator = qt.QFrame()
        separator.setFrameShape(qt.QFrame.HLine)
        separator.setFrameShadow(qt.QFrame.Plain)
        separator.setLineWidth(2)
        separator.setMidLineWidth(0)
        separator.setStyleSheet("QFrame { background-color: #000000; max-height: 2px; margin: 15px 0px; }")
        evalFormLayout.addRow(separator)

        # 连接信号
        self.evalFixedVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)
        self.evalMovingVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)
        self.evalTransformSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)
        self.fixedFiducialsSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateFiducialStatus)
        self.movingFiducialsSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateFiducialStatus)

    def updateButtonStates(self):
        """更新按钮状态"""
        try:
            hasFixed = self.evalFixedVolumeSelector.currentNode() is not None
            hasMoving = self.evalMovingVolumeSelector.currentNode() is not None
            hasTransform = self.evalTransformSelector.currentNode() is not None
            hasFixedFid = self.fixedFiducialsSelector.currentNode() is not None
            hasMovingFid = self.movingFiducialsSelector.currentNode() is not None
            
            # 检查点对数量
            numFixedPoints = 0
            numMovingPoints = 0
            if hasFixedFid:
                numFixedPoints = self.fixedFiducialsSelector.currentNode().GetNumberOfControlPoints()
            if hasMovingFid:
                numMovingPoints = self.movingFiducialsSelector.currentNode().GetNumberOfControlPoints()
            
            # TRE 需要变换和配对的标注点
            hasPairedPoints = hasFixedFid and hasMovingFid and numFixedPoints > 0 and numFixedPoints == numMovingPoints
            self.computeTREButton.enabled = hasTransform and hasPairedPoints
            
            # 删除按钮
            self.deleteLastPairButton.enabled = hasPairedPoints
            self.clearAllPairsButton.enabled = (numFixedPoints > 0 or numMovingPoints > 0)
            
            # MI 需要固定图像、浮动图像和变换
            self.computeMIButton.enabled = hasFixed and hasMoving and hasTransform
            
            # 保存按钮需要有计算结果
            hasResults = self.treResult is not None or self.miResult is not None
            self.saveEvalResultButton.enabled = hasResults
            
            # 更新状态标签
            if not hasFixed or not hasMoving:
                self.evalStatusLabel.text = "状态: 请选择固定图像和浮动图像"
                self.evalStatusLabel.setStyleSheet("color: orange;")
            elif not hasTransform:
                self.evalStatusLabel.text = "状态: 请选择空间变换"
                self.evalStatusLabel.setStyleSheet("color: orange;")
            else:
                self.evalStatusLabel.text = "状态: 准备就绪，可以计算评估指标"
                self.evalStatusLabel.setStyleSheet("color: green;")
                
        except Exception as e:
            self.logCallback(f"更新按钮状态失败: {str(e)}")
    
    def updateFiducialStatus(self):
        """更新标注点状态显示"""
        try:
            fixedNode = self.fixedFiducialsSelector.currentNode()
            movingNode = self.movingFiducialsSelector.currentNode()
            
            numFixed = fixedNode.GetNumberOfControlPoints() if fixedNode else 0
            numMoving = movingNode.GetNumberOfControlPoints() if movingNode else 0
            
            # 更新列表表格
            self.updateFiducialListTable()
            
            if numFixed == 0 and numMoving == 0:
                self.pairStatusLabel.setText("点对状态: 无标注点")
                self.pairStatusLabel.setStyleSheet("color: gray; font-size: 12px; padding: 0px;")
            elif numFixed == numMoving:
                self.pairStatusLabel.setText(f"点对状态: {numFixed} 对点已配对 ✓")
                self.pairStatusLabel.setStyleSheet("color: green; font-size: 12px; padding: 0px; ")
            else:
                self.pairStatusLabel.setText(f"点对状态: Fixed={numFixed}, Moving={numMoving} (不匹配 ✗)")
                self.pairStatusLabel.setStyleSheet("color: red; font-size: 11px; padding: 5px;")
            
            self.updateButtonStates()
            
        except Exception as e:
            self.logCallback(f"更新标注点状态失败: {str(e)}")
    
    def updateFiducialListTable(self):
        """更新标注点列表表格"""
        try:
            fixedNode = self.fixedFiducialsSelector.currentNode()
            movingNode = self.movingFiducialsSelector.currentNode()
            
            numFixed = fixedNode.GetNumberOfControlPoints() if fixedNode else 0
            numMoving = movingNode.GetNumberOfControlPoints() if movingNode else 0
            maxRows = max(numFixed, numMoving)
            
            self.fiducialListTable.setRowCount(maxRows)
            
            # 填充 Fixed 列
            for i in range(maxRows):
                if i < numFixed:
                    label = fixedNode.GetNthControlPointLabel(i)
                    self.fiducialListTable.setItem(i, 0, qt.QTableWidgetItem(label if label else f"F-{i+1}"))
                else:
                    self.fiducialListTable.setItem(i, 0, qt.QTableWidgetItem(""))
            
            # 填充 Moving 列
            for i in range(maxRows):
                if i < numMoving:
                    label = movingNode.GetNthControlPointLabel(i)
                    self.fiducialListTable.setItem(i, 1, qt.QTableWidgetItem(label if label else f"M-{i+1}"))
                else:
                    self.fiducialListTable.setItem(i, 1, qt.QTableWidgetItem(""))
            
            # 高亮不匹配的行
            for i in range(maxRows):
                if i >= numFixed or i >= numMoving:
                    # 不匹配的行设置为浅红色背景
                    for col in range(2):
                        item = self.fiducialListTable.item(i, col)
                        if item:
                            item.setBackground(qt.QColor(255, 200, 200))
                else:
                    # 匹配的行设置为浅绿色背景
                    for col in range(2):
                        item = self.fiducialListTable.item(i, col)
                        if item:
                            item.setBackground(qt.QColor(200, 255, 200))
                            
        except Exception as e:
            self.logCallback(f"更新标注点列表失败: {str(e)}")
    
    def addFiducialObservers(self):
        """添加标注点观察者"""
        try:
            # 移除旧的观察者
            self.removeFiducialObservers()
            
            fixedNode = self.fixedFiducialsSelector.currentNode()
            movingNode = self.movingFiducialsSelector.currentNode()
            
            if fixedNode:
                self.fixedObserverTag = fixedNode.AddObserver(
                    slicer.vtkMRMLMarkupsNode.PointAddedEvent, 
                    lambda caller, event: self.updateFiducialStatus()
                )
                fixedNode.AddObserver(
                    slicer.vtkMRMLMarkupsNode.PointRemovedEvent, 
                    lambda caller, event: self.updateFiducialStatus()
                )
                fixedNode.AddObserver(
                    slicer.vtkMRMLMarkupsNode.PointModifiedEvent, 
                    lambda caller, event: self.updateFiducialStatus()
                )
            
            if movingNode:
                self.movingObserverTag = movingNode.AddObserver(
                    slicer.vtkMRMLMarkupsNode.PointAddedEvent, 
                    lambda caller, event: self.updateFiducialStatus()
                )
                movingNode.AddObserver(
                    slicer.vtkMRMLMarkupsNode.PointRemovedEvent, 
                    lambda caller, event: self.updateFiducialStatus()
                )
                movingNode.AddObserver(
                    slicer.vtkMRMLMarkupsNode.PointModifiedEvent, 
                    lambda caller, event: self.updateFiducialStatus()
                )
                
        except Exception as e:
            self.logCallback(f"添加观察者失败: {str(e)}")
    
    def removeFiducialObservers(self):
        """移除标注点观察者"""
        try:
            fixedNode = self.fixedFiducialsSelector.currentNode()
            movingNode = self.movingFiducialsSelector.currentNode()
            
            if fixedNode and self.fixedObserverTag:
                fixedNode.RemoveObserver(self.fixedObserverTag)
                self.fixedObserverTag = None
            
            if movingNode and self.movingObserverTag:
                movingNode.RemoveObserver(self.movingObserverTag)
                self.movingObserverTag = None
                
        except Exception as e:
            pass

    # =========================================================================
    # TRE 相关操作
    # =========================================================================

    def onCreateFiducialPair(self):
        """创建新的标注点对组"""
        try:
            # 创建 Fixed 标注点
            fixedNode = self.logic.createFiducialNode("Eval_Fixed_Points")
            self.fixedFiducialsSelector.setCurrentNode(fixedNode)
            
            # 设置 Fixed 颜色为红色
            displayNode = fixedNode.GetDisplayNode()
            if displayNode:
                displayNode.SetSelectedColor(1.0, 0.0, 0.0)
                displayNode.SetColor(1.0, 0.0, 0.0)
                # 设置点的显示大小：图形绝对值1mm，文字3%
                displayNode.SetGlyphScale(1.0)  # 绝对值1mm
                displayNode.SetTextScale(1.5)   # 文字大小1.5%
                displayNode.SetGlyphTypeFromString("Sphere3D")
            
            # 创建 Moving 标注点
            movingNode = self.logic.createFiducialNode("Eval_Moving_Points")
            self.movingFiducialsSelector.setCurrentNode(movingNode)
            
            # 设置 Moving 颜色为蓝色
            displayNode = movingNode.GetDisplayNode()
            if displayNode:
                displayNode.SetSelectedColor(0.0, 0.5, 1.0)
                displayNode.SetColor(0.0, 0.5, 1.0)
                # 设置点的显示大小：图形绝对值1mm，文字3%
                displayNode.SetGlyphScale(1.0)  # 绝对值1mm
                displayNode.SetTextScale(1.5)   # 文字大小1.5%
                displayNode.SetGlyphTypeFromString("Sphere3D")
            
            # 标记这些节点为新建的（保存后需要删除）
            self.createdFixedFiducials = fixedNode
            self.createdMovingFiducials = movingNode
            
            # 添加观察者
            self.addFiducialObservers()
            
            self.logCallback("已创建标注点对组: Fixed(红色) 和 Moving(蓝色)")
            self.logCallback("提示: 先点击'放置 Fixed'在固定图像上添加点，再点击'放置 Moving'在浮动图像上添加对应点")
            
            self.updateFiducialStatus()
            
        except Exception as e:
            self.showError(f"创建标注点对组失败: {str(e)}")

    def onPlaceFixedToggled(self, checked):
        """切换 Fixed 标注点放置模式"""
        try:
            if checked:
                # 确保有 Fixed 标注点节点
                fixedNode = self.fixedFiducialsSelector.currentNode()
                if not fixedNode:
                    self.onCreateFiducialPair()
                    fixedNode = self.fixedFiducialsSelector.currentNode()
                
                if fixedNode:
                    # 添加观察者来实时更新列表
                    self.addFiducialObservers()
                    
                    # 激活 Fixed 标注点持续放置模式
                    selectionNode = slicer.app.applicationLogic().GetSelectionNode()
                    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
                    selectionNode.SetActivePlaceNodeID(fixedNode.GetID())
                    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
                    interactionNode.SetCurrentInteractionMode(interactionNode.Place)
                    interactionNode.SetPlaceModePersistence(True)  # 关键: 持续放置模式
                    
                    # 取消 Moving 按钮
                    self.placeMovingButton.setChecked(False)
                    
                    self.logCallback("已激活 Fixed 点放置模式 (红色) - 可连续放置多个点")
                    self.pairStatusLabel.setText("正在放置 Fixed 点...")
                    self.pairStatusLabel.setStyleSheet("color: red; font-size: 11px; padding: 5px; font-weight: bold;")
            else:
                # 取消放置模式
                interactionNode = slicer.app.applicationLogic().GetInteractionNode()
                interactionNode.SetPlaceModePersistence(False)
                interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
                self.updateFiducialStatus()
                
        except Exception as e:
            self.showError(f"切换 Fixed 放置模式失败: {str(e)}")
            self.placeFixedButton.setChecked(False)

    def onPlaceMovingToggled(self, checked):
        """切换 Moving 标注点放置模式"""
        try:
            if checked:
                # 确保有 Moving 标注点节点
                movingNode = self.movingFiducialsSelector.currentNode()
                if not movingNode:
                    self.onCreateFiducialPair()
                    movingNode = self.movingFiducialsSelector.currentNode()
                
                if movingNode:
                    # 添加观察者来实时更新列表
                    self.addFiducialObservers()
                    
                    # 激活 Moving 标注点持续放置模式
                    selectionNode = slicer.app.applicationLogic().GetSelectionNode()
                    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
                    selectionNode.SetActivePlaceNodeID(movingNode.GetID())
                    interactionNode = slicer.app.applicationLogic().GetInteractionNode()
                    interactionNode.SetCurrentInteractionMode(interactionNode.Place)
                    interactionNode.SetPlaceModePersistence(True)  # 关键: 持续放置模式
                    
                    # 取消 Fixed 按钮
                    self.placeFixedButton.setChecked(False)
                    
                    self.logCallback("已激活 Moving 点放置模式 (蓝色) - 可连续放置多个点")
                    self.pairStatusLabel.setText("正在放置 Moving 点...")
                    self.pairStatusLabel.setStyleSheet("color: blue; font-size: 11px; padding: 5px; font-weight: bold;")
            else:
                # 取消放置模式
                interactionNode = slicer.app.applicationLogic().GetInteractionNode()
                interactionNode.SetPlaceModePersistence(False)
                interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
                self.updateFiducialStatus()
                
        except Exception as e:
            self.showError(f"切换 Moving 放置模式失败: {str(e)}")
            self.placeMovingButton.setChecked(False)

    def onDeleteLastPair(self):
        """删除最后一对标注点"""
        try:
            fixedNode = self.fixedFiducialsSelector.currentNode()
            movingNode = self.movingFiducialsSelector.currentNode()
            
            if fixedNode and movingNode:
                numFixed = fixedNode.GetNumberOfControlPoints()
                numMoving = movingNode.GetNumberOfControlPoints()
                
                if numFixed > 0:
                    fixedNode.RemoveNthControlPoint(numFixed - 1)
                if numMoving > 0:
                    movingNode.RemoveNthControlPoint(numMoving - 1)
                
                self.logCallback("已删除最后一对标注点")
                self.updateFiducialStatus()
                
        except Exception as e:
            self.showError(f"删除标注点失败: {str(e)}")

    def onClearAllPairs(self):
        """清除所有标注点"""
        try:
            fixedNode = self.fixedFiducialsSelector.currentNode()
            movingNode = self.movingFiducialsSelector.currentNode()
            
            if fixedNode:
                fixedNode.RemoveAllControlPoints()
            if movingNode:
                movingNode.RemoveAllControlPoints()
            
            self.logCallback("已清除所有标注点")
            self.updateFiducialStatus()
            
        except Exception as e:
            self.showError(f"清除标注点失败: {str(e)}")

    def onComputeTRE(self):
        """计算 TRE"""
        try:
            fixedFiducials = self.fixedFiducialsSelector.currentNode()
            movingFiducials = self.movingFiducialsSelector.currentNode()
            transformNode = self.evalTransformSelector.currentNode()
            
            if not fixedFiducials or not movingFiducials:
                self.showError("请选择固定标注点和浮动标注点")
                return
            
            if not transformNode:
                self.showError("请选择空间变换")
                return
            
            self.logCallback("===== 开始计算 TRE =====")
            self.evalStatusLabel.text = "状态: 正在计算 TRE..."
            self.evalStatusLabel.setStyleSheet("color: blue;")
            slicer.app.processEvents()
            
            # 计算 TRE
            self.treResult = self.logic.computeTRE(fixedFiducials, movingFiducials, transformNode)
            
            # 更新结果显示
            self.treResultLabel.setText(
                f"TRE：\n"
                f"平均：{self.treResult['meanTRE']:.4f} mm\n"
                f"最大：{self.treResult['maxTRE']:.4f} mm\n"
                f"最小：{self.treResult['minTRE']:.4f} mm\n"
                f"标准差：{self.treResult['stdTRE']:.4f} mm\n"
                f"点对数：{self.treResult['numPoints']}"
            )
            self.treResultLabel.setStyleSheet("color: green; padding: 5px; background-color: #f0f0f0;")
            
            # 更新详细表格
            self._updateTREDetailTable(self.treResult)
            
            self.evalStatusLabel.text = "状态: TRE 计算完成"
            self.evalStatusLabel.setStyleSheet("color: green;")
            
            # 更新保存按钮状态
            self.updateButtonStates()
            
        except Exception as e:
            self.showError(f"TRE 计算失败: {str(e)}")

    def _updateTREDetailTable(self, treResult):
        """更新 TRE 详细表格"""
        self.treDetailTable.setRowCount(0)
        
        if treResult and 'pointTREs' in treResult:
            pointTREs = treResult['pointTREs']
            self.treDetailTable.setRowCount(len(pointTREs))
            
            for i, tre in enumerate(pointTREs):
                self.treDetailTable.setItem(i, 0, qt.QTableWidgetItem(f"点对 {i+1}"))
                self.treDetailTable.setItem(i, 1, qt.QTableWidgetItem(f"{tre:.4f}"))
            
            self.treDetailTable.show()
        else:
            self.treDetailTable.hide()

    # =========================================================================
    # MI 相关操作
    # =========================================================================

    def onComputeMI(self):
        """计算 Mattes MI（异步执行）"""
        try:
            fixedVolume = self.evalFixedVolumeSelector.currentNode()
            movingVolume = self.evalMovingVolumeSelector.currentNode()
            transformNode = self.evalTransformSelector.currentNode()
            fixedMaskNode = self.evalFixedMaskSelector.currentNode()
            
            if not fixedVolume or not movingVolume:
                self.showError("请选择固定图像和浮动图像")
                return
            
            if not transformNode:
                self.showError("请选择空间变换")
                return
            
            self.logCallback("===== 开始计算 Mattes MI =====")
            self.evalStatusLabel.text = "状态: 正在计算 MI..."
            self.evalStatusLabel.setStyleSheet("color: blue;")
            
            # 禁用按钮防止重复点击
            self.computeMIButton.enabled = False
            slicer.app.processEvents()
            
            # 设置完成回调
            self.logic.setMIFinishCallback(self.onMIFinished)
            
            # 异步计算 MI
            success = self.logic.computeMattesMI(
                fixedVolume, movingVolume, transformNode, fixedMaskNode
            )
            
            if not success:
                self.computeMIButton.enabled = True
                self.showError("MI 计算启动失败")
            
        except Exception as e:
            self.computeMIButton.enabled = True
            self.showError(f"MI 计算失败: {str(e)}")
    
    def onMIFinished(self, success, result):
        """MI 计算完成回调"""
        try:
            self.computeMIButton.enabled = True
            
            if not success or result is None:
                self.showError("MI 计算失败，请查看日志")
                self.evalStatusLabel.text = "状态: MI 计算失败"
                self.evalStatusLabel.setStyleSheet("color: red;")
                return
            
            self.miResult = result
            
            # 简化结果显示：只显示 MI 值
            self.miResultLabel.setText(f"MI：{self.miResult['MI']:.6f}")
            self.miResultLabel.setStyleSheet("color: green; padding: 5px; background-color:#f0f0f0")
            
            self.evalStatusLabel.text = "状态: MI 计算完成"
            self.evalStatusLabel.setStyleSheet("color: green;")
            
            # 更新保存按钮状态
            self.updateButtonStates()
            
        except Exception as e:
            self.showError(f"MI 结果处理失败: {str(e)}")

    # =========================================================================
    # 保存结果
    # =========================================================================

    def onSaveResult(self):
        """保存评估结果到场景"""
        try:
            if not self.treResult and not self.miResult:
                self.showError("请先计算 TRE 或 MI")
                return
            
            fixedVolume = self.evalFixedVolumeSelector.currentNode()
            movingVolume = self.evalMovingVolumeSelector.currentNode()
            transformNode = self.evalTransformSelector.currentNode()
            fixedFiducials = self.fixedFiducialsSelector.currentNode()
            movingFiducials = self.movingFiducialsSelector.currentNode()
            
            # 获取文件夹名称
            mainFolderName = self.getMainFolderNameCallback()
            moduleFolderName = self.evalModuleFolderNameEdit.text
            
            if not mainFolderName or not moduleFolderName:
                self.showError("请输入文件夹名称")
                return
            
            self.logCallback(f"正在保存评估结果到场景...")
            self.logCallback(f"  总文件夹: {mainFolderName}")
            self.logCallback(f"  模块子文件夹: {moduleFolderName}")
            
            # 检查是否为新建的点对组
            isCreatedFixed = (fixedFiducials == self.createdFixedFiducials)
            isCreatedMoving = (movingFiducials == self.createdMovingFiducials)
            
            # 保存结果
            success = self.logic.saveEvaluationToScene(
                fixedVolume, movingVolume, transformNode,
                fixedFiducials, movingFiducials,
                self.treResult, self.miResult,
                mainFolderName, moduleFolderName,
                deleteOriginalFixed=isCreatedFixed,
                deleteOriginalMoving=isCreatedMoving
            )
            
            if success:
                self.logCallback(f"✓ 评估结果已保存到场景文件夹")
                self.evalStatusLabel.text = "状态: 结果已保存到场景"
                self.evalStatusLabel.setStyleSheet("color: green;")
                
                # 如果是新建的点对组，清除创建标记（因为原始节点已删除）
                if isCreatedFixed:
                    self.createdFixedFiducials = None
                if isCreatedMoving:
                    self.createdMovingFiducials = None
            else:
                self.showError("保存结果失败")
                
        except Exception as e:
            self.showError(f"保存结果失败: {str(e)}")

    def showError(self, errorMessage):
        """显示错误信息"""
        self.logCallback(f"✗ 错误: {errorMessage}")
        self.evalStatusLabel.text = f"状态: 错误"
        self.evalStatusLabel.setStyleSheet("color: red;")
        slicer.util.errorDisplay(errorMessage)
        import traceback
        self.logCallback(traceback.format_exc())
