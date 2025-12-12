"""
TMJ Extension - 主入口文件（模块化版本）
将代码拆分为 Data Manager 和 Gold Standard Set 两个独立模块
"""
import os
import sys
import unittest
import logging
import vtk, qt, ctk, slicer
from datetime import datetime
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

# 确保子模块路径在 sys.path 中
_module_dir = os.path.dirname(os.path.abspath(__file__))
if _module_dir not in sys.path:
    sys.path.insert(0, _module_dir)

# 导入模块化组件
from DataManager.data_manager_widget import DataManagerWidget
from DataManager.data_manager_logic import DataManagerLogic
from GoldStandardSet.gold_standard_widget import GoldStandardWidget
from GoldStandardSet.gold_standard_logic import GoldStandardLogic
from CoarseRegistration.coarse_registration_widget import CoarseRegistrationWidget
from CoarseRegistration.coarse_registration_logic import CoarseRegistrationLogic
from ROIMaskSet.roi_mask_set_widget import ROIMaskSetWidget
from ROIMaskSet.roi_mask_set_logic import ROIMaskSetLogic


#
# TMJExtension
#

class TMJExtension(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class"""

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "TMJ Extension"
        self.parent.categories = ["TMJ Analysis"]
        self.parent.dependencies = []
        self.parent.contributors = ["Feng"]
        self.parent.helpText = """
这是一个用于TMJ(颞下颌关节)分析的3D Slicer插件。
Data Manager 模块用于导入、管理和导出医学影像数据，保留原始 HU/强度信息。
Gold Standard Set 模块用于手动配准和金标准设置。
Coarse Registration 模块用于基于基准点的粗配准。
ROI Mask Set 模块用于生成颞下颌关节ROI区域的掩膜。
"""
        self.parent.acknowledgementText = """
This module was developed for TMJ research.
"""


#
# TMJExtensionWidget
#

class TMJExtensionWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """主界面Widget类 - 组合各个模块的UI"""

    def __init__(self, parent=None):
        """初始化主Widget"""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        
        # 子模块引用
        self.dataManagerWidget = None
        self.goldStandardWidget = None
        self.coarseRegistrationWidget = None
        self.roiMaskSetWidget = None

    def setup(self):
        """设置主界面"""
        ScriptedLoadableModuleWidget.setup(self)

        # 开发者工具区域（用于重载）
        self.setupDeveloperTools()

        # 创建 Data Manager 模块
        self.dataManagerWidget = DataManagerWidget(
            parent=self.layout,
            logCallback=self.addLog
        )

        # 创建 Gold Standard Set 模块
        self.goldStandardWidget = GoldStandardWidget(
            parent=self.layout,
            logCallback=self.addLog,
            getMainFolderNameCallback=self.dataManagerWidget.getMainFolderName
        )

        # 创建 Coarse Registration 模块
        self.coarseRegistrationWidget = CoarseRegistrationWidget(
            parent=self.layout,
            logCallback=self.addLog,
            getMainFolderNameCallback=self.dataManagerWidget.getMainFolderName
        )

        # 创建 ROI Mask Set 模块
        self.roiMaskSetWidget = ROIMaskSetWidget(
            parent=self.layout,
            logCallback=self.addLog,
            getMainFolderNameCallback=self.dataManagerWidget.getMainFolderName
        )

        # 日志区域
        self.setupLogArea()

        # 添加垂直间距
        self.layout.addStretch(1)
    def setupDeveloperTools(self):
        """设置开发者工具区域"""
        devCollapsibleButton = ctk.ctkCollapsibleButton()
        devCollapsibleButton.text = "🔧 开发者工具"
        devCollapsibleButton.collapsed = True
        self.layout.addWidget(devCollapsibleButton)
        devFormLayout = qt.QFormLayout(devCollapsibleButton)

        # 重载按钮
        reloadButton = qt.QPushButton("🔄 重载")
        reloadButton.toolTip = "重新加载所有子模块的代码，无需重启 Slicer"
        reloadButton.connect('clicked(bool)', self.onReloadModules)
        devFormLayout.addRow(reloadButton)

        # 状态标签
        self.reloadStatusLabel = qt.QLabel("")
        devFormLayout.addRow(self.reloadStatusLabel)

    def onReloadModules(self):
        """热重载所有子模块"""
        import importlib
        import shutil
        import gc
        
        self.addLog("=" * 50)
        self.addLog("🔥 开始热重载...")
        
        try:
            # 步骤1: 清除 __pycache__
            module_path = os.path.dirname(os.path.abspath(__file__))
            cache_cleared = 0
            
            for root, dirs, files in os.walk(module_path):
                if '__pycache__' in dirs:
                    cache_dir = os.path.join(root, '__pycache__')
                    try:
                        shutil.rmtree(cache_dir)
                        cache_cleared += 1
                    except:
                        pass
            
            if cache_cleared > 0:
                self.addLog(f"✓ 清除了 {cache_cleared} 个缓存目录")
            
            # 步骤2: 重载所有子模块
            import DataManager.data_manager_logic as dm_logic
            import DataManager.data_manager_widget as dm_widget
            import GoldStandardSet.gold_standard_logic as gs_logic
            import GoldStandardSet.gold_standard_widget as gs_widget
            import CoarseRegistration.coarse_registration_logic as cr_logic
            import CoarseRegistration.coarse_registration_widget as cr_widget
            import ROIMaskSet.roi_mask_set_logic as rm_logic
            import ROIMaskSet.roi_mask_set_widget as rm_widget
            
            modules_to_reload = [
                ('DataManager.Logic', dm_logic),
                ('DataManager.Widget', dm_widget),
                ('GoldStandardSet.Logic', gs_logic),
                ('GoldStandardSet.Widget', gs_widget),
                ('CoarseRegistration.Logic', cr_logic),
                ('CoarseRegistration.Widget', cr_widget),
                ('ROIMaskSet.Logic', rm_logic),
                ('ROIMaskSet.Widget', rm_widget),
            ]
            
            for name, module in modules_to_reload:
                try:
                    importlib.reload(module)
                    self.addLog(f"✓ {name}")
                except Exception as e:
                    self.addLog(f"✗ {name}: {str(e)}")
            
            # 步骤3: 垃圾回收
            gc.collect()
            
            # 步骤4: 使用 Slicer API 重载主模块
            slicer.util.reloadScriptedModule("TMJExtension")
            
            self.addLog("✅ 热重载完成!")
            self.addLog("📌 请切换到其他模块再切回来查看更新")
            self.addLog("=" * 50)
            
            self.reloadStatusLabel.setText("✅ 重载成功 - 请切换模块")
            
        except Exception as e:
            error_msg = f"重载失败: {str(e)}"
            self.addLog(f"❌ {error_msg}")
            self.reloadStatusLabel.setText(f"❌ {error_msg}")
            import traceback
            self.addLog(traceback.format_exc())

    def setupLogArea(self):
        """设置日志区域"""
        logCollapsibleButton = ctk.ctkCollapsibleButton()
        logCollapsibleButton.text = "日志与错误信息"
        logCollapsibleButton.collapsed = False  # 默认展开
        self.layout.addWidget(logCollapsibleButton)
        logFormLayout = qt.QVBoxLayout(logCollapsibleButton)

        self.logTextEdit = qt.QTextEdit()
        self.logTextEdit.setReadOnly(True)
        self.logTextEdit.setMaximumHeight(200)
        logFormLayout.addWidget(self.logTextEdit)

        clearLogButton = qt.QPushButton("清除日志")
        clearLogButton.connect('clicked(bool)', self.onClearLog)
        logFormLayout.addWidget(clearLogButton)

    def addLog(self, message):
        """添加日志信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        logMessage = f"[{timestamp}] {message}"
        self.logTextEdit.append(logMessage)
        logging.info(message)

    def onClearLog(self):
        """清除日志"""
        self.logTextEdit.clear()
        self.addLog("日志已清除")

    def cleanup(self):
        """清理资源"""
        self.removeObservers()


#
# TMJExtensionLogic
#

class TMJExtensionLogic(ScriptedLoadableModuleLogic):
    """
    主Logic类 - 现在主要作为模块的容器
    实际的业务逻辑在各个子模块的Logic类中
    """

    def __init__(self):
        """初始化Logic"""
        ScriptedLoadableModuleLogic.__init__(self)
        self.dataManagerLogic = DataManagerLogic()
        self.goldStandardLogic = GoldStandardLogic()
        self.coarseRegistrationLogic = CoarseRegistrationLogic()
        self.roiMaskSetLogic = ROIMaskSetLogic()


#
# TMJExtensionTest
#

class TMJExtensionTest(ScriptedLoadableModuleTest):
    """测试用例类"""

    def setUp(self):
        """重置状态"""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """运行测试"""
        self.setUp()
        self.test_TMJExtension1()

    def test_TMJExtension1(self):
        """基础测试"""
        self.delayDisplay("Starting the test")
        # TODO: 添加测试代码
        self.delayDisplay('Test passed')
