# 聊天自动回复小工具

一个本机 Windows 桌面小工具，通过桌面自动化读取当前聊天窗口里的最新文本消息，并按规则或大模型自动回复。

支持两种回复模式：
- **关键词规则模式**：按 `rules.json` 的关键词匹配回复
- **大模型模式**：接入 Agnes Chat API，结合本地 Skill 生成自然回复

## 功能特性

- 🤖 **双模式回复**：关键词规则 + Agnes 大模型
- 📚 **Skill 系统**：可插拔的话术风格包，针对不同对象使用不同语气
- 🎯 **OCR 识别**：基于 RapidOCR，支持坐标过滤对方消息
- 🔍 **UIA 控件识别**：备选方案，兼容性更强
- 💾 **聊天记忆**：每个聊天对象独立记忆最近 30 条对话
- 📝 **承诺备忘**：自动提取对话中做出的承诺并保存
- 🎨 **主题切换**：内置多套主题，实时切换
- 📖 **内置教程**：详细使用说明，新手友好

## 快速开始

### 方式一：直接运行（需要 Python 环境）

1. **安装 Python 3.8+**
   - 到 https://www.python.org/downloads/ 下载安装
   - 安装时勾选 "Add Python to PATH"

2. **克隆仓库**
   ```bash
   git clone https://github.com/你的用户名/wechat-auto-reply.git
   cd wechat-auto-reply
   ```

3. **安装依赖**
   - 双击 `install_rapidocr.bat` 安装 OCR 依赖
   - 或手动运行：`pip install -r requirements.txt`

4. **启动程序**
   - 双击 `start.bat`
   - 或运行：`python wechat_auto_reply.py`

### 方式二：打包成 exe（无需 Python 环境）

1. 完成上述步骤 1-3
2. 双击 `build_app.bat` 打包
3. 打包完成后，exe 在 `dist\WeChatAutoReply.exe`
4. 把 exe 分发给朋友即可（朋友需要自己安装 OCR 依赖，见下文）

## 首次配置

### 1. 校准坐标

程序需要知道聊天窗口中关键元素的位置：

1. 打开聊天窗口，让它显示在前台
2. 在程序中点击「校准发送」
3. 按提示点击输入框位置
4. 拖框选择聊天记录区域
5. 选择对方消息所在侧（左侧/右侧）

坐标会保存到 `agnes_config.json`。

### 2. 配置大模型（可选）

如果要用大模型回复：

1. 到 Agnes 平台创建 API Key
2. 在程序中勾选「使用 Agnes 大模型」
3. 填写：
   - **Base URL**：`https://apihub.agnes-ai.com/v1`
   - **模型**：`agnes-2.0-flash`
   - **API Key**：你的 Agnes Key
4. 点击「保存 Agnes 配置」
5. 点击「测试 Agnes」，日志显示成功即可

### 3. 选择 Skill

在「Skill 管理」页面：
- 点击某个 Skill 卡片锁定它
- 锁定后该 Skill 的话术风格会被注入到大模型提示词中
- 同一时刻只能锁定一个 Skill

## Skill 系统

Skill 是可插拔的话术风格包，每个 Skill 是 `skills/` 目录下的一个子文件夹，里面有一个 `SKILL.md` 文件。

### 目录结构

```
skills/
├── chat-with-crush/         # 和暗恋对象聊天
├── chat-with-friends/       # 和朋友聊天
├── chat-with-partner/       # 和伴侣聊天
├── chat-with-strangers/     # 和陌生人聊天
├── reply-to-leader/         # 回复领导
└── wechat_reply_assistant/  # 通用回复助手
```

### SKILL.md 格式

```markdown
---
name: skill-name
description: 一句话描述这个 Skill 的用途
trigger_words: [关键词1, 关键词2]
---

# Skill 内容

这里写具体的指令、话术、注意事项等。
```

### 添加自定义 Skill

1. 在 `skills/` 下新建文件夹（英文名，用连字符）
2. 创建 `SKILL.md`，按上述格式填写
3. 在程序中点击「重载规则」即可生效

## 项目结构

```
wechat-auto-reply/
├── wechat_auto_reply.py      # 主程序源码
├── agnes_config.json         # 大模型配置（.gitignore 已排除）
├── requirements.txt          # Python 依赖
├── WeChatAutoReply.spec      # PyInstaller 打包配置
├── build_app.bat             # 打包脚本
├── start.bat                 # 启动脚本
├── install_rapidocr.bat      # OCR 依赖安装
├── install_rapidocr.ps1      # PowerShell 安装脚本
├── assets/                   # 图标和 Logo
│   ├── app_icon.ico
│   └── app_logo.png
├── skills/                   # Skill 目录
└── README.md                 # 本文档
```

