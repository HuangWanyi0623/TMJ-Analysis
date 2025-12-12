"""
MI Registration Logic - 互信息配准的业务逻辑
"""
import os
import sys
import logging
import tempfile
import subprocess
import shutil
import threading
import slicer


class RegistrationWorker(threading.Thread):
    """
    配准工作线程
    在后台执行配准，避免阻塞UI
    """
    
    def __init__(self, cmd, tempDir, outputDir, logCallback):
        super(RegistrationWorker, self).__init__()
        self.daemon = True  # 守护线程，主程序退出时自动结束
        self.cmd = cmd
        self.tempDir = tempDir
        self.outputDir = outputDir
        self.logCallback = logCallback
        self.process = None
        self.success = False
        self.transformPath = ""
        self._stop_event = threading.Event()
        
    def run(self):
        """线程运行函数"""
        try:
            self._log(f"执行命令: {' '.join(self.cmd)}")
            
            # 启动配准进程
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.tempDir
            )
            
            # 实时读取输出
            while True:
                if self._stop_event.is_set():
                    break
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    self._log(line)
            
            self.process.wait()
            
            if self.process.returncode != 0:
                self._log(f"配准进程返回错误代码: {self.process.returncode}")
                self.success = False
                return
            
            # 查找输出变换文件
            outputTransformPath = None
            h5Files = []
            
            for filename in os.listdir(self.outputDir):
                if filename.endswith(".h5"):
                    if filename != "initial_transform.h5":
                        filepath = os.path.join(self.outputDir, filename)
                        h5Files.append(filepath)
                        if "registration_transform" in filename.lower():
                            outputTransformPath = filepath
                            break
            
            if not outputTransformPath and h5Files:
                outputTransformPath = h5Files[0]
            
            if not outputTransformPath or not os.path.exists(outputTransformPath):
                self._log("❌ 找不到输出变换文件")
                self.success = False
                return
            
            self._log(f"找到输出变换: {outputTransformPath}")
            self.success = True
            self.transformPath = outputTransformPath
            
        except Exception as e:
            self._log(f"❌ 配准过程出错: {str(e)}")
            import traceback
            self._log(traceback.format_exc())
            self.success = False
    
    def _log(self, message):
        """线程安全的日志输出"""
        if self.logCallback:
            self.logCallback(message)
    
    def stop(self):
        """停止线程"""
        self._stop_event.set()
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass


