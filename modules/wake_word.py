"""
唤醒词检测模块
封装 OpenWakeWord 开源唤醒词检测
"""

import numpy as np
from typing import Callable, Optional


class WakeWordDetector:
    def __init__(self, model_name: str = "default", threshold: float = 0.5):
        """
        初始化唤醒词检测器

        Args:
            model_name: 唤醒词模型名称，"default" 使用内置模型，
                        也可指定 .onnx 文件路径
            threshold: 检测阈值 (0-1)，越高越严格，越不容易误触发
        """
        self.model_name = model_name
        self.threshold = threshold

        self._model = None
        self._wake_word_callback: Optional[Callable[[], None]] = None
        self._is_running = False

        print(f"[WakeWordDetector] 初始化完成，模型={model_name}, 阈值={threshold}")

    def start(self, callback: Callable[[], None]) -> None:
        """
        开始检测唤醒词

        Args:
            callback: 检测到唤醒词后的回调函数
        """
        if self._is_running:
            return

        self._wake_word_callback = callback

        from openwakeword import Model

        if self.model_name == "default":
            self._model = Model(inference_framework="onnx")
        else:
            self._model = Model(wakeword_models=[self.model_name], inference_framework="onnx")

        self._is_running = True
        print(f"[WakeWordDetector] 已启动，可用唤醒词: {list(self._model.models.keys())}")

    def stop(self) -> None:
        """停止检测并释放资源"""
        if not self._is_running:
            return

        self._is_running = False
        self._model = None

        print("[WakeWordDetector] 已停止")

    def process_frame(self, audio_frame: np.ndarray) -> None:
        """
        处理一帧音频数据

        Args:
            audio_frame: 音频帧，int16 格式，16kHz 单声道
        """
        if not self._is_running or self._model is None:
            return

        prediction = self._model.predict(audio_frame)

        for wake_word, score in prediction.items():
            if score > self.threshold:
                print(f"[WakeWordDetector] 检测到唤醒词 '{wake_word}'，置信度={score:.3f}")
                self._model.reset()
                if self._wake_word_callback is not None:
                    self._wake_word_callback()
                return

    def is_running(self) -> bool:
        """返回是否正在检测"""
        return self._is_running
