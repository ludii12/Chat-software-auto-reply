# Agnes 聊天自动回复助手

一个基于 Python + Tkinter 的桌面聊天自动回复工具，通过 OCR 识别聊天窗口中的对方消息，调用大模型 API 生成自然回复，模拟真人聊天节奏。

支持微信桌面版等主流聊天软件，内置 Skill 话术系统，可针对不同联系人（领导、朋友、对象等）自动切换回复风格。

## 功能特性

- **自动识别 + 回复**：OCR 实时识别聊天窗口对方消息，调用 Agnes AI 生成自然回复并发送
- **Skill 话术系统**：针对不同关系对象（领导/朋友/对象/暧昧对象/路人）自动加载不同回复风格，互不污染
- **独立记忆**：每个聊天对象保留独立对话记忆（最近 30 条），切换对象自动加载
- **只回复最新消息**：切换聊天对象时预扫描标记已有消息，不会疯狂回复历史记录
- **承诺备忘**：AI 自动提取回复中的承诺（如"11点去吃饭"），保存到承诺备忘菜单
- **赞赏入口**：内置赞赏地址，支持一键复制
- **主题切换**：支持多种主题配色
- **纯 Tkinter UI**：不依赖任何第三方 UI 库，打包体积小

## 快速开始

### 环境要求

- Windows 10/11
- Python 3.8+
- 聊天软件桌面版（如微信 PC 版）

### 方式一：直接使用打包版（推荐普通用户）

1. 下载 [Releases](../../releases) 页面的 `WeChatAutoReply.exe`
2. 放到任意文件夹运行即可
3. 首次使用请看软件内"使用教程"页面

### 方式二：从源码运行（推荐开发者）

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 OCR 运行时（首次必须执行）
.\install_rapidocr.bat

# 4. 运行
python wechat_auto_reply.py
```

或直接双击 `start.bat` 启动。

## 首次配置（6 步）

软件内有完整的图形化教程，这里是要点：

1. **获取 Agnes API 密钥**：前往 [Agnes 官网](https://agnes-ai.com) 注册，创建 API Key（sk- 开头）
2. **绑定密钥**：软件内"Agnes 设置" → 粘贴 API Key → 保存
3. **校准聊天区域**：软件内"校准发送" → 定位输入框 → 定位聊天记录框四角
4. **配置聊天对象**：选择分类 → 添加名字 → 锁定对象
5. **开启自动回复**：勾选"Agnes 生成回复"（首次建议勾选"只预览，不发送"测试）
6. **连接并运行**：点"连接聊天" → 点"开始"

详细图文教程请看软件内"使用教程"页面。

## Skill 系统

Skill 是一份 Markdown 格式的话术规范，决定 AI 回复的语气和风格。

### 内置 Skill

| Skill | 适用场景 |
|-------|---------|
| `reply-to-leader` | 回复领导/上级，恭敬稳重不卑微 |
| `chat-with-partner` | 和对象/伴侣聊天，亲密自然 |
| `chat-with-crush` | 和暧昧对象聊天，有分寸的撩 |
| `chat-with-friends` | 和朋友聊天，随意轻松 |
| `chat-with-strangers` | 和陌生人聊天，礼貌有距离 |
| `wechat_reply_assistant` | 默认通用风格 |

### 自定义 Skill

在 `skills/` 目录下新建文件夹（英文+连字符命名），创建 `SKILL.md`：

```markdown
---
name: your-skill-name
description: |
  这个 skill 的用途说明。
  适用场景：xxx。
  核心原则：xxx。
  触发场景：xxx。
---

# 话术规范标题

## 核心原则
1. 规则一
2. 规则二

## 常见场景回复模板
### 1. 场景一
- "回复示例1"
- "回复示例2"

## 禁忌
- 不能说什么、不能做什么
```

保存后重启软件，在"Agnes 设置"里把某个分类关联到新 Skill 即可。

详细编写指南请看软件内"使用教程" → "三、Skill 系统"。

## 项目结构

```
wechat-auto-reply/
├── wechat_auto_reply.py     # 主程序源码（单文件）
├── WeChatAutoReply.spec      # PyInstaller 打包配置
├── requirements.txt          # Python 依赖
├── agnes_config.json         # 配置文件（API Key、校准坐标等）
├── assets/
│   ├── app_icon.ico          # 应用图标
│   └── app_logo.png          # 应用 Logo
├── skills/                   # Skill 话术规范
│   ├── reply-to-leader/
│   │   └── SKILL.md
│   ├── chat-with-friends/
│   │   └── SKILL.md
│   └── ...
├── build_app.bat             # 一键打包脚本
├── start.bat                 # 一键启动脚本
├── install_rapidocr.bat      # OCR 运行时安装脚本
└── install_rapidocr.ps1      # OCR 安装 PowerShell 版
```

## 从源码打包 EXE

```bash
# 1. 确保已安装依赖和 OCR 运行时
pip install -r requirements.txt
.\install_rapidocr.bat

# 2. 安装 PyInstaller
pip install pyinstaller

