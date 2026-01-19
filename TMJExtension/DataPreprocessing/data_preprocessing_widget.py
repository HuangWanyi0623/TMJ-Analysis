"""
Data Preprocessing Widget - UI界面
用于CBCT和MRI数据的预处理
"""
import qt
import ctk
import slicer
from .data_preprocessing_logic import DataPreprocessingLogic


class DataPreprocessingWidget:
    """
    Data Preprocessing 的UI组件类
    负责CBCT和MRI数据的预处理界面
    """

    def __init__(self, parent, logCallback, getMainFolderNameCallback):
        """
        初始化 Data Preprocessing Widget
        
        :param parent: 父布局
        :param logCallback: 日志回调函数
        :param getMainFolderNameCallback: 获取主文件夹名称的回调函数
        """
        self.parent = parent
        self.logCallback = logCallback
        self.getMainFolderNameCallback = getMainFolderNameCallback
        self.logic = DataPreprocessingLogic(logCallback=logCallback)
        
        # UI 组件引用 - CBCT
        self.cbctVolumeSelector = None
        self.roiSelector = None
        self.targetDimXSpinBox = None
        self.targetDimYSpinBox = None
        self.targetDimZSpinBox = None
        self.targetSpacingXSpinBox = None
        self.targetSpacingYSpinBox = None
        self.targetSpacingZSpinBox = None
        self.volumeInfoLabel = None
        self.roiInfoLabel = None
        self.statusLabel = None
        
        # UI 组件引用 - MRI
        self.mriVolumeSelector = None
        self.templateVolumeSelector = None
        self.transformSelector = None
        self.mriInfoLabel = None
        self.templateInfoLabel = None
        self.mriStatusLabel = None
        
        # 保存相关
        self.moduleFolderNameEdit = None
        self.saveResultButton = None
        self.saveStatusLabel = None
        
        # 当前ROI节点
        self.currentROI = None
        self.roiObserverTag = None
        
        # 存储预处理结果的节点引用
        self.lastROI = None
        self.lastTemplate = None
        
        self.setupUI()

    def setupUI(self):
        """设置 Data Preprocessing 的UI界面"""
        # Data Preprocessing 模块
        preprocessCollapsibleButton = ctk.ctkCollapsibleButton()
        preprocessCollapsibleButton.text = "Data Preprocessing"
        preprocessCollapsibleButton.collapsed = True  # 默认折叠
        self.parent.addWidget(preprocessCollapsibleButton)
        mainLayout = qt.QVBoxLayout(preprocessCollapsibleButton)
        
        # CBCT（固定图像）数据预处理折叠面板
        cbctCollapsibleButton = ctk.ctkCollapsibleButton()
        cbctCollapsibleButton.text = "CBCT（固定图像）数据预处理"
        cbctCollapsibleButton.collapsed = True
        mainLayout.addWidget(cbctCollapsibleButton)
        cbctLayout = qt.QVBoxLayout(cbctCollapsibleButton)
        
        # ========== 1. CBCT数据选择区域 ==========
        cbctGroupBox = qt.QGroupBox("1.CBCT数据选择")
        cbctGroupLayout = qt.QFormLayout(cbctGroupBox)
        cbctGroupBox.setStyleSheet("QGroupBox { color: gray; }")
        cbctLayout.addWidget(cbctGroupBox)

        # CBCT体数据选择器
        self.cbctVolumeSelector = slicer.qMRMLNodeComboBox()
        self.cbctVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.cbctVolumeSelector.selectNodeUponCreation = False
        self.cbctVolumeSelector.addEnabled = False
        self.cbctVolumeSelector.removeEnabled = False
        self.cbctVolumeSelector.noneEnabled = True
        self.cbctVolumeSelector.showHidden = False
        self.cbctVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.cbctVolumeSelector.setToolTip("选择CBCT体数据")
        self.cbctVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onCBCTVolumeChanged)
        cbctGroupLayout.addRow("CBCT数据:", self.cbctVolumeSelector)

        # 体数据信息显示
        self.volumeInfoLabel = qt.QLabel("未选择数据")
        self.volumeInfoLabel.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5;")
        self.volumeInfoLabel.setWordWrap(True)
        cbctGroupLayout.addRow("数据信息:", self.volumeInfoLabel)

        # ========== 2. ROI设置区域 ==========
        roiGroupBox = qt.QGroupBox("2.ROI裁剪设置（调整尺寸）")
        roiLayout = qt.QFormLayout(roiGroupBox)
        roiGroupBox.setStyleSheet("QGroupBox { color: gray; }")
        cbctLayout.addWidget(roiGroupBox)

        # ROI选择器
        self.roiSelector = slicer.qMRMLNodeComboBox()
        self.roiSelector.nodeTypes = ["vtkMRMLMarkupsROINode"]
        self.roiSelector.selectNodeUponCreation = True
        self.roiSelector.addEnabled = False
        self.roiSelector.removeEnabled = False
        self.roiSelector.noneEnabled = True
        self.roiSelector.showHidden = False
        self.roiSelector.setMRMLScene(slicer.mrmlScene)
        self.roiSelector.setToolTip("选择用于裁剪的ROI（可在3D视图中手动调整）")
        self.roiSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onROIChanged)
        roiLayout.addRow("ROI:", self.roiSelector)

        # 创建ROI按钮
        createROIButton = qt.QPushButton("根据CBCT创建ROI")
        createROIButton.toolTip = "基于当前CBCT数据的边界创建ROI，可在3D视图中手动调整"
        createROIButton.connect('clicked(bool)', self.onCreateROI)
        roiLayout.addRow(createROIButton)

        # 目标尺寸设置
        dimLabel = qt.QLabel("目标体素尺寸 (X, Y, Z):")
        roiLayout.addRow(dimLabel)
        
        dimLayout = qt.QHBoxLayout()
        self.targetDimXSpinBox = qt.QSpinBox()
        self.targetDimXSpinBox.setRange(1, 2048)
        self.targetDimXSpinBox.setValue(528)
        self.targetDimXSpinBox.setSuffix(" voxels")
        dimLayout.addWidget(self.targetDimXSpinBox)
        
        self.targetDimYSpinBox = qt.QSpinBox()
        self.targetDimYSpinBox.setRange(1, 2048)
        self.targetDimYSpinBox.setValue(528)
        self.targetDimYSpinBox.setSuffix(" voxels")
        dimLayout.addWidget(self.targetDimYSpinBox)
        
        self.targetDimZSpinBox = qt.QSpinBox()
        self.targetDimZSpinBox.setRange(1, 2048)
        self.targetDimZSpinBox.setValue(528)
        self.targetDimZSpinBox.setSuffix(" voxels")
        dimLayout.addWidget(self.targetDimZSpinBox)
        roiLayout.addRow(dimLayout)

        # 应用尺寸到ROI按钮
        applyDimButton = qt.QPushButton("应用目标尺寸到ROI")
        applyDimButton.toolTip = "根据目标体素尺寸和当前间距自动调整ROI大小"
        applyDimButton.connect('clicked(bool)', self.onApplyDimensionsToROI)
        roiLayout.addRow(applyDimButton)

        # ROI信息显示
        self.roiInfoLabel = qt.QLabel("未选择ROI")
        self.roiInfoLabel.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5;")
        self.roiInfoLabel.setWordWrap(True)
        roiLayout.addRow("ROI信息:", self.roiInfoLabel)

        # ========== 3. 重采样设置区域 ==========
        resampleGroupBox = qt.QGroupBox("3.重采样设置（调整间距，用于生成Template）")
        resampleLayout = qt.QFormLayout(resampleGroupBox)
        resampleGroupBox.setStyleSheet("QGroupBox { color: gray; }")
        cbctLayout.addWidget(resampleGroupBox)

        # 目标间距设置
        spacingLabel = qt.QLabel("目标间距 (X, Y, Z):")
        resampleLayout.addRow(spacingLabel)
        
        spacingLayout = qt.QHBoxLayout()
        self.targetSpacingXSpinBox = qt.QDoubleSpinBox()
        self.targetSpacingXSpinBox.setRange(0.01, 10.0)
        self.targetSpacingXSpinBox.setValue(0.99)
        self.targetSpacingXSpinBox.setDecimals(3)
        self.targetSpacingXSpinBox.setSingleStep(0.1)
        self.targetSpacingXSpinBox.setSuffix(" mm")
        spacingLayout.addWidget(self.targetSpacingXSpinBox)
        
        self.targetSpacingYSpinBox = qt.QDoubleSpinBox()
        self.targetSpacingYSpinBox.setRange(0.01, 10.0)
        self.targetSpacingYSpinBox.setValue(0.99)
        self.targetSpacingYSpinBox.setDecimals(3)
        self.targetSpacingYSpinBox.setSingleStep(0.1)
        self.targetSpacingYSpinBox.setSuffix(" mm")
        spacingLayout.addWidget(self.targetSpacingYSpinBox)
        
        self.targetSpacingZSpinBox = qt.QDoubleSpinBox()
        self.targetSpacingZSpinBox.setRange(0.01, 10.0)
        self.targetSpacingZSpinBox.setValue(0.99)
        self.targetSpacingZSpinBox.setDecimals(3)
        self.targetSpacingZSpinBox.setSingleStep(0.1)
        self.targetSpacingZSpinBox.setSuffix(" mm")
        spacingLayout.addWidget(self.targetSpacingZSpinBox)
        resampleLayout.addRow(spacingLayout)

        # 执行按钮
        self.executeButton = qt.QPushButton("执行CBCT预处理")
        self.executeButton.toolTip = "执行完整的CBCT预处理流程：ROI裁剪、填充、原点归零、生成模板"
        self.executeButton.enabled = False
        self.executeButton.setStyleSheet("font-weight: 500; padding: 3px;")
        self.executeButton.connect('clicked(bool)', self.onExecutePreprocessing)
        cbctLayout.addWidget(self.executeButton)

        # CBCT预处理状态信息
        statusLayout = qt.QHBoxLayout()
        statusLabel = qt.QLabel("状态:")
        statusLabel.setStyleSheet("color: gray;")
        statusLayout.addWidget(statusLabel)
        
        self.statusLabel = qt.QLabel("就绪")
        self.statusLabel.setStyleSheet("color: #666; padding: 5px;")
        statusLayout.addWidget(self.statusLabel)
        statusLayout.addStretch()
        
        cbctLayout.addLayout(statusLayout)
        
        # ========== MRI（浮动图像）数据预处理折叠面板 ==========
        mriCollapsibleButton = ctk.ctkCollapsibleButton()
        mriCollapsibleButton.text = "MRI（浮动图像）数据预处理"
        mriCollapsibleButton.collapsed = True
        mainLayout.addWidget(mriCollapsibleButton)
        mriLayout = qt.QVBoxLayout(mriCollapsibleButton)
        
        # ========== 1. MRI数据选择区域 ==========
        mriGroupBox = qt.QGroupBox("1.MRI数据选择")
        mriGroupLayout = qt.QFormLayout(mriGroupBox)
        mriGroupBox.setStyleSheet("QGroupBox { color: gray; }")
        mriLayout.addWidget(mriGroupBox)

        # MRI体数据选择器
        self.mriVolumeSelector = slicer.qMRMLNodeComboBox()
        self.mriVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.mriVolumeSelector.selectNodeUponCreation = False
        self.mriVolumeSelector.addEnabled = False
        self.mriVolumeSelector.removeEnabled = False
        self.mriVolumeSelector.noneEnabled = True
        self.mriVolumeSelector.showHidden = False
        self.mriVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.mriVolumeSelector.setToolTip("选择MRI体数据")
        self.mriVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onMRIVolumeChanged)
        mriGroupLayout.addRow("MRI数据:", self.mriVolumeSelector)

        # MRI体数据信息显示
        self.mriInfoLabel = qt.QLabel("未选择数据")
        self.mriInfoLabel.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5;")
        self.mriInfoLabel.setWordWrap(True)
        mriGroupLayout.addRow("数据信息:", self.mriInfoLabel)

        # ========== 2. Template和Transform选择区域 ==========
        templateGroupBox = qt.QGroupBox("2.选择Template和初始变换，统一尺寸和间距")
        templateGroupLayout = qt.QFormLayout(templateGroupBox)
        templateGroupBox.setStyleSheet("QGroupBox { color: gray; }")
        mriLayout.addWidget(templateGroupBox)

        # Template Volume选择器
        self.templateVolumeSelector = slicer.qMRMLNodeComboBox()
        self.templateVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.templateVolumeSelector.selectNodeUponCreation = False
        self.templateVolumeSelector.addEnabled = False
        self.templateVolumeSelector.removeEnabled = False
        self.templateVolumeSelector.noneEnabled = True
        self.templateVolumeSelector.showHidden = False
        self.templateVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.templateVolumeSelector.setToolTip("选择Template Volume（由CBCT预处理生成）")
        self.templateVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onTemplateVolumeChanged)
        templateGroupLayout.addRow("Template Volume:", self.templateVolumeSelector)

        # Template信息显示
        self.templateInfoLabel = qt.QLabel("未选择Template")
        self.templateInfoLabel.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5;")
        self.templateInfoLabel.setWordWrap(True)
        templateGroupLayout.addRow("Template信息:", self.templateInfoLabel)

        # 初始变换选择器
        self.transformSelector = slicer.qMRMLNodeComboBox()
        self.transformSelector.nodeTypes = ["vtkMRMLTransformNode"]
        self.transformSelector.selectNodeUponCreation = False
        self.transformSelector.addEnabled = False
        self.transformSelector.removeEnabled = False
        self.transformSelector.noneEnabled = True
        self.transformSelector.showHidden = False
        self.transformSelector.setMRMLScene(slicer.mrmlScene)
        self.transformSelector.setToolTip("（可选）选择初始空间变换（如粗配准变换）")
        templateGroupLayout.addRow("初始变换（可选）:", self.transformSelector)

        # 执行MRI预处理按钮
        self.executeMRIButton = qt.QPushButton("执行MRI预处理")
        self.executeMRIButton.toolTip = "将MRI重采样到Template空间，可选应用初始变换"
        self.executeMRIButton.enabled = False
        self.executeMRIButton.setStyleSheet("font-weight: 500; padding: 3px;")
        self.executeMRIButton.connect('clicked(bool)', self.onExecuteMRIPreprocessing)
        mriLayout.addWidget(self.executeMRIButton)

        # MRI预处理状态信息
        mriStatusLayout = qt.QHBoxLayout()
        mriStatusLabelText = qt.QLabel("状态:")
        mriStatusLabelText.setStyleSheet("color: gray;")
        mriStatusLayout.addWidget(mriStatusLabelText)
        
        self.mriStatusLabel = qt.QLabel("就绪")
        self.mriStatusLabel.setStyleSheet("color: #666; padding: 5px;")
        mriStatusLayout.addWidget(self.mriStatusLabel)
        mriStatusLayout.addStretch()
        
        mriLayout.addLayout(mriStatusLayout)
        
        # ========== 保存预处理结果区域 ==========
        saveLabel = qt.QLabel("保存预处理结果:")
        saveLabel.setStyleSheet("font-weight: bold;")
        mainLayout.addWidget(saveLabel)
        
        saveLayout = qt.QFormLayout()
        
        # 模块子文件夹名称
        self.moduleFolderNameEdit = qt.QLineEdit()
        self.moduleFolderNameEdit.text = "Data Preprocessing"
        self.moduleFolderNameEdit.setToolTip("预处理结果在总场景文件夹下的子文件夹名称")
        saveLayout.addRow("场景子文件夹:", self.moduleFolderNameEdit)
        
        # 保存按钮
        self.saveResultButton = qt.QPushButton("保存预处理结果到场景")
        self.saveResultButton.toolTip = "保存ROI和Template到场景文件夹，并设置Slice视图前景/背景"
        self.saveResultButton.enabled = False
        self.saveResultButton.setStyleSheet("font-weight: 500; padding: 3px;")
        self.saveResultButton.connect('clicked(bool)', self.onSaveResults)
        saveLayout.addRow(self.saveResultButton)
        
        # 保存状态标签
        saveStatusLayout = qt.QHBoxLayout()
        saveStatusLabelText = qt.QLabel("状态:")
        saveStatusLabelText.setStyleSheet("color: gray;")
        saveStatusLayout.addWidget(saveStatusLabelText)
        
        self.saveStatusLabel = qt.QLabel("等待预处理完成")
        self.saveStatusLabel.setStyleSheet("color: #666; padding: 5px;")
        saveStatusLayout.addWidget(self.saveStatusLabel)
        saveStatusLayout.addStretch()
        
        saveLayout.addRow(saveStatusLayout)
        mainLayout.addLayout(saveLayout)

    def onCBCTVolumeChanged(self):
        """CBCT体数据改变时的回调"""
        volumeNode = self.cbctVolumeSelector.currentNode()
        
        if volumeNode:
            info = self.logic.getVolumeInfo(volumeNode)
            if info:
                dims = info['dimensions']
                spacing = info['spacing']
                origin = info['origin']
                self.volumeInfoLabel.setText(
                    f"尺寸: {dims[0]} × {dims[1]} × {dims[2]} voxels\n"
                    f"间距: {spacing[0]:.4f} × {spacing[1]:.4f} × {spacing[2]:.4f} mm\n"
                    f"原点: ({origin[0]:.2f}, {origin[1]:.2f}, {origin[2]:.2f})"
                )
                # 更新目标尺寸为当前尺寸（方便用户调整）
                self.targetDimXSpinBox.setValue(dims[0])
                self.targetDimYSpinBox.setValue(dims[1])
                self.targetDimZSpinBox.setValue(dims[2])
        else:
            self.volumeInfoLabel.setText("未选择数据")
        
        self.updateExecuteButtonState()

    def onROIChanged(self):
        """ROI改变时的回调"""
        # 移除旧的观察者
        if self.currentROI and self.roiObserverTag:
            self.currentROI.RemoveObserver(self.roiObserverTag)
            self.roiObserverTag = None
        
        roiNode = self.roiSelector.currentNode()
        self.currentROI = roiNode
        
        if roiNode:
            # 添加观察者监听ROI修改事件，实现实时更新
            self.roiObserverTag = roiNode.AddObserver(
                roiNode.PointModifiedEvent,
                lambda caller, event: self.updateROIInfo()
            )
            self.updateROIInfo()
        else:
            self.roiInfoLabel.setText("未选择ROI")
        
        self.updateExecuteButtonState()
    
    def updateROIInfo(self):
        """更新ROI信息显示（实时更新）"""
        roiNode = self.currentROI
        if not roiNode:
            return
        
        center = [0, 0, 0]
        roiNode.GetCenter(center)
        size = roiNode.GetSize()
        
        # 计算预计裁剪后的体素尺寸
        volumeNode = self.cbctVolumeSelector.currentNode()
        if volumeNode:
            spacing = volumeNode.GetSpacing()
            estDims = [int(round(size[i] / spacing[i])) for i in range(3)]
            self.roiInfoLabel.setText(
                f"中心: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f})\n"
                f"尺寸: {size[0]:.2f} × {size[1]:.2f} × {size[2]:.2f} mm\n"
                f"预计裁剪后体素: {estDims[0]} × {estDims[1]} × {estDims[2]}"
            )
        else:
            self.roiInfoLabel.setText(
                f"中心: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f})\n"
                f"尺寸: {size[0]:.2f} × {size[1]:.2f} × {size[2]:.2f} mm"
            )

    def onCreateROI(self):
        """创建ROI按钮点击事件"""
        volumeNode = self.cbctVolumeSelector.currentNode()
        
        if not volumeNode:
            self.logCallback("错误: 请先选择CBCT数据")
            return
        
        roiNode = self.logic.createROIFromVolume(volumeNode)
        
        if roiNode:
            self.roiSelector.setCurrentNode(roiNode)
            self.logCallback(f"已创建ROI: {roiNode.GetName()}")
            self.logCallback("提示: 可在3D视图中拖动ROI手柄调整位置和大小")

    def onApplyDimensionsToROI(self):
        """应用目标尺寸到ROI"""
        volumeNode = self.cbctVolumeSelector.currentNode()
        roiNode = self.roiSelector.currentNode()
        
        if not volumeNode:
            self.logCallback("错误: 请先选择CBCT数据")
            return
        
        if not roiNode:
            self.logCallback("错误: 请先选择或创建ROI")
            return
        
        targetDimensions = [
            self.targetDimXSpinBox.value,
            self.targetDimYSpinBox.value,
            self.targetDimZSpinBox.value
        ]
        
        self.logic.updateROISizeByDimensions(roiNode, volumeNode, targetDimensions)
        self.onROIChanged()  # 更新ROI信息显示

    def updateExecuteButtonState(self):
        """更新执行按钮状态"""
        hasVolume = self.cbctVolumeSelector.currentNode() is not None
        hasROI = self.roiSelector.currentNode() is not None
        self.executeButton.enabled = hasVolume and hasROI

    def onExecutePreprocessing(self):
        """执行预处理按钮点击事件"""
        cbctVolume = self.cbctVolumeSelector.currentNode()
        roiNode = self.roiSelector.currentNode()
        
        if not cbctVolume:
            self.logCallback("错误: 请选择CBCT数据")
            return
        
        if not roiNode:
            self.logCallback("错误: 请选择ROI")
            return
        
        # 获取目标间距
        targetSpacing = [
            self.targetSpacingXSpinBox.value,
            self.targetSpacingYSpinBox.value,
            self.targetSpacingZSpinBox.value
        ]
        
        self.statusLabel.setText("预处理中...")
        self.statusLabel.setStyleSheet("color: #FFA500;")
        self.executeButton.enabled = False
        
        # 使用slicer.app.processEvents()确保UI更新
        slicer.app.processEvents()
        
        try:
            # 获取目标尺寸
            targetDimensions = [
                self.targetDimXSpinBox.value,
                self.targetDimYSpinBox.value,
                self.targetDimZSpinBox.value
            ]
            
            # 直接执行：替换原始+生成模板
            fixedVolume, templateVolume = self.logic.processCBCT(
                cbctVolume, roiNode, targetSpacing,
                targetDimensions=targetDimensions,
                replaceOriginal=True,
                createTemplateVolume=True
            )
            
            if fixedVolume or templateVolume:
                self.statusLabel.setText("预处理完成!")
                self.statusLabel.setStyleSheet("color: #008000;")
                # 更新显示信息
                self.onCBCTVolumeChanged()
                
                # 保存预处理结果节点引用
                self.lastROI = roiNode
                self.lastTemplate = templateVolume
                
                # 启用保存按钮
                self.updateSaveButtonState()
            else:
                self.statusLabel.setText("预处理失败")
                self.statusLabel.setStyleSheet("color: #FF0000;")
                
        except Exception as e:
            self.statusLabel.setText("预处理失败")
            self.statusLabel.setStyleSheet("color: #FF0000;")
            self.logCallback(f"预处理过程出错: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
        finally:
            self.executeButton.enabled = True

    def onMRIVolumeChanged(self):
        """MRI体数据改变时的回调"""
        volumeNode = self.mriVolumeSelector.currentNode()
        
        if volumeNode:
            info = self.logic.getVolumeInfo(volumeNode)
            if info:
                dims = info['dimensions']
                spacing = info['spacing']
                origin = info['origin']
                self.mriInfoLabel.setText(
                    f"尺寸: {dims[0]} × {dims[1]} × {dims[2]} voxels\n"
                    f"间距: {spacing[0]:.4f} × {spacing[1]:.4f} × {spacing[2]:.4f} mm\n"
                    f"原点: ({origin[0]:.2f}, {origin[1]:.2f}, {origin[2]:.2f})"
                )
        else:
            self.mriInfoLabel.setText("未选择数据")
        
        self.updateExecuteMRIButtonState()
    
    def onTemplateVolumeChanged(self):
        """Template Volume改变时的回调"""
        volumeNode = self.templateVolumeSelector.currentNode()
        
        if volumeNode:
            info = self.logic.getVolumeInfo(volumeNode)
            if info:
                dims = info['dimensions']
                spacing = info['spacing']
                origin = info['origin']
                self.templateInfoLabel.setText(
                    f"尺寸: {dims[0]} × {dims[1]} × {dims[2]} voxels\n"
                    f"间距: {spacing[0]:.4f} × {spacing[1]:.4f} × {spacing[2]:.4f} mm\n"
                    f"原点: ({origin[0]:.2f}, {origin[1]:.2f}, {origin[2]:.2f})"
                )
        else:
            self.templateInfoLabel.setText("未选择Template")
        
        self.updateExecuteMRIButtonState()
    
    def updateExecuteMRIButtonState(self):
        """更新MRI执行按钮状态"""
        hasMRI = self.mriVolumeSelector.currentNode() is not None
        hasTemplate = self.templateVolumeSelector.currentNode() is not None
        self.executeMRIButton.enabled = hasMRI and hasTemplate
    
    def onExecuteMRIPreprocessing(self):
        """执行MRI预处理按钮点击事件"""
        mriVolume = self.mriVolumeSelector.currentNode()
        templateVolume = self.templateVolumeSelector.currentNode()
        transformNode = self.transformSelector.currentNode()
        
        if not mriVolume:
            self.logCallback("错误: 请选择MRI数据")
            return
        
        if not templateVolume:
            self.logCallback("错误: 请选择Template Volume")
            return
        
        self.mriStatusLabel.setText("预处理中...")
        self.mriStatusLabel.setStyleSheet("color: #FFA500;")
        self.executeMRIButton.enabled = False
        
        # 使用slicer.app.processEvents()确保UI更新
        slicer.app.processEvents()
        
        try:
            # 直接执行：替换原始MRI
            movingVolume = self.logic.processMRI(
                mriVolume, 
                templateVolume, 
                transformNode,
                replaceOriginal=True
            )
            
            if movingVolume:
                self.mriStatusLabel.setText("预处理完成!")
                self.mriStatusLabel.setStyleSheet("color: #008000;")
                # 更新显示信息
                self.onMRIVolumeChanged()
                
                # 更新保存按钮状态
                self.updateSaveButtonState()
            else:
                self.mriStatusLabel.setText("预处理失败")
                self.mriStatusLabel.setStyleSheet("color: #FF0000;")
                
        except Exception as e:
            self.mriStatusLabel.setText("预处理失败")
            self.mriStatusLabel.setStyleSheet("color: #FF0000;")
            self.logCallback(f"预处理过程出错: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
        finally:
            self.executeMRIButton.enabled = True

    def updateSaveButtonState(self):
        """更新保存按钮状态"""
        # CBCT和MRI都预处理完成后才能保存
        cbctDone = self.lastROI is not None and self.lastTemplate is not None
        mriDone = self.mriVolumeSelector.currentNode() is not None
        
        self.saveResultButton.enabled = cbctDone and mriDone
        
        if cbctDone and mriDone:
            self.saveStatusLabel.setText("就绪")
            self.saveStatusLabel.setStyleSheet("color: #008000; padding: 5px;")
        else:
            self.saveStatusLabel.setText("等待预处理完成")
            self.saveStatusLabel.setStyleSheet("color: #666; padding: 5px;")
    
    def onSaveResults(self):
        """保存预处理结果按钮点击事件"""
        try:
            # 获取主文件夹名称
            mainFolderName = self.getMainFolderNameCallback()
            if not mainFolderName:
                self.logCallback("错误: 请先设置总场景文件夹名称")
                return
            
            # 获取模块子文件夹名称
            moduleFolderName = self.moduleFolderNameEdit.text.strip()
            if not moduleFolderName:
                self.logCallback("错误: 请输入模块子文件夹名称")
                return
            
            # 获取预处理后的体数据
            fixedVolume = self.cbctVolumeSelector.currentNode()
            movingVolume = self.mriVolumeSelector.currentNode()
            
            if not fixedVolume or not movingVolume:
                self.logCallback("错误: 缺少预处理后的体数据")
                return
            
            if not self.lastROI or not self.lastTemplate:
                self.logCallback("错误: 缺少ROI或Template节点")
                return
            
            self.saveStatusLabel.setText("保存中...")
            self.saveStatusLabel.setStyleSheet("color: #FFA500; padding: 5px;")
            self.saveResultButton.enabled = False
            slicer.app.processEvents()
            
            # 调用logic保存
            success = self.logic.savePreprocessingResults(
                self.lastROI,
                self.lastTemplate,
                fixedVolume,
                movingVolume,
                mainFolderName,
                moduleFolderName
            )
            
            if success:
                self.saveStatusLabel.setText("保存成功!")
                self.saveStatusLabel.setStyleSheet("color: #008000; padding: 5px;")
                self.logCallback("✓ 预处理结果已保存到场景")
            else:
                self.saveStatusLabel.setText("保存失败")
                self.saveStatusLabel.setStyleSheet("color: #FF0000; padding: 5px;")
                
        except Exception as e:
            self.saveStatusLabel.setText("保存失败")
            self.saveStatusLabel.setStyleSheet("color: #FF0000; padding: 5px;")
            self.logCallback(f"保存过程出错: {str(e)}")
            import traceback
            self.logCallback(traceback.format_exc())
        finally:
            self.saveResultButton.enabled = True
    
    def getModuleFolderName(self):
        """获取模块文件夹名称"""
        return "DataPreprocessing"
