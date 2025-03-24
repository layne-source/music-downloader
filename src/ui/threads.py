#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import traceback
from PyQt5.QtCore import QThread, pyqtSignal


class SearchThread(QThread):
    """搜索线程"""
    # 定义信号
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    
    def __init__(self, api, keyword, page=1, page_size=30):
        """
        初始化搜索线程
        :param api: API实例
        :param keyword: 搜索关键词
        :param page: 页码
        :param page_size: 每页数量
        """
        super().__init__()
        self.api = api
        self.keyword = keyword
        self.page = page
        self.page_size = page_size
    
    def run(self):
        """执行搜索"""
        try:
            result = self.api.search(self.keyword, self.page, self.page_size)
            self.result_signal.emit(result)
        except Exception as e:
            error_msg = f"搜索出错: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            self.error_signal.emit(error_msg)


class DownloadThread(QThread):
    """下载线程"""
    # 定义信号
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, api, song_id, save_path):
        """
        初始化下载线程
        :param api: API实例
        :param song_id: 歌曲ID
        :param save_path: 保存路径
        """
        super().__init__()
        self.api = api
        self.song_id = song_id
        self.save_path = save_path
        self.is_cancelled = False
    
    def cancel(self):
        """取消下载"""
        self.is_cancelled = True
    
    def run(self):
        """执行下载"""
        try:
            # 设置初始进度
            self.progress_signal.emit(0)
            
            # 确保目录存在
            save_dir = os.path.dirname(self.save_path)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            
            # 尝试使用API的下载方法
            if hasattr(self.api, 'download'):
                max_retries = 3
                for retry in range(max_retries):
                    if self.is_cancelled:
                        break
                        
                    try:
                        # 模拟进度更新
                        self.progress_signal.emit(5 + retry * 5)
                        
                        # 直接调用download方法，内部获取链接
                        saved_path = self.api.download(self.song_id, self.save_path)
                        if saved_path:
                            self.progress_signal.emit(100)
                            self.finished_signal.emit(saved_path)
                            return
                        
                        if retry < max_retries - 1:
                            print(f"下载重试 ({retry+1}/{max_retries})...")
                            time.sleep(1)  # 短暂延迟后重试
                    except Exception as e:
                        print(f"下载尝试 {retry+1}/{max_retries} 失败: {e}")
                        if retry == max_retries - 1:
                            raise
                        time.sleep(1)
                
                # 如果API的download方法失败，尝试自己实现下载
                if not os.path.exists(self.save_path) or os.path.getsize(self.save_path) < 10 * 1024:
                    url = None
                    if hasattr(self.api, 'get_song_url'):
                        url = self.api.get_song_url(self.song_id)
                        
                    if not url:
                        self.error_signal.emit("下载失败，无法获取下载链接")
                        self._cleanup()
                        return
                else:
                    # API下载方法成功
                    return
            
            # 无法使用API的download方法，或者API的download方法失败后
            # 使用自己的下载实现
            import requests
            
            # 获取下载链接
            url = None
            if hasattr(self.api, 'get_song_url'):
                url = self.api.get_song_url(self.song_id)
            
            if not url:
                self.error_signal.emit("下载失败，无法获取下载链接")
                self._cleanup()
                return
            
            # 使用API的session进行下载
            session = self.api.session if hasattr(self.api, 'session') else requests.Session()
            
            # 添加超时和重试机制
            max_retries = 3
            for retry in range(max_retries):
                if self.is_cancelled:
                    break
                    
                try:
                    # 检查URL有效性
                    self.progress_signal.emit(5)
                    head_resp = session.head(url, timeout=10, allow_redirects=True)
                    if head_resp.status_code >= 400:
                        if retry < max_retries - 1:
                            print(f"URL无效 ({head_resp.status_code})，重试中...")
                            time.sleep(1)
                            continue
                        else:
                            self.error_signal.emit(f"下载链接无效 (HTTP {head_resp.status_code})")
                            self._cleanup()
                            return
                    
                    total_size = int(head_resp.headers.get('content-length', 0))
                    if total_size > 0 and total_size < 10 * 1024:  # 小于10KB
                        print(f"警告：文件过小 ({total_size} 字节)")
                    
                    # 开始下载
                    self.progress_signal.emit(10)
                    downloaded = 0
                    chunk_size = 16384  # 更大的块大小，提高效率
                    
                    with session.get(url, stream=True, timeout=60) as response:
                        response.raise_for_status()
                        
                        # 更新实际大小
                        total_size = int(response.headers.get('content-length', total_size))
                        
                        with open(self.save_path, 'wb') as f:
                            if total_size > 0:
                                # 有总大小，可以显示进度
                                for chunk in response.iter_content(chunk_size=chunk_size):
                                    if self.is_cancelled:
                                        break
                                        
                                    if chunk:
                                        f.write(chunk)
                                        downloaded += len(chunk)
                                        progress = int(min(10 + downloaded * 90 / total_size, 100))
                                        self.progress_signal.emit(progress)
                            else:
                                # 无法获取总大小，只能模拟进度
                                for i, chunk in enumerate(response.iter_content(chunk_size=chunk_size)):
                                    if self.is_cancelled:
                                        break
                                        
                                    if chunk:
                                        f.write(chunk)
                                        downloaded += len(chunk)
                                        # 每10块更新一次进度，最多到95%
                                        if i % 5 == 0:
                                            progress = min(10 + i, 95)
                                            self.progress_signal.emit(progress)
                    
                    # 如果因取消而中断
                    if self.is_cancelled:
                        self._cleanup()
                        return
                    
                    # 校验文件
                    if os.path.exists(self.save_path):
                        file_size = os.path.getsize(self.save_path)
                        if file_size > 100 * 1024:  # 大于100KB的文件可能是有效的音乐
                            self.progress_signal.emit(100)
                            self.finished_signal.emit(self.save_path)
                            return
                        elif file_size > 10 * 1024:  # 大于10KB可能是短音频
                            print(f"警告：下载的文件较小 ({file_size} 字节)")
                            self.progress_signal.emit(100)
                            self.finished_signal.emit(self.save_path)
                            return
                        else:
                            print(f"下载的文件过小 ({file_size} 字节)，可能无效")
                            if retry < max_retries - 1:
                                os.remove(self.save_path)
                                time.sleep(1)
                                continue
                    
                    # 文件验证失败但已尝试最大次数
                    self.error_signal.emit("下载文件不完整或无效")
                    self._cleanup()
                    return
                    
                except requests.RequestException as e:
                    if retry < max_retries - 1:
                        print(f"下载出错，正在重试 ({retry+1}/{max_retries}): {e}")
                        time.sleep(1)
                    else:
                        error_msg = f"下载失败: {e}"
                        print(error_msg)
                        print(traceback.format_exc())
                        self.error_signal.emit(error_msg)
                        self._cleanup()
                except Exception as e:
                    error_msg = f"下载出错: {e}"
                    print(error_msg)
                    print(traceback.format_exc())
                    self.error_signal.emit(error_msg)
                    self._cleanup()
                    return
            
        except Exception as e:
            error_msg = f"下载过程出错: {e}"
            print(error_msg)
            print(traceback.format_exc())
            self.error_signal.emit(error_msg)
            self.progress_signal.emit(0)
            self._cleanup()
    
    def _cleanup(self):
        """清理临时文件"""
        try:
            if os.path.exists(self.save_path):
                file_size = os.path.getsize(self.save_path)
                if file_size < 100 * 1024:  # 小于100KB的文件可能无效
                    os.remove(self.save_path)
                    print(f"已删除可能不完整的文件: {self.save_path}")
        except Exception as e:
            print(f"清理文件时出错: {e}") 