# 3. 打包
.\build_app.bat
```

打包完成后，`dist/WeChatAutoReply.exe` 即为最终程序。

## 配置文件说明

### agnes_config.json

软件运行时的核心配置，包含 API Key、模型参数、校准坐标等。**首次运行软件会自动生成**，也可手动编辑：

| 字段 | 说明 |
|------|------|
| `api_key` | Agnes API 密钥（必填） |
| `base_url` | API 地址，默认 `https://apihub.agnes-ai.com/v1` |
| `model` | 模型名，默认 `agnes-2.0-flash` |
| `temperature` | 回复随机性，0-1，默认 0.6 |
| `max_tokens` | 回复最大长度，默认 160 |
| `input_click_x/y` | 输入框点击坐标（校准生成） |
| `chat_box_x1/y1/x2/y2` | 聊天记录框四角坐标（校准生成） |
| `incoming_side` | 对方消息位置，left 或 right |
| `system_prompt` | 系统提示词 |
| `active_skill` | 当前激活的 Skill 名 |

### 运行时生成的文件

| 文件 | 说明 | 是否敏感 |
|------|------|---------|
| `chat_memory.json` | 各联系人对话记忆 | 是，包含聊天内容 |
| `contacts.json` | 联系人分类管理 | 是，包含联系人信息 |
| `promises.json` | 承诺备忘数据 | 是 |
| `theme.json` | 主题偏好 | 否 |
| `rules.json` | 自定义规则 | 否 |
| `wechat_auto_reply.log` | 运行日志 | 是，可能含识别内容 |
| `debug/` | 调试截图 | 是，包含聊天截图 |

**这些文件已在 `.gitignore` 中排除，不会上传到 GitHub。**

## 技术栈

- **Python 3.8+** - 主语言
- **Tkinter** - GUI 框架（纯原生，无第三方 UI 库）
- **pywinauto** - Windows 窗口操作
- **RapidOCR (ONNX Runtime)** - 本地文字识别
- **Pillow** - 图像处理
- **Agnes AI API** - 大模型对话生成
- **PyInstaller** - 打包成 EXE

## 工作原理

1. **连接窗口**：通过 `pywinauto` 找到聊天软件桌面窗口
2. **OCR 识别**：定时截图聊天记录区域，用 RapidOCR 本地识别文字
3. **坐标判断**：根据消息中心 x 坐标判断是对方消息还是自己消息
4. **去重过滤**：用规范化文本（去标点空格）做去重，避免重复回复
5. **AI 生成**：把最新对方消息 + 对话记忆 + Skill 话术发给 Agnes API
6. **延迟发送**：5-10 秒随机延迟后，通过模拟键盘输入发送回复
7. **承诺提取**：异步调用 AI 判断回复中是否含承诺，有则保存到承诺备忘

## 常见问题

### 回复发不出去？
- 检查是否已锁定对象
- 检查输入框位置是否校准
- 检查是否勾选了"只预览，不发送"
- 确保聊天窗口在前台

### 回复语气不对？
- 检查"Agnes 设置"里该分类关联的 Skill 是否正确
- 点"重载 Skill"刷新

### 切换对象后回复历史消息？
- 确认聊天记录框四角校准准确
- 软件会预扫描标记已有消息，若仍出现请检查 OCR 识别准确度

### OCR 识别不准？
- 重新校准聊天记录框四角，确保范围准确
- 查看运行日志了解识别结果

### API 报错？
- 检查 API Key 是否正确
- 检查账户是否欠费
- 在"Agnes 设置"点"测试连接"验证

## 开发说明

### 添加新功能

主程序是单文件 `wechat_auto_reply.py`，结构清晰：

- **数据管理类**：`AgnesConfig`、`ChatMemory`、`ContactManager`、`PromiseManager`、`SkillManager`、`ThemeManager`
- **服务类**：`AgnesClient`（AI 调用）、`WeChatController`（窗口控制）、`OCREngine`（OCR 识别）
- **UI 类**：`App`（主窗口）、`Card`、`RoundedButton`、`ModernDialog`、`ModernCombobox`
- **页面构建**：`_build_reply_page`、`_build_calibrate_page`、`_build_settings_page`、`_build_tutorial_page`、`_build_logs_page`、`_build_promises_page`、`_build_sponsor_page`

### 贡献

欢迎提交 Issue 和 PR：

- 发现 Bug 请提 Issue，附上日志和复现步骤
- 想加新功能请先开 Issue 讨论
- 提交 PR 前请确保代码能正常运行且不破坏现有功能

## 开源协议

[MIT License](LICENSE) - 可自由使用、修改、分发

## 致谢

- [RapidOCR](https://github.com/RapidAI/RapidOCR) - 高性能本地 OCR
- [pywinauto](https://github.com/pywinauto/pywinauto) - Windows GUI 自动化
- [Agnes AI](https://agnes-ai.com) - 大模型 API 服务

## Star History

如果这个项目帮到了你，欢迎 Star ⭐
