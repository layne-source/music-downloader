#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import platform
import subprocess
import importlib.util
import time
from pathlib import Path
import traceback
import tempfile

# 全局变量
fake_ua_static_data = None  # 用于存储fake_useragent静态数据目录路径

def check_pyinstaller():
    """检查PyInstaller是否已安装"""
    if importlib.util.find_spec("PyInstaller") is None:
        print("正在安装PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=5.13.0"])
            print("PyInstaller安装成功！")
        except Exception as e:
            print(f"安装PyInstaller失败: {e}")
            print("请手动安装: pip install pyinstaller>=5.13.0")
            return False
    return True

def prepare_icon():
    """准备程序图标"""
    icons_dir = "icons"
    icon_path = os.path.join(icons_dir, "icon.ico")
    
    # 创建图标目录
    if not os.path.exists(icons_dir):
        os.makedirs(icons_dir)
    
    # 如果图标不存在，创建一个简单的图标
    if not os.path.exists(icon_path):
        print("图标文件不存在，创建简单图标...")
        try:
            # 最小的有效.ico文件
            with open(icon_path, 'wb') as f:
                f.write(bytes([0, 0, 1, 0, 1, 0, 16, 16, 0, 0, 1, 0, 4, 0, 40, 0, 0, 0, 22, 0, 0, 0, 40, 0, 0, 0, 16, 0, 0, 0, 32, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]))
            print(f"创建图标文件成功: {icon_path}")
        except Exception as e:
            print(f"创建图标文件失败: {e}")
            print("将使用PyInstaller默认图标")
            return None
    
    return icon_path

