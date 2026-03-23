# MXTerm

MXTerm 是一个跨平台 Shell 增强工具。它接入现有的 `zsh`、`bash`、`PowerShell`，在保留原生命令体验的同时，增加自然语言转命令、安全校验、会话上下文、agent 规划能力，以及 Ollama 本地模型接入。

[English](README.en.md)

## 支持平台

- macOS：优先支持 `zsh`，兼容 `bash`
- Linux：优先支持 `bash`，兼容 `zsh`
- Windows：优先支持 PowerShell 7+，基础支持 Windows PowerShell 5.1

只要终端程序启动的是受支持的 Shell，安装后都可以使用 MXTerm，例如：

- Terminal.app
- iTerm2
- GNOME Terminal
- Windows Terminal
- VS Code Terminal

## 安装

### 推荐方式：`pipx`

```bash
pipx install mxterm
mxterm config init
mxterm install --shell auto
```

### 现在即可从 GitHub 安装

如果你还没有发布到 PyPI，可以直接从当前仓库安装：

```bash
pipx install git+https://github.com/ziguishian/mxterm.git
mxterm config init
mxterm install --shell auto
```

### 本地开发安装

```bash
python -m pip install -e .[dev]
mxterm config init
mxterm install --shell auto
```

### 一键安装脚本

```bash
curl -fsSL https://raw.githubusercontent.com/ziguishian/mxterm/main/scripts/install/install.sh | sh
```

```powershell
irm https://raw.githubusercontent.com/ziguishian/mxterm/main/scripts/install/install.ps1 | iex
```

### 二进制发布包

GitHub Releases 可以提供：

- `mxterm-macos-universal.tar.gz`
- `mxterm-linux-x86_64.tar.gz`
- `mxterm-windows-x64.zip`

## 快速开始

1. 安装 MXTerm
2. 运行 `mxterm install --shell auto`
3. 重启终端，或重新加载对应 profile
4. 直接输入自然语言，或使用 `mx` 显式调用

示例：

```bash
帮我看看当前目录有哪些文件
mx 帮我安装这个项目的依赖
gti status
```

## 常用命令

```bash
mxterm doctor
mxterm doctor --json
mxterm help
mxterm config init
mxterm config path
mxterm config show --json
mxterm install --shell auto
mxterm uninstall --shell auto
mxterm hooks path --shell bash
mxterm hooks refresh --shell bash
mxterm hooks show --shell zsh
mxterm hooks doctor --shell zsh
mxterm model list
mxterm model current
mxterm model use qwen3:14b
mxterm permission current
mxterm permission use high
mxterm resolve --shell bash --cwd "$PWD" --input "show files here"
mxterm explain --shell powershell --cwd . --input "帮我查看当前目录"
mxterm run --shell powershell --cwd . --input "帮我看看当前目录" --yes
mxterm history
mxterm session
mxterm reset-session
mxterm runtime
mxterm logs path
mxterm logs tail -n 20
mxterm logs clear
mxterm self-update
```

## 工作方式

- 如果输入本身已经是合法命令，MXTerm 直接放行
- 如果输入更像自然语言，MXTerm 会调用 Ollama 进行翻译
- 所有自然语言请求默认都会经过 agent 决策层
- 简单请求通常会退化成单步执行
- 多步骤请求会生成一个短计划，再进入确认和执行流程
- 执行前会先做本地风险扫描

## 帮助命令

运行 `mxterm help` 可以看到：

- MXTerm 能处理哪些任务
- 推荐的自然语言示例
- 当前配置中的模型名
- 常用的诊断、历史、hook、自定义模型命令

## 模型管理

MXTerm 会把当前使用的 Ollama 模型保存在配置文件中。

- `mxterm model list`：查看已安装模型，并高亮当前配置模型
- `mxterm model current`：显示当前配置模型
- `mxterm model use <name>`：切换到另一个已安装模型
- `mxterm model use <name> --force`：即使 Ollama 当前不可达，也强制写入配置

## 安全机制

当前版本会检测以下高风险模式：

- `rm -rf`
- `shutdown` / `reboot`
- `mkfs`
- `dd`
- `format`
- 覆盖系统关键路径
- 链式命令和提权命令

默认策略：

- 低风险 AI 命令可直接执行
- 中风险命令需要确认
- 高风险命令默认阻断

权限级别：

