"""
系统托盘模块
提供系统托盘图标和菜单，支持后台运行、开机自启配置
"""

import os
import sys
import winreg
from PIL import Image, ImageDraw
import pystray
from typing import Callable, Optional


class SystemTray:
    """系统托盘管理"""

    def __init__(self, app, on_exit: Callable[[], None], on_reload: Callable[[], None]):
        """
        初始化系统托盘

        Args:
            app: 语音控制应用实例
            on_exit: 退出回调
            on_reload: 重载命令配置回调
        """
        self.app = app
        self.on_exit = on_exit
        self.on_reload = on_reload
        self._icon: Optional[pystray.Icon] = None
        self._is_running = False

        # 创建默认图标
        self._default_icon = self._create_default_icon()

    def _create_default_icon(self, size: int = 64) -> Image.Image:
        """创建一个简单的麦克风图标"""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 绘制一个深蓝色圆形背景
        padding = 4
        draw.ellipse([padding, padding, size - padding, size - padding],
                     fill=(41, 128, 185))

        # 绘制麦克风简化图形
        mic_w = size // 5
        mic_h = size // 3
        x = (size - mic_w) // 2
        y = size // 4
        draw.rectangle([x, y, x + mic_w, y + mic_h], fill=(255, 255, 255))

        # 底座
        base_w = size // 3
        base_h = size // 10
        x_base = (size - base_w) // 2
        y_base = y + mic_h + size // 20
        draw.rectangle([x_base, y_base, x_base + base_w, y_base + base_h],
                       fill=(255, 255, 255))

        return img

    def _get_menu(self) -> pystray.Menu:
        """创建托盘菜单"""
        return pystray.Menu(
            pystray.MenuItem("语音控制", lambda: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("重载命令配置", self._on_reload_click),
            pystray.MenuItem("设置开机自启", self._on_auto_start_click),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_exit_click)
        )

    def _on_reload_click(self) -> None:
        """重载命令点击"""
        print("[SystemTray] 重载命令配置")
        self.on_reload()

    def _on_exit_click(self) -> None:
        """退出点击"""
        print("[SystemTray] 用户请求退出")
        self.stop()
        self.on_exit()

    def _on_auto_start_click(self) -> None:
        """切换开机自启点击"""
        enabled = self.is_auto_start_enabled()
        if enabled:
            self.disable_auto_start()
        else:
            self.enable_auto_start()

    def enable_auto_start(self) -> bool:
        """启用开机自启 (Windows)"""
        if sys.platform != "win32":
            print("[SystemTray] 开机自启仅支持 Windows")
            return False

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )

            # 获取当前 exe 或脚本路径
            if getattr(sys, 'frozen', False):
                # 打包为 exe
                app_path = sys.executable
            else:
                # 源码运行，使用 pythonw 启动
                script_path = os.path.abspath(sys.argv[0])
                app_path = f'"{sys.executable}" "{script_path}" --tray'

            winreg.SetValueEx(key, "VoiceControl", 0, winreg.REG_SZ, app_path)
            winreg.CloseKey(key)
            print("[SystemTray] 已启用开机自启")
            return True
        except Exception as e:
            print(f"[SystemTray] 启用开机自启失败: {e}")
            return False

    def disable_auto_start(self) -> bool:
        """禁用开机自启"""
        if sys.platform != "win32":
            return False

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, "VoiceControl")
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            print("[SystemTray] 已禁用开机自启")
            return True
        except Exception as e:
            print(f"[SystemTray] 禁用开机自启失败: {e}")
            return False

    def is_auto_start_enabled(self) -> bool:
        """检查是否已启用开机自启"""
        if sys.platform != "win32":
            return False

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, "VoiceControl")
                exists = value is not None and value != ""
            except FileNotFoundError:
                exists = False
            winreg.CloseKey(key)
            return exists
        except Exception:
            return False

    def start(self) -> None:
        """启动系统托盘"""
        if self._is_running:
            return

        self._icon = pystray.Icon(
            "VoiceControl",
            self._default_icon,
            "语音控制",
            self._get_menu()
        )

        print("[SystemTray] 系统托盘已启动")
        self._is_running = True
        self._icon.run()

    def stop(self) -> None:
        """停止系统托盘"""
        if self._icon is not None and self._is_running:
            self._icon.stop()
            self._is_running = False
            print("[SystemTray] 系统托盘已停止")
