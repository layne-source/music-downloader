from PIL import Image
import os
import sys

def create_icon_from_image(input_image_path, output_ico_path='icons/icon.ico'):
    """将图片转换为ICO格式的图标文件"""
    try:
        # 确保图标目录存在
        os.makedirs(os.path.dirname(output_ico_path), exist_ok=True)
        
        # 打开原始图片
        img = Image.open(input_image_path)
        
        # 准备多种尺寸的图标(Windows推荐的尺寸)
        sizes = [(256, 256)]
        
        # 保存为ICO格式，包含多种尺寸
        img.save(output_ico_path, format='ICO', sizes=sizes)
        
        print(f"图标创建成功: {output_ico_path}")
        return True
    except Exception as e:
        print(f"创建图标时出错: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python create_icon.py <图片文件路径> [输出ICO文件路径]")
        sys.exit(1)
        
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'icons/icon.ico'
    
    if create_icon_from_image(input_path, output_path):
        print("图标文件已成功创建！")
    else:
        print("图标创建失败!") 