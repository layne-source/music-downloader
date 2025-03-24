#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import time
import platform
from datetime import datetime

class Tools:
    """工具类"""
    
    @staticmethod
    def format_time(seconds):
        """
        格式化时间
        :param seconds: 秒数
        :return: 格式化后的时间字符串
        """
        if not isinstance(seconds, (int, float)) or seconds < 0:
            return "00:00"
            
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"
    
    @staticmethod
    def format_file_size(size_bytes):
        """
        格式化文件大小
        :param size_bytes: 文件大小（字节）
        :return: 格式化后的文件大小字符串
        """
        if not size_bytes or not isinstance(size_bytes, (int, float)):
            return "未知"
        
        if size_bytes < 0:
            return "0 B"
            
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
    
    @staticmethod
    def sanitize_filename(filename):
        """
        清理文件名，去除非法字符
        :param filename: 原始文件名
        :return: 清理后的文件名
        """
        if not filename:
            return "unnamed"
            
        # 移除Windows文件名中的非法字符 \ / : * ? " < > |
        illegal_chars = r'[\\/:*?"<>|]'
        sanitized = re.sub(illegal_chars, '_', filename)
        
        # 移除前导和尾随空格
        sanitized = sanitized.strip()
        
        # 移除控制字符
        sanitized = re.sub(r'[\x00-\x1f\x7f]', '', sanitized)
        
        # 限制文件名长度，为扩展名保留空间
        if len(sanitized) > 200:
            name, ext = os.path.splitext(sanitized)
            max_len = 200 - len(ext)
            sanitized = name[:max_len] + ext
        
        # 确保文件名不为空
        if not sanitized or sanitized.isspace():
            return "unnamed"
            
        return sanitized
    
    @staticmethod
    def get_default_download_path():
        """
        获取默认下载路径
        :return: 默认下载路径
        """
        try:
            # 在用户桌面创建Music文件夹
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            # 兼容中文系统
            if not os.path.exists(desktop):
                desktop = os.path.join(os.path.expanduser("~"), "桌面")
                
            # 如果桌面路径仍然不存在，使用用户目录中的Music文件夹
            if not os.path.exists(desktop):
                if platform.system() == 'Windows':
                    return os.path.join(os.path.expanduser("~"), "Music")
                else:
                    return os.path.join(os.path.expanduser("~"), "Music")
                    
            download_path = os.path.join(desktop, "Music")
            
            # 确保目录存在
            if not os.path.exists(download_path):
                try:
                    os.makedirs(download_path)
                    print(f"已创建下载目录: {download_path}")
                except Exception as e:
                    print(f"创建下载目录失败: {e}")
                    # 创建失败时，使用当前目录下的downloads文件夹
                    download_path = os.path.join(os.getcwd(), "downloads")
                    if not os.path.exists(download_path):
                        os.makedirs(download_path)
            
            return download_path
            
        except Exception as e:
            print(f"获取默认下载路径出错: {e}")
            # 出错时返回当前目录下的downloads文件夹
            fallback_path = os.path.join(os.getcwd(), "downloads")
            if not os.path.exists(fallback_path):
                os.makedirs(fallback_path)
            return fallback_path
    
    @staticmethod
    def generate_filename(song_info):
        """
        根据歌曲信息生成文件名
        :param song_info: 歌曲信息
        :return: 文件名
        """
        if not song_info or not isinstance(song_info, dict):
            return "unknown.mp3"
            
        name = song_info.get('name', '')
        singer = song_info.get('singer', '')
        
        if not name:
            name = "未知歌曲"
            
        if singer:
            filename = f"{name} - {singer}.mp3"
        else:
            filename = f"{name}.mp3"
        
        return Tools.sanitize_filename(filename)
    
    @staticmethod
    def get_current_timestamp():
        """
        获取当前时间戳
        :return: 时间戳字符串
        """
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
    @staticmethod
    def ensure_dir(directory):
        """
        确保目录存在
        :param directory: 目录路径
        :return: 确保存在后的目录路径
        """
        if not directory:
            return os.getcwd()
            
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"创建目录: {directory}")
            return directory
        except Exception as e:
            print(f"创建目录失败 {directory}: {e}")
            fallback = os.getcwd()
            print(f"使用备用目录: {fallback}")
            return fallback 