# 本地语音控制 PC 技术方案

> 个人使用 · 本地部署 · 低性能消耗 · 开源/免费

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────┐
│                    主控循环 (main.py)                  │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  音频采集模块    │────▶│  唤醒词检测模块  │  常驻后台，CPU <1%
│  AudioCapture   │     │  OpenWakeWord   │
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
                        │  pyttsx3        │
                        └─────────────────┘
```

---

## 二、技术选型

| 模块 | 技术方案 | 版本 | 理由 |
|------|---------|------|------|
| 唤醒词检测 | OpenWakeWord (openwakeword) | latest | 开源免费，无需注册，CPU<1% |
| 语音识别 | Vosk | 0.3.x | 离线，模型50MB，CPU可跑 |
| 语音合成 | pyttsx3 | latest | Windows 原生引擎，无需模型，安装即用 |
| 音频采集 | PyAudio | 0.2.x | 跨平台，低延迟 |
| PC控制 | pyautogui + psutil | latest | 鼠标键盘+系统控制 |
| 配置管理 | PyYAML | latest | 命令词可配置化 |
| 运行环境 | Python 3.10+ | - | Windows 11 |

---

## 三、项目结构

```
voice-control/
├── main.py                  # 主入口，启动主控循环
├── config.yaml              # 全局配置（唤醒词、模型路径等）
├── commands.yaml            # 命令词配置（可自定义扩展）
│
├── modules/
│   ├── audio_capture.py     # 麦克风采集，音频流管理
│   ├── wake_word.py         # 唤醒词检测（OpenWakeWord 封装）
│   ├── recognizer.py        # 语音识别（Vosk封装）
│   ├── command_parser.py    # 命令解析，关键词匹配
│   ├── action_executor.py   # 动作执行，PC控制
│   ├── tts.py               # 语音合成（pyttsx3 封装）
│   └── tray.py              # 系统托盘 + 开机自启
│
└── models/
    └── vosk/                # Vosk中文模型（vosk-model-small-cn）
```

---

## 四、核心流程设计

### 4.1 主控循环状态机

```
[IDLE] ──唤醒词──▶ [LISTENING] ──静音/超时──▶ [RECOGNIZING]
  ▲                                                    │
  └──────────────────────────────────────────[EXECUTING]
                                              │
                                         [SPEAKING] ──完成──▶ [IDLE]
```

### 4.2 录音结束判断策略

- 静音检测：连续 1.5 秒静音视为说完
- 超时保护：最长录音 8 秒，防止误触后一直录音
- 能量阈值：低于 RMS 阈值判定为静音

### 4.3 命令解析策略

采用**关键词匹配**而非 NLP，轻量且可靠：

```yaml
# commands.yaml 示例
commands:
  - name: open_browser
    keywords: ["打开浏览器", "浏览器", "上网"]
    action: open_app
    params: { app: "chrome" }

  - name: volume_up
    keywords: ["音量大一点", "调高音量", "大声一点"]
    action: volume_control
    params: { direction: "up", step: 10 }

  - name: screenshot
    keywords: ["截图", "截屏"]
    action: screenshot
    params: {}
```

---

## 五、支持的命令分类

### 5.1 系统控制
| 命令示例 | 动作 |
|---------|------|
| 调高音量 / 调低音量 | 系统音量 ±10% |
| 静音 / 取消静音 | 切换静音状态 |
| 截图 | 全屏截图保存桌面 |
| 关机 / 重启 | 系统关机/重启（需二次确认） |
| 锁屏 | 锁定屏幕 |

### 5.2 应用控制
| 命令示例 | 动作 |
|---------|------|
| 打开浏览器 | 启动 Chrome/Edge |
| 打开记事本 | 启动 Notepad |
| 关闭当前窗口 | Alt+F4 |
| 切换窗口 | Alt+Tab |

### 5.3 媒体控制
| 命令示例 | 动作 |
|---------|------|
| 播放 / 暂停 | 媒体播放键 |
| 下一首 / 上一首 | 媒体切换键 |

### 5.4 自定义命令（可扩展）
通过修改 `commands.yaml` 添加任意命令，无需改代码。

---

## 六、性能设计目标

| 指标 | 目标值 | 说明 |
|------|-------|------|
| 常驻内存 | <150MB | 唤醒词检测待机状态 |
| 唤醒延迟 | <200ms | 从说出唤醒词到提示音 |
| 识别延迟 | <2s | 说完命令到开始执行 |
| CPU 待机 | <2% | 仅唤醒词检测运行时 |
| CPU 识别时 | <30% | Vosk 识别期间峰值 |

---

## 七、依赖清单

```txt
# requirements.txt
openwakeword         # 唤醒词检测（开源免费，无需注册）
vosk                 # 语音识别
pyttsx3              # 语音合成（Windows 原生）
pyaudio              # 音频采集
pyautogui            # 键盘鼠标控制
psutil               # 系统信息/进程控制
pycaw                # Windows 音量控制
pyyaml               # 配置文件解析
pystray              # 系统托盘图标
Pillow               # 图标处理
```

---

## 八、模型文件清单

| 模型 | 来源 | 大小 | 用途 |
|------|------|------|------|
| vosk-model-small-cn-0.22 | alphacephei.com | ~50MB | 中文语音识别 |

> OpenWakeWord 和 pyttsx3 均开箱即用，无需额外下载模型文件。

---

## 九、风险与注意事项

1. **OpenWakeWord 内置唤醒词**：默认提供 "hey jarvis" 等英文唤醒词，中文唤醒词需训练自定义模型
2. **Vosk 中文识别率**：小模型识别率约 80-85%，命令词较短时影响不大；如不满意可换 faster-whisper tiny
3. **PyAudio 安装**：Windows 下需要先安装 PortAudio，建议用预编译包 `pipwin install pyaudio`
4. **关机/重启命令**：需加二次语音确认（"确认关机"），防止误触
5. **后台常驻**：建议打包为系统托盘应用，开机自启

---

## 十、后续可扩展方向

- [x] 系统托盘图标 + 开机自启（pystray）
- [ ] 命令词热更新（修改 yaml 无需重启）
- [ ] 训练中文自定义唤醒词模型（OpenWakeWord）
- [ ] 识别率不满意时替换为 faster-whisper tiny
- [x] 语音反馈文本可配置化
