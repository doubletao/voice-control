# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

全离线本地语音控制 PC 应用，通过自然语言语音命令控制计算机。支持系统控制、应用控制、媒体控制，所有计算在本地完成，无需联网。

## 技术栈

- **语言**: Python 3.10+
- **唤醒词检测**: Porcupine (pvporcupine)
- **语音识别**: Vosk 0.3.x (离线)
- **语音合成**: Piper TTS (离线)
- **音频采集**: PyAudio 0.2.x
- **PC 控制**: pyautogui + psutil + pycaw
- **配置**: PyYAML

## 项目架构

```
┌─────────────────────────────────────────────────────┐
│               主控循环 (main.py)                      │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  音频采集模块    │────▶│  唤醒词检测模块  │  常驻后台，CPU <1%
│  AudioCapture   │     │  Porcupine      │
└─────────────────┘     └────────┬────────┘
                                  │ 检测到唤醒词
                                  ▼
                        ┌─────────────────┐
                        │  语音识别模块    │  录音 + 识别
                        │  Vosk           │
                        └────────┬────────┘
                                  │ 识别文本
                                  ▼
                        ┌─────────────────┐
                        │  命令解析模块    │  关键词匹配
                        │  CommandParser  │
                        └────────┬────────┘
                                  │ 结构化命令
                                  ▼
                        ┌─────────────────┐
                        │  动作执行模块    │  控制 PC
                        │  ActionExecutor │
                        └────────┬────────┘
                                  │ 执行结果
                                  ▼
                        ┌─────────────────┐
                        │  语音反馈模块    │  播报结果
                        │  Piper TTS      │
                        └─────────────────┘
```

### 状态机流程

```
[IDLE] ──唤醒词──▶ [LISTENING] ──静音/超时──▶ [RECOGNIZING]
  ▲                                                    │
  └──────────────────────────────────────────[EXECUTING]
                                            │
                                       [SPEAKING] ──完成──▶ [IDLE]
```

## 项目结构

```
voice-control/
├── main.py                  # 主入口，主控循环
├── config.yaml              # 全局配置（唤醒词、模型路径等）
├── commands.yaml            # 命令词配置（可自定义扩展）
├── requirements.txt         # Python 依赖清单
├── voice-control-design.md  # 技术方案文档
├── modules/
│   ├── audio_capture.py     # 麦克风采集，音频流管理
│   ├── wake_word.py         # 唤醒词检测（Porcupine 封装）
│   ├── recognizer.py        # 语音识别（Vosk 封装）
│   ├── command_parser.py    # 命令解析，关键词匹配
│   ├── action_executor.py   # 动作执行，PC 控制
│   └── tts.py               # 语音合成（Piper TTS 封装）
└── models/
    ├── porcupine/           # 唤醒词模型文件 (.ppn)
    ├── vosk/                # Vosk 中文模型
    └── piper/               # Piper 中文模型文件
```

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 解决 Windows PyAudio 安装问题（需要先安装 pipwin）
pip install pipwin
pipwin install pyaudio

# 运行主程序
python main.py
```

## 设计要点

### 命令解析策略
采用关键词匹配而非大型 NLP 模型，轻量可靠。所有命令通过 `commands.yaml` 配置：
```yaml
commands:
  - name: open_browser
    keywords: ["打开浏览器", "浏览器", "上网"]
    action: open_app
    params: { app: "chrome" }
```

### 录音结束判断
- 静音检测：连续 1.5 秒静音视为说完
- 超时保护：最长录音 8 秒
- 能量阈值：低于 RMS 阈值判定为静音

### 性能目标
- 常驻内存：<150MB（待机状态）
- 唤醒延迟：<200ms
- 识别延迟：<2s
- CPU 待机：<2%
- CPU 识别峰值：<30%

## 重要注意事项

1. **Porcupine AccessKey**：需要在 Picovoice Console 注册获取，个人非商业使用免费
2. **模型文件**：需要手动下载到 `models/` 目录：
   - vosk-model-small-cn-0.22 (~50MB)
   - zh_CN-huayan-medium.onnx (~60MB)
3. **关机/重启命令**：必须二次语音确认，防止误触
4. **扩展方式**：新增命令只需修改 `commands.yaml`，无需修改代码

## 可扩展方向

- 系统托盘图标 + 开机自启（pystray）
- 命令词热更新（修改 yaml 无需重启）
- 多唤醒词支持
- 可替换为 faster-whisper tiny 提升识别率
- 语音反馈文本可配置化
