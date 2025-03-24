#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import platform
import subprocess
import requests
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QComboBox, 
                            QTableWidget, QTableWidgetItem, QHeaderView, 
                            QFileDialog, QMessageBox, QApplication, QProgressBar,
                            QStatusBar, QDesktopWidget, QRadioButton)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QFont, QColor

from src.api.api_factory import APIFactory
from src.api.base_api import MusicAPI
from src.ui.threads import SearchThread, DownloadThread
from src.utils.tools import Tools


class SearchThread(QThread):
    """搜索线程"""
    # 定义信号
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, api, keyword):
        super().__init__()
        self.api = api
        self.keyword = keyword
    
    def run(self):
        try:
            result = self.api.search(self.keyword)
            self.result_signal.emit(result)
        except Exception as e:
            self.error_signal.emit(str(e))


class DownloadThread(QThread):
    """下载线程"""
    # 定义信号
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, api, song_id, save_path):
        super().__init__()
        self.api = api
        self.song_id = song_id
        self.save_path = save_path
    
    def run(self):
        try:
            print(f"下载线程启动: 歌曲ID = {self.song_id}")
            
            # 先获取URL
            url = self.api.get_song_url(self.song_id)
            if not url:
                self.error_signal.emit("无法获取歌曲下载链接，请尝试其他音源")
                return
            
            print(f"获取到下载URL: {url[:100]}...")
            
            # 发送初始进度
            self.progress_signal.emit(5)
            
            # 创建目录
            save_dir = os.path.dirname(self.save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                print(f"创建下载目录: {save_dir}")
            
            # 使用requests下载
            try:
                session = requests.Session()
                session.headers.update({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
                })
                
                # 先检查URL可用性
                head_resp = session.head(url, timeout=5)
                if head_resp.status_code >= 400:
                    print(f"URL检查失败，状态码: {head_resp.status_code}")
                    raise Exception(f"下载链接无效，状态码: {head_resp.status_code}")
                
                # 获取文件大小
                content_length = int(head_resp.headers.get('Content-Length', 0))
                print(f"文件大小: {content_length} 字节")
                
                # 开始下载
                with session.get(url, stream=True, timeout=30) as response:
                    response.raise_for_status()
                    
                    # 获取总大小
                    total_size = int(response.headers.get('Content-Length', 0))
                    if total_size == 0:
                        total_size = content_length
                    
                    # 已下载的大小
                    downloaded = 0
                    
                    with open(self.save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                
                                # 计算进度
                                if total_size > 0:
                                    progress = int(min(downloaded / total_size * 100, 100))
                                    self.progress_signal.emit(progress)
                                    print(f"下载进度: {progress}%") if progress % 10 == 0 else None
                                else:
                                    # 如果无法获取总大小，使用一个模拟进度
                                    self.progress_signal.emit(min(int(downloaded / 1024 / 1024 * 10), 95))
            
            except requests.RequestException as e:
                print(f"下载请求出错: {e}")
                self.error_signal.emit(f"下载请求出错: {e}")
                return
            
            # 检查文件是否有效
            if os.path.exists(self.save_path):
                file_size = os.path.getsize(self.save_path)
                print(f"下载完成，文件大小: {file_size} 字节")
                
                if file_size < 1024:  # 小于1KB的文件很可能是错误信息
                    with open(self.save_path, 'r', errors='ignore') as f:
                        content = f.read(1000)
                        if 'error' in content.lower() or '错误' in content or '失败' in content:
                            print(f"下载的文件包含错误信息: {content}")
                            os.remove(self.save_path)
                            self.error_signal.emit("下载失败，接收到错误响应")
                            return
                
                if file_size > 10 * 1024:  # 大于10KB的文件可能是有效的音乐文件
                    self.progress_signal.emit(100)
                    self.finished_signal.emit(self.save_path)
                else:
                    print(f"下载的文件太小，可能不是有效的音乐文件")
                    os.remove(self.save_path)
                    self.error_signal.emit("下载失败，文件太小，不是有效的音乐文件")
            else:
                print(f"下载后文件不存在")
                self.error_signal.emit("下载失败，文件未能保存")
        
        except Exception as e:
            print(f"下载过程中出现异常: {e}")
            self.error_signal.emit(str(e))


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        """
        初始化主窗口
        """
        super().__init__()
        print("正在初始化主窗口...")
        
        # 获取API工厂
        self.api_factory = APIFactory()
        
        # 初始化API实例 - 使用GD音乐API
        self.current_api = self.api_factory.get_api('GD音乐')
        
        # 设置默认数据源为网易云
        self.current_api.set_source('netease')
        
        # 初始化变量
        self.current_song = None
        self.download_path = Tools.get_default_download_path()  # 使用工具类获取默认下载路径
        self.result_list = []
        self.source_buttons = {}
        self.last_search_keyword = ""
        
        # 添加标志位，用于区分初始状态和搜索后无结果状态
        self.has_searched = False
        # 添加标志位，用于区分手动搜索和切换平台自动搜索
        self.is_source_changing = False
        # 添加标志位，标记窗口是否正在关闭
        self.is_closing = False
        
        # 初始化线程变量
        self.search_thread = None
        self.download_thread = None
        
        # 添加状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle('GD音乐下载器')
        self.setWindowIcon(QIcon('./icons/icon.png'))
        self.resize(1000, 700)  # 增加高度从600到700
        
        # 设置固定大小，防止窗口大小变化
        self.setMinimumSize(1000, 700)
        self.setMaximumSize(1000, 700)
        
        # 设置中心控件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建搜索区域
        self.create_search_area()
        main_layout.addLayout(self.search_layout)
        
        # 创建结果显示区域
        self.create_result_area()
        main_layout.addWidget(self.result_table)
        
        # 创建分页按钮区域
        self.create_pagination_area()
        main_layout.addLayout(self.pagination_layout)
        
        # 创建下载区域
        self.create_download_area()
        main_layout.addLayout(self.download_layout)
        
        # 调整布局
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 自动调整列宽
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # 显示窗口
        self.center()
        self.show()
        print("正在显示主窗口...")
        
        # 更新状态栏
        self.update_status_bar(f"当前平台: {self.current_api.name} | 状态: 就绪")
        
        print("====== 程序已启动 ======")
    
    def create_search_area(self):
        """创建搜索区域"""
        self.search_layout = QHBoxLayout()
        
        # 搜索标签
        search_label = QLabel("搜索歌曲:")
        search_label.setFixedWidth(60)
        self.search_layout.addWidget(search_label)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入歌曲名、歌手或专辑")
        self.search_input.returnPressed.connect(self.search_music)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
                background-color: #fff;
            }
            QLineEdit:focus {
                border: 1px solid #1E90FF;
            }
        """)
        self.search_layout.addWidget(self.search_input, 1)  # 设置拉伸因子为1，使其可以自适应
        
        # 搜索按钮
        search_btn = QPushButton("搜索")
        search_btn.setFixedWidth(80)  # 固定宽度
        search_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E90FF;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1a7fd1;
            }
        """)
        search_btn.clicked.connect(self.search_music)
        self.search_layout.addWidget(search_btn)
        
        # 平台标题
        platform_label = QLabel(f"{self.current_api.name}")
        platform_label.setFixedWidth(100)  # 固定宽度
        platform_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #1E90FF;
            }
        """)
        self.search_layout.addWidget(platform_label)
    
    def create_result_area(self):
        """创建结果显示区域"""
        self.result_table = QTableWidget(0, 6)  # 6列，去掉时长
        self.result_table.setHorizontalHeaderLabels(["歌曲名", "歌手", "专辑", "大小", "音质", "来源"])
        
        # 设置表格属性
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # 歌曲名列宽自适应
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        # 允许多选
        self.result_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.result_table.setSelectionBehavior(QTableWidget.SelectRows)  # 整行选择
        
        # 设置样式
        self.result_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fcfcfc;
                alternate-background-color: #f5f5f5;
            }
            QTableWidget::item:selected {
                background-color: #c2dbff;
                color: #000;
            }
            QHeaderView::section {
                background-color: #e6f2ff;
                border: none;
                padding: 6px;
                font-weight: bold;
                color: #333;
                border-right: 1px solid #ddd;
                border-bottom: 1px solid #ddd;
            }
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #c0c0c0;
                min-height: 20px;
                border-radius: 5px;
            }
        """)
        
        # 启用交替行颜色
        self.result_table.setAlternatingRowColors(True)
        
        # 表格选中事件
        self.result_table.itemClicked.connect(self.on_table_item_clicked)
        # 双击直接下载
        self.result_table.itemDoubleClicked.connect(self.on_table_item_double_clicked)
    
    def create_pagination_area(self):
        """创建分页区域"""
        self.pagination_layout = QHBoxLayout()
        
        # 上一页按钮
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 15px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #aaa;
                border: 1px solid #eee;
            }
        """)
        self.prev_page_btn.clicked.connect(self.load_previous_page)
        self.prev_page_btn.setEnabled(False)  # 初始禁用
        self.pagination_layout.addWidget(self.prev_page_btn)
        
        # 页码信息
        self.page_info_label = QLabel("第1页")
        self.page_info_label.setAlignment(Qt.AlignCenter)
        self.page_info_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                color: #333;
                padding: 0 10px;
            }
        """)
        self.pagination_layout.addWidget(self.page_info_label)
        
        # 下一页按钮
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 15px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #aaa;
                border: 1px solid #eee;
            }
        """)
        self.next_page_btn.clicked.connect(self.load_next_page)
        self.next_page_btn.setEnabled(False)  # 初始禁用
        self.pagination_layout.addWidget(self.next_page_btn)
        
        # 添加弹性空间，使分页控件居中
        self.pagination_layout.addStretch(1)
    
    def create_download_area(self):
        """创建下载区域"""
        self.download_layout = QHBoxLayout()
        
        # 当前选中歌曲
        self.current_song_label = QLabel("当前未选择歌曲")
        self.current_song_label.setFixedWidth(300)  # 固定宽度
        self.current_song_label.setToolTip("当前选中的歌曲")  # 添加提示，当文本过长时可以通过提示查看完整内容
        self.current_song_label.setStyleSheet("""
            QLabel {
                color: #333;
                padding: 5px;
                background-color: #f9f9f9;
                border: 1px solid #eee;
                border-radius: 4px;
                text-overflow: ellipsis;  /* 文本溢出时显示省略号 */
                overflow: hidden;
            }
        """)
        self.download_layout.addWidget(self.current_song_label)
        
        # 下载路径按钮
        path_btn = QPushButton("下载路径")
        path_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 12px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        path_btn.clicked.connect(self.select_download_path)
        self.download_layout.addWidget(path_btn)
        
        # 显示当前下载路径
        self.path_label = QLabel(f"下载到: {self.download_path}")
        self.path_label.setStyleSheet("""
            QLabel {
                color: #555;
                padding: 0 10px;
            }
        """)
        self.download_layout.addWidget(self.path_label)
        
        # 批量下载按钮
        self.batch_download_btn = QPushButton("批量下载")
        self.batch_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.batch_download_btn.clicked.connect(self.batch_download_music)
        self.batch_download_btn.setEnabled(False)
        self.download_layout.addWidget(self.batch_download_btn)
        
        # 下载按钮
        self.download_btn = QPushButton("下载")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E90FF;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1a7fd1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.download_btn.clicked.connect(self.download_music)
        self.download_btn.setEnabled(False)
        self.download_layout.addWidget(self.download_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
                background-color: #f5f5f5;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        self.download_layout.addWidget(self.progress_bar)
    
    def search_music(self):
        """搜索歌曲"""
        keyword = self.search_input.text()
        if not keyword:
            self.show_message('请输入搜索关键词')
            return
        
        # 标记已经进行过搜索
        self.has_searched = True
        
        # 保存当前搜索关键词
        self.last_search_keyword = keyword
        
        # 清空之前的搜索结果
        self.result_list = []
        self.update_result_table(clear_only=True)  # 仅清空表格，不显示提示
        
        # 重置进度条
        self.progress_bar.setValue(0)
        
        # 禁用批量下载按钮
        self.batch_download_btn.setEnabled(False)
        
        # 显示加载状态
        self.update_status_bar(f"正在搜索: {keyword}...")
        print(f"开始搜索: {keyword}")
        
        # 确保之前的搜索线程已结束
        if self.search_thread and self.search_thread.isRunning():
            print(f"有正在运行的搜索线程，等待其完成...")
            self.search_thread.wait(1000)  # 等待1秒
            
            if self.search_thread.isRunning():
                print(f"搜索线程仍在运行，终止它...")
                self.search_thread.terminate()
                self.search_thread.wait()
        
        # 创建线程
        self.search_thread = SearchThread(self.current_api, keyword)
        
        # 连接信号
        self.search_thread.result_signal.connect(self.handle_search_result)
        self.search_thread.error_signal.connect(self.handle_search_error)
        
        # 启动线程
        self.search_thread.start()
        print(f"搜索线程已启动...")
    
    def on_table_item_clicked(self, item):
        """表格项点击事件"""
        # 获取所有选中的行
        selected_rows = self.result_table.selectionModel().selectedRows()
        
        if len(selected_rows) == 1:
            # 单选模式
            row = selected_rows[0].row()
            
            # 获取歌曲信息
            self.current_song = self.result_list[row]
            song_name = self.current_song.get('name', '')
            singer = self.current_song.get('singer', '')
            
            # 获取音质信息
            quality = self.current_song.get('quality', '')
            if quality:
                quality_text = f"[{quality}]"
            else:
                quality_text = ""
            
            # 更新当前选中歌曲标签
            self.current_song_label.setText(f"当前选择: {song_name} - {singer} {quality_text}")
            
            # 启用下载按钮
            self.download_btn.setEnabled(True)
        elif len(selected_rows) > 1:
            # 多选模式
            self.current_song = None
            self.current_song_label.setText(f"已选择 {len(selected_rows)} 首歌曲")
            
            # 禁用单个下载按钮，使用批量下载
            self.download_btn.setEnabled(False)
        else:
            # 没有选中行
            self.current_song = None
            self.current_song_label.setText("当前未选择歌曲")
            self.download_btn.setEnabled(False)
    
    def on_table_item_double_clicked(self, item):
        """表格项双击事件 - 直接下载"""
        # 获取当前选中的行
        row = item.row()
        
        # 获取歌曲信息
        self.current_song = self.result_list[row]
        
        # 立即开始下载
        self.download_music()
    
    def handle_search_result(self, result):
        """处理搜索结果"""
        # 如果窗口正在关闭，忽略处理
        if hasattr(self, 'is_closing') and self.is_closing:
            print("窗口正在关闭，忽略搜索结果处理")
            return
        
        print(f"搜索结果返回，数量: {len(result)}")
        self.result_list = result
        self.update_result_table()
        
        if len(result) > 0:
            # 启用下一页按钮
            self.next_page_btn.setEnabled(True)
            # 根据当前页码启用/禁用上一页按钮
            self.prev_page_btn.setEnabled(self.current_api.current_page > 1)
            # 更新页码信息
            self.page_info_label.setText(f"第{self.current_api.current_page}页")
            
            print(f"搜索成功，当前页: {self.current_api.current_page}, 结果数: {len(result)}")
            self.update_status_bar(f"当前平台: {self.current_api.name} | 第{self.current_api.current_page}页 | 找到 {len(result)} 首歌曲")
        else:
            # 禁用分页按钮
            self.next_page_btn.setEnabled(False)
            self.prev_page_btn.setEnabled(False)
            self.page_info_label.setText("无结果")
            
            print(f"搜索无结果")
            self.update_status_bar(f"当前平台: {self.current_api.name} | 未找到匹配的歌曲")
    
    def handle_search_error(self, error_msg):
        """处理搜索错误"""
        # 如果窗口正在关闭，忽略处理
        if hasattr(self, 'is_closing') and self.is_closing:
            print("窗口正在关闭，忽略搜索错误处理")
            return
            
        print(f"搜索出错: {error_msg}")
        
        # 更新状态栏
        self.update_status_bar(f"当前平台: {self.current_api.name} | 搜索错误: {error_msg}")
        
        # 清空搜索结果
        self.result_list = []
        self.update_result_table(clear_only=True)  # 只清空表格，不显示提示
        
        # 禁用分页按钮
        self.next_page_btn.setEnabled(False)
        self.prev_page_btn.setEnabled(False)
        self.page_info_label.setText("搜索出错")
        
        # 显示错误信息
        self.show_message(f'搜索出错: {error_msg}')
    
    def load_next_page(self):
        """加载下一页结果"""
        if not self.last_search_keyword:
            return
        
        # 显示加载状态
        next_page = self.current_api.current_page + 1
        self.update_status_bar(f"正在加载第{next_page}页...")
        
        # 获取下一页数据
        next_page_results = self.current_api.get_next_page(self.last_search_keyword)
        
        # 处理搜索结果
        if next_page_results:
            # 替换结果列表，而不是追加
            self.result_list = next_page_results
            self.update_result_table()
            
            # 更新页码信息
            self.page_info_label.setText(f"第{self.current_api.current_page}页")
            self.prev_page_btn.setEnabled(self.current_api.current_page > 1)
            
            print(f"下一页加载完成，结果数: {len(next_page_results)}")
            self.update_status_bar(f"当前平台: {self.current_api.name} | 第{self.current_api.current_page}页 | 找到 {len(next_page_results)} 首歌曲")
        else:
            print(f"下一页没有更多结果")
            self.update_status_bar(f"当前平台: {self.current_api.name} | 没有更多结果")
            self.next_page_btn.setEnabled(False)
    
    def load_previous_page(self):
        """加载上一页结果"""
        if not self.last_search_keyword or self.current_api.current_page <= 1:
            return
        
        # 显示加载状态
        prev_page = self.current_api.current_page - 1
        self.update_status_bar(f"正在加载第{prev_page}页...")
        
        # 获取上一页数据
        prev_page_results = self.current_api.get_previous_page(self.last_search_keyword)
        
        # 处理搜索结果
        if prev_page_results:
            # 替换结果列表，而不是追加
            self.result_list = prev_page_results
            self.update_result_table()
            
            # 更新页码信息
            self.page_info_label.setText(f"第{self.current_api.current_page}页")
            self.prev_page_btn.setEnabled(self.current_api.current_page > 1)
            self.next_page_btn.setEnabled(True)
            
            self.update_status_bar(f"当前平台: {self.current_api.name} | 第{self.current_api.current_page}页 | 找到 {len(prev_page_results)} 首歌曲")
        else:
            self.update_status_bar(f"当前平台: {self.current_api.name} | 无法加载上一页")
    
    def download_music(self):
        """
        下载选中的歌曲
        """
        # 检查当前是否已选择歌曲
        if self.current_song:
            song = self.current_song
        else:
            # 获取选中的行
            selected_rows = self.result_table.selectionModel().selectedRows()
            
            if len(selected_rows) == 0:
                self.show_message('请先选择要下载的歌曲')
                return
            
            # 获取选中的歌曲
            row = selected_rows[0].row()
            if row >= len(self.result_list):
                self.show_message('选择的歌曲无效，请重新选择')
                return
            
            song = self.result_list[row]
            self.current_song = song
        
        # 更新状态栏
        self.update_status_bar(f"正在下载: {song['name']} - {song['singer']}...")
        print(f"开始下载歌曲: {song['name']} - {song['singer']}, ID: {song['id']}")
        
        # 准备下载路径
        file_ext = '.mp3'
        if '无损' in song.get('quality', '') or 'FLAC' in song.get('quality', ''):
            file_ext = '.flac'
        
        save_path = os.path.join(
            self.download_path, 
            f"{song['name']} - {song['singer']}{file_ext}"
        )
        
        print(f"下载路径: {save_path}")
        
        # 准备歌曲ID参数
        song_id = song['id']
        # 对于网易云音乐，可能需要额外的音质信息
        if 'max_br' in song:
            song_id = f"{song_id}|{song.get('max_br')}"
        
        # 创建线程
        self.download_thread = DownloadThread(
            self.current_api, 
            song_id, 
            save_path
        )
        
        # 连接信号
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.handle_download_complete)
        self.download_thread.error_signal.connect(self.handle_download_error)
        
        # 禁用下载按钮，防止重复点击
        self.download_btn.setEnabled(False)
        
        # 启动线程
        self.download_thread.start()
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def handle_download_complete(self, save_path):
        """处理下载完成"""
        # 如果窗口正在关闭，忽略处理
        if hasattr(self, 'is_closing') and self.is_closing:
            print("窗口正在关闭，忽略下载完成处理")
            return
            
        song = self.current_song
        
        print(f"下载完成: {song['name']} - {song['singer']}, 路径: {save_path}")
        
        # 更新状态栏
        self.update_status_bar(f"下载完成: {song['name']} - {song['singer']}")
        
        # 重新启用下载按钮
        self.download_btn.setEnabled(True)
        
        # 重置进度条
        self.progress_bar.setValue(0)
        
        if save_path:
            self.show_message(f'下载成功！\n保存在: {save_path}')
            # 不再弹出打开目录的提示
        else:
            self.show_message('下载失败')
    
    def handle_download_error(self, error_msg):
        """处理下载错误"""
        # 如果窗口正在关闭，忽略处理
        if hasattr(self, 'is_closing') and self.is_closing:
            print("窗口正在关闭，忽略下载错误处理")
            return
            
        song = self.current_song
        
        print(f"下载出错: {song['name']} - {song['singer']}, 错误: {error_msg}")
        
        # 更新状态栏
        self.update_status_bar(f"下载失败: {song['name']} - {song['singer']}")
        
        # 重新启用下载按钮
        self.download_btn.setEnabled(True)
        
        # 重置进度条
        self.progress_bar.setValue(0)
        
        # 显示错误信息
        self.show_message(f'下载出错: {error_msg}')
    
    def update_status_bar(self, message):
        """更新状态栏信息"""
        self.status_bar.showMessage(message)
    
    def show_message(self, message):
        """显示消息"""
        QMessageBox.information(self, "提示", message)
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        print("窗口正在关闭，正在清理线程...")
        
        # 设置关闭标志，防止其他操作
        self.is_closing = True
        
        # 等待搜索线程结束
        if self.search_thread and self.search_thread.isRunning():
            print("等待搜索线程结束...")
            self.search_thread.wait(1000)  # 等待最多1秒
            
            if self.search_thread.isRunning():
                print("强制终止搜索线程...")
                self.search_thread.terminate()
                self.search_thread.wait()
            print("搜索线程已终止")
        
        # 等待下载线程结束
        if self.download_thread and self.download_thread.isRunning():
            print("等待下载线程结束...")
            self.download_thread.wait(1000)  # 等待最多1秒
            
            if self.download_thread.isRunning():
                print("强制终止下载线程...")
                self.download_thread.terminate()
                self.download_thread.wait()
            print("下载线程已终止")
        
        # 调用父类方法
        super().closeEvent(event)
    
    def center(self):
        """居中显示窗口"""
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def show(self):
        """显示窗口"""
        super().show()
        self.raise_()
        self.activateWindow()

    def batch_download_music(self):
        """批量下载歌曲"""
        selected_rows = self.result_table.selectionModel().selectedRows()
        
        # 如果有选中行，就只下载选中的歌曲
        if len(selected_rows) > 0:
            songs_to_download = [self.result_list[row.row()] for row in selected_rows]
        else:
            # 否则下载当前页面所有歌曲
            songs_to_download = self.result_list
        
        if not songs_to_download:
            self.show_message('没有可下载的歌曲')
            return
        
        # 确认下载
        reply = QMessageBox.question(
            self, 
            '批量下载', 
            f'确定要批量下载 {len(songs_to_download)} 首歌曲吗？',
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # 重置进度条
            self.progress_bar.setValue(0)
            
            # 开始批量下载
            self.batch_download_songs(songs_to_download)
    
    def batch_download_songs(self, songs_list):
        """批量下载歌曲列表"""
        # 禁用下载按钮
        self.download_btn.setEnabled(False)
        self.batch_download_btn.setEnabled(False)
        
        # 创建下载队列
        self.download_queue = songs_list.copy()
        self.total_songs = len(self.download_queue)
        self.downloaded_count = 0
        
        # 开始下载第一首歌曲
        self.download_next_song()
    
    def download_next_song(self):
        """下载队列中的下一首歌曲"""
        if not self.download_queue:
            # 队列为空，下载完成
            self.show_message(f'批量下载完成，共 {self.downloaded_count}/{self.total_songs} 首歌曲下载成功')
            
            # 重置进度条
            self.progress_bar.setValue(0)
            
            # 恢复按钮状态
            self.batch_download_btn.setEnabled(True)
            if self.current_song:
                self.download_btn.setEnabled(True)
            
            return
        
        # 取出队列中的第一首歌曲
        song = self.download_queue.pop(0)
        self.current_song = song
        
        # 更新状态栏
        self.update_status_bar(f"正在下载: {song['name']} - {song['singer']}... ({self.downloaded_count+1}/{self.total_songs})")
        print(f"批量下载: {song['name']} - {song['singer']}, ID: {song['id']}")
        
        # 准备下载路径
        file_ext = '.mp3'
        if '无损' in song.get('quality', '') or 'FLAC' in song.get('quality', ''):
            file_ext = '.flac'
        
        save_path = os.path.join(
            self.download_path, 
            f"{song['name']} - {song['singer']}{file_ext}"
        )
        
        print(f"下载路径: {save_path}")
        
        # 准备歌曲ID参数
        song_id = song['id']
        # 对于网易云音乐，可能需要额外的音质信息
        if 'max_br' in song:
            song_id = f"{song_id}|{song.get('max_br')}"
        
        # 创建线程
        self.download_thread = DownloadThread(
            self.current_api, 
            song_id, 
            save_path
        )
        
        # 连接信号
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.finished_signal.connect(self.handle_batch_download_complete)
        self.download_thread.error_signal.connect(self.handle_batch_download_error)
        
        # 启动线程
        self.download_thread.start()
    
    def handle_batch_download_complete(self, save_path):
        """处理批量下载中的单首歌曲下载完成"""
        # 如果窗口正在关闭，忽略处理
        if hasattr(self, 'is_closing') and self.is_closing:
            print("窗口正在关闭，忽略下载完成处理")
            return
            
        song = self.current_song
        
        print(f"批量下载完成一首: {song['name']} - {song['singer']}, 路径: {save_path}")
        
        # 更新计数
        self.downloaded_count += 1
        
        # 继续下载下一首
        self.download_next_song()
    
    def handle_batch_download_error(self, error_msg):
        """处理批量下载中的单首歌曲下载错误"""
        # 如果窗口正在关闭，忽略处理
        if hasattr(self, 'is_closing') and self.is_closing:
            print("窗口正在关闭，忽略下载错误处理")
            return
            
        song = self.current_song
        
        print(f"批量下载出错: {song['name']} - {song['singer']}, 错误: {error_msg}")
        
        # 继续下载下一首
        self.download_next_song()

    def select_download_path(self):
        """选择下载路径"""
        path = QFileDialog.getExistingDirectory(
            self, 
            "选择下载目录", 
            self.download_path,
            QFileDialog.ShowDirsOnly
        )
        
        if path:
            self.download_path = path
            self.path_label.setText(f"下载到: {path}")
            self.show_message(f"下载路径已设置为: {path}")

    def update_result_table(self, clear_only=False):
        """更新结果表格
        :param clear_only: 是否只清空表格，不显示提示
        """
        if not self.result_list:
            # 清空表格
            self.result_table.setRowCount(0)
            
            # 禁用批量下载按钮
            self.batch_download_btn.setEnabled(False)
            
            # 仅当有搜索且不是源切换时才显示提示
            if self.has_searched and not clear_only and not self.is_source_changing:
                print(f"无搜索结果，显示提示框")
                self.show_message("未找到相关歌曲")
            return
        
        print(f"更新结果表格，结果数: {len(self.result_list)}")
        
        # 清空表格
        self.result_table.setRowCount(0)
        
        # 添加搜索结果到表格
        for row, song in enumerate(self.result_list):
            self.result_table.insertRow(row)
            
            # 歌曲名
            name_item = QTableWidgetItem(song.get('name', ''))
            name_item.setData(Qt.UserRole, song)  # 存储歌曲完整信息
            self.result_table.setItem(row, 0, name_item)
            
            # 歌手
            self.result_table.setItem(row, 1, QTableWidgetItem(song.get('singer', '')))
            
            # 专辑
            album_name = ""
            if isinstance(song.get('album'), str):
                album_name = song.get('album')
            elif isinstance(song.get('album'), dict):
                album_name = song.get('album', {}).get('name', '')
            self.result_table.setItem(row, 2, QTableWidgetItem(album_name))
            
            # 大小
            size_item = QTableWidgetItem(song.get('size', '未知'))
            self.result_table.setItem(row, 3, size_item)
            
            # 音质
            quality = song.get('quality', '标准')
            quality_item = QTableWidgetItem(quality)
            # 根据音质设置不同颜色
            if '320K' in quality or '高品' in quality:
                quality_item.setForeground(QColor(0, 0, 255))  # 蓝色表示高品质
            self.result_table.setItem(row, 4, quality_item)
            
            # 来源
            source_text = self.current_api.name
            self.result_table.setItem(row, 5, QTableWidgetItem(source_text))
        
        # 如果有结果，启用批量下载按钮
        if len(self.result_list) > 0:
            self.batch_download_btn.setEnabled(True) 