def check_dependencies():
    """检查依赖项"""
    print("\n检查依赖项...")
    
    required_packages = ["PyQt5", "requests", "lxml", "bs4", "fake_useragent", "pycryptodome"]
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == "pycryptodome":
                # pycryptodome导入为Crypto
                __import__("Crypto")
            else:
                __import__(package)
            print(f"√ {package} 已安装")
        except ImportError:
            print(f"× {package} 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print("\n请安装以下缺失的依赖项:")
        for package in missing_packages:
            print(f"pip install {package}")
        print("\n安装完成后重新运行此脚本")
        return False
    
    print("所有依赖项检查通过")
    return True

def collect_pyqt_files():
    """收集PyQt5所需的文件和插件"""
    print("正在收集PyQt5组件...")
    import os
    import shutil
    import sys
    from pathlib import Path
    
    try:
        import PyQt5
        pyqt_path = Path(PyQt5.__file__).parent
        print(f"PyQt5路径: {pyqt_path}")
        
        # 创建临时目录用于收集文件
        temp_dir = Path("temp_pyqt")
        if not temp_dir.exists():
            temp_dir.mkdir(parents=True)
            
        # 收集关键组件
        qt5_dir = pyqt_path / "Qt5"
        if qt5_dir.exists():
            # 收集平台插件
            platform_plugins = qt5_dir / "plugins" / "platforms"
            if platform_plugins.exists():
                print(f"找到平台插件: {platform_plugins}")
                for plugin in platform_plugins.glob("*.dll"):
                    print(f"- 收集插件: {plugin.name}")
                    target_dir = temp_dir / "PyQt5" / "Qt5" / "plugins" / "platforms"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(plugin, target_dir)
            else:
                print("警告: 未找到平台插件目录")
                
            # 收集样式插件
            styles_plugins = qt5_dir / "plugins" / "styles"
            if styles_plugins.exists():
                print(f"找到样式插件: {styles_plugins}")
                for plugin in styles_plugins.glob("*.dll"):
                    print(f"- 收集样式: {plugin.name}")
                    target_dir = temp_dir / "PyQt5" / "Qt5" / "plugins" / "styles"
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(plugin, target_dir)
            
            # 收集核心DLL
            bin_dir = qt5_dir / "bin"
            if bin_dir.exists():
                print(f"找到Qt5 bin目录: {bin_dir}")
                core_dlls = ["Qt5Core.dll", "Qt5Gui.dll", "Qt5Widgets.dll", "Qt5Network.dll"]
                for dll in core_dlls:
                    dll_path = bin_dir / dll
                    if dll_path.exists():
                        print(f"- 收集DLL: {dll}")
                        target_dir = temp_dir / "PyQt5" / "Qt5" / "bin"
                        target_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(dll_path, target_dir)
                    else:
                        print(f"警告: 未找到 {dll}")
            else:
                print("警告: 未找到Qt5 bin目录")
        
        # 创建qt.conf文件
        qt_conf = temp_dir / "qt.conf"
        with open(qt_conf, "w") as f:
            f.write("[Paths]\nPlugins = PyQt5/Qt5/plugins\nBinaries = PyQt5/Qt5/bin")
        print("已创建qt.conf文件")
        
        return str(temp_dir)
    except Exception as e:
        print(f"收集PyQt5文件时出错: {e}")
        return None

def prepare_fake_useragent_data():
    """准备fake_useragent数据目录"""
    print("\n准备fake_useragent数据目录...")
    
    try:
        from fake_useragent import UserAgent
        ua = UserAgent()
        print(f"fake_useragent初始化成功，示例UA: {ua.chrome[:30]}...")
        
        # 获取fake_useragent数据文件位置
        import fake_useragent
        fake_ua_dir = os.path.dirname(fake_useragent.__file__)
        fake_ua_data = os.path.join(fake_ua_dir, "data", "browsers.json")
        
        global fake_ua_static_data
        if os.path.exists(fake_ua_data):
            fake_ua_static_data = os.path.dirname(fake_ua_data)
            print(f"找到fake_useragent数据文件: {fake_ua_static_data}")
        else:
            # 如果未找到，创建静态数据
            print("未找到fake_useragent数据文件，将使用在线模式")
            fake_ua_static_data = None
        
        return True
    except Exception as e:
        print(f"准备fake_useragent数据时出错: {e}")
        fake_ua_static_data = None
        return False

def create_static_browsers_json_content(file_path):
    """创建一个静态的browsers.json文件内容"""
    print(f"创建静态browsers.json: {file_path}")
    
    # 一个简单的browsers.json内容
    browsers_data = """{
    "browsers": {
        "chrome": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ],
        "firefox": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/115.0"
        ],
        "edge": [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
        ],
        "safari": [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
        ]
    },
    "randomize": {
        "chrome": 90,
        "firefox": 5,
        "edge": 3,
        "safari": 2
    }
}"""
    
    # 写入静态文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(browsers_data)
    
    print(f"已创建静态browsers.json文件: {file_path}")

def build_executable():
    """构建可执行文件"""
    start_time = time.time()
    
    print("=" * 80)
    print(f"开始打包音乐下载器 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 使用临时目录存放日志
    log_dir = tempfile.gettempdir()
    log_file = os.path.join(log_dir, f"build_log_{int(time.time())}.txt")
    print(f"构建日志将临时保存到: {os.path.abspath(log_file)}")
    
    # 检查依赖项
    check_dependencies()
    
    # 预先准备fake_useragent数据目录
    prepare_fake_useragent_data()
    
    print("\n开始配置PyInstaller命令...")
    
    # 准备命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--onedir",  # 使用onedir模式
        "--noconsole",  # 不显示控制台
        "--name", "音乐下载器",
        "--noconfirm"
    ]
    
    # 添加图标
    icon_path = os.path.join("src", "icons", "icon.ico")
    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
    
    # 添加关键的隐藏导入
    essential_imports = [
        "PyQt5.sip", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets",
        "requests", "bs4", "lxml", "Crypto"
    ]
    
    for module in essential_imports:
        cmd.extend(["--hidden-import", module])
    
    # 添加fake_useragent数据文件
    try:
        if fake_ua_static_data and os.path.exists(fake_ua_static_data):
            cmd.extend(["--add-data", f"{fake_ua_static_data}{os.pathsep}fake_useragent{os.sep}data"])
    except Exception as e:
        print(f"添加fake_useragent数据失败: {e}")
    
    # 添加PyQt5数据文件
    try:
        import PyQt5
        pyqt_dir = os.path.dirname(PyQt5.__file__)
        
        # 添加platforms插件
        platforms_src = os.path.join(pyqt_dir, "Qt5", "plugins", "platforms")
        platforms_dst = os.path.join("PyQt5", "Qt5", "plugins", "platforms")
        cmd.extend(["--add-data", f"{platforms_src}{os.pathsep}{platforms_dst}"])
        
        # 添加Qt5 bin目录
        qt5bin_src = os.path.join(pyqt_dir, "Qt5", "bin")
        qt5bin_dst = os.path.join("PyQt5", "Qt5", "bin")
        cmd.extend(["--add-data", f"{qt5bin_src}{os.pathsep}{qt5bin_dst}"])
    except Exception as e:
        print(f"添加PyQt5文件失败: {e}")
    
    # 创建PyQt5钩子
    hook_content = """# PyQt5钩子
import os
import sys

# 设置关键环境变量
if hasattr(sys, 'frozen'):
    # 设置PyQt5插件路径
    os.environ['QT_PLUGIN_PATH'] = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins', 'platforms')
    
    # 强制使用UTF-8编码
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    # 确保当前目录也在PATH中
    os.environ['PATH'] = os.path.dirname(sys.executable) + os.pathsep + os.environ.get('PATH', '')
"""
    
    hook_file = os.path.join(os.getcwd(), "pyqt5_hook.py")
    with open(hook_file, "w", encoding="utf-8") as f:
        f.write(hook_content)
    
    cmd.extend(["--runtime-hook", hook_file])
    
    # 添加主程序
    cmd.append("main.py")
    
    print("\n完整PyInstaller命令:")
    print(' '.join(cmd))
    
    print("\n开始执行构建...\n")
    
    try:
        # 执行构建命令并记录日志
        with open(log_file, 'w') as f:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                   universal_newlines=True)
            
            # 实时输出日志
            for line in process.stdout:
                print(line, end='')
                f.write(line)
                f.flush()
                
            process.wait()
        
        # 检查构建结果
        exe_dir = os.path.join("dist", "音乐下载器")
        executable_path = os.path.join(exe_dir, "音乐下载器.exe") if platform.system() == "Windows" else os.path.join(exe_dir, "音乐下载器")
        
        if process.returncode == 0 and os.path.exists(executable_path):
            end_time = time.time()
            total_time = end_time - start_time
            print(f"\n构建成功！耗时: {total_time:.2f}秒")
            print(f"可执行文件已生成: {os.path.abspath(executable_path)}")
            
            # 创建简单的README
            create_simple_readme(exe_dir)
            
            # 创建ZIP分发包
            create_distribution_zip(exe_dir)
            
            # 清理临时文件
            try:
                if os.path.exists(log_file):
                    os.remove(log_file)
                
                if os.path.exists(hook_file):
                    os.remove(hook_file)
                
                print("临时文件清理完成")
            except Exception as e:
                print(f"清理临时文件时出错: {e}")
            
            return executable_path
        else:
            print(f"\n构建失败，返回代码: {process.returncode}")
            print(f"构建日志已保存到: {os.path.abspath(log_file)}")
            return None
    except Exception as e:
        print(f"\n构建过程出错: {e}")
        traceback.print_exc()
        print(f"构建日志已保存到: {os.path.abspath(log_file)}")
        return None

