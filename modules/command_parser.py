"""
命令解析模块
使用关键词匹配方式解析识别文本，找到对应的命令
"""

import yaml
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class ParsedCommand:
    """解析后的命令结构"""
    name: str
    keywords: List[str]
    action: str
    params: Dict[str, Any]
    response: str  # 语音反馈文本（可配置化）


class CommandParser:
    def __init__(self, commands_file: str = "commands.yaml"):
        """
        初始化命令解析器

        Args:
            commands_file: 命令配置文件路径
        """
        self.commands_file = commands_file
        self.commands: List[ParsedCommand] = []
        self.default_responses: Dict[str, str] = {
            "unrecognized": "抱歉，我没听懂这个命令",
            "error": "执行出错了"
        }
        self._load_commands()

    def _load_commands(self) -> None:
        """从配置文件加载命令"""
        with open(self.commands_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        self.commands.clear()

        for cmd in config.get("commands", []):
            parsed = ParsedCommand(
                name=cmd.get("name", ""),
                keywords=cmd.get("keywords", []),
                action=cmd.get("action", ""),
                params=cmd.get("params", {}),
                response=cmd.get("response", "")
            )
            self.commands.append(parsed)

        # 加载默认响应配置
        if "default_responses" in config:
            self.default_responses.update(config["default_responses"])

        print(f"[CommandParser] 已加载 {len(self.commands)} 条命令")

    def parse(self, text: str) -> Optional[ParsedCommand]:
        """
        解析文本，找到匹配的命令

        Args:
            text: 语音识别得到的文本

        Returns:
            匹配到的命令，None 表示未匹配到
        """
        text = text.strip()
        if not text:
            return None

        # 关键词匹配：任意一个关键词出现在文本中就算匹配
        # 多个命令匹配时返回第一个（配置文件顺序决定优先级）
        for cmd in self.commands:
            for keyword in cmd.keywords:
                if keyword in text:
                    print(f"[CommandParser] 匹配到命令: {cmd.name} (关键词: '{keyword}')")
                    return cmd

        print(f"[CommandParser] 未匹配到任何命令，文本: '{text}'")
        return None

    def get_default_response(self, response_type: str) -> str:
        """获取默认响应文本"""
        return self.default_responses.get(response_type, "")

    def reload_commands(self) -> None:
        """重新加载命令配置（支持热更新）"""
        self._load_commands()
        print("[CommandParser] 命令配置已重新加载")
