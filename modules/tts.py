"""
语音合成模块
使用 pyttsx3 - Windows 原生语音引擎，不需要额外模型，安装即用
"""

from typing import Optional


class TTS:
    def __init__(self, enabled: bool = True):
        """
        初始化 TTS

        Args:
            enabled: 是否启用 TTS，False 则只打印不合成
        """
        self.enabled = enabled
        self._engine: Optional[object] = None
        self._is_loaded = False

        print(f"[TTS] 初始化完成，启用状态: {enabled}")
        if enabled:
            self._load_engine()

    def _load_engine(self) -> None:
        """加载 pyttsx3 引擎"""
        try:
            import pyttsx3
            print("[TTS] 初始化 pyttsx3 引擎 (Windows 原生)")
            self._engine = pyttsx3.init()
            # 设置语速 (150 words per minute)
            self._engine.setProperty('rate', 150)
            # 尝试选择中文语音
            voices = self._engine.getProperty('voices')
            for voice in voices:
                # 查找包含中文的语音包
                if 'zh' in voice.id.lower() or 'Chinese' in voice.name or '中文' in voice.name:
                    self._engine.setProperty('voice', voice.id)
                    print(f"[TTS] 选择中文语音: {voice.name}")
                    break
            self._is_loaded = True
            print("[TTS] 引擎初始化完成")
        except ImportError as e:
            print(f"[TTS] pyttsx3 导入失败，请先安装: pip install pyttsx3")
            print(f"错误: {e}")
            self.enabled = False
        except Exception as e:
            print(f"[TTS] pyttsx3 初始化失败: {e}")
            self.enabled = False

    def speak(self, text: str) -> None:
        """
        合成语音并播放

        Args:
            text: 要合成的文本
        """
        if not self.enabled or not self._is_loaded or self._engine is None:
            print(f"[TTS] (已禁用) 输出: {text}")
            return

        if not text.strip():
            return

        print(f"[TTS] 语音输出: {text}")

        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            print(f"[TTS] 播放失败: {e}")

    def stop(self) -> None:
        """停止并释放引擎"""
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
            self._engine = None
            self._is_loaded = False
            print("[TTS] 引擎已停止")

    def unload(self) -> None:
        """卸载引擎（兼容旧接口）"""
        self.stop()
