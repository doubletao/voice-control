"""
语音识别模块
封装 Vosk 离线语音识别
支持录音（静音检测）+ 识别
"""

import numpy as np
from vosk import Model, KaldiRecognizer
from typing import Optional, Callable
import json


class SpeechRecognizer:
    def __init__(self, model_path: str, sample_rate: int = 16000,
                 silence_threshold: int = 500, silence_duration: float = 1.5, max_duration: float = 8.0):
        """
        初始化语音识别器

        Args:
            model_path: Vosk 模型目录路径
            sample_rate: 采样率
            silence_threshold: RMS 静音阈值，低于此值认为是静音
            silence_duration: 连续静音多少秒视为说话结束
            max_duration: 最大录音时长（秒），超时强制结束
        """
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_duration = max_duration

        self._model: Optional[Model] = None
        self._recognizer: Optional[KaldiRecognizer] = None
        self._audio_buffer: list[np.ndarray] = []
        self._silence_frames = 0
        self._is_recording = False
        self._completed_callback: Optional[Callable[[str], None]] = None

        # 预计算需要多少静音帧
        self._silence_frames_needed = int((silence_duration * sample_rate) / 512)
        self._max_frames = int((max_duration * sample_rate) / 512)
        self._frame_count = 0

        print(f"[SpeechRecognizer] 初始化完成，静音阈值={silence_threshold}, "
              f"静音时长={silence_duration}s (需要 {self._silence_frames_needed} 帧), "
              f"最大时长={max_duration}s (最多 {self._max_frames} 帧)")

    def load_model(self) -> None:
        """加载模型，需要在开始前调用"""
        print(f"[SpeechRecognizer] 加载模型: {self.model_path}")
        self._model = Model(self.model_path)
        self._recognizer = KaldiRecognizer(self._model, self.sample_rate)
        print("[SpeechRecognizer] 模型加载完成")

    def start_recording(self, callback: Callable[[str], None]) -> None:
        """
        开始录音

        Args:
            callback: 录音完成（静音/超时）后的回调，返回识别文本
        """
        if self._is_recording:
            return

        if self._recognizer is None:
            self.load_model()

        self._completed_callback = callback
        self._audio_buffer.clear()
        self._silence_frames = 0
        self._frame_count = 0
        self._recognizer.reset()
        self._is_recording = True
        print("[SpeechRecognizer] 开始录音")

    def stop_recording(self) -> None:
        """停止录音"""
        self._is_recording = False
        self._audio_buffer.clear()
        print("[SpeechRecognizer] 停止录音")

    def process_frame(self, audio_frame: np.ndarray) -> bool:
        """
        处理一帧音频数据，判断是否结束录音

        Args:
            audio_frame: 音频帧 int16

        Returns:
            True 表示录音已结束，False 表示继续录音
        """
        if not self._is_recording or self._recognizer is None:
            return False

        self._audio_buffer.append(audio_frame)
        self._frame_count += 1

        # 计算 RMS 能量判断是否静音
        rms = self._calculate_rms(audio_frame)
        if rms < self.silence_threshold:
            self._silence_frames += 1
        else:
            self._silence_frames = 0

        # 送入识别器进行部分解码
        if self._recognizer.AcceptWaveform(audio_frame.tobytes()):
            pass  # 结果会在最后得到

        # 检查是否应该结束录音
        should_end = False
        if self._silence_frames >= self._silence_frames_needed:
            print(f"[SpeechRecognizer] 检测到连续静音，结束录音")
            should_end = True
        elif self._frame_count >= self._max_frames:
            print(f"[SpeechRecognizer] 达到最大时长，结束录音")
            should_end = True

        if should_end:
            self._finalize_recognition()
            return True

        return False

    def _calculate_rms(self, audio_frame: np.ndarray) -> float:
        """计算音频帧的 RMS 能量"""
        return np.sqrt(np.mean(audio_frame.astype(np.float64) ** 2))

    def _finalize_recognition(self) -> None:
        """完成识别并调用回调"""
        self._is_recording = False

        if self._recognizer is None or self._completed_callback is None:
            return

        # 获取最终结果
        result_json = self._recognizer.FinalResult()
        result_dict = json.loads(result_json)
        text = result_dict.get("text", "").strip()

        print(f"[SpeechRecognizer] 识别结果: '{text}'")
        self._completed_callback(text)

    def is_recording(self) -> bool:
        """返回是否正在录音"""
        return self._is_recording

    def unload_model(self) -> None:
        """卸载模型释放内存"""
        if self._model is not None:
            del self._model
            del self._recognizer
            self._model = None
            self._recognizer = None
            print("[SpeechRecognizer] 模型已卸载")
