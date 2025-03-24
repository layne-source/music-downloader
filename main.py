#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
import traceback
import platform
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QCoreApplication
from src.ui.main_window import MainWindow
from src.utils.tools import Tools

# 设置应用程序信息
APP_NAME = "音乐下载器"
APP_VERSION = "1.2.0"

def setup_logging():
    """设置日志目录"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
        except:
            log_dir = os.getcwd()
    
    # 创建日志文件名，包含日期
    log_file = os.path.join(log_dir, f"error_log_{datetime.now().strftime('%Y%m%d')}.txt")
    return log_file

def exception_hook(exctype, value, tb):
    """全局异常捕获处理函数"""
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] 发生未捕获的异常: {error_msg}")
    
    # 获取日志文件路径
    log_file = setup_logging()
    
    # 将错误写入日志文件
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"===== {timestamp} {os.path.basename(__file__)} 异常 =====\n")
            f.write(f"操作系统: {platform.platform()}\n")
            f.write(f"Python版本: {platform.python_version()}\n")
            f.write(error_msg)
            f.write("\n\n")
    except Exception as e:
        print(f"写入日志文件失败: {e}")
    
    # 显示错误对话框
    if QApplication.instance():
        error_details = str(value)
        if len(error_details) > 200:
            error_details = error_details[:200] + "..."
        
        QMessageBox.critical(
            None, 
            f"{APP_NAME} - 错误", 
            f"程序发生错误:\n{error_details}\n\n详细信息已写入日志文件: {log_file}"
        )
    
    sys.__excepthook__(exctype, value, tb)

if __name__ == "__main__":
    # 设置全局异常钩子
    sys.excepthook = exception_hook
    
    # 设置应用程序信息
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)
    
    # 确保日志目录存在
    log_file = setup_logging()
    print(f"日志文件路径: {log_file}")
    
    try:
        print("====== 正在启动音乐下载器 ======")
        print(f"版本: {APP_VERSION}")
        print(f"操作系统: {platform.platform()}")
        print(f"Python版本: {platform.python_version()}")
        
        # 启动应用程序
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # 初始化下载目录
        default_download_path = Tools.get_default_download_path()
        print(f"默认下载路径: {default_download_path}")
        
        print("正在初始化主窗口...")
        window = MainWindow()
        
        print("正在显示主窗口...")
        window.show()
        
        print("====== 程序已启动 ======")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"主程序启动失败: {e}")
        traceback.print_exc()
        
        if QApplication.instance():
            QMessageBox.critical(
                None, 
                f"{APP_NAME} - 启动失败", 
                f"程序启动失败，请检查系统配置:\n{str(e)}\n\n详细信息已写入日志文件。"
            ) 