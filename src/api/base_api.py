#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import random
import traceback
from fake_useragent import UserAgent
from abc import ABC, abstractmethod


class MusicAPI(ABC):
    """音乐搜索API基类"""
    
    # 预定义的可靠User-Agent
    DEFAULT_USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    def __init__(self):
        self.session = self._create_session()
    
    def _create_session(self):
        """创建并配置请求会话"""
        session = requests.Session()
        
        # 尝试使用fake_useragent，失败则使用预定义的User-Agent
        try:
            ua = UserAgent().random
        except Exception as e:
            print(f"获取随机User-Agent失败: {e}，使用默认值")
            ua = random.choice(self.DEFAULT_USER_AGENTS)
        
        # 设置基本请求头
        session.headers.update({
            'User-Agent': ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # 配置安全选项
        session.verify = True  # 启用SSL证书验证
        
        # 配置重试策略
        adapter = requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=10,
            pool_maxsize=10
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def _refresh_session(self):
        """刷新会话，用于处理会话失效的情况"""
        old_cookies = self.session.cookies.copy()
        self.session = self._create_session()
        self.session.cookies.update(old_cookies)
        return self.session
    
    def _safe_request(self, method, url, **kwargs):
        """安全的请求封装，处理异常和重试"""
        max_retries = kwargs.pop('max_retries', 3)
        timeout = kwargs.pop('timeout', 15)
        
        # 确保有超时设置
        if 'timeout' not in kwargs:
            kwargs['timeout'] = timeout
            
        for retry in range(max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                print(f"请求失败 ({retry+1}/{max_retries}): {e}")
                if retry == max_retries - 1:  # 最后一次重试
                    print(f"请求最终失败: {url}")
                    raise
                
                # 遇到特定错误时刷新会话
                if isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.TooManyRedirects)):
                    self._refresh_session()
                    
        return None  # 不应该到达这里
    
    @abstractmethod
    def search(self, keyword, page=1, page_size=20):
        """
        搜索歌曲
        :param keyword: 搜索关键词
        :param page: 页码
        :param page_size: 每页数量
        :return: 搜索结果列表
        """
        pass
    
    @abstractmethod
    def get_song_url(self, song_id):
        """
        获取歌曲下载链接
        :param song_id: 歌曲ID
        :return: 歌曲下载链接
        """
        pass
    
    @abstractmethod
    def download(self, song_id, save_path):
        """
        下载歌曲
        :param song_id: 歌曲ID
        :param save_path: 保存路径
        :return: 保存路径
        """
        pass
        
    def get_next_page(self, keyword):
        """默认的下一页实现"""
        raise NotImplementedError("该API未实现获取下一页功能")
        
    def get_previous_page(self, keyword):
        """默认的上一页实现"""
        raise NotImplementedError("该API未实现获取上一页功能") 