## 打包指南

### 打包成 exe

1. 确保 Python 3.8+ 已安装
2. 双击 `build_app.bat`
3. 等待打包完成（约 3-5 分钟）
4. exe 输出在 `dist\WeChatAutoReply.exe`

### 分发给朋友

朋友拿到 exe 后，需要：

1. 安装 Python 3.8+（用于安装 OCR 依赖）
2. 把 `install_rapidocr.bat` 和 `install_rapidocr.ps1` 也发给朋友
3. 朋友双击 `install_rapidocr.bat` 安装 OCR 依赖
4. 双击 `WeChatAutoReply.exe` 运行

### 上传到 GitHub Release

1. 在 GitHub 仓库页面点 **Releases → Create a new release**
2. Tag 输入 `v1.0`
3. 把 `WeChatAutoReply.exe`、`install_rapidocr.bat`、`install_rapidocr.ps1` 拖到附件区
4. 发布 Release

## 配置文件说明

| 文件 | 用途 | 是否上传 GitHub |
|------|------|----------------|
| `agnes_config.json` | 大模型配置（含 API Key） | ❌ 已排除 |
| `chat_memory.json` | 聊天记忆 | ❌ 已排除 |
| `contacts.json` | 联系人列表 | ❌ 已排除 |
| `promises.json` | 承诺备忘 | ❌ 已排除 |
| `rules.json` | 关键词规则 | ❌ 已排除 |
| `theme.json` | 主题设置 | ❌ 已排除 |

`.gitignore` 已自动排除这些文件，防止泄露敏感数据。

## 技术栈

- **Python 3.8+**
- **Tkinter**：GUI（纯 Canvas/Frame 自绘，无第三方 UI 库）
- **pywinauto**：Windows 桌面自动化
- **RapidOCR**：OCR 文字识别
- **Pillow**：图像处理
- **pyperclip**：剪贴板操作
- **PyInstaller**：打包成 exe

## 工作原理

```
聊天窗口 → 截图 → OCR 识别 → 坐标过滤对方消息 → 去重 → 大模型/规则 → 回复
                ↓
        UIA 控件识别（备选）
```

1. **截图**：截取聊天记录区域
2. **OCR 识别**：用 RapidOCR 识别文字和坐标
3. **坐标过滤**：根据对方消息所在侧（左/右）过滤
4. **去重**：用 canonical 比较避免重复回复
5. **生成回复**：调用 Agnes 大模型 或 匹配关键词规则
6. **发送**：自动粘贴到输入框并发送

## 常见问题

### Q: OCR 识别不出来中文？

A: 运行 `install_rapidocr.bat` 安装 OCR 依赖。如果还是不行，检查网络（脚本会尝试清华镜像和官方 PyPI）。

### Q: 切换聊天对象后还是回复旧消息？

A: 程序会自动预标记可见消息为已处理。如果还有问题，点击「重置记忆」清空去重列表。

### Q: 大模型请求失败？

A: 检查 API Key 是否正确，网络是否通畅。失败时会自动回退到关键词规则模式。

### Q: 打包后 exe 闪退？

A: 确保打包时没有排除 numpy。`WeChatAutoReply.spec` 的 `excludes` 只能包含 `psutil`、`pip`、`setuptools`。

### Q: 如何修改主题？

A: 在程序侧边栏点「主题外观」，选择喜欢的主题即可。主题会保存到 `theme.json`。

## 开发说明

### 修改源码

直接编辑 `wechat_auto_reply.py`。源码约 4000 行，主要模块：

- `ChatMemory`：聊天记忆管理
- `AgnesConfig`：大模型配置
- `App`：主窗口和业务逻辑
- `RoundedButton`：自绘圆角按钮
- `Card`：卡片容器组件

### 添加新功能

建议在 `App` 类中添加新方法。新菜单项注册流程：

1. 在 `nav_items` 列表添加新项
2. 创建对应的页面 Frame
3. 在 `pages` 字典注册
4. 在 `titles` 字典注册标题
5. 实现 `_build_xxx_page` 方法

## 注意事项

- ⚠️ 这个工具**不逆向聊天软件协议**，**不读取聊天数据库**，只通过桌面上已打开的窗口工作
- ⚠️ 首次使用建议开启「只预览，不发送」，避免误发
- ⚠️ API Key 是敏感信息，不要把带 Key 的 `agnes_config.json` 发给别人
- ⚠️ 不建议用于骚扰、营销轰炸或违反平台规则的用途
- ⚠️ 请遵守当地法律法规，理性使用

## License

MIT License - 详见 [LICENSE](LICENSE)
