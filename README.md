# 聊天自动回复小工具

一个本机 Windows 桌面小工具，通过桌面自动化读取当前聊天窗口里的最新文本消息，并自动生成回复发送回去。支持两种回复模式：基于关键词规则（`rules.json`）的快速回复，以及接入 Agnes 大模型的智能对话回复。

工具还内置 **Skill 系统**：把话术风格、知识框架写进 `skills/` 目录下的 Markdown 文件，应用会自动加载并作为大模型的系统上下文，让回复更贴合你想要的语气和场景。

---

## 功能特性

- **桌面自动化读取消息**：通过 `pywinauto` 操作当前已打开的聊天窗口，截取聊天记录区域，用 `rapidocr` 做 OCR 识别最新文本。
- **关键词规则回复**：`rules.json` 配置关键词匹配规则，命中即回复对应文本，未命中走默认回复；支持冷却时间防重复。
- **Agnes 大模型回复**：接入 Agnes Chat API，把聊天消息、系统提示词、本地 Skill 一起送进模型，生成像真人一样的自然回复。
- **Skill 系统**：`skills/` 目录下每个文件夹一个 Skill，写进 `SKILL.md`，应用启动或点击「重载规则」时自动加载，作为大模型的上下文。
- **预览模式**：勾选「只预览，不发送」可以先看识别结果和生成回复，确认无误再真正发送。
- **控件诊断**：点「诊断控件」可输出当前窗口控件结构，便于在不同版本客户端上调整坐标。
- **配置可视化**：所有坐标、API 配置、Skill 选择都在 GUI 里填写，保存到本地 JSON 文件。
- **自动回退**：大模型请求失败时，自动回退到关键词规则，保证流程不中断。
- **可选打包为单文件 exe**：附带 `WeChatAutoReply.spec` 和 `build_app.bat`，用 PyInstaller 一键打包。

---

## 快速开始

### 环境要求

- Windows 10 / 11（64 位）
- Python 3.8 及以上
- 已登录并打开聊天客户端（保持聊天窗口在前台，不要最小化）

### 步骤

1. **克隆仓库**

   ```bash
   git clone <仓库地址>
   cd <仓库目录>
   ```

2. **安装依赖**

   双击 `start.bat`，或在命令行执行：

   ```bash
   python -m pip install -r requirements.txt
   ```

   > 如果 `rapidocr_onnxruntime` 安装失败，可使用项目根目录下的 `install_rapidocr.bat` 或 `install_rapidocr.ps1` 辅助安装。

3. **启动程序**

   双击 `start.bat`，或执行：

   ```bash
   python wechat_auto_reply.py
   ```

4. **连接聊天窗口**

   在程序主界面点「连接」（或「连接聊天」）。程序会自动找到当前前台的聊天窗口。

5. **先预览，再发送**

   - 勾选「只预览，不发送」。
   - 点「开始」。
   - 观察日志里识别到的最新消息是否正确。
   - 确认无误后取消「只预览，不发送」，再点「开始」正式自动回复。

---

## 首次配置

### 1. 配置聊天区域坐标

程序需要知道聊天记录在窗口里的位置。两种方式：

- **自动捕获**：在 GUI 里点「拾取坐标」相关按钮，按提示点击聊天窗口的左上角和右下角。
- **手动填写**：在配置区直接填 `chat_box_x1 / y1 / x2 / y2` 四个值。

还要填「输入框点击坐标」`input_click_x / input_click_y`，程序会点这个位置激活输入框。

### 2. 设置对方消息所在侧

`incoming_side` 表示对方消息显示在聊天区域的左侧还是右侧：

- `"left"`：对方在左
- `"right"`：对方在右

判断错了会导致回复错对象，首次使用务必在预览模式下确认。

### 3.（可选）接入 Agnes 大模型

1. 到 Agnes 平台创建 API Key。
2. 在程序里勾选「使用 Agnes 大模型」。
3. 填写：
   - `Base URL`：`https://apihub.agnes-ai.com/v1`
   - `模型`：`agnes-2.0-flash`
   - `API Key`：你的 Agnes Key