- `low`：每一条可执行动作都要确认；多步 agent 会逐步确认
- `medium`：默认平衡模式；按风险和路由决定是否确认
- `high`：允许的命令直接执行，不弹确认

MXTerm 还会把执行日志写入 JSONL 文件，例如：

- Windows：`%LOCALAPPDATA%\\MXTerm\\logs\\mxterm.log.jsonl`
- macOS / Linux：`~/.local/state/MXTerm/logs/mxterm.log.jsonl`

## Shell 接入说明

- `zsh` 会安装自定义 `accept-line` widget，在按下 Enter 时优先接管未解析输入
- `bash` 会通过 Readline 的 `bind -x` 在 Enter 时优先接管未解析输入
- PowerShell 优先使用 PSReadLine 的 Enter 拦截，同时保留 `mx` 显式入口
- 所有生成的 hook 都会写入会话标记，例如 `MXTERM_HOOK_ACTIVE`
- `mxterm hooks doctor --shell <name>` 会同时检查 hook 文件和当前会话是否真的已加载
- 当自然语言请求进入 Ollama 时，shell hook 会显示当前模型名和加载动画
- 如果 Ollama 没有返回可执行命令，MXTerm 会提示你重新输入，而不是伪造命令
- 删除类请求在可解析目标时，会先展示命中预览，再进入确认流程
- 所有自然语言请求都会走 agent 层
- `mxterm run` 在执行 agent 计划时，会先做本地预检查，并支持分步确认和失败重试
- `cd` 这类会改变当前终端状态的动作，会在当前 Shell 会话内执行

## 配置

默认配置示例：

```toml
[ollama]
host = "http://127.0.0.1:11434"
model = "qwen3:8b"
timeout_seconds = 60

[shell]
preferred = "auto"
confirm_mode = "auto_low_risk" # auto_low_risk | always | never
auto_capture = true
auto_capture_mode = "smart"    # smart | natural_language | always
explicit_command = "mx"
show_banner = true

[safety]
dry_run = false
block_high_risk = true
preview_ai_commands = true
permission_level = "medium"

[agent]
enabled = true
max_steps = 5
preflight_checks = true
confirm_each_step = true
retry_on_failure = true
max_retries = 1
```

自动接管模式：

- `smart`：接管自然语言和大多数未解析的多词输入
- `natural_language`：只接管明显的自然语言请求
- `always`：更激进，优先把未解析输入交给 MXTerm

Agent 行为：

- 当 `agent.enabled = true` 时，所有自然语言请求都会通过 agent 规划器
- 小任务通常会生成一条可执行命令和一个简短计划摘要
- 大任务会展开成多步计划，并在执行前要求确认
- `preflight_checks` 会在多步计划开始前检查本地命令和目标目录
- `confirm_each_step` 可以让 MXTerm 在多步计划里逐步确认
- `retry_on_failure` 和 `max_retries` 用来控制失败步骤的本地重试
- 如果你想回到旧的单命令翻译路径，可以把 `agent.enabled = false`

常用查看命令：

```bash
mxterm help
mxterm config path
mxterm config show --json
mxterm history
mxterm session
mxterm runtime
mxterm logs tail -n 20
mxterm model list
mxterm model current
mxterm model use qwen3:14b
mxterm permission current
mxterm permission use high
mxterm hooks refresh --shell zsh
mxterm hooks doctor --shell zsh
```

## 单次执行模式

如果你还没有安装 hook，也可以直接单次执行：

```bash
mxterm run --shell powershell --cwd . --input "帮我看看当前目录" --yes
```

## 开发与测试

```bash
python -m pip install -e .[dev]
pytest
```

## 发布能力

当前发布脚本和工作流已经支持：

- 为 macOS、Linux、Windows 构建 PyInstaller 二进制
- 打包平台归档文件
- 为每个平台生成包含体积和 SHA-256 的 manifest 文件
- 在版本 tag 上上传 GitHub Release 资产和 Python 发行包

## 当前限制

- 暂未支持 `fish`、`nushell`、`cmd.exe`
- `zsh` / `bash` 的 Enter 自动接管依赖交互式 shell 和 `zle` / `readline`
- 当前版本不是完整 PTY 终端模拟器
- 当你后续发布到 PyPI 后，可以把安装脚本默认安装源切回 `pipx install mxterm`
