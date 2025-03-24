#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import time
import random
import requests
from urllib.parse import quote

from src.api.base_api import MusicAPI
from src.api.netease_api import NeteaseAPI


class GDMusicAPI(MusicAPI):
    """GDMusic API - GD音乐平台API实现，默认使用网易云音乐数据源"""

    def __init__(self):
        super().__init__()
        self.name = 'GD音乐'
        
        # 仅初始化网易云API（用作备选）
        self.netease_api = NeteaseAPI()
        
        # API源映射 - 仅保留网易云音乐
        self.api_map = {
            'netease': self.netease_api
        }
        
        # 名称映射 - 仅保留网易云音乐
        self.name_map = {
            '网易云': 'netease'
        }
        
        # GD音乐API地址 - 使用新的公共API地址
        self.base_url = 'https://music-api.gdstudio.xyz'
        self.api_url = f'{self.base_url}/api.php'
        
        # 更新请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Origin': 'https://music.gdstudio.xyz',
            'Referer': 'https://music.gdstudio.xyz/',
        })
        
        # 默认使用的源
        self.current_source = 'netease'
        
        # 每页结果数
        self.limit = 30
        self.current_page = 1
    
    def set_source(self, source_name):
        """设置当前使用的音源"""
        if source_name in self.name_map:
            self.current_source = self.name_map[source_name]
            print(f"已设置音源为: {source_name} ({self.current_source})")
            # 重置页码
            self.current_page = 1
            return True
        return False
    
    def search(self, keyword, page=1, limit=30, source=None):
        """
        搜索歌曲
        :param keyword: 搜索关键词
        :param page: 页码
        :param limit: 每页数量
        :param source: 指定音源，如不指定则使用当前音源
        :return: 搜索结果列表
        """
        if not source:
            source = self.current_source
        
        self.current_page = page
        self.limit = limit
            
        print(f"正在搜索GD音乐({source}): {keyword}, 页码: {page}")
        
        try:
            # 使用GD音乐API搜索
            params = {
                'types': 'search',
                'source': source,
                'name': keyword,  # 注意这里是name而不是keywords
                'count': limit,   # 注意这里是count而不是limit
                'pages': page     # 注意这里是pages而不是page
            }
            
            response = self.session.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            
            # 打印原始响应内容进行调试
            print(f"GD音乐API响应: {response.text[:200]}...")
            
            # 尝试解析响应
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"搜索GD音乐({source})返回的数据不是有效的JSON格式: {e}")
                return self._fallback_search(keyword, page, limit, source)
            
            # 处理搜索结果
            result = []
            
            # 检查API返回的数据结构
            if isinstance(data, list):
                # 列表结构，直接遍历
                for song in data:
                    song_info = self._parse_song_data(song, source)
                    if song_info:
                        result.append(song_info)
            elif isinstance(data, dict):
                # 可能是嵌套的字典结构
                if 'data' in data:
                    songs = data.get('data', [])
                    for song in songs:
                        song_info = self._parse_song_data(song, source)
                        if song_info:
                            result.append(song_info)
                elif 'songs' in data and isinstance(data['songs'], list):
                    songs = data['songs']
                    for song in songs:
                        song_info = self._parse_song_data(song, source)
                        if song_info:
                            result.append(song_info)
                elif 'result' in data and isinstance(data['result'], dict) and 'songs' in data['result']:
                    songs = data['result']['songs']
                    for song in songs:
                        song_info = self._parse_song_data(song, source)
                        if song_info:
                            result.append(song_info)
            
            if not result:
                print(f"搜索GD音乐({source})解析结果为空，尝试使用本地API")
                return self._fallback_search(keyword, page, limit, source)
            
            print(f"搜索完成，找到 {len(result)} 首歌曲")
            return result
            
        except Exception as e:
            print(f"搜索GD音乐({source})出错: {e}")
            return self._fallback_search(keyword, page, limit, source)
    
    def _parse_song_data(self, song, source):
        """解析歌曲数据"""
        try:
            # 检查是否是有效的歌曲数据
            if not isinstance(song, dict):
                return None
            
            # 检查必要的字段
            song_id = song.get('id', '')
            song_name = song.get('name', '')
            
            if not song_id or not song_name:
                return None
            
            # 格式化歌手信息
            artists = []
            artist_data = song.get('artist', [])
            
            if isinstance(artist_data, list):
                for artist in artist_data:
                    if isinstance(artist, dict) and 'name' in artist:
                        artists.append(artist['name'])
                    elif isinstance(artist, str):
                        artists.append(artist)
            elif isinstance(artist_data, str):
                artists = [artist_data]
            elif isinstance(artist_data, dict) and 'name' in artist_data:
                artists = [artist_data['name']]
            
            # 如果还没有艺术家信息，尝试从artists字段获取
            if not artists and 'artists' in song:
                artists_data = song.get('artists', [])
                if isinstance(artists_data, list):
                    for artist in artists_data:
                        if isinstance(artist, dict) and 'name' in artist:
                            artists.append(artist['name'])
                        elif isinstance(artist, str):
                            artists.append(artist)
            
            singer = ', '.join(filter(None, artists)) if artists else '未知歌手'
            
            # 获取专辑信息
            album_name = ""
            album_data = song.get('album', {})
            if isinstance(album_data, dict) and 'name' in album_data:
                album_name = album_data['name']
            elif isinstance(album_data, str):
                album_name = album_data
            
            # 获取图片URL
            pic_url = ""
            if 'pic' in song:
                pic_url = song['pic']
            elif 'pic_id' in song:
                pic_url = song['pic_id']
            elif isinstance(album_data, dict) and 'picUrl' in album_data:
                pic_url = album_data['picUrl']
            
            # 获取时长
            duration = 0
            if 'duration' in song:
                try:
                    duration = int(song['duration'])
                except (ValueError, TypeError):
                    duration = 0
            
            # 估算文件大小 (320K大约是8-15MB)
            size = random.uniform(8, 15)
            size_text = f"{size:.1f}MB"
            
            return {
                'id': f"{source}:{song_id}",  # 添加源前缀
                'name': song_name,
                'singer': singer,
                'album': album_name,
                'duration': duration,
                'source': source,
                'platform': self.name,
                'size': size_text,
                'quality': '320K高品',  # 统一设为320K高品
                'url': '',
                'lyric': '',
                'pic': pic_url,
                'max_br': 320000,  # 设为320K
            }
        except Exception as e:
            print(f"解析歌曲数据出错: {e}")
            return None
    
    def _fallback_search(self, keyword, page, limit, source):
        """使用本地API作为备选搜索方法"""
        print(f"尝试使用本地API搜索({source}): {keyword}")
        source_api = self.api_map.get(source)
        if source_api:
            result = source_api.search(keyword, page, limit)
            if result:
                # 修改音乐来源为GD音乐，保留原始源信息
                for song in result:
                    song['platform'] = self.name
                    song['source'] = source
                    # 统一音质显示为320K高品
                    song['quality'] = '320K高品'
                return result
        return []
    
    def get_song_url(self, song_id):
        """
        获取歌曲下载链接
        :param song_id: 歌曲ID
        :return: 歌曲下载链接
        """
        try:
            # 检查是否包含源信息
            source = 'netease'  # 默认使用网易云音乐
            orig_id = song_id
            max_br = 320000
            
            # 处理ID格式
            if isinstance(song_id, str) and '|' in song_id:
                # 如果ID是"id|br"格式，需要先分离
                song_id, br_str = song_id.split('|', 1)
                try:
                    max_br = int(br_str)
                except:
                    max_br = 320000
            
            # 处理"source:id"格式
            if isinstance(song_id, str) and ':' in song_id:
                source, orig_id = song_id.split(':', 1)
            
            print(f"正在获取歌曲链接: {source}:{orig_id}")
            
            # 定义不同的比特率尝试列表，从高到低，限制最高320
            bit_rates = [320, 192, 128]
            
            # 如果用户请求了320以下的音质，那就只用请求的比特率
            if max_br < 320000 and max_br >= 128000:
                # 根据用户请求的比特率，限制可用的比特率列表
                req_br = max_br // 1000
                bit_rates = [br for br in bit_rates if br <= req_br]
                if not bit_rates:  # 如果列表为空，至少保留一个最低比特率
                    bit_rates = [128]
            
            # 打印用户请求和实际采用的比特率信息
            print(f"用户请求的最大比特率: {max_br//1000}K, 将尝试的比特率: {bit_rates}")
            
            # 尝试不同的比特率
            for br in bit_rates:
                try:
                    # 使用GD音乐新的公共API格式获取
                    params = {
                        'types': 'url',
                        'source': source,
                        'id': orig_id,
                        'br': br  # 尝试不同比特率
                    }
                    
                    # 添加请求头模拟浏览器
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/json, text/plain, */*',
                        'Referer': 'https://music.gdstudio.xyz/'
                    }
                    
                    # 添加重试机制
                    max_retries = 3
                    retry_count = 0
                    response = None
                    
                    while retry_count < max_retries:
                        try:
                            response = self.session.get(self.api_url, params=params, headers=headers, timeout=15)
                            response.raise_for_status()
                            break
                        except requests.exceptions.RequestException as e:
                            retry_count += 1
                            print(f"请求失败 (尝试 {retry_count}/{max_retries}): {e}")
                            if retry_count == max_retries:
                                raise
                            time.sleep(1)  # 等待1秒后重试
                    
                    if not response:
                        continue
                    
                    print(f"获取歌曲URL响应 (br={br}): {response.text[:200]}...")
                    
                    try:
                        data = response.json()
                    except json.JSONDecodeError as e:
                        print(f"获取GD音乐链接返回的数据不是有效的JSON格式: {e}")
                        continue
                    
                    # 提取URL
                    url = None
                    
                    # 处理新的API返回格式
                    if 'data' in data and isinstance(data['data'], dict) and 'url' in data['data']:
                        url = data['data']['url']
                    elif 'url' in data:
                        url = data['url']
                    
                    if url and isinstance(url, str) and url.startswith('http'):
                        # 如果URL包含转义字符，需要去除
                        if '\\' in url:
                            url = url.replace('\\', '')
                        
                        print(f"获取到歌曲URL (br={br}): {url[:100]}...")
                        
                        # 检查URL是否可能是有效的音乐文件
                        try:
                            head_resp = self.session.head(url, allow_redirects=True, timeout=10)
                            content_length = int(head_resp.headers.get('Content-Length', 0))
                            
                            # 检查内容类型
                            content_type = head_resp.headers.get('Content-Type', '')
                            is_audio = 'audio' in content_type or 'octet-stream' in content_type
                            
                            # 检查是否为FLAC格式，如果是FLAC格式但用户请求的是MP3，则跳过
                            is_flac = 'flac' in url.lower() or 'flac' in content_type.lower()
                            
                            # 估算比特率MP3大约是44.1kHz × 16bit × 2channels × 大约1/10压缩率 = 141.12 kbps
                            # 一分钟大约是 (141.12 / 8) × 60 = 1058.4 KB
                            # 所以10MB大约是10分钟320kbps的歌曲
                            max_expected_size = 15 * 1024 * 1024  # 15MB上限
                            
                            # 调整日志，显示MB而非KB
                            size_mb = content_length / (1024 * 1024)
                            
                            if content_length > max_expected_size:
                                print(f"警告: URL返回的文件过大 ({size_mb:.2f}MB)，可能是高质量FLAC，跳过")
                                continue
                                
                            if is_flac and max_br <= 320000:
                                print(f"警告: 检测到FLAC格式 ({size_mb:.2f}MB)，但用户请求的是MP3，跳过")
                                continue
                            
                            if content_length > 1000000 or (is_audio and content_length > 100000):
                                print(f"URL返回的文件大小合适 ({size_mb:.2f}MB), 内容类型: {content_type}")
                                print(f"获取到下载URL: {url[:100]}...")
                                print(f"文件大小: {content_length} 字节")
                                return url
                            else:
                                print(f"警告: URL返回的文件过小 ({content_length/1024:.2f}KB), 内容类型: {content_type}")
                                # 继续尝试下一个比特率
                        except Exception as e:
                            print(f"检查URL时出错: {e}")
                            # 无法检查URL，但仍可能有效，返回它
                            return url
                    
                    print(f"使用比特率 {br} 未能获取有效URL")
                
                except Exception as e:
                    print(f"获取比特率 {br} 的链接时出错: {e}")
            
            # 如果所有比特率都尝试失败，使用备选方法
            print(f"所有比特率尝试都失败，使用备选方法")
            return self._fallback_get_song_url(source, orig_id)
                
        except Exception as e:
            print(f"获取GD音乐链接出错: {e}")
            return self._fallback_get_song_url(source, orig_id)
    
    def _fallback_get_song_url(self, source, orig_id):
        """使用本地API作为备选获取歌曲URL的方法"""
        print(f"尝试使用本地API获取歌曲链接: {source}:{orig_id}")
        source_api = self.api_map.get(source)
        if source_api:
            # 确保ID不包含质量参数
            clean_id = orig_id
            if isinstance(clean_id, str) and '|' in clean_id:
                clean_id = clean_id.split('|')[0]
                
            url = source_api.get_song_url(clean_id)
            if url:
                print(f"本地API获取到URL: {url[:100]}...")
                
                # 验证URL是否返回足够大的文件
                try:
                    head_resp = self.session.head(url, allow_redirects=True, timeout=5)
                    content_length = head_resp.headers.get('Content-Length', 0)
                    if int(content_length) < 1000000:  # 小于1MB的可能不是完整音乐文件
                        print(f"警告: 本地API返回的文件过小 ({int(content_length)/1024:.2f}KB)")
                except:
                    pass  # 检查失败时继续使用URL
                    
                return url
            else:
                print(f"本地API未能获取到URL")
        else:
            print(f"未找到对应的本地API: {source}")
        
        # 如果是网易云音乐，尝试一个额外的备选办法
        if source == 'netease':
            try:
                # 尝试直接使用API获取
                api_url = f"https://autumnfish.cn/song/url?id={orig_id}"
                resp = self.session.get(api_url, timeout=10)
                data = resp.json()
                
                if data.get('code') == 200 and data.get('data'):
                    url = data['data'][0].get('url')
                    if url:
                        print(f"备选API获取到URL: {url[:100]}...")
                        return url
            except Exception as e:
                print(f"备选API获取失败: {e}")
                
        return None
    
    def download(self, song_id, save_path):
        """
        下载歌曲
        :param song_id: 歌曲ID
        :param save_path: 保存路径
        :return: 保存路径
        """
        try:
            # 检查是否包含源信息
            source = 'netease'  # 默认使用网易云音乐
            orig_id = song_id
            
            if ':' in str(song_id):
                source, orig_id = song_id.split(':', 1)
                
            # 获取下载链接 - 先尝试不同的比特率
            url = None
            bit_rates = [320, 192, 128]  # 去除999，只使用MP3比特率
            
            for br in bit_rates:
                try:
                    # 使用GD音乐API获取特定比特率的URL
                    params = {
                        'types': 'url',
                        'source': source,
                        'id': orig_id,
                        'br': br
                    }
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'application/json, text/plain, */*',
                        'Referer': 'https://music.gdstudio.xyz/'
                    }
                    
                    response = self.session.get(self.api_url, params=params, headers=headers, timeout=15)
                    data = response.json()
                    
                    if 'data' in data and isinstance(data['data'], dict) and 'url' in data['data']:
                        url = data['data']['url']
                    elif 'url' in data:
                        url = data['url']
                    
                    if url and isinstance(url, str) and url.startswith('http'):
                        # 检查URL是否返回足够大的文件
                        head_resp = self.session.head(url, allow_redirects=True, timeout=10)
                        content_length = int(head_resp.headers.get('Content-Length', 0))
                        
                        if content_length > 1000000:  # 大于1MB的文件可能是有效的音乐
                            print(f"找到有效下载链接 (br={br}): {url[:100]}...")
                            break
                        else:
                            print(f"比特率 {br} 的链接文件太小 ({content_length/1024:.2f}KB)，尝试较低比特率")
                            url = None  # 重置URL继续尝试
                
                except Exception as e:
                    print(f"获取比特率 {br} 的下载链接时出错: {e}")
            
            # 如果所有比特率都失败，尝试原始方法
            if not url:
                url = self.get_song_url(song_id)
            
            if not url:
                print(f"无法获取歌曲 {orig_id} 的下载链接")
                return None
            
            print(f"开始下载歌曲: {url[:100]}...")
            
            # 创建目录
            if not os.path.exists(os.path.dirname(save_path)):
                os.makedirs(os.path.dirname(save_path))
                
            # 下载文件
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': '*/*',
                    'Referer': 'https://music.gdstudio.xyz/'
                }
                
                # 添加重试机制
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        with self.session.get(url, headers=headers, stream=True, timeout=60) as response:
                            response.raise_for_status()
                            total_size = int(response.headers.get('content-length', 0))
                            print(f"文件大小: {total_size} 字节")
                            
                            if total_size < 1000000 and total_size > 0:  # 小于1MB且大于0的可能不是完整音乐文件
                                print(f"警告: 下载的文件可能不完整，大小仅有 {total_size/1024:.2f}KB")
                                if retry < max_retries - 1:
                                    print(f"尝试重新下载 (尝试 {retry+1}/{max_retries})")
                                    continue
                            
                            with open(save_path, 'wb') as f:
                                downloaded_size = 0
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                                        downloaded_size += len(chunk)
                                
                                print(f"下载完成，文件大小: {downloaded_size} 字节")
                                
                            # 如果下载成功，跳出重试循环
                            break
                            
                    except Exception as e:
                        print(f"下载尝试 {retry+1}/{max_retries} 失败: {e}")
                        if retry == max_retries - 1:  # 如果是最后一次尝试
                            raise
                        time.sleep(1)  # 等待1秒后重试
                        
            except Exception as e:
                print(f"下载过程出错: {e}")
                # 如果当前URL下载失败，尝试本地API下载
                print(f"尝试使用本地API下载: {source}:{orig_id}")
                source_api = self.api_map.get(source)
                if source_api:
                    return source_api.download(orig_id, save_path)
                return None
            
            # 检查文件是否有效
            if os.path.exists(save_path):
                file_size = os.path.getsize(save_path)
                if file_size > 1000000:  # 大于1MB的文件可能是有效的音乐
                    print(f"下载完成: {save_path}")
                    return save_path
                elif file_size > 10 * 1024:  # 大于10KB但小于1MB的文件可能是部分有效
                    print(f"警告: 下载的文件可能不完整，大小仅有 {file_size/1024:.2f}KB")
                    # 尝试使用本地API下载
                    os.remove(save_path)  # 删除不完整的文件
                else:
                    print(f"下载文件不完整或无效")
                    if os.path.exists(save_path):
                        os.remove(save_path)
            
            # 如果GD音乐API下载失败，尝试使用本地API下载
            print(f"尝试使用本地API下载: {source}:{orig_id}")
            source_api = self.api_map.get(source)
            if source_api:
                return source_api.download(orig_id, save_path)
            
            return None
                
        except Exception as e:
            print(f"下载GD音乐出错: {e}")
            # 使用本地对应的API
            clean_id = song_id
            source = 'netease'
            if ':' in str(song_id):
                source, clean_id = song_id.split(':', 1)
            
            source_api = self.api_map.get(source)
            if source_api:
                print(f"尝试使用本地API下载: {source}:{clean_id}")
                return source_api.download(clean_id, save_path)
            return None
    
    def get_next_page(self, keyword):
        """获取下一页搜索结果"""
        self.current_page += 1
        return self.search(keyword, self.current_page, self.limit, self.current_source)
    
    def get_previous_page(self, keyword):
        """获取上一页搜索结果"""
        if self.current_page > 1:
            self.current_page -= 1
            return self.search(keyword, self.current_page, self.limit, self.current_source)
        return [] 