4. 点「保存配置」。
5. 点「测试 Agnes」，日志里出现测试成功后即可开始。

> 不接入大模型也能用，程序会走 `rules.json` 的关键词规则。

### 4. 配置关键词规则

编辑 `rules.json`：

- `default_reply`：没有匹配关键词时的默认回复。
- `reply_cooldown_seconds`：同一条内容短时间内不重复回复的冷却时间。
- `rules`：关键词匹配规则，命中任意关键词就回复对应文本。

---

## Skill 系统说明

Skill 是这个工具的核心特色。它让大模型不只是「通用聊天机器人」，而是能借鉴你写好的话术风格、知识框架来回复。

### 目录结构

```text
skills/
  chat-with-crush/          # 和暧昧对象聊天的话术
    SKILL.md
  chat-with-friends/         # 和朋友聊天的话术
    SKILL.md
  chat-with-partner/         # 和伴侣聊天的话术
    SKILL.md
  chat-with-strangers/       # 和陌生人破冰的话术
    SKILL.md
  reply-to-leader/           # 回复领导的话术
    SKILL.md
  wechat_reply_assistant/    # 通用回复约束（语气、长度、安全边界）
    SKILL.md
```

每个 Skill 就是一个文件夹加一个 `SKILL.md`，纯 Markdown 文本，没有复杂格式。

### 工作方式

- 应用启动或点「重载规则」时，会扫描 `skills/` 目录，读取所有 `SKILL.md`。
- 这些 Skill 内容会作为大模型的系统上下文一起发送。
- 在 GUI 里可以选择「当前激活的 Skill」（`active_skill`），程序会给模型额外强提示，优先使用这个 Skill 的风格。
- Skill 只作为**风格和知识参考**，程序会显式约束模型不要自称是 Skill 里的真人或角色。

### 自定义 Skill

新建一个文件夹，比如 `skills/my-style/`，在里面放一个 `SKILL.md`，写上你想要的回复风格、常用话术、注意事项，保存后点「重载规则」即可。

---

## 项目结构

```text
opensource_release/
├── wechat_auto_reply.py        # 主程序（GUI + 自动化 + 大模型调用）
├── agnes_config.json           # Agnes 大模型配置模板（API Key 留空）
├── requirements.txt            # Python 依赖
├── WeChatAutoReply.spec        # PyInstaller 打包配置
├── build_app.bat               # 一键打包脚本
├── start.bat                   # 一键启动脚本
├── install_rapidocr.bat        # rapidocr 辅助安装脚本
├── install_rapidocr.ps1        # rapidocr 辅助安装脚本（PowerShell）
├── .gitignore
├── LICENSE
├── README.md
├── assets/
│   ├── app_icon.ico            # 应用图标
│   └── app_logo.png            # 应用 Logo
└── skills/
    ├── chat-with-crush/
    │   └── SKILL.md
    ├── chat-with-friends/
    │   └── SKILL.md
    ├── chat-with-partner/
    │   └── SKILL.md
    ├── chat-with-strangers/
    │   └── SKILL.md
    ├── reply-to-leader/
    │   └── SKILL.md
    └── wechat_reply_assistant/
        └── SKILL.md
```

### 运行时会生成的文件

这些文件不在仓库里（已被 `.gitignore` 排除），程序运行后会自动创建：

- `rules.json`：关键词规则配置（首次运行生成默认模板）。
- `chat_memory.json`：聊天记忆，用于大模型多轮上下文。
- `contacts.json`：联系人备注。
- `promises.json`：承诺/待办记录。
- `theme.json`：界面主题。
- `debug/`：调试截图和 OCR 原始输出。
- `wechat_auto_reply.log`：运行日志。

---

## 打包指南

如果想把程序打包成单个 `WeChatAutoReply.exe`（无需安装 Python 即可运行），使用项目自带的打包脚本。

### 一键打包

双击 `build_app.bat`，或在命令行执行：

```bash
build_app.bat
```

脚本会自动：

1. 安装 `requirements.txt` 里的依赖。
2. 安装 `pyinstaller`。
3. 清理旧的 `build/` 和 `dist/` 目录。
4. 用 `WeChatAutoReply.spec` 配置打包。