class MIRegistrationLogic:
    """
    互信息配准的逻辑类
    负责调用 C++ 后端执行配准
    """

    def __init__(self, logCallback=None):
        """
        初始化 MI Registration Logic
        
        :param logCallback: 日志回调函数
        """
        self.logCallback = logCallback
        self._executablePath = None
        self.worker = None
        self.tempDir = None

    def log(self, message):
        """输出日志"""
        if self.logCallback:
            self.logCallback(message)
        logging.info(message)

    def getExecutablePath(self):
        """获取 C++ 后端可执行文件路径"""
        if self._executablePath and os.path.exists(self._executablePath):
            return self._executablePath

        # 查找可执行文件的可能位置
        modulePath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        possiblePaths = [
            # 开发环境中的位置
            os.path.join(modulePath, "Backend", "bin", "Release", "MIRegistration.exe"),
            os.path.join(modulePath, "Backend", "bin", "Debug", "MIRegistration.exe"),
            os.path.join(modulePath, "Backend", "bin", "MIRegistration.exe"),
            os.path.join(modulePath, "Backend", "build", "bin", "Release", "MIRegistration.exe"),
            # Linux/Mac
            os.path.join(modulePath, "Backend", "bin", "MIRegistration"),
            os.path.join(modulePath, "Backend", "build", "bin", "MIRegistration"),
            # Slicer 安装目录
            os.path.join(slicer.app.slicerHome, "lib", "Slicer-" + str(slicer.app.majorVersion) + "." + str(slicer.app.minorVersion), "cli-modules", "MIRegistration.exe"),
            os.path.join(slicer.app.slicerHome, "lib", "Slicer-" + str(slicer.app.majorVersion) + "." + str(slicer.app.minorVersion), "cli-modules", "MIRegistration"),
        ]

        for path in possiblePaths:
            if os.path.exists(path):
                self._executablePath = path
                return path

        # 如果找不到，尝试在 PATH 中查找
        executableName = "MIRegistration.exe" if sys.platform == "win32" else "MIRegistration"
        pathExec = shutil.which(executableName)
        if pathExec:
            self._executablePath = pathExec
            return pathExec

        return None

    def runRegistration(self, fixedNode, movingNode, outputTransformNode,
                        configPath=None, samplingPercentage=0.10,
                        fixedMaskNode=None, initialTransformNode=None):
        """
        执行配准 (异步)
        
        Args:
            fixedNode: 固定图像节点
            movingNode: 移动图像节点
            outputTransformNode: 输出变换节点
            configPath: 配准配置文件路径 (JSON)
            samplingPercentage: 采样比例 (0.0-1.0)
            fixedMaskNode: 固定掩膜节点（可选）
            initialTransformNode: 初始变换节点（可选）
            
        Returns:
            bool: 是否成功启动
        """
        # 获取可执行文件路径
        execPath = self.getExecutablePath()
        if not execPath:
            self.log("❌ 找不到配准可执行文件 (MIRegistration)")
            self.log("请确保已编译后端代码或正确安装了扩展")
            return False

        self.log(f"使用可执行文件: {execPath}")

        # 创建临时目录
        self.tempDir = tempfile.mkdtemp(prefix="TMJRegistration_")
        self.log(f"临时目录: {self.tempDir}")

        try:
            # 导出图像到临时文件
            fixedPath = os.path.join(self.tempDir, "fixed.nrrd")
            movingPath = os.path.join(self.tempDir, "moving.nrrd")
            outputDir = self.tempDir

            self.log("导出固定图像...")
            slicer.util.saveNode(fixedNode, fixedPath)

            self.log("导出移动图像...")
            slicer.util.saveNode(movingNode, movingPath)

            # 复制配置文件到临时目录（避免中文路径问题）
            tempConfigPath = None
            if configPath and os.path.exists(configPath):
                tempConfigPath = os.path.join(self.tempDir, "config.json")
                shutil.copy2(configPath, tempConfigPath)
                self.log(f"配置文件已复制到临时目录: {os.path.basename(configPath)}")

            # 导出掩膜（如果有）
            maskPath = None
            if fixedMaskNode:
                maskPath = os.path.join(self.tempDir, "mask.nrrd")
                self.log("导出固定掩膜...")
                slicer.util.saveNode(fixedMaskNode, maskPath)

            # 导出初始变换（如果有）
            initialTransformPath = None
            if initialTransformNode:
                initialTransformPath = os.path.join(self.tempDir, "initial_transform.h5")
                self.log("导出初始变换...")
                slicer.util.saveNode(initialTransformNode, initialTransformPath)

            # 构建命令行
            cmd = [execPath]
            
            # 使用临时目录中的配置文件（避免中文路径问题）
            if tempConfigPath and os.path.exists(tempConfigPath):
                cmd.extend(["--config", tempConfigPath])
                self.log(f"使用配置文件: {os.path.basename(configPath)}")
            else:
                self.log("⚠️ 未指定配置文件，使用默认 Rigid 配准")
            
            cmd.extend(["--sampling-percentage", str(samplingPercentage)])

            if maskPath:
                cmd.extend(["--fixed-mask", maskPath])

            if initialTransformPath:
                cmd.extend(["--initial", initialTransformPath])

            cmd.extend([fixedPath, movingPath, outputDir])

            # 保存输出变换节点引用
            self.outputTransformNode = outputTransformNode

            # 创建工作线程
            self.worker = RegistrationWorker(cmd, self.tempDir, outputDir, self.log)
            
            # 启动线程
            self.worker.start()
            
            # 启动定时器检查状态 (使用slicer.app.processEvents定期更新)
            import qt
            self.checkTimer = qt.QTimer()
            self.checkTimer.timeout.connect(self._checkWorkerStatus)
            self.checkTimer.start(100)  # 每100ms检查一次
            
            return True

        except Exception as e:
            self.log(f"❌ 配准启动失败: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            self._cleanup()
            return False
    
    def _checkWorkerStatus(self):
        """检查工作线程状态"""
        if self.worker and not self.worker.is_alive():
            # 线程已完成
            self.checkTimer.stop()
            
            success = self.worker.success
            transformPath = self.worker.transformPath
            
            if success and transformPath:
                self._loadTransform(transformPath)
            else:
                if hasattr(self, 'finishCallback') and self.finishCallback:
                    self.finishCallback(False, None)
            
            self._cleanup()
    
    def _loadTransform(self, transformPath):
        """加载变换文件"""
        try:
            self.log(f"加载输出变换: {transformPath}")
            
            # 加载变换到 Slicer
            loadedTransformNode = slicer.util.loadTransform(transformPath)
            if loadedTransformNode and self.outputTransformNode:
                # 复制变换到输出节点
                self.outputTransformNode.CopyContent(loadedTransformNode)
                slicer.mrmlScene.RemoveNode(loadedTransformNode)
                self.log("✅ 变换已加载")
                
                if hasattr(self, 'finishCallback') and self.finishCallback:
                    self.finishCallback(True, self.outputTransformNode)
            else:
                self.log("❌ 无法加载变换文件")
                if hasattr(self, 'finishCallback') and self.finishCallback:
                    self.finishCallback(False, None)
        
        except Exception as e:
            self.log(f"❌ 加载变换失败: {str(e)}")
            import traceback
            self.log(traceback.format_exc())
            if hasattr(self, 'finishCallback') and self.finishCallback:
                self.finishCallback(False, None)
    
    def _cleanup(self):
        """清理临时文件"""
        if self.tempDir:
            try:
                shutil.rmtree(self.tempDir)
                self.log("已清理临时文件")
            except Exception as e:
                self.log(f"清理临时文件失败: {str(e)}")
            self.tempDir = None
        
        if hasattr(self, 'checkTimer'):
            self.checkTimer.stop()
    
    def setFinishCallback(self, callback):
        """设置完成回调"""
        self.finishCallback = callback
    
    def cancelRegistration(self):
        """取消配准"""
        if self.worker and self.worker.is_alive():
            self.worker.stop()
            self.worker.join(timeout=2)
        if hasattr(self, 'checkTimer'):
            self.checkTimer.stop()
        self._cleanup()
