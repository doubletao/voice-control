"""
唤醒词检测模块
封装 Porcupine 唤醒词检测
"""

import pvporcupine
import numpy as np
from typing import Callable, Optional


class WakeWordDetector:
    def __init__(self, access_key: str, model_path: str, sensitivity: float = 0.5):
        """
        初始化唤醒词检测器

        Args:
            access_key: Picovoice AccessKey
            model_path: 唤醒词模型文件路径 (.ppn)
            sensitivity: 检测灵敏度 (0-1)，越高越敏感但越可能误触发
        """
        self.access_key = access_key
        self.model_path = model_path
        self.sensitivity = sensitivity

        self._porcupine: Optional[pvporcupine.Porcupine] = None
        self._wake_word_callback: Optional[Callable[[], None]] = None
        self._is_running = False

    def start(self, callback: Callable[[], None]) -> None:
        """
        开始检测唤醒词

        Args:
            callback: 检测到唤醒词后的回调函数
        """
        if self._is_running:
            return

        self._wake_word_callback = callback

        self._porcupine = pvporcupine.create(
            access_key=self.access_key,
            keyword_paths=[self.model_path],
            sensitivities=[self.sensitivity]
        )

        self._is_running = True
        print(f"[WakeWordDetector] 已启动，模型={self.model_path}, 灵敏度={self.sensitivity}")
        print(f"[WakeWordDetector] 期望帧长={self._porcupine.frame_length}, 采样率={self._porcupine.sample_rate}")

    def stop(self) -> None:
        """停止检测并释放资源"""
        if not self._is_running:
            return

        self._is_running = False

        if self._porcupine is not None:
            self._porcupine.delete()
            self._porcupine = None

        print("[WakeWordDetector] 已停止")

    def process_frame(self, audio_frame: np.ndarray) -> None:
        """
        处理一帧音频数据

        Args:
            audio_frame: 音频帧，int16 格式，长度必须匹配 Porcupine 要求
        """
        if not self._is_running or self._porcupine is None:
            return

        # 确保帧长正确
        if len(audio_frame) != self._porcupine.frame_length:
            return

        # 检测唤醒词
        result = self._porcupine.process(audio_frame)
        if result >= 0 and self._wake_word_callback is not None:
            print("[WakeWordDetector] 检测到唤醒词!")
            self._wake_word_callback()

    def get_sample_rate(self) -> int:
        """获取所需采样率"""
        if self._porcupine is not None:
            return self._porcupine.sample_rate
        return 16000

    def get_frame_length(self) -> int:
        """获取所需帧长度"""
        if self._porcupine is not None:
            return self._porcupine.frame_length
        return 512

    def is_running(self) -> bool:
        """返回是否正在检测"""
        return self._is_running