打包成功后，`dist\WeChatAutoReply.exe` 就是最终产物。

### 关于 spec 文件

`WeChatAutoReply.spec` 已经处理好：

- 把 `assets/app_logo.png`、`skills/`、`agnes_config.json`、`rules.json` 一起打包进 exe。
- 显式声明 `numpy`、`onnxruntime`、`rapidocr_onnxruntime` 等隐式依赖为 `hiddenimports`（**注意：不能把 numpy 排除掉**，否则 OCR 会报错）。
- 用 `collect_all('rapidocr_onnxruntime')` 自动收集该包的所有数据文件。
- 排除 `psutil`、`pip`、`setuptools` 等无用大包以减小体积。
- 设置 `console=False`，运行时不弹黑框。

### 手动打包命令

```bash
pyinstaller WeChatAutoReply.spec --noconfirm
```

---

## 配置文件说明

### agnes_config.json

Agnes 大模型的核心配置。**仓库里的模板 API Key 留空，请填入你自己的 Key，不要把带 Key 的文件提交或发给别人。**

| 字段 | 说明 |
|------|------|
| `enabled` | 是否启用 Agnes 大模型回复。`false` 时走关键词规则。 |
| `base_url` | Agnes API 地址，默认 `https://apihub.agnes-ai.com/v1`。 |
| `model` | 模型名，默认 `agnes-2.0-flash`。 |
| `api_key` | 你的 API Key，敏感信息。 |
| `temperature` | 采样温度，越高越随机，默认 0.6。 |
| `max_tokens` | 单次回复最大 token 数，默认 160。 |
| `input_click_x` / `input_click_y` | 输入框点击坐标。 |
| `chat_box_x1` / `y1` / `x2` / `y2` | 聊天记录区域的左上和右下坐标。 |
| `incoming_side` | 对方消息所在侧，`left` 或 `right`。 |
| `system_prompt` | 系统提示词，约束模型的角色和回复风格。 |
| `active_skill_hint` | 给激活 Skill 的额外强提示文本。 |
| `active_skill` | 当前激活的 Skill 文件夹名，留空表示不激活特定 Skill。 |

### rules.json（运行时生成）

关键词规则配置：

- `default_reply`：默认回复。
- `reply_cooldown_seconds`：冷却时间。
- `rules`：关键词到回复文本的映射列表。

---

## 技术栈

| 用途 | 库 / 工具 |
|------|-----------|
| Windows UI 自动化 | `pywinauto` |
| 剪贴板操作 | `pyperclip` |
| 图像处理 | `Pillow` |
| OCR 文字识别 | `rapidocr_onnxruntime` |
| GUI 界面 | Python 内置 `tkinter` |
| 大模型调用 | 标准 `urllib` / `requests`（HTTP 直连 Agnes Chat API） |
| 打包 | `PyInstaller` |

---

## 工作原理

1. **连接窗口**：通过 `pywinauto` 找到当前前台的聊天窗口句柄。
2. **截取区域**：按配置的 `chat_box` 坐标截取聊天记录区域的屏幕截图。
3. **OCR 识别**：用 `rapidocr` 对截图做文字识别，得到文本和每个文本块的位置坐标。
4. **判断对方消息**：根据 `incoming_side` 配置，筛选出对方那一侧、且位置在最底部的最新 1~3 条消息。
5. **生成回复**：
   - 如果启用 Agnes：把识别到的消息、系统提示词、所有 Skill 内容一起发给 Agnes Chat API，拿回模型回复。
   - 如果未启用或请求失败：走 `rules.json` 的关键词匹配，命中即回复对应文本，否则回默认回复。
6. **发送回复**：通过剪贴板把回复文本粘贴到输入框，模拟回车发送。
7. **循环执行**：按设定的间隔循环上述流程，持续监听新消息。

---

## 常见问题

### Q：连接窗口失败怎么办？

- 确认聊天客户端已登录且聊天窗口在前台，没有最小化。
- 多显示器时，把聊天窗口移到主显示器。
- 点「诊断控件」看能否拿到窗口结构，拿不到说明窗口未正确激活。

