"""
动作执行模块
执行解析后的命令，控制 PC
"""

import os
import sys
import subprocess
import pyautogui
import psutil
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from datetime import datetime
from typing import Optional, Tuple
from .command_parser import ParsedCommand


class ActionExecutor:
    def __init__(self, volume_step: int = 10):
        """
        初始化动作执行器

        Args:
            volume_step: 每次音量调整步长（百分比）
        """
        self.volume_step = volume_step
        self._volume_interface: Optional[IAudioEndpointVolume] = None
        self._init_volume()
        print("[ActionExecutor] 初始化完成")

    def _init_volume(self) -> None:
        """初始化音量控制接口"""
        try:
            devices = AudioUtilities.GetSpeakers()
            self._volume_interface = devices.EndpointVolume
            print("[ActionExecutor] 音量控制初始化成功")
        except Exception as e:
            print(f"[ActionExecutor] 音量控制初始化失败: {e}")

    def execute(self, command: ParsedCommand) -> Tuple[bool, str]:
        """
        执行命令

        Args:
            command: 解析后的命令

        Returns:
            (执行成功与否, 结果消息/反馈文本)
        """
        action = command.action
        params = command.params
        response = command.response

        try:
            print(f"[ActionExecutor] 执行动作: {action}, 参数: {params}")

            if action == "volume_control":
                direction = params.get("direction", "up")
                step = params.get("step", self.volume_step)
                return self._volume_control(direction, step), response

            elif action == "toggle_mute":
                success, status = self._toggle_mute()
                response = response.replace("{{status}}", "已静音" if status else "已取消静音")
                return success, response

            elif action == "screenshot":
                return self._screenshot(), response

            elif action == "lock_screen":
                return self._lock_screen(), response

            elif action == "shutdown":
                confirm = params.get("confirm", False)
                if not confirm:
                    return True, response  # 返回确认提示
                return self._shutdown(), response

            elif action == "reboot":
                confirm = params.get("confirm", False)
                if not confirm:
                    return True, response  # 返回确认提示
                return self._reboot(), response

            elif action == "open_app":
                app = params.get("app", "")
                return self._open_app(app), response

            elif action == "close_window":
                return self._close_window(), response

            elif action == "switch_window":
                return self._switch_window(), response

            elif action == "play_pause":
                return self._play_pause(), response

            elif action == "next_track":
                return self._next_track(), response

            elif action == "previous_track":
                return self._previous_track(), response

            else:
                print(f"[ActionExecutor] 未知动作: {action}")
                return False, f"未知动作: {action}"

        except Exception as e:
            print(f"[ActionExecutor] 执行出错: {e}")
            return False, str(e)

    def _volume_control(self, direction: str, step: int) -> bool:
        """音量控制"""
        if self._volume_interface is None:
            return False

        current_volume = self._volume_interface.GetMasterVolumeLevelScalar()
        step_scalar = step / 100.0

        if direction == "up":
            new_volume = min(1.0, current_volume + step_scalar)
        else:
            new_volume = max(0.0, current_volume - step_scalar)

        self._volume_interface.SetMasterVolumeLevelScalar(new_volume, None)
        print(f"[ActionExecutor] 音量调整: {int(current_volume * 100)}% -> {int(new_volume * 100)}%")
        return True

    def _toggle_mute(self) -> Tuple[bool, bool]:
        """切换静音，返回 (成功与否, 当前是否静音)"""
        if self._volume_interface is None:
            return False, False

        current_mute = self._volume_interface.GetMute()
        new_mute = not current_mute
        self._volume_interface.SetMute(new_mute, None)
        print(f"[ActionExecutor] 静音切换: {current_mute} -> {new_mute}")
        return True, new_mute

    def _screenshot(self) -> bool:
        """全屏截图保存到桌面"""
        try:
            screenshot = pyautogui.screenshot()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filepath = os.path.join(desktop, f"screenshot_{timestamp}.png")
            screenshot.save(filepath)
            print(f"[ActionExecutor] 截图已保存: {filepath}")
            return True
        except Exception as e:
            print(f"[ActionExecutor] 截图失败: {e}")
            return False

    def _lock_screen(self) -> bool:
        """锁定屏幕 (Windows)"""
        try:
            if sys.platform == "win32":
                # Windows 锁定屏幕
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
                print("[ActionExecutor] 已锁定屏幕")
                return True
            # 其他平台可后续扩展
            return False
        except Exception as e:
            print(f"[ActionExecutor] 锁定屏幕失败: {e}")
            return False

    def _shutdown(self) -> bool:
        """关机"""
        try:
            if sys.platform == "win32":
                subprocess.run(["shutdown", "/s", "/t", "5"], check=True)
                print("[ActionExecutor] 计划关机")
                return True
            return False
        except Exception as e:
            print(f"[ActionExecutor] 关机失败: {e}")
            return False

    def _reboot(self) -> bool:
        """重启"""
        try:
            if sys.platform == "win32":
                subprocess.run(["shutdown", "/r", "/t", "5"], check=True)
                print("[ActionExecutor] 计划重启")
                return True
            return False
        except Exception as e:
            print(f"[ActionExecutor] 重启失败: {e}")
            return False

    def _open_app(self, app: str) -> bool:
        """打开应用"""
        app_map = {
            "chrome": "chrome",
            "edge": "msedge",
            "notepad": "notepad.exe",
            "notepad++": "notepad++",
        }

        cmd = app_map.get(app, app)

        try:
            if sys.platform == "win32":
                os.startfile(cmd)
            else:
                subprocess.Popen([cmd])
            print(f"[ActionExecutor] 已启动应用: {cmd}")
            return True
        except Exception as e:
            print(f"[ActionExecutor] 启动应用失败: {e}")
            return False

    def _close_window(self) -> bool:
        """关闭当前窗口 (Alt+F4)"""
        try:
            pyautogui.hotkey('alt', 'f4')
            print("[ActionExecutor] 已发送 Alt+F4")
            return True
        except Exception as e:
            print(f"[ActionExecutor] 关闭窗口失败: {e}")
            return False

    def _switch_window(self) -> bool:
        """切换窗口 (Alt+Tab)"""
        try:
            pyautogui.hotkey('alt', 'tab')
            print("[ActionExecutor] 已发送 Alt+Tab")
            return True
        except Exception as e:
            print(f"[ActionExecutor] 切换窗口失败: {e}")
            return False

    def _play_pause(self) -> bool:
        """播放/暂停媒体键"""
        try:
            pyautogui.press('playpause')
            print("[ActionExecutor] 已发送 Play/Pause 键")
            return True
        except Exception as e:
            print(f"[ActionExecutor] 播放/暂停失败: {e}")
            return False

    def _next_track(self) -> bool:
        """下一首"""
        try:
            pyautogui.press('nexttrack')
            print("[ActionExecutor] 已发送 Next Track 键")
            return True
        except Exception as e:
            print(f"[ActionExecutor] 下一首失败: {e}")
            return False

    def _previous_track(self) -> bool:
        """上一首"""
        try:
            pyautogui.press('prevtrack')
            print("[ActionExecutor] 已发送 Previous Track 键")
            return True
        except Exception as e:
            print(f"[ActionExecutor] 上一首失败: {e}")
            return False
