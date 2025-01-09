# filepath: /Users/xumx/Documents/MyWork/MediaSync/main.py
import os
from ppadb.client import Client as AdbClient
from tqdm import tqdm

# 初始化ADB
adb = AdbClient(host="127.0.0.1", port=5037)

# 连接设备
devices = adb.devices()
if len(devices) == 0:
    print("没有连接的设备")
    exit(1)
device = devices[0]

# 获取设备上的照片路径
photos_path = '/sdcard/DCIM/Camera/'
photos_path1 = '/sdcard/Pictures/'
# 本地保存路径
local_path = '/Volumes/EricData/MobileData/Huawei/Camera/'
local_path1 = '/Volumes/EricData/MobileData/Huawei/Pictures/'

def sync_photos(remote_path, local_path):
    # 获取远程路径下的文件和文件夹列表
    items = device.shell(f'ls {remote_path}').split()
    
    for item in tqdm(items, desc=f"同步目录 {remote_path}"):
        remote_item_path = os.path.join(remote_path, item)
        local_item_path = os.path.join(local_path, item)
        
        # 检查是否为目录
        if device.shell(f'if [ -d {remote_item_path} ]; then echo "dir"; fi').strip() == "dir":
            # 创建本地目录
            if not os.path.exists(local_item_path):
                os.makedirs(local_item_path)
            # 递归同步子目录
            sync_photos(remote_item_path, local_item_path)
        else:
            # 检查本地文件是否存在且大小一致
            if os.path.exists(local_item_path):
                remote_size = int(device.shell(f'stat -c%s {remote_item_path}').strip())
                local_size = os.path.getsize(local_item_path)
                if remote_size == local_size:
                    tqdm.write(f"文件已存在且大小一致，跳过: {local_item_path}")
                    continue
            
            # 同步文件
            device.pull(remote_item_path, local_item_path)
            tqdm.write(f"同步文件: {local_item_path}")

# 同步照片
# sync_photos(photos_path, local_path)
sync_photos(photos_path1, local_path1)

print("照片同步完成")