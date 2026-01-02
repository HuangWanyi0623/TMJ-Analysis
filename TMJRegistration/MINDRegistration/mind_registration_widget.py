"""
MIND Registration Widget - MIND配准的UI界面
"""
import os
import time
from datetime import datetime
import qt
import ctk
import slicer
from .mind_registration_logic import MINDRegistrationLogic


class MINDRegistrationWidget:
    """
    MIND配准的UI组件类
    负责用户交互和参数设置
    """

    def __init__(self, parent, logCallback):
        """
        初始化 MIND Registration Widget
        
        :param parent: 父布局
        :param logCallback: 日志回调函数
        """
        self.parent = parent
        self.logCallback = logCallback
        self.logic = MINDRegistrationLogic(logCallback=logCallback)
        
        # UI 组件引用
        self.fixedVolumeSelector = None
        self.movingVolumeSelector = None
        self.fixedMaskSelector = None
        self.initialTransformSelector = None
        self.initModeComboBox = None
        self.configStrategyComboBox = None
        self.samplingPercentageSpinBox = None
        self.outputTransformSelector = None
        self.applyTransformCheckBox = None
        self.runButton = None
        self.cancelButton = None
        self.progressBar = None
        self.statusLabel = None
        
        # 运行状态
        self.registrationStartTime = None
        self._customConfigPath = None
        
        self.setupUI()

    def setupUI(self):
        """设置 MIND Registration 的UI界面"""
        # MIND Registration 区域
        mindRegistrationCollapsibleButton = ctk.ctkCollapsibleButton()
        mindRegistrationCollapsibleButton.text = "MIND Registration"
        mindRegistrationCollapsibleButton.collapsed = True  # 默认折叠
        self.parent.addWidget(mindRegistrationCollapsibleButton)
        mindFormLayout = qt.QFormLayout(mindRegistrationCollapsibleButton)

        # ===== 输入参数 =====
        inputLabel = qt.QLabel("从已加载数据中选择:")
        inputLabel.setStyleSheet("font-weight: bold;")
        mindFormLayout.addRow(inputLabel)
        
        inputGroupBox = qt.QGroupBox()
        inputLayout = qt.QFormLayout(inputGroupBox)
        mindFormLayout.addRow(inputGroupBox)

        # 固定图像选择器
        self.fixedVolumeSelector = slicer.qMRMLNodeComboBox()
        self.fixedVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.fixedVolumeSelector.selectNodeUponCreation = False
        self.fixedVolumeSelector.addEnabled = False
        self.fixedVolumeSelector.removeEnabled = False
        self.fixedVolumeSelector.noneEnabled = True
        self.fixedVolumeSelector.showHidden = False
        self.fixedVolumeSelector.showChildNodeTypes = False
        self.fixedVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.fixedVolumeSelector.setToolTip("选择固定图像（参考图像）")
        inputLayout.addRow("Fixed Volume(CBCT):", self.fixedVolumeSelector)

        # 移动图像选择器
        self.movingVolumeSelector = slicer.qMRMLNodeComboBox()
        self.movingVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.movingVolumeSelector.selectNodeUponCreation = False
        self.movingVolumeSelector.addEnabled = False
        self.movingVolumeSelector.removeEnabled = False
        self.movingVolumeSelector.noneEnabled = True
        self.movingVolumeSelector.showHidden = False
        self.movingVolumeSelector.showChildNodeTypes = False
        self.movingVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.movingVolumeSelector.setToolTip("选择移动图像（待配准图像）")
        inputLayout.addRow("Moving Volume(MRI):", self.movingVolumeSelector)

        # 固定掩膜选择器（可选）
        self.fixedMaskSelector = slicer.qMRMLNodeComboBox()
        self.fixedMaskSelector.nodeTypes = ["vtkMRMLLabelMapVolumeNode", "vtkMRMLScalarVolumeNode"]
        self.fixedMaskSelector.selectNodeUponCreation = False
        self.fixedMaskSelector.addEnabled = False
        self.fixedMaskSelector.removeEnabled = False
        self.fixedMaskSelector.noneEnabled = True
        self.fixedMaskSelector.showHidden = False
        self.fixedMaskSelector.showChildNodeTypes = False
        self.fixedMaskSelector.setMRMLScene(slicer.mrmlScene)
        self.fixedMaskSelector.setToolTip("选择固定图像的掩膜（可选，用于局部配准）")
        inputLayout.addRow("固定掩膜 (可选):", self.fixedMaskSelector)

        # 初始变换选择器（可选）
        self.initialTransformSelector = slicer.qMRMLNodeComboBox()
        self.initialTransformSelector.nodeTypes = ["vtkMRMLTransformNode"]
        self.initialTransformSelector.selectNodeUponCreation = False
        self.initialTransformSelector.addEnabled = False
        self.initialTransformSelector.removeEnabled = False
        self.initialTransformSelector.noneEnabled = True
        self.initialTransformSelector.showHidden = False
        self.initialTransformSelector.showChildNodeTypes = True
        self.initialTransformSelector.setMRMLScene(slicer.mrmlScene)
        self.initialTransformSelector.setToolTip("选择初始变换（可选，用于粗配准后的精配准）")
        inputLayout.addRow("初始变换 (可选):", self.initialTransformSelector)

        # 初始化模式选择器（无初始变换时使用）
        self.initModeComboBox = qt.QComboBox()
        self.initModeComboBox.addItem("无", "none")  # 占位选项，当有初始变换时显示
        self.initModeComboBox.addItem("几何中心 (Geometry)", "geometry")
        self.initModeComboBox.addItem("质心 (Moments)", "moments")
        self.initModeComboBox.setCurrentIndex(1)  # 默认选择几何中心
        self.initModeComboBox.setToolTip(
            "无初始变换时的对齐方式:\n"
            "• 几何中心: 使用图像边界框的中心对齐\n"
            "• 质心: 使用图像强度的质心对齐（推荐用于偏心对象）"
        )
        inputLayout.addRow("初始化模式:", self.initModeComboBox)
        
        # 连接初始变换选择器信号，用于更新初始化模式下拉框状态
        self.initialTransformSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onInitialTransformChanged)

        # ===== 配准参数 =====
        paramLabel = qt.QLabel("配准参数:")
        paramLabel.setStyleSheet("font-weight: bold; margin-top: 10px;")
        mindFormLayout.addRow(paramLabel)
        
        paramGroupBox = qt.QGroupBox()
        paramLayout = qt.QFormLayout(paramGroupBox)
        mindFormLayout.addRow(paramGroupBox)

        # 配准策略选择（下拉框）
        self.configStrategyComboBox = qt.QComboBox()
        self.configStrategyComboBox.addItem("Rigid", "Rigid.json")
        self.configStrategyComboBox.addItem("Affine", "Affine.json")
        self.configStrategyComboBox.addItem("Rigid+Affine", "Rigid+Affine.json")
        self.configStrategyComboBox.setToolTip("选择配准策略")
        
        # 创建水平布局，包含下拉框和浏览按钮
        strategyLayout = qt.QHBoxLayout()
        strategyLayout.addWidget(self.configStrategyComboBox)
        
        # 浏览按钮（三个点）
        browseButton = qt.QPushButton("...")
        browseButton.setMaximumWidth(30)
        browseButton.setToolTip("浏览选择其他配置文件")
        browseButton.connect('clicked(bool)', self.onBrowseConfig)
        strategyLayout.addWidget(browseButton)
        
        paramLayout.addRow("配准策略:", strategyLayout)

        # 采样比例
        self.samplingPercentageSpinBox = qt.QDoubleSpinBox()
        self.samplingPercentageSpinBox.setRange(0.01, 1.0)
        self.samplingPercentageSpinBox.setSingleStep(0.05)
        self.samplingPercentageSpinBox.setValue(0.10)
        self.samplingPercentageSpinBox.setToolTip("配准时使用的体素采样比例 (0.01-1.0)\nMIND推荐: 0.10-0.15")
        paramLayout.addRow("采样比例:", self.samplingPercentageSpinBox)

        # ===== 输出设置 =====
        outputLabel = qt.QLabel("输出设置:")
        outputLabel.setStyleSheet("font-weight: bold; margin-top: 10px;")
        mindFormLayout.addRow(outputLabel)
        
        outputGroupBox = qt.QGroupBox()
        outputLayout = qt.QFormLayout(outputGroupBox)
        mindFormLayout.addRow(outputGroupBox)

        # 输出变换选择器
        self.outputTransformSelector = slicer.qMRMLNodeComboBox()
        self.outputTransformSelector.nodeTypes = ["vtkMRMLTransformNode"]
        self.outputTransformSelector.selectNodeUponCreation = True
        self.outputTransformSelector.addEnabled = True
        self.outputTransformSelector.removeEnabled = True
        self.outputTransformSelector.noneEnabled = True
        self.outputTransformSelector.renameEnabled = True
        self.outputTransformSelector.showHidden = False
        self.outputTransformSelector.showChildNodeTypes = True
        self.outputTransformSelector.baseName = "MINDRegistrationTransform"
        self.outputTransformSelector.setMRMLScene(slicer.mrmlScene)
        self.outputTransformSelector.setToolTip("选择或创建输出变换节点")
        outputLayout.addRow("输出变换:", self.outputTransformSelector)

        # 应用变换到移动图像
        self.applyTransformCheckBox = qt.QCheckBox("配准后自动应用变换到移动图像")
        self.applyTransformCheckBox.setChecked(True)
        outputLayout.addRow(self.applyTransformCheckBox)

        # ===== 执行按钮 =====
        buttonLayout = qt.QHBoxLayout()
        
        self.runButton = qt.QPushButton("开始配准")
        self.runButton.toolTip = "执行MIND配准"
        self.runButton.enabled = True
        self.runButton.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; color: green; }")
        self.runButton.connect('clicked(bool)', self.onRunButtonClicked)
        buttonLayout.addWidget(self.runButton)

        self.cancelButton = qt.QPushButton("取消配准")
        self.cancelButton.toolTip = "强制停止配准"
        self.cancelButton.enabled = False
        self.cancelButton.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; color: red; }")
        self.cancelButton.connect('clicked(bool)', self.onCancelButtonClicked)
        buttonLayout.addWidget(self.cancelButton)
        
        mindFormLayout.addRow(buttonLayout)

        # 进度条
        self.progressBar = qt.QProgressBar()
        self.progressBar.setVisible(False)
        mindFormLayout.addRow(self.progressBar)
        
        # 状态信息
        self.statusLabel = qt.QLabel("状态: 等待选择数据")
        self.statusLabel.setStyleSheet("color: gray;")
        mindFormLayout.addRow(self.statusLabel)
        
        # 添加模块末尾分隔线（黑色粗线）
        separator = qt.QFrame()
        separator.setFrameShape(qt.QFrame.HLine)
        separator.setFrameShadow(qt.QFrame.Plain)
        separator.setLineWidth(2)
        separator.setMidLineWidth(0)
        separator.setStyleSheet("QFrame { background-color: #000000; max-height: 2px; margin: 15px 0px; }")
        mindFormLayout.addRow(separator)

        # 连接信号以更新状态
        self.fixedVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)
        self.movingVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)

    def onInitialTransformChanged(self, node):
        """当初始变换选择器改变时，更新初始化模式下拉框状态"""
        if node:
            # 选择了初始变换，设置为"无"并禁用
            self.initModeComboBox.setCurrentIndex(0)  # 设置为"无"
            self.initModeComboBox.setEnabled(False)
            self.initModeComboBox.setToolTip("已选择初始变换，将使用初始变换进行对齐")
        else:
            # 未选择初始变换，恢复到默认选项并启用
            if self.initModeComboBox.currentIndex == 0:  # 如果当前是"无"
                self.initModeComboBox.setCurrentIndex(1)  # 恢复为"几何中心"
            self.initModeComboBox.setEnabled(True)
            self.initModeComboBox.setToolTip(
                "无初始变换时的对齐方式:\n"
                "• 几何中心: 使用图像边界框的中心对齐\n"
                "• 质心: 使用图像强度的质心对齐（推荐用于偏心对象）"
            )

    def updateButtonStates(self):
        """更新按钮状态和UI状态"""
        fixedNode = self.fixedVolumeSelector.currentNode()
        movingNode = self.movingVolumeSelector.currentNode()
        
        # 更新状态标签
        if fixedNode and movingNode:
            self.updateStatus("准备就绪", "green")
        elif fixedNode:
            self.updateStatus("等待选择移动图像", "orange")
        elif movingNode:
            self.updateStatus("等待选择固定图像", "orange")
        else:
            self.updateStatus("等待选择数据", "gray")

    def onBrowseConfig(self):
        """浏览选择配置文件"""
        fileDialog = qt.QFileDialog()
        fileDialog.setFileMode(qt.QFileDialog.ExistingFile)
        fileDialog.setNameFilter("JSON Files (*.json)")
        
        # 设置默认目录为 Backend/config/MIND
        modulePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        defaultDir = os.path.join(modulePath, "Backend", "config", "MIND")
        if os.path.exists(defaultDir):
            fileDialog.setDirectory(defaultDir)
        
        if fileDialog.exec_():
            selectedFiles = fileDialog.selectedFiles()
            if selectedFiles:
                self._customConfigPath = selectedFiles[0]
                # 更新下拉框显示为自定义
                self.configStrategyComboBox.setCurrentIndex(-1)
                self.logCallback(f"已选择自定义配置: {os.path.basename(self._customConfigPath)}")
    
    def getConfigPath(self):
        """获取当前选择的配置文件路径"""
        # 如果有自定义路径，优先使用
        if self._customConfigPath and os.path.exists(self._customConfigPath):
            return self._customConfigPath
        
        # 否则使用下拉框选择的内置配置
        modulePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        configFileName = self.configStrategyComboBox.currentData
        if configFileName:
            configPath = os.path.join(modulePath, "Backend", "config", "MIND", configFileName)
            if os.path.exists(configPath):
                return configPath
        
        return None

    def updateStatus(self, status, color="gray"):
        """更新状态显示"""
        self.statusLabel.setText(f"状态: {status}")
        self.statusLabel.setStyleSheet(f"color: {color};")

    def onRunButtonClicked(self):
        """执行配准"""
        # 验证输入
        fixedNode = self.fixedVolumeSelector.currentNode()
        movingNode = self.movingVolumeSelector.currentNode()

        if not fixedNode or not movingNode:
            slicer.util.errorDisplay("请选择固定图像和移动图像")
            return

        # 获取参数
        samplingPercentage = self.samplingPercentageSpinBox.value
        fixedMaskNode = self.fixedMaskSelector.currentNode()
        initialTransformNode = self.initialTransformSelector.currentNode()
        outputTransformNode = self.outputTransformSelector.currentNode()
        # 只有在没有初始变换时才使用初始化模式
        initMode = None
        if not initialTransformNode:
            currentData = self.initModeComboBox.currentData
            if currentData and currentData != "none":
                initMode = currentData
            else:
                initMode = "geometry"  # 默认几何中心

        # 如果没有选择输出变换节点，创建一个
        if not outputTransformNode:
            outputTransformNode = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLLinearTransformNode", "MINDRegistrationTransform")
            self.outputTransformSelector.setCurrentNode(outputTransformNode)

        self.logCallback("=" * 50)
        self.logCallback(f"开始MIND配准: {movingNode.GetName()} -> {fixedNode.GetName()}")
        
        # 获取配置文件路径
        configPath = self.getConfigPath()
        if not configPath or not os.path.exists(configPath):
            slicer.util.errorDisplay("请选择有效的配准配置文件")
            return
        
        self.logCallback(f"配准配置: {os.path.basename(configPath)}")
        self.logCallback(f"采样比例: {samplingPercentage}")
        if not initialTransformNode:
            self.logCallback(f"初始化模式: {initMode}")

        # 记录开始时间
        self.registrationStartTime = time.time()
        self.updateStatus("配准中...", "blue")

        self.runButton.enabled = False
        self.cancelButton.enabled = True

        try:
            qt.QApplication.setOverrideCursor(qt.Qt.WaitCursor)
            
            # 设置完成回调
            self.logic.setFinishCallback(self.onRegistrationFinished)
            
            # 执行配准 (异步)
            success = self.logic.runRegistration(
                fixedNode=fixedNode,
                movingNode=movingNode,
                outputTransformNode=outputTransformNode,
                configPath=configPath,
                samplingPercentage=samplingPercentage,
                fixedMaskNode=fixedMaskNode,
                initialTransformNode=initialTransformNode,
                initMode=initMode
            )
            
            qt.QApplication.restoreOverrideCursor()
            
            if not success:
                self.logCallback("❌ 配准启动失败")
                self.updateStatus("配准启动失败", "red")
                self.runButton.enabled = True
                self.cancelButton.enabled = False

        except Exception as e:
            qt.QApplication.restoreOverrideCursor()
            elapsed_time = time.time() - self.registrationStartTime if self.registrationStartTime else 0
            self.logCallback(f"❌ 配准出错: {str(e)} (耗时: {elapsed_time:.2f} 秒)")
            self.updateStatus("配准出错", "red")
            slicer.util.errorDisplay(f"配准出错: {str(e)}")
            self.runButton.enabled = True
            self.cancelButton.enabled = False

    def onRegistrationFinished(self, success, outputTransformNode):
        """配准完成回调"""
        # 计算耗时
        elapsed_time = time.time() - self.registrationStartTime
        time_str = f"耗时: {elapsed_time:.2f} 秒"

        if success:
            self.logCallback(f"✅ MIND配准完成! {time_str}")
            self.updateStatus(f"配准完成 ({time_str})", "green")
            
            # 应用变换到移动图像
            if self.applyTransformCheckBox.isChecked() and outputTransformNode:
                movingNode = self.movingVolumeSelector.currentNode()
                if movingNode:
                    movingNode.SetAndObserveTransformNodeID(outputTransformNode.GetID())
                    self.logCallback(f"已将变换应用到: {movingNode.GetName()}")
        else:
            self.logCallback(f"❌ 配准失败 ({time_str})")
            self.updateStatus(f"配准失败", "red")
            slicer.util.errorDisplay("配准失败，请查看日志获取详细信息")

        self.runButton.enabled = True
        self.cancelButton.enabled = False

    def onCancelButtonClicked(self):
        """取消配准"""
        self.logCallback("⚠️ 正在取消配准...")
        self.updateStatus("正在取消...", "orange")
        
        try:
            self.logic.cancelRegistration()
            self.logCallback("✅ 配准已取消")
            
            # 计算耗时
            if self.registrationStartTime:
                elapsed_time = time.time() - self.registrationStartTime
                self.updateStatus(f"已取消 (耗时: {elapsed_time:.2f} 秒)", "orange")
        except Exception as e:
            self.logCallback(f"❌ 取消失败: {str(e)}")
        finally:
            self.runButton.enabled = True
            self.cancelButton.enabled = False
