from pymobiledevice3 import usbmux
from pymobiledevice3.services.afc import AfcService
from pymobiledevice3.lockdown import create_using_usbmux
import os
import sys
import time
from datetime import datetime

class PhotoSyncError(Exception):
    """自定义同步错误类"""
    pass

def format_size(size):
    """将字节大小转换为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def progress_bar(current, total, width=50):
    """显示进度条"""
    progress = int(width * current / total)
    return f"[{'=' * progress}{' ' * (width - progress)}] {current}/{total} ({(current/total)*100:.1f}%)"

def sync_photos_from_iphone(backup_path):
    start_time = time.time()
    stats = {
        'total_files': 0,
        'copied_files': 0,
        'skipped_files': 0,
        'failed_files': 0,
        'total_size': 0
    }
    failed_files_list = []

    try:
        # 获取连接的设备
        print("正在检查设备连接...")
        devices = usbmux.list_devices()
        if not devices:
            raise PhotoSyncError("未找到已连接的iOS设备")
            
        # 连接到第一个设备
        device = devices[0]
        print(f"找到设备: {device}")
        
        print("正在建立连接...")
        # 使用新的连接方式
        lockdown = create_using_usbmux()
        if not lockdown:
            raise PhotoSyncError("无法建立与设备的连接")
            
        # 创建 AFC 服务
        try:
            afc = AfcService(lockdown=lockdown)
            if not afc:
                raise PhotoSyncError("无法启动 AFC 服务")
        except Exception as e:
            raise PhotoSyncError(f"AFC 服务启动失败: {str(e)}")
        
        # 确保备份目录存在
        os.makedirs(backup_path, exist_ok=True)
        
        print("\n开始扫描设备照片...")
        dcim_path = 'DCIM'
        try:
            all_files = []
            # 首先检查 DCIM 目录是否存在
            try:
                dir_contents = afc.listdir(dcim_path)
                if not dir_contents:
                    raise PhotoSyncError("DCIM目录为空")
            except Exception as e:
                raise PhotoSyncError(f"无法访问DCIM目录: {str(e)}")

            # 遍历所有子目录
            for folder in dir_contents:
                folder_path = f"{dcim_path}/{folder}"
                try:
                    if afc.isdir(folder_path):
                        for file in afc.listdir(folder_path):
                            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.heic')):
                                all_files.append((folder_path, file))
                except Exception as e:
                    print(f"警告: 无法访问文件夹 {folder}: {str(e)}")
                    continue

        except PhotoSyncError as e:
            raise e
        except Exception as e:
            raise PhotoSyncError(f"扫描文件时出错: {str(e)}")

        stats['total_files'] = len(all_files)
        if stats['total_files'] == 0:
            print("未找到任何照片文件")
            return

        print(f"\n找到 {stats['total_files']} 个文件")
        print("=" * 70)

        for folder_path, file in all_files:
            try:
                source_path = f"{folder_path}/{file}"
                target_path = os.path.join(backup_path, file)
                
                # 检查文件是否已存在且大小相同
                try:
                    file_info = afc.stat(source_path)
                    file_size = file_info.get('st_size', 0)
                except Exception as e:
                    print(f"\n无法获取文件信息 {file}: {str(e)}")
                    continue
                
                if os.path.exists(target_path):
                    if os.path.getsize(target_path) == file_size:
                        print(f"跳过已存在的文件: {file}")
                        stats['skipped_files'] += 1
                        continue
                
                #复制文件
                try:   
                    afc.pull(source_path, target_path)
                    stats['copied_files'] += 1
                    stats['total_size'] += file_size
                    
                    # 显示进度
                    progress = progress_bar(stats['copied_files'] + stats['skipped_files'], stats['total_files'])
                    print(f"\r{progress} - 正在处理: {file}", end='')
                    sys.stdout.flush()
                    
                except Exception as e:
                    print(f"\n复制文件失败 {file}: {str(e)}")
                    stats['failed_files'] += 1
                    failed_files_list.append((file, str(e)))
                    continue
                
            except Exception as e:
                print(f"\n处理文件失败 {file}: {str(e)}")
                stats['failed_files'] += 1
                failed_files_list.append((file, str(e)))
                continue
        
    except PhotoSyncError as e:
        print(f"\n同步错误: {str(e)}")
        return
    except Exception as e:
        print(f"\n发生未预期的错误: {str(e)}")
        return
    finally:
        # 显示最终统计信息
        elapsed_time = time.time() - start_time
        print("\n\n同步完成!")
        print("=" * 70)
        print(f"总耗时: {elapsed_time:.1f} 秒")
        print(f"总文件数: {stats['total_files']}")
        print(f"成功复制: {stats['copied_files']}")
        print(f"已跳过: {stats['skipped_files']}")
        print(f"失败: {stats['failed_files']}")
        print(f"总传输大小: {format_size(stats['total_size'])}")
        
        if failed_files_list:
            print("\n失败的文件:")
            for file, error in failed_files_list:
                print(f"- {file}: {error}")

if __name__ == "__main__":
    # 在当前目录下创建一个带时间戳的备份文件夹
    backup_dir = os.path.join(os.getcwd(), f"iphone_photos_backup")
    sync_photos_from_iphone(backup_dir)