"""
音频采集模块
负责麦克风采集和音频流管理
"""

import pyaudio
import numpy as np
from typing import Callable, Optional


class AudioCapture:
    def __init__(self, sample_rate: int = 16000, frame_length: int = 512, device_index: int = -1):
        """
        初始化音频采集

        Args:
            sample_rate: 采样率，默认16000Hz (Porcupine/Vosk 都要求 16000)
            frame_length: 每帧采样点数，默认512
            device_index: 麦克风设备索引，-1 表示默认设备
        """
        self.sample_rate = sample_rate
        self.frame_length = frame_length
        self.device_index = device_index if device_index >= 0 else None

        self._pa: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._callback: Optional[Callable[[np.ndarray], None]] = None
        self._is_running = False

    def start(self, callback: Callable[[np.ndarray], None]) -> None:
        """
        开始采集音频

        Args:
            callback: 每帧音频数据的回调函数，接收 np.ndarray[int16] 格式的音频帧
        """
        if self._is_running:
            return

        self._callback = callback
        self._pa = pyaudio.PyAudio()

        if self.device_index is not None:
            device_info = self._pa.get_device_info_by_index(self.device_index)
            print(f"[AudioCapture] 使用设备: [{self.device_index}] {device_info['name']}")

        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.frame_length,
            input_device_index=self.device_index,
            stream_callback=self._audio_callback
        )

        self._stream.start_stream()
        self._is_running = True
        print(f"[AudioCapture] 开始采集，采样率={self.sample_rate}, 帧长={self.frame_length}")

    def stop(self) -> None:
        """停止采集并释放资源"""
        if not self._is_running:
            return

        self._is_running = False

        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._pa is not None:
            self._pa.terminate()
            self._pa = None

        print("[AudioCapture] 已停止采集")

    def is_running(self) -> bool:
        """返回是否正在采集"""
        return self._is_running

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio 回调"""
        if self._callback is not None:
            # 转换为 numpy 数组
            audio_frame = np.frombuffer(in_data, dtype=np.int16)
            self._callback(audio_frame)

        return (None, pyaudio.paContinue)

    def list_devices(self) -> None:
        """列出所有可用音频输入设备"""
        pa = pyaudio.PyAudio()
        print("可用音频输入设备:")
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                print(f"  [{i}] {info['name']}, 输入通道: {info['maxInputChannels']}, 默认采样率: {info['defaultSampleRate']}")
        pa.terminate()
