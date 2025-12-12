"""
ROI Mask Set Widget - UI界面
"""
import qt
import ctk
import slicer
from .roi_mask_set_logic import ROIMaskSetLogic


class ROIMaskSetWidget:
    """
    ROI Mask Set 的UI组件类
    负责基于高分辨率ROI浮动图像生成固定图像的掩膜
    """

    def __init__(self, parent, logCallback, getMainFolderNameCallback):
        """
        初始化 ROI Mask Set Widget
        
        :param parent: 父布局
        :param logCallback: 日志回调函数
        :param getMainFolderNameCallback: 获取主文件夹名称的回调函数
        """
        self.parent = parent
        self.logCallback = logCallback
        self.getMainFolderNameCallback = getMainFolderNameCallback
        self.logic = ROIMaskSetLogic(logCallback=logCallback)
        
        # UI 组件引用
        self.roiFixedVolumeSelector = None
        self.roiMovingVolumeSelector = None
        self.transformSelector = None
        self.expansionSlider = None
        self.roiMaskNameEdit = None  # 掩膜名称输入框
        self.generateMaskButton = None
        self.cancelButton = None  # 取消按钮
        self.saveResultButton = None
        self.roiStatusLabel = None
        self.roiModuleFolderNameEdit = None
        
        # 生成的掩膜节点
        self.maskVolume = None
        
        self.setupUI()

    def setupUI(self):
        """设置 ROI Mask Set 的UI界面"""
        # ROI Mask Set 模块
        roiMaskCollapsibleButton = ctk.ctkCollapsibleButton()
        roiMaskCollapsibleButton.text = "ROI Mask Set"
        roiMaskCollapsibleButton.collapsed = True  # 默认折叠
        self.parent.addWidget(roiMaskCollapsibleButton)
        roiMaskFormLayout = qt.QFormLayout(roiMaskCollapsibleButton)

        # 模块说明
        """
        descLabel = qt.QLabel(
            "本模块用于生成颞下颌关节ROI区域的掩膜，用于后续精细配准。\n"
            "策略：基于高分辨率ROI Moving Volume的物理范围自动生成Fixed Volume的掩膜。\n"
            "提示：请从Data Manager场景文件夹中选择已添加的ROI高分辨率MRI图像。"
        )
        descLabel.setWordWrap(True)
        descLabel.setStyleSheet("color: #2E86AB; margin: 5px 0px; padding: 5px; background-color: #E8F4F8;")
        roiMaskFormLayout.addRow(descLabel)
        """
        # 选择数据
        selectLabel = qt.QLabel("选择设置ROI Mask的数据:")
        selectLabel.setStyleSheet("font-weight: bold; margin-top: 10px;")
        roiMaskFormLayout.addRow(selectLabel)

        # Fixed Volume 选择器
        self.roiFixedVolumeSelector = slicer.qMRMLNodeComboBox()
        self.roiFixedVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.roiFixedVolumeSelector.selectNodeUponCreation = False
        self.roiFixedVolumeSelector.addEnabled = False
        self.roiFixedVolumeSelector.removeEnabled = False
        self.roiFixedVolumeSelector.noneEnabled = True
        self.roiFixedVolumeSelector.showHidden = False
        self.roiFixedVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.roiFixedVolumeSelector.setToolTip("选择 Fixed Volume (CBCT)，通常从Data Manager文件夹选择")
        roiMaskFormLayout.addRow("Fixed Volume (CBCT): ", self.roiFixedVolumeSelector)

        # ROI Moving Volume 选择器
        self.roiMovingVolumeSelector = slicer.qMRMLNodeComboBox()
        self.roiMovingVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.roiMovingVolumeSelector.selectNodeUponCreation = False
        self.roiMovingVolumeSelector.addEnabled = False
        self.roiMovingVolumeSelector.removeEnabled = False
        self.roiMovingVolumeSelector.noneEnabled = True
        self.roiMovingVolumeSelector.showHidden = False
        self.roiMovingVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.roiMovingVolumeSelector.setToolTip(
            "选择高分辨率的 ROI Moving Volume (局部MRI)\n"
            "如：Moving_Volume_右斜矢、Moving_Volume_左斜矢、Moving_Volume_右斜冠、Moving_Volume_右斜冠"
        )
        roiMaskFormLayout.addRow("ROI Moving Volume (局部MRI): ", self.roiMovingVolumeSelector)

        # 粗配准变换选择器
        transformLabel = qt.QLabel("粗配准变换:")
        transformLabel.setStyleSheet("font-weight: bold; margin-top: 10px;")
        roiMaskFormLayout.addRow(transformLabel)
        
        self.transformSelector = slicer.qMRMLNodeComboBox()
        self.transformSelector.nodeTypes = ["vtkMRMLTransformNode"]
        self.transformSelector.selectNodeUponCreation = False
        self.transformSelector.addEnabled = False
        self.transformSelector.removeEnabled = False
        self.transformSelector.noneEnabled = True
        self.transformSelector.showHidden = False
        self.transformSelector.setMRMLScene(slicer.mrmlScene)
        self.transformSelector.setToolTip(
            "选择粗配准得到的变换矩阵\n"
            "通常是Coarse Registration模块生成的CoarseReg_Transform\n"
            "该变换将自动应用到ROI Moving Volume来计算掩膜"
        )
        roiMaskFormLayout.addRow("粗配准变换 (可选): ", self.transformSelector)

        # 重要提示
        """
        warningLabel = qt.QLabel(
            "💡 提示：选择粗配准变换后，系统会自动应用到ROI Moving Volume进行掩膜计算"
        )
        warningLabel.setWordWrap(True)
        warningLabel.setStyleSheet(
            "color: #1976D2; margin: 10px 0px; "
            "padding: 8px; background-color: #E3F2FD; border-left: 4px solid #1976D2;"
        )
        roiMaskFormLayout.addRow(warningLabel)
        """
        # 掩膜参数设置
        paramLabel = qt.QLabel("掩膜参数设置:")
        paramLabel.setStyleSheet("font-weight: bold; margin-top: 10px;")
        roiMaskFormLayout.addRow(paramLabel)

        # 膨胀量滑块
        expansionLayout = qt.QHBoxLayout()
        
        expansionLabel = qt.QLabel("膨胀量 (mm):")
        expansionLayout.addWidget(expansionLabel)
        
        self.expansionSlider = ctk.ctkSliderWidget()
        self.expansionSlider.minimum = 0
        self.expansionSlider.maximum = 30
        self.expansionSlider.value = 5
        self.expansionSlider.singleStep = 1
        self.expansionSlider.setToolTip(
            "掩膜膨胀量，防止ROI范围太死。"
        )
        expansionLayout.addWidget(self.expansionSlider)
        
        roiMaskFormLayout.addRow(expansionLayout)

        # ROI掩膜名称设置
        self.roiMaskNameEdit = qt.QLineEdit()
        self.roiMaskNameEdit.text = "Fixed_ROI_Mask"  # 默认名称
        self.roiMaskNameEdit.setToolTip("设置生成的ROI掩膜的名称")
        roiMaskFormLayout.addRow("ROI掩膜名称:", self.roiMaskNameEdit)

        # 生成掩膜按钮
        generateLabel = qt.QLabel("生成ROI掩膜:")
        generateLabel.setStyleSheet("font-weight: bold; margin-top: 10px;")
        roiMaskFormLayout.addRow(generateLabel)

        buttonLayout = qt.QHBoxLayout()
        self.generateMaskButton = qt.QPushButton("生成ROI掩膜")
        self.generateMaskButton.toolTip = "基于ROI Moving Volume的物理范围自动生成固定图像的掩膜"
        self.generateMaskButton.enabled = False
        self.generateMaskButton.connect('clicked(bool)', self.onGenerateMask)
        buttonLayout.addWidget(self.generateMaskButton)
        
        self.cancelButton = qt.QPushButton("取消")
        self.cancelButton.toolTip = "取消正在进行的掩膜生成"
        self.cancelButton.enabled = False
        self.cancelButton.connect('clicked(bool)', self.onCancelGeneration)
        buttonLayout.addWidget(self.cancelButton)
        
        roiMaskFormLayout.addRow(buttonLayout)

        # 保存结果
        saveLabel = qt.QLabel("保存ROI掩膜结果:")
        saveLabel.setStyleSheet("font-weight: bold; margin-top: 10px;")
        roiMaskFormLayout.addRow(saveLabel)

        # ROI Mask Set 子文件夹名称
        self.roiModuleFolderNameEdit = qt.QLineEdit()
        self.roiModuleFolderNameEdit.text = "ROI Mask Set"
        self.roiModuleFolderNameEdit.setToolTip("ROI Mask Set 模块在总场景文件夹下的子文件夹名称")
        roiMaskFormLayout.addRow("ROI Mask Set场景子文件夹:", self.roiModuleFolderNameEdit)

        self.saveResultButton = qt.QPushButton("保存ROI掩膜结果到场景")
        self.saveResultButton.toolTip = "将掩膜和相关数据保存到场景文件夹"
        self.saveResultButton.enabled = False
        self.saveResultButton.connect('clicked(bool)', self.onSaveResult)
        roiMaskFormLayout.addRow(self.saveResultButton)

        # 状态信息
        self.roiStatusLabel = qt.QLabel("状态: 等待选择数据")
        self.roiStatusLabel.setStyleSheet("color: gray;")
        roiMaskFormLayout.addRow(self.roiStatusLabel)

        # 添加模块末尾分隔线
        separator = qt.QFrame()
        separator.setFrameShape(qt.QFrame.HLine)
        separator.setFrameShadow(qt.QFrame.Plain)
        separator.setLineWidth(2)
        separator.setMidLineWidth(0)
        separator.setStyleSheet("QFrame { background-color: #000000; max-height: 2px; margin: 15px 0px; }")
        roiMaskFormLayout.addRow(separator)

        # 连接信号
        self.roiFixedVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)
        self.roiMovingVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)
        self.transformSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)

    def updateButtonStates(self):
        """更新按钮状态"""
        try:
            hasFixed = self.roiFixedVolumeSelector.currentNode() is not None
            hasROIMoving = self.roiMovingVolumeSelector.currentNode() is not None
            hasTransform = self.transformSelector.currentNode() is not None
            
            # 生成掩膜按钮需要两个数据都选中
            self.generateMaskButton.enabled = hasFixed and hasROIMoving
            
            # 更新状态标签
            if not hasFixed or not hasROIMoving:
                self.roiStatusLabel.text = "状态: 请选择 Fixed Volume 和 ROI Moving Volume"
                self.roiStatusLabel.setStyleSheet("color: orange;")
            elif not hasTransform:
                self.roiStatusLabel.text = "状态: 建议选择粗配准变换以获得更准确的掩膜"
                self.roiStatusLabel.setStyleSheet("color: #FF9800;")
            else:
                self.roiStatusLabel.text = "状态: 准备就绪，可以生成掩膜"
                self.roiStatusLabel.setStyleSheet("color: green;")
            
        except Exception as e:
            self.logCallback(f"更新按钮状态失败: {str(e)}")

    def onGenerateMask(self):
        """生成ROI掩膜（异步）"""
        try:
            fixedVolume = self.roiFixedVolumeSelector.currentNode()
            roiMovingVolume = self.roiMovingVolumeSelector.currentNode()
            transformNode = self.transformSelector.currentNode()
            expansionMm = self.expansionSlider.value
            maskName = self.roiMaskNameEdit.text.strip()  # 获取用户输入的掩膜名称

            if not fixedVolume or not roiMovingVolume:
                self.showError("请选择 Fixed Volume 和 ROI Moving Volume")
                return
            
            if not maskName:
                self.showError("请输入掩膜名称")
                return

            self.logCallback(f"===== 开始生成 ROI 掩膜（异步模式）=====")
            self.logCallback(f"  掩膜名称: {maskName}")
            
            # 禁用生成按钮，启用取消按钮
            self.generateMaskButton.enabled = False
            self.cancelButton.enabled = True  # 启用取消按钮
            self.saveResultButton.enabled = False
            
            # 更新状态
            self.roiStatusLabel.text = "状态: 正在生成掩膜..."
            self.roiStatusLabel.setStyleSheet("color: blue;")
            
            # 异步调用生成掩膜
            self.logic.generateROIMaskAsync(
                fixedVolume, 
                roiMovingVolume, 
                transformNode,
                expansionMm,
                maskName,  # 传递掩膜名称
                self.onProgress,
                self.onCompleted
            )

        except Exception as e:
            self.showError(f"生成掩膜失败: {str(e)}")
            self.generateMaskButton.enabled = True
            self.cancelButton.enabled = False
    
    def onProgress(self, percent, message):
        """进度更新回调"""
        self.roiStatusLabel.text = f"状态: {message} ({percent}%)"
        self.roiStatusLabel.setStyleSheet("color: blue;")
        slicer.app.processEvents()  # 更新UI
    
    def onCompleted(self, maskVolume):
        """生成完成回调"""
        try:
            self.generateMaskButton.enabled = True
            self.cancelButton.enabled = False  # 禁用取消按钮
            
            if maskVolume:
                self.maskVolume = maskVolume
                self.logCallback(f"✓ ROI掩膜生成完成")
                self.roiStatusLabel.text = "状态: 掩膜生成成功，请保存到场景"
                self.roiStatusLabel.setStyleSheet("color: green;")

                # 启用保存按钮
                self.saveResultButton.enabled = True
            else:
                self.showError("掩膜生成失败")

        except Exception as e:
            self.showError(f"完成回调失败: {str(e)}")
    
    def onCancelGeneration(self):
        """取消掩膜生成"""
        try:
            self.logCallback("用户点击了取消按钮")
            self.logic.cancelAsyncGeneration()
            self.roiStatusLabel.text = "状态: 已取消"
            self.roiStatusLabel.setStyleSheet("color: orange;")
            self.generateMaskButton.enabled = True
            self.cancelButton.enabled = False  # 禁用取消按钮
        except Exception as e:
            self.logCallback(f"取消操作失败: {str(e)}")

    def onSaveResult(self):
        """保存ROI掩膜结果到场景"""
        try:
            if not self.maskVolume:
                self.showError("请先生成掩膜")
                return

            fixedVolume = self.roiFixedVolumeSelector.currentNode()
            roiMovingVolume = self.roiMovingVolumeSelector.currentNode()

            # 获取文件夹名称
            mainFolderName = self.getMainFolderNameCallback()
            moduleFolderName = self.roiModuleFolderNameEdit.text

            if not mainFolderName or not moduleFolderName:
                self.showError("请输入文件夹名称")
                return

            self.logCallback(f"正在保存 ROI 掩膜结果到场景...")
            self.logCallback(f"  总文件夹: {mainFolderName}")
            self.logCallback(f"  ROI Mask Set 子文件夹: {moduleFolderName}")

            # 保存原始maskVolume引用
            originalMaskVolume = self.maskVolume

            # 调用 Logic 保存结果
            success = self.logic.saveROIMaskToScene(
                fixedVolume, roiMovingVolume, self.maskVolume,
                mainFolderName, moduleFolderName
            )

            if success:
                # 删除原始的临时节点
                if originalMaskVolume:
                    slicer.mrmlScene.RemoveNode(originalMaskVolume)
                    self.logCallback(f"  ✓ 已删除原始临时掩膜节点")
                
                self.maskVolume = None  # 清除引用
                
                self.logCallback(f"✓ ROI掩膜结果已保存到场景文件夹")
                self.logCallback(f"  路径: {mainFolderName}/{moduleFolderName}")
                self.roiStatusLabel.text = "状态: 结果已保存到场景"
                self.roiStatusLabel.setStyleSheet("color: green;")
                
                # 禁用保存按钮（已保存）
                self.saveResultButton.enabled = False
            else:
                self.showError("保存结果失败")

        except Exception as e:
            self.showError(f"保存结果失败: {str(e)}")

    def showError(self, errorMessage):
        """显示错误信息"""
        self.logCallback(f"✗ 错误: {errorMessage}")
        self.roiStatusLabel.text = f"状态: 错误"
        self.roiStatusLabel.setStyleSheet("color: red;")
        slicer.util.errorDisplay(errorMessage)
        import traceback
        self.logCallback(traceback.format_exc())
