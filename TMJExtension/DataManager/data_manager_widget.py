"""
Data Manager Widget - 数据管理模块的UI界面
"""
import qt
import ctk
import slicer
from datetime import datetime
from .data_manager_logic import DataManagerLogic


class DataManagerWidget:
    """
    Data Manager 的UI组件类
    负责数据导入、管理和显示
    """

    def __init__(self, parent, logCallback):
        """
        初始化 Data Manager Widget
        
        :param parent: 父布局
        :param logCallback: 日志回调函数
        """
        self.parent = parent
        self.logCallback = logCallback
        self.logic = DataManagerLogic(logCallback=logCallback)
        
        # UI 组件引用
        self.fixedVolumeSelector = None
        self.movingVolumeSelector = None
        self.roiVolumeSelectors = {}  # 存储4个ROI volume选择器
        self.mainFolderNameEdit = None
        self.moduleFolderNameEdit = None
        self.loadDataButton = None
        self.statusLabel = None
        
        self.setupUI()

    def setupUI(self):
        """设置 Data Manager 的UI界面"""
        # Data Manager 区域
        dataManagerCollapsibleButton = ctk.ctkCollapsibleButton()
        dataManagerCollapsibleButton.text = "Data Manager"
        dataManagerCollapsibleButton.collapsed = True  # 默认折叠
        self.parent.addWidget(dataManagerCollapsibleButton)
        dataManagerFormLayout = qt.QFormLayout(dataManagerCollapsibleButton)

        # 从已加载数据中选择
        importLabel0 = qt.QLabel("从已加载数据中选择:")
        importLabel0.setStyleSheet("font-weight: bold;")
        dataManagerFormLayout.addRow(importLabel0)
        
        # Fixed Volume 选择器 (通常是 CT)
        fixedVolumeLayout = qt.QVBoxLayout()
        self.fixedVolumeSelector = slicer.qMRMLNodeComboBox()
        self.fixedVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.fixedVolumeSelector.selectNodeUponCreation = True
        self.fixedVolumeSelector.addEnabled = False
        self.fixedVolumeSelector.removeEnabled = False
        self.fixedVolumeSelector.noneEnabled = True
        self.fixedVolumeSelector.showHidden = False
        self.fixedVolumeSelector.showChildNodeTypes = False
        self.fixedVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.fixedVolumeSelector.setToolTip("选择固定图像 (CBCT)")
        fixedVolumeLayout.addWidget(self.fixedVolumeSelector)
        dataManagerFormLayout.addRow("Fixed Volume(CBCT): ", fixedVolumeLayout)

        # Moving Volume 选择器 (通常是 MR)
        movingVolumeLayout = qt.QVBoxLayout()
        self.movingVolumeSelector = slicer.qMRMLNodeComboBox()
        self.movingVolumeSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
        self.movingVolumeSelector.selectNodeUponCreation = True
        self.movingVolumeSelector.addEnabled = False
        self.movingVolumeSelector.removeEnabled = False
        self.movingVolumeSelector.noneEnabled = True
        self.movingVolumeSelector.showHidden = False
        self.movingVolumeSelector.showChildNodeTypes = False
        self.movingVolumeSelector.setMRMLScene(slicer.mrmlScene)
        self.movingVolumeSelector.setToolTip("选择整体头颅浮动图像 (MRI)")
        movingVolumeLayout.addWidget(self.movingVolumeSelector)
        dataManagerFormLayout.addRow("Moving Volume(整体MRI): ", movingVolumeLayout)

        # ROI高分辨率MRI选择器
        roiLabel = qt.QLabel("高分辨率TMJ ROI浮动图像（可选）:")
        roiLabel.setStyleSheet("font-weight: bold; margin-top: 10px;")
        dataManagerFormLayout.addRow(roiLabel)
        
        # 4个ROI volume选择器
        roiTypes = [
            ("右斜矢", "Moving_Volume_右斜矢"),
            ("左斜矢", "Moving_Volume_左斜矢"),
            ("右斜冠", "Moving_Volume_右斜冠"),
            ("左斜冠", "Moving_Volume_左斜冠")
        ]
        
        for displayName, internalName in roiTypes:
            roiVolumeLayout = qt.QVBoxLayout()
            roiSelector = slicer.qMRMLNodeComboBox()
            roiSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
            roiSelector.selectNodeUponCreation = False
            roiSelector.addEnabled = False
            roiSelector.removeEnabled = False
            roiSelector.noneEnabled = True
            roiSelector.showHidden = False
            roiSelector.showChildNodeTypes = False
            roiSelector.setMRMLScene(slicer.mrmlScene)
            roiSelector.setToolTip(f"选择{displayName}位高分辨率MRI（可选）")
            roiVolumeLayout.addWidget(roiSelector)
            dataManagerFormLayout.addRow(f"{displayName}位: ", roiVolumeLayout)
            
            # 保存到字典中
            self.roiVolumeSelectors[internalName] = roiSelector

        # 或者导入新文件
        importLabel = qt.QLabel("或者从文件夹导入新的DICOM文件:")
        importLabel.setStyleSheet("font-weight: bold; margin-top: 10px;")
        dataManagerFormLayout.addRow(importLabel)

        importButtonsLayout = qt.QHBoxLayout()
        self.loadFixedButton = qt.QPushButton("加载 Fixed Volume")
        self.loadFixedButton.toolTip = "从文件导入 Fixed Volume (CBCT)"
        self.loadFixedButton.connect('clicked(bool)', self.onLoadFixedVolume)
        importButtonsLayout.addWidget(self.loadFixedButton)

        self.loadMovingButton = qt.QPushButton("加载 Moving Volume")
        self.loadMovingButton.toolTip = "从文件导入 Moving Volume (整体MRI)"
        self.loadMovingButton.connect('clicked(bool)', self.onLoadMovingVolume)
        importButtonsLayout.addWidget(self.loadMovingButton)
        dataManagerFormLayout.addRow(importButtonsLayout)
        
        # ROI MRI导入按钮
        roiImportButtonsLayout1 = qt.QHBoxLayout()
        self.loadRightSagButton = qt.QPushButton("加载右斜矢Moving Volume")
        self.loadRightSagButton.toolTip = "从文件导入右斜矢位高分辨率MRI"
        self.loadRightSagButton.connect('clicked(bool)', lambda: self.onLoadROIVolume("ROI_Right_Sagittal", "右斜矢"))
        roiImportButtonsLayout1.addWidget(self.loadRightSagButton)
        
        self.loadLeftSagButton = qt.QPushButton("加载左斜矢Moving Volume")
        self.loadLeftSagButton.toolTip = "从文件导入左斜矢位高分辨率MRI"
        self.loadLeftSagButton.connect('clicked(bool)', lambda: self.onLoadROIVolume("ROI_Left_Sagittal", "左斜矢"))
        roiImportButtonsLayout1.addWidget(self.loadLeftSagButton)
        dataManagerFormLayout.addRow(roiImportButtonsLayout1)
        
        roiImportButtonsLayout2 = qt.QHBoxLayout()
        self.loadRightCorButton = qt.QPushButton("加载右斜冠Moving Volume")
        self.loadRightCorButton.toolTip = "从文件导入右斜冠位高分辨率MRI"
        self.loadRightCorButton.connect('clicked(bool)', lambda: self.onLoadROIVolume("ROI_Right_Coronal", "右斜冠"))
        roiImportButtonsLayout2.addWidget(self.loadRightCorButton)
        
        self.loadLeftCorButton = qt.QPushButton("加载左斜冠Moving Volume")
        self.loadLeftCorButton.toolTip = "从文件导入左斜冠位高分辨率MRI"
        self.loadLeftCorButton.connect('clicked(bool)', lambda: self.onLoadROIVolume("ROI_Left_Coronal", "左斜冠"))
        roiImportButtonsLayout2.addWidget(self.loadLeftCorButton)
        dataManagerFormLayout.addRow(roiImportButtonsLayout2)

        # 配准流程总文件夹名称
        folderLabel = qt.QLabel("场景文件夹设置:")
        folderLabel.setStyleSheet("font-weight: bold; margin-top: 2px;")
        dataManagerFormLayout.addRow(folderLabel)
        
        self.mainFolderNameEdit = qt.QLineEdit()
        self.mainFolderNameEdit.text = "TMJ_配准"
        self.mainFolderNameEdit.setToolTip("配准流程的总文件夹名称,所有模块的结果都将保存在此文件夹下")
        dataManagerFormLayout.addRow("场景总文件夹: ", self.mainFolderNameEdit)

        # 模块子文件夹名称
        self.moduleFolderNameEdit = qt.QLineEdit()
        self.moduleFolderNameEdit.text = "Data Manager"
        self.moduleFolderNameEdit.setToolTip("Data Manager在总场景文件夹下的子文件夹名称")
        dataManagerFormLayout.addRow("Data Manager场景子文件夹: ", self.moduleFolderNameEdit)

        # 加载到场景按钮
        self.loadDataButton = qt.QPushButton("加载配准数据")
        self.loadDataButton.toolTip = "将选择的 Fixed 和 Moving Volume 组织到配准流程文件夹中"
        self.loadDataButton.enabled = True
        self.loadDataButton.connect('clicked(bool)', self.onLoadData)
        dataManagerFormLayout.addRow(self.loadDataButton)

        # 状态信息
        self.statusLabel = qt.QLabel("状态: 等待选择数据")
        self.statusLabel.setStyleSheet("color: gray;")
        dataManagerFormLayout.addRow(self.statusLabel)

        # 添加模块末尾分隔线（黑色粗线）
        separator1 = qt.QFrame()
        separator1.setFrameShape(qt.QFrame.HLine)
        separator1.setFrameShadow(qt.QFrame.Plain)
        separator1.setLineWidth(2)
        separator1.setMidLineWidth(0)
        separator1.setStyleSheet("QFrame { background-color: #000000; max-height: 2px; margin: 15px 0px; }")
        dataManagerFormLayout.addRow(separator1)

        # 连接信号以更新按钮状态
        self.fixedVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)
        self.movingVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateButtonStates)

    def onLoadFixedVolume(self):
        """加载 Fixed Volume"""
        try:
            filePath = qt.QFileDialog.getOpenFileName(
                None, 
                "选择 Fixed Volume", 
                "", 
                "Medical Images (*.nrrd *.nii *.nii.gz *.dcm *.mha *.mhd);;All Files (*)"
            )
            if filePath:
                self.logCallback(f"正在加载 Fixed Volume: {filePath}")
                volumeNode = self.logic.loadVolume(filePath, "fixed_volume")
                if volumeNode:
                    self.fixedVolumeSelector.setCurrentNode(volumeNode)
                    self.logCallback(f"✓ Fixed Volume 加载成功: {volumeNode.GetName()}")
                    self.statusLabel.text = "状态: Fixed Volume 已加载"
                    self.statusLabel.setStyleSheet("color: green;")
        except Exception as e:
            self.showError(f"加载 Fixed Volume 失败: {str(e)}")

    def onLoadMovingVolume(self):
        """加载 Moving Volume"""
        try:
            filePath = qt.QFileDialog.getOpenFileName(
                None, 
                "选择 Moving Volume (整体MRI)", 
                "", 
                "Medical Images (*.nrrd *.nii *.nii.gz *.dcm *.mha *.mhd);;All Files (*)"
            )
            if filePath:
                self.logCallback(f"正在加载 Moving Volume: {filePath}")
                volumeNode = self.logic.loadVolume(filePath, "Moving_Volume")
                if volumeNode:
                    self.movingVolumeSelector.setCurrentNode(volumeNode)
                    self.logCallback(f"✓ Moving Volume 加载成功: {volumeNode.GetName()}")
                    self.statusLabel.text = "状态: Moving Volume 已加载"
                    self.statusLabel.setStyleSheet("color: green;")
        except Exception as e:
            self.showError(f"加载 Moving Volume 失败: {str(e)}")
    
    def onLoadROIVolume(self, internalName, displayName):
        """加载 ROI Volume"""
        try:
            filePath = qt.QFileDialog.getOpenFileName(
                None, 
                f"选择{displayName}位高分辨率MRI", 
                "", 
                "Medical Images (*.nrrd *.nii *.nii.gz *.dcm *.mha *.mhd);;All Files (*)"
            )
            if filePath:
                self.logCallback(f"正在加载{displayName}位MRI: {filePath}")
                volumeNode = self.logic.loadVolume(filePath, internalName)
                if volumeNode:
                    self.roiVolumeSelectors[internalName].setCurrentNode(volumeNode)
                    self.logCallback(f"✓ {displayName}位MRI加载成功: {volumeNode.GetName()}")
                    self.statusLabel.text = f"状态: {displayName}位已加载"
                    self.statusLabel.setStyleSheet("color: green;")
        except Exception as e:
            self.showError(f"加载{displayName}位MRI失败: {str(e)}")

    def onLoadData(self):
        """加载配准数据到场景文件夹"""
        try:
            # 检查是否选择了体积
            fixedNode = self.fixedVolumeSelector.currentNode()
            movingNode = self.movingVolumeSelector.currentNode()
            
            if not fixedNode or not movingNode:
                self.showError("请选择 Fixed Volume 和 Moving Volume")
                return
            
            # 获取文件夹名称
            mainFolderName = self.mainFolderNameEdit.text
            moduleFolderName = self.moduleFolderNameEdit.text
            
            if not mainFolderName:
                self.showError("请输入配准流程总文件夹名称")
                return
            
            if not moduleFolderName:
                self.showError("请输入模块子文件夹名称")
                return
            
            # 收集所有选择的ROI volumes
            roiVolumes = {}
            for internalName, selector in self.roiVolumeSelectors.items():
                node = selector.currentNode()
                if node:
                    roiVolumes[internalName] = node
            
            self.logCallback(f"正在创建配准流程结构...")
            self.logCallback(f"  总文件夹: {mainFolderName}")
            self.logCallback(f"  Data Manager子文件夹: {moduleFolderName}")
            if roiVolumes:
                self.logCallback(f"  包含 {len(roiVolumes)} 个ROI高分辨率MRI图像")
            
            # 调用 Logic 加载数据到场景
            success = self.logic.loadDataToScene(
                fixedNode, movingNode, mainFolderName, moduleFolderName, roiVolumes
            )
            
            if success:
                self.logCallback(f"✓ 配准数据已组织到场景文件夹")
                self.logCallback(f"  路径: {mainFolderName}/{moduleFolderName}")
                if roiVolumes:
                    for name in roiVolumes.keys():
                        displayName = self._getDisplayName(name)
                        self.logCallback(f"  ✓ {displayName}位已添加")
                self.statusLabel.text = "状态: 配准数据已加载"
                self.statusLabel.setStyleSheet("color: green;")
            else:
                self.showError("加载配准数据失败")
                
        except Exception as e:
            self.showError(f"加载配准数据失败: {str(e)}")
    
    def _getDisplayName(self, internalName):
        """将内部名称转换为显示名称"""
        nameMap = {
            "ROI_Moving_Volume_右斜矢": "右斜矢",
            "ROI_Moving_Volume_左斜矢": "左斜矢",
            "ROI_Moving_Volume_右斜冠": "右斜冠",
            "ROI_Moving_Volume_左斜冠": "左斜冠"
        }
        return nameMap.get(internalName, internalName)

    def updateButtonStates(self):
        """更新按钮状态"""
        hasFixed = self.fixedVolumeSelector.currentNode() is not None
        hasMoving = self.movingVolumeSelector.currentNode() is not None

        self.loadDataButton.enabled = hasFixed and hasMoving

        if hasFixed and hasMoving:
            self.statusLabel.text = "状态: 准备就绪,可以加载"
            self.statusLabel.setStyleSheet("color: green;")
        elif hasFixed or hasMoving:
            self.statusLabel.text = "状态: 已选择部分数据"
            self.statusLabel.setStyleSheet("color: orange;")

    def showError(self, errorMessage):
        """显示错误信息"""
        self.logCallback(f"✗ 错误: {errorMessage}")
        self.statusLabel.text = f"状态: 错误"
        self.statusLabel.setStyleSheet("color: red;")
        slicer.util.errorDisplay(errorMessage)
        import traceback
        self.logCallback(traceback.format_exc())

    def getMainFolderName(self):
        """获取主文件夹名称,供其他模块使用"""
        return self.mainFolderNameEdit.text