def create_simple_readme(exe_dir):
    """创建简单的README文件"""
    print("\n创建README文件...")
    
    readme_path = os.path.join(exe_dir, "README.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(r"""音乐下载器使用说明
==============

欢迎使用音乐下载器！这是一个简单易用的音乐下载工具。

【使用方法】
1. 双击"音乐下载器.exe"启动程序
2. 在搜索框中输入歌曲名称或歌手
3. 点击搜索按钮
4. 在结果列表中选择要下载的歌曲
5. 点击下载按钮

【注意事项】
- 首次运行可能需要较长时间加载
- 程序需要网络连接才能正常工作
- 下载的音乐默认保存在程序所在目录的"下载"文件夹中

【常见问题】
- 如果程序无法启动，请确保您的系统安装了Visual C++ Redistributable 2015-2019
- 如果搜索没有结果，请检查网络连接或尝试更换搜索关键词
- 如果下载失败，可能是下载源暂时不可用，请稍后再试

【技术支持】
如有任何问题，请联系开发者获取支持。
""")
    
    print(f"已创建README文件: {readme_path}")
    return readme_path

def create_distribution_zip(exe_dir):
    """创建分发ZIP包"""
    print("\n创建分发ZIP包...")
    
    try:
        import zipfile
        
        # 创建ZIP文件名
        zip_filename = os.path.join("dist", "音乐下载器.zip")
        
        # 如果已存在则删除
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        
        # 创建ZIP文件
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(exe_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(
                        file_path,
                        os.path.relpath(file_path, os.path.dirname(exe_dir))
                    )
        
        print(f"分发ZIP包已创建: {os.path.abspath(zip_filename)}")
        return True
    except Exception as e:
        print(f"创建分发ZIP包时出错: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("音乐下载器打包工具")
    print("=" * 60)
    
    start_time = time.time()
    
    # 检查Python版本
    if sys.version_info < (3, 6):
        print("错误: 需要Python 3.6或更高版本")
        return
    
    # 检查当前目录
    if not os.path.exists("main.py") or not os.path.isdir("src"):
        print("错误: 请在项目根目录下运行此脚本")
        return
    
    # 构建标准版可执行文件
    executable_path = build_executable()
    
    if executable_path:
        elapsed_time = time.time() - start_time
        print(f"\n打包完成！耗时: {elapsed_time:.2f}秒")
        print("您可以分发dist目录下的可执行文件。")
        print("注意事项:")
        print("- 首次运行可能需要较长时间加载")
        print("- 程序需要网络连接才能正常工作")
    else:
        print("\n打包未完成。请检查以上错误信息。")
    
    print("\n按Enter键退出...")
    input()

if __name__ == "__main__":
    main() 