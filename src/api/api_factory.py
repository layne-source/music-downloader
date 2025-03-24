#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src.api.netease_api import NeteaseAPI
from src.api.gdmusic_api import GDMusicAPI


class APIFactory:
    """API工厂类，用于获取不同平台的API实例"""
    
    def __init__(self):
        self._apis = {}
        self._init_apis()
    
    def _init_apis(self):
        """初始化所有支持的API"""
        self._apis['网易云音乐'] = NeteaseAPI()
        self._apis['GD音乐'] = GDMusicAPI()
        
    def get_api(self, name):
        """
        获取指定平台的API实例
        :param name: 平台名称
        :return: API实例
        """
        return self._apis.get(name)
    
    def get_all_apis(self):
        """
        获取所有支持的API实例
        :return: API实例字典
        """
        return self._apis
    
    def get_api_names(self):
        """获取支持的API名称列表"""
        return ['GD音乐', '网易云音乐'] 