### Q：OCR 识别不准怎么办？

- 调整 `chat_box` 坐标，确保截取的是纯聊天记录区域，避开头像、时间戳、输入框。
- 聊天背景太花或字体太小时识别率会下降，可在客户端里调大字体。
- 开启「只预览，不发送」反复测试坐标。

### Q：回复发错对象（自己回复自己）？

- 检查 `incoming_side` 配置，对方在左填 `left`，对方在右填 `right`。
- 在预览模式下确认识别到的最新消息确实来自对方那一侧。

### Q：Agnes 大模型请求失败怎么办？

- 检查 `api_key` 是否正确，`base_url` 是否能访问。
- 点「测试 Agnes」看具体报错。
- 请求失败时程序会自动回退到关键词规则，不会中断。

### Q：rapidocr 安装失败？

- 使用项目根目录的 `install_rapidocr.bat` 或 `install_rapidocr.ps1` 辅助安装。
- 确认 Python 版本是 3.8 及以上、64 位。
- 网络问题可配置国内 pip 镜像源。

### Q：打包后 exe 闪退？

- 用 `console=True` 重新打包看错误信息。
- 确认 `WeChatAutoReply.spec` 里没有把 `numpy` 加进 `excludes`。
- 确认打包时 `assets/`、`skills/`、`agnes_config.json` 都在同级目录。

### Q：Skill 没生效？

- 确认 `SKILL.md` 在 `skills/<skill名>/` 目录下，文件名必须正好是 `SKILL.md`。
- 点「重载规则」重新加载。
- 查看日志里是否提示加载成功。

---

## 开发说明

### 代码结构

主程序集中在 `wechat_auto_reply.py` 一个文件里，主要包含：

- 配置管理类：读写 `agnes_config.json`、`rules.json` 等配置文件。
- 窗口自动化类：封装 `pywinauto` 的窗口查找、截图、控件操作。
- OCR 识别模块：调用 `rapidocr` 识别截图文本。
- 大模型调用模块：HTTP 直连 Agnes Chat API。
- Skill 加载器：扫描 `skills/` 目录，读取 `SKILL.md`。
- GUI 类：`tkinter` 界面，包含配置区、日志区、控制按钮。

### 本地开发

```bash
# 克隆后安装依赖
python -m pip install -r requirements.txt

# 直接运行主程序
python wechat_auto_reply.py

# 调试 OCR 时可查看 debug/ 目录下的截图和原始识别结果
```

### 调试技巧

- 程序会在 `debug/` 目录下保存最后一次截图和 OCR 原始输出，便于排查识别问题。
- `wechat_auto_reply.log` 记录完整运行日志，包括每次识别结果和模型回复。
- 预览模式下不会真正发送，可以放心反复测试。

### 添加新 Skill

在 `skills/` 下新建文件夹，放一个 `SKILL.md`，写清楚：

- 这个 Skill 适用什么场景。
- 期望的回复风格（语气、长度、句式）。
- 常用话术示例。
- 不要做什么（禁忌词、避免的行为）。

保存后点「重载规则」即可生效。

---

## 注意事项

- **本工具不逆向任何聊天协议，不读取客户端数据库**，只通过桌面上已打开的窗口工作，属于本机 UI 自动化。
- **首次使用务必开启「只预览，不发送」**，确认识别和回复都正确后再正式发送，避免误发。
- 不同版本聊天客户端、不同窗口语言和 UI 结构，可能需要点一次「诊断控件」调整坐标。
- **API Key 是敏感信息**，`agnes_config.json` 填入 Key 后不要提交到公开仓库、不要发给别人。仓库的 `.gitignore` 已默认排除该文件。
- 大模型请求失败时，程序会自动回退到关键词规则，保证流程不中断。
- **请勿用于骚扰、营销轰炸、欺诈或违反平台规则的用途**。本工具仅作为个人效率辅助，使用者自行承担一切责任。
- 程序在对方长时间不回复时不会主动发起话题，避免打扰；具体行为可在 `rules.json` 和系统提示词里调整。

---

## License

MIT License，详见 [LICENSE](LICENSE)。
