"""
TMJ Registration - 3D Slicer Module for Image Registration
This module provides a GUI wrapper for multiple registration algorithms.
"""
import os
import sys
import logging
import qt
import ctk
import slicer
from datetime import datetime
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

# 确保子模块路径在 sys.path 中
_module_dir = os.path.dirname(os.path.abspath(__file__))
if _module_dir not in sys.path:
    sys.path.insert(0, _module_dir)

# 导入模块化组件
from MIRegistration.mi_registration_widget import MIRegistrationWidget
from MIRegistration.mi_registration_logic import MIRegistrationLogic
from MINDRegistration.mind_registration_widget import MINDRegistrationWidget
from MINDRegistration.mind_registration_logic import MINDRegistrationLogic


#
# TMJRegistration
#

class TMJRegistration(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class"""

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "TMJ Registration"
        self.parent.categories = ["TMJ Analysis"]
        self.parent.dependencies = []
        self.parent.contributors = ["Feng"]
        self.parent.helpText = """
TMJ Registration 模块用于对医学影像进行配准操作。
支持两种配准算法：
1. 互信息(MI): 基于统计的经典配准方法
2. MIND: 模态独立邻域描述符，适合多模态配准
支持刚性（Rigid）和仿射（Affine）变换。
底层使用 ITK 实现的 C++ 可执行程序进行高效配准。
"""
        self.parent.acknowledgementText = """
This module was developed for TMJ research using ITK-based registration algorithms.
"""


#
# TMJRegistrationWidget
#

class TMJRegistrationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """主界面Widget类 - 组合各个配准算法的UI"""

    def __init__(self, parent=None):
        """初始化主Widget"""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        
        # 子模块引用
        self.miRegistrationWidget = None
        self.mindRegistrationWidget = None

    def setup(self):
        """设置主界面"""
        ScriptedLoadableModuleWidget.setup(self)

        # 开发者工具区域（用于重载）
        self.setupDeveloperTools()

        # 创建 MI Registration 模块
        self.miRegistrationWidget = MIRegistrationWidget(
            parent=self.layout,
            logCallback=self.addLog
        )
        
        # 创建 MIND Registration 模块
        self.mindRegistrationWidget = MINDRegistrationWidget(
            parent=self.layout,
            logCallback=self.addLog
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
        reloadButton.toolTip = "重新加载模块代码，无需重启 Slicer"
        reloadButton.connect('clicked(bool)', self.onReloadModule)
        devFormLayout.addRow(reloadButton)

    def onReloadModule(self):
        """热重载模块"""
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
            import MIRegistration.mi_registration_logic as mi_logic
            import MIRegistration.mi_registration_widget as mi_widget
            import MINDRegistration.mind_registration_logic as mind_logic
            import MINDRegistration.mind_registration_widget as mind_widget
            
            modules_to_reload = [
                ('MIRegistration.Logic', mi_logic),
                ('MIRegistration.Widget', mi_widget),
                ('MINDRegistration.Logic', mind_logic),
                ('MINDRegistration.Widget', mind_widget),
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
            slicer.util.reloadScriptedModule("TMJRegistration")
            
            self.addLog("✅ 热重载完成!")
            self.addLog("📌 请切换到其他模块再切回来查看更新")
            self.addLog("=" * 50)
                
        except Exception as e:
            error_msg = f"重载失败: {str(e)}"
            self.addLog(f"❌ {error_msg}")
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

    def onClearLog(self):
        """清除日志"""
        self.logTextEdit.clear()
        self.addLog("日志已清除")

    def addLog(self, message):
        """添加日志消息"""
        self.logTextEdit.append(message)
        logging.info(message)

    def cleanup(self):
        """Called when the application closes and the module widget is destroyed."""
        pass


#
# TMJRegistrationTest
#

class TMJRegistrationTest(ScriptedLoadableModuleTest):
    """Test case for TMJRegistration module"""

    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_TMJRegistration1()

    def test_TMJRegistration1(self):
        """Test basic module functionality"""
        self.delayDisplay("Starting the test")
        # Add actual test logic here if needed
        self.delayDisplay('Test passed')

