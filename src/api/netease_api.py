#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import requests
import random
import time
from urllib.parse import quote
import traceback

from src.api.base_api import MusicAPI


class NeteaseAPI(MusicAPI):
    """网易云音乐API - 使用公开API接口"""

    def __init__(self):
        super().__init__()
        self.name = '网易云音乐'
        
        # 使用公开搜索API
        self.search_url = 'https://music.163.com/api/search/get'
        self.song_url_api = 'https://music.163.com/api/song/enhance/player/url'
        self.song_detail_api = 'https://music.163.com/api/song/detail'
        
        # 备用下载API
        self.alt_song_url_api = 'https://music.163.com/song/media/outer/url'
        
        # 添加当前页码属性
        self.current_page = 1
        
        # 更新必要的请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
            'Referer': 'https://music.163.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def search(self, keyword, page=1, page_size=30):
        """
        搜索歌曲
        :param keyword: 搜索关键词
        :param page: 页码
        :param page_size: 每页数量
        :return: 搜索结果列表
        """
        try:
            print(f"正在搜索网易云音乐: {keyword}")
            # 更新当前页码
            self.current_page = page
            
            # 使用简单的搜索API
            params = {
                's': keyword,
                'type': 1,  # 1: 单曲, 10: 专辑, 100: 歌手, 1000: 歌单
                'limit': page_size,
                'offset': (page - 1) * page_size
            }
            
            try:
                # 使用安全请求方法
                response = self._safe_request(
                    'get',
                    self.search_url,
                    params=params,
                    timeout=15
                )
                
                data = response.json()
                if data.get('code') != 200:
                    print(f"搜索API返回错误: {data.get('code')}")
                    return []
                
                songs = data.get('result', {}).get('songs', [])
                if not songs:
                    print("未找到相关歌曲")
                    return []
                
                result = []
                for song in songs:
                    # 基本信息
                    song_id = song.get('id', '')
                    song_name = song.get('name', '')
                    
                    # 歌手信息
                    artists = song.get('artists', [])
                    artist_names = '/'.join([artist.get('name', '') for artist in artists])
                    
                    # 专辑信息
                    album = song.get('album', {})
                    album_name = album.get('name', '')
                    
                    # 时长
                    duration = int(song.get('duration', 0) / 1000)  # 毫秒转秒
                    
                    # 音质信息 - 只处理MP3格式
                    max_br = 320000  # 默认最高码率
                    if song.get('hMusic'):
                        max_br = 320000
                        quality = '320K'
                        size = song.get('hMusic', {}).get('size', 0)
                    elif song.get('mMusic'):
                        max_br = 192000
                        quality = '192K'
                        size = song.get('mMusic', {}).get('size', 0)
                    elif song.get('lMusic'):
                        max_br = 128000
                        quality = '128K'
                        size = song.get('lMusic', {}).get('size', 0)
                    else:
                        quality = '标准'
                        size = 0
                    
                    # 格式化大小
                    size_text = self._format_size(size)
                    
                    # 获取专辑图片
                    pic_url = album.get('picUrl', '')
                    
                    # 添加到结果列表
                    result.append({
                        'name': song_name,
                        'id': song_id,
                        'singer': artist_names,
                        'album': album_name,
                        'duration': duration,
                        'source': self.name,
                        'size': size_text,
                        'quality': quality,
                        'max_br': max_br,
                        'pic_url': pic_url
                    })
                
                print(f"搜索完成，找到 {len(result)} 首歌曲")
                return result
                
            except Exception as e:
                print(f"搜索API请求出错: {e}")
                return []
            
        except Exception as e:
            print(f"网易云音乐搜索出错: {e}")
            return []
    
    def _format_size(self, size_bytes):
        """格式化文件大小"""
        if not size_bytes or size_bytes == 0:
            return "未知"
        
        b = float(size_bytes)
        kb = b / 1024
        if kb < 1024:
            return f"{kb:.2f}KB"
        mb = kb / 1024
        if mb < 1024:
            return f"{mb:.2f}MB"
        gb = mb / 1024
        return f"{gb:.2f}GB"
    
    def get_song_url(self, song_id, br=320000):
        """
        获取歌曲下载链接
        :param song_id: 歌曲ID
        :param br: 比特率，可选值: 320000, 192000, 128000
        :return: 歌曲下载链接
        """
        try:
            print(f"正在获取歌曲链接: {song_id}, 比特率: {br/1000:.0f}K")
            
            params = {
                'ids': song_id,
                'br': br,
                'id': song_id,
            }
            
            try:
                response = self._safe_request(
                    'get',
                    self.song_url_api,
                    params=params,
                    timeout=15
                )
                
                data = response.json()
                
                if data.get('code') != 200:
                    print(f"获取歌曲URL API返回错误: {data.get('code')}")
                    # 尝试备选URL方式
                    return self._get_alt_song_url(song_id)
                
                url_data = data.get('data', [{}])[0]
                url = url_data.get('url', '')
                
                if not url:
                    print(f"API返回的URL为空，尝试备选方式")
                    return self._get_alt_song_url(song_id)
                
                # 验证URL是否有效
                try:
                    head_resp = self._safe_request('head', url, allow_redirects=True, timeout=10)
                    content_length = int(head_resp.headers.get('Content-Length', 0))
                    
                    if content_length < 10240:  # 小于10KB可能无效
                        print(f"警告: URL返回的文件过小 ({content_length} 字节)")
                        if content_length < 1000:  # 非常小，可能无效
                            return self._get_alt_song_url(song_id)
                except Exception as e:
                    print(f"验证URL出错: {e}")
                    # 即使验证失败，仍返回URL
                
                return url
            
            except Exception as e:
                print(f"获取歌曲URL请求失败: {e}")
                # 尝试备选URL方式
                return self._get_alt_song_url(song_id)
        
        except Exception as e:
            print(f"获取网易云音乐下载链接出错: {e}")
            traceback.print_exc()
            # 尝试备用链接
            return self._get_alt_song_url(song_id)
    
    def _get_alt_song_url(self, song_id):
        """
        备用方法获取歌曲下载链接
        :param song_id: 歌曲ID
        :return: 歌曲下载链接
        """
        try:
            # 尝试多个方法获取歌曲URL
            
            # 方法1: 从歌曲详情获取
            detail_url = f"https://music.163.com/api/v1/song/detail?ids=[{song_id}]"
            detail_resp = self.session.get(detail_url, timeout=10)
            detail_data = detail_resp.json()
            
            if detail_data.get('code') == 200 and detail_data.get('songs'):
                song_detail = detail_data['songs'][0]
                song_id = song_detail.get('id')
                song_name = song_detail.get('name')
                
                # 方法2: 尝试从第三方API获取
                third_party_urls = [
                    f"https://autumnfish.cn/song/url?id={song_id}",
                    f"https://netease-cloud-music-api-eta-tawny.vercel.app/song/url?id={song_id}",
                    f"https://music.cyrilstudio.top/song/url?id={song_id}&br=320000"
                ]
                
                for api_url in third_party_urls:
                    try:
                        resp = self.session.get(api_url, timeout=10)
                        data = resp.json()
                        
                        if data.get('code') == 200 and data.get('data'):
                            url = data['data'][0].get('url')
                            if url and url.startswith('http'):
                                # 验证URL返回的文件大小
                                try:
                                    head_resp = self.session.head(url, allow_redirects=True, timeout=10)
                                    content_length = head_resp.headers.get('Content-Length', 0)
                                    if int(content_length) > 1000000:  # 文件大于1MB才可能是有效的音乐文件
                                        print(f"第三方API获取到有效URL，预计文件大小: {int(content_length)/1024/1024:.2f}MB")
                                        return url
                                except:
                                    pass
                    except Exception as e:
                        print(f"尝试第三方API失败: {e}")
                
                # 方法3: 使用直接的URL模式
                cdn_url = f"https://music.163.com/song/media/outer/url?id={song_id}.mp3"
                try:
                    # 尝试模拟浏览器访问
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36',
                        'Referer': 'https://music.163.com/'
                    }
                    head_resp = self.session.head(cdn_url, headers=headers, allow_redirects=True, timeout=10)
                    final_url = head_resp.url
                    
                    # 检查重定向后的URL是否可能是有效的音乐
                    if "m" in final_url and ".music.126.net" in final_url:
                        content_length = head_resp.headers.get('Content-Length', 0)
                        if int(content_length) > 1000000:
                            print(f"CDN链接重定向到有效音乐URL: {final_url[:100]}...")
                            return final_url
                        else:
                            print(f"CDN链接重定向后文件大小不足: {int(content_length)/1024:.2f}KB")
                except Exception as e:
                    print(f"检查CDN链接失败: {e}")
                
                # 方法4: 尝试通过其他API获取
                api_url = f"https://music.163.com/api/song/enhance/download/url?id={song_id}&br=320000"
                try:
                    resp = self.session.get(api_url, timeout=10)
                    data = resp.json()
                    if data.get('code') == 200 and data.get('data') and data['data'].get('url'):
                        dl_url = data['data']['url']
                        print(f"通过官方下载API获取到URL: {dl_url[:100]}...")
                        return dl_url
                except Exception as e:
                    print(f"通过官方下载API获取失败: {e}")
            
            print("所有备用方法都已尝试，未能获取有效下载链接")
            return None
                
        except Exception as e:
            print(f"获取备用下载链接出错: {e}")
            return None
    
    def get_song_detail(self, song_id):
        """
        获取歌曲详情
        :param song_id: 歌曲ID
        :return: 歌曲详情
        """
        try:
            params = {
                'ids': f'[{song_id}]'
            }
            
            try:
                response = self._safe_request(
                    'get',
                    self.song_detail_api,
                    params=params,
                    timeout=15
                )
                
                data = response.json()
                if data.get('code') != 200:
                    print(f"获取歌曲详情API返回错误: {data.get('code')}")
                    return {}
                
                return data.get('songs', [{}])[0]
            except Exception as e:
                print(f"获取歌曲详情请求失败: {e}")
                return {}
            
        except Exception as e:
            print(f"获取网易云音乐详情出错: {e}")
            traceback.print_exc()
            return {}
    
    def download(self, song_id, save_path):
        """
        下载歌曲
        :param song_id: 歌曲ID (song_id|max_br)
        :param save_path: 保存路径
        :return: 保存路径
        """
        try:
            # 检查是否包含音质信息
            if '|' in str(song_id):
                song_id, max_br = song_id.split('|')
                max_br = int(max_br)
            else:
                # 默认使用320kbps
                max_br = 320000
            
            # 获取下载链接 - 尝试不同的比特率
            url = None
            bit_rates = [320000, 192000, 128000]  # 从高到低尝试不同比特率
            
            for br in bit_rates:
                try:
                    # 如果请求的比特率高于当前尝试的比特率，降级
                    if br > max_br:
                        continue
                        
                    temp_url = self.get_song_url(song_id, br)
                    if not temp_url:
                        continue
                        
                    # 验证URL返回的文件大小
                    try:
                        head_resp = self.session.head(temp_url, allow_redirects=True, timeout=10)
                        content_length = int(head_resp.headers.get('Content-Length', 0))
                        content_type = head_resp.headers.get('Content-Type', '')
                        
                        # 检查是否是有效的音频文件
                        is_audio = 'audio' in content_type or 'octet-stream' in content_type
                        
                        if content_length > 1000000 or (is_audio and content_length > 100000):
                            print(f"找到有效下载链接 (br={br/1000:.0f}K): {temp_url[:100]}...")
                            url = temp_url
                            break
                        else:
                            print(f"比特率 {br/1000:.0f}K 的链接文件太小 ({content_length/1024:.2f}KB)，尝试较低比特率")
                    except Exception as e:
                        print(f"验证URL时出错: {e}")
                        # 即使验证失败，也存储这个URL作为备选
                        if not url:
                            url = temp_url
                except Exception as e:
                    print(f"获取比特率 {br/1000:.0f}K 的URL时出错: {e}")
            
            # 如果还是没有找到有效URL，尝试使用备用方法
            if not url:
                url = self._get_alt_song_url(song_id)
                
            # 如果所有方法都失败
            if not url:
                print(f"无法获取歌曲 {song_id} 的下载链接")
                return None
            
            print(f"开始下载歌曲: {url[:100]}...")
            
            # 创建目录
            if not os.path.exists(os.path.dirname(save_path)):
                os.makedirs(os.path.dirname(save_path))
            
            # 下载文件
            try:
                # 添加重试机制
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                            'Accept': '*/*',
                            'Referer': 'https://music.163.com/'
                        }
                        
                        with self.session.get(url, headers=headers, stream=True, timeout=30) as response:
                            response.raise_for_status()
                            total_size = int(response.headers.get('Content-Length', 0))
                            print(f"文件大小: {total_size} 字节")
                            
                            if total_size < 1000000 and total_size > 0:  # 小于1MB且大于0的可能不是完整音乐文件
                                print(f"警告: 下载的文件可能不完整，大小仅有 {total_size/1024:.2f}KB")
                                if retry < max_retries - 1:
                                    # 如果还有重试机会，尝试使用备用方法获取新URL
                                    alt_url = self._get_alt_song_url(song_id)
                                    if alt_url and alt_url != url:
                                        url = alt_url
                                        print(f"尝试使用备用链接: {url[:100]}...")
                                        continue
                            
                            with open(save_path, 'wb') as f:
                                downloaded = 0
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                                        downloaded += len(chunk)
                                
                                print(f"下载完成，文件大小: {downloaded} 字节")
                            
                            # 如果下载成功，跳出重试循环
                            break
                    except Exception as e:
                        print(f"下载尝试 {retry+1}/{max_retries} 失败: {e}")
                        if retry == max_retries - 1:  # 如果是最后一次尝试
                            raise
                        time.sleep(1)  # 等待1秒后重试
                
                # 检查文件大小，如果小于10KB可能是无效的
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    
                    if file_size < 10 * 1024:
                        print(f"下载的文件过小，可能是无效的: {save_path}")
                        os.remove(save_path)
                        
                        # 最后尝试一次备用下载
                        backup_url = self._get_alt_song_url(song_id)
                        if backup_url and backup_url != url:
                            print(f"尝试使用最终备用链接下载: {backup_url[:100]}...")
                            with self.session.get(backup_url, headers=headers, stream=True, timeout=30) as response:
                                response.raise_for_status()
                                with open(save_path, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
            except Exception as e:
                print(f"下载过程出错: {e}")
                # 如果文件存在但可能不完整，删除它
                if os.path.exists(save_path):
                    os.remove(save_path)
                return None
            
            # 最终检查
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                if file_size > 1000000:  # 大于1MB的文件可能是有效的音乐
                    print(f"下载完成: {save_path}")
                    return save_path
                elif file_size > 100 * 1024:  # 大于100KB的文件可能是有效的短音乐
                    print(f"下载完成(小文件): {save_path}")
                    return save_path
                else:
                    print(f"下载失败或文件无效: {save_path}")
                    if os.path.exists(save_path):
                        os.remove(save_path)
                    return None
            else:
                print(f"下载失败，文件不存在: {save_path}")
                return None
            
        except Exception as e:
            print(f"下载网易云音乐出错: {e}")
            return None
    
    def get_next_page(self, keyword):
        """获取下一页搜索结果"""
        self.current_page += 1
        return self.search(keyword, self.current_page)
    
    def get_previous_page(self, keyword):
        """获取上一页搜索结果"""
        if self.current_page > 1:
            self.current_page -= 1
            return self.search(keyword, self.current_page)
        return [] 