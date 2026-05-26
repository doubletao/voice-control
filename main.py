#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地语音控制 PC
主入口 - 主控循环 + 状态机

状态机:
[IDLE] ──唤醒词──▶ [LISTENING] ──静音/超时──▶ [RECOGNIZING]
  ▲                                                    │
  └──────────────────────────────────────────[EXECUTING]
                                            │
                                       [SPEAKING] ──完成──▶ [IDLE]

Usage:
  python main.py          # 控制台模式运行
  python main.py --tray    # 系统托盘模式后台运行
"""

import yaml
import signal
import sys
import threading
from typing import Optional

import numpy as np

from modules.audio_capture import AudioCapture
from modules.wake_word import WakeWordDetector
from modules.recognizer import SpeechRecognizer
from modules.command_parser import CommandParser, ParsedCommand
from modules.action_executor import ActionExecutor
from modules.tts import TTS
from modules.tray import SystemTray


class VoiceControlApp:
    """语音控制主应用"""

    # 状态定义
    STATE_IDLE = "IDLE"
    STATE_LISTENING = "LISTENING"
    STATE_RECOGNIZING = "RECOGNIZING"
    STATE_EXECUTING = "EXECUTING"
    STATE_SPEAKING = "SPEAKING"

    def __init__(self, config_path: str = "config.yaml", commands_path: str = "commands.yaml"):
        # 加载配置
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # 当前状态（需通过 _state_lock 保护）
        self._state_lock = threading.Lock()
        self.state = self.STATE_IDLE

        # 初始化模块
        self._init_modules(commands_path)

        # 控制标志
        self.running = True
        self._stop_event = threading.Event()

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print("[VoiceControlApp] 应用初始化完成")

    def _init_modules(self, commands_path: str) -> None:
        """初始化所有模块"""
        # 音频配置
        audio_cfg = self.config.get('audio', {})
        sample_rate = audio_cfg.get('sample_rate', 16000)
        frame_length = audio_cfg.get('frame_length', 512)
        device_index = audio_cfg.get('device_index', -1)

        # 录音配置
        recording_cfg = self.config.get('recording', {})
        silence_threshold = recording_cfg.get('silence_threshold', 500)
        silence_duration = recording_cfg.get('silence_duration', 1.5)
        max_duration = recording_cfg.get('max_duration', 8.0)

        # 模型路径
        model_paths = self.config.get('model_paths', {})

        # 唤醒词检测
        wake_word_cfg = self.config.get('wake_word', {})
        self.detector = WakeWordDetector(
            model_name=wake_word_cfg.get('model_name', 'default'),
            threshold=wake_word_cfg.get('threshold', 0.5)
        )

        # 语音识别
        self.recognizer = SpeechRecognizer(
            model_path=model_paths.get('vosk', ''),
            sample_rate=sample_rate,
            frame_length=frame_length,
            silence_threshold=silence_threshold,
            silence_duration=silence_duration,
            max_duration=max_duration
        )

        # 命令解析
        self.parser = CommandParser(commands_path)

        # 动作执行
        volume_cfg = self.config.get('volume', {})
        self.executor = ActionExecutor(
            volume_step=volume_cfg.get('step', 10)
        )

        # TTS
        tts_cfg = self.config.get('tts', {})
        self.tts = TTS(
            enabled=tts_cfg.get('enabled', True)
        )

        # 音频采集
        self.capture = AudioCapture(
            sample_rate=sample_rate,
            frame_length=frame_length,
            device_index=device_index
        )

    def _signal_handler(self, signum, frame):
        """信号处理，退出"""
        print("\n[VoiceControlApp] 收到退出信号，正在停止...")
        self.running = False
        self._stop_event.set()

    def _on_wake_word_detected(self) -> None:
        """唤醒词检测到的回调"""
        with self._state_lock:
            if self.state != self.STATE_IDLE:
                return
            self.state = self.STATE_LISTENING

        print("\n[VoiceControlApp] ←↓↓↓ 唤醒词检测到，开始聆听 ↓↓↓→")
        self.recognizer.start_recording(self._on_recording_completed)
        # TTS 在独立线程播放，避免阻塞音频回调
        threading.Thread(target=self.tts.speak, args=("我在",), daemon=True).start()

    def _on_recording_completed(self, text: str) -> None:
        """录音完成回调"""
        with self._state_lock:
            self.state = self.STATE_RECOGNIZING
        print(f"[VoiceControlApp] 识别文本: '{text}'")

        # 解析命令
        parsed = self.parser.parse(text)
        with self._state_lock:
            self.state = self.STATE_EXECUTING
        self._execute_command(parsed)

    def _execute_command(self, parsed: Optional[ParsedCommand]) -> None:
        """执行命令"""
        response_text = ""

        if parsed is None:
            response_text = self.parser.get_default_response("unrecognized")
        else:
            success, response = self.executor.execute(parsed)
            if not success:
                response_text = self.parser.get_default_response("error")
                if response:
                    response_text = response
            else:
                response_text = response

        # 语音反馈（TTS 阻塞，放在线程中执行）
        with self._state_lock:
            self.state = self.STATE_SPEAKING

        if response_text:
            print(f"[VoiceControlApp] 语音反馈: {response_text}")
            # 等待 TTS 播放完成后再返回待机
            tts_done = threading.Event()
            def _speak_and_signal():
                self.tts.speak(response_text)
                tts_done.set()
            threading.Thread(target=_speak_and_signal, daemon=True).start()
            tts_done.wait()

        self._return_to_idle()

    def _return_to_idle(self) -> None:
        """返回待机状态"""
        with self._state_lock:
            self.state = self.STATE_IDLE
        print("\n[VoiceControlApp] 等待唤醒词...")

    def _audio_frame_callback(self, frame: np.ndarray) -> None:
        """音频帧回调"""
        if not self.running:
            return

        with self._state_lock:
            current_state = self.state

        if current_state == self.STATE_IDLE:
            self.detector.process_frame(frame)
        elif current_state == self.STATE_LISTENING:
            self.recognizer.process_frame(frame)

    def start(self) -> None:
        """启动应用"""
        print("=" * 60)
        print("本地语音控制 PC")
        print("=" * 60)
        print()
        print("[VoiceControlApp] 正在启动...")

        # 启动唤醒词检测
        self.detector.start(self._on_wake_word_detected)

        # 启动音频采集
        self.capture.start(self._audio_frame_callback)

        self.state = self.STATE_IDLE
        print()
        print("[VoiceControlApp] 已启动，等待唤醒词...")
        print()

        # 主循环（Windows 兼容：用 Event 代替 signal.pause）
        try:
            while self.running:
                self._stop_event.wait(timeout=1.0)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """停止应用并清理"""
        print("[VoiceControlApp] 正在停止...")

        self._stop_event.set()
        self.capture.stop()
        self.detector.stop()
        self.recognizer.stop_recording()
        self.tts.stop()

        print("[VoiceControlApp] 已退出")

    def reload_commands(self) -> None:
        """重新加载命令配置"""
        self.parser.reload_commands()
        self.tts.speak("命令配置已重新加载")


def main():
    """主函数"""
    # 检查命令行参数
    run_as_tray = "--tray" in sys.argv

    app = VoiceControlApp()

    if run_as_tray:
        # 托盘模式：启动托盘后启动应用
        print("[Main] 系统托盘模式启动")

        tray = SystemTray(
            app=app,
            on_exit=lambda: (app.stop(), sys.exit(0)),
            on_reload=app.reload_commands
        )

        # 在后台线程启动应用
        def app_thread():
            app.start()

        thread = threading.Thread(target=app_thread, daemon=True)
        thread.start()

        # 在主线程启动托盘（阻塞直到退出）
        tray.start()
    else:
        # 控制台模式
        app.start()


if __name__ == "__main__":
    main()
