# My Skills

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Agents](https://img.shields.io/badge/agents-Claude%20Code%20%C2%B7%20Codex%20%C2%B7%20opencode-6c5ce7.svg)](#安装)

面向多种 Agent 的技能集合。每个一级子目录是一个可独立使用、修改和验证的 skill；核心流程使用通用 `SKILL.md`、`references/`、`assets/` 和 `scripts/`，平台专属元数据只作为可选适配层。

## 当前技能

| Skill | 做什么 |
|---|---|
| [`wechat-biosci-writer/`](wechat-biosci-writer/) | 将生命科学论文、技术或草稿写成「快评」或「深解」两级微信公众号文章，并生成兼容微信发布流程的完整文章包 |
| [`novel-writing/`](novel-writing/) | 长篇网络小说创作协作，覆盖开书立纲、日更写作、剧情讨论修改、角色代入推演，并提供选题扫榜和审稿去 AI 味检查 |
| [`cross-agent-review/`](cross-agent-review/) | 跨 agent 工作审查：请求方把刚完成的工作写成带锚点的审查请求，审查方按风险分层核对并产出分级审查结果 |
| [`opencode/`](opencode/) | 仅在用户明确要求时，由 Codex 优先、兼容其他终端 Agent 调用本机 OpenCode，支持模型、推理强度、会话恢复和低上下文长任务管理 |
| [`draw-complex-interactions/`](draw-complex-interactions/) | 为小分子、核酸、修饰、离子及大分子界面生成可追溯的局部二维互作图或残基网络图 |
| [`my-academic-ppt/`](my-academic-ppt/) | My Academic PPT：制作图文充实、技术路线清晰、适合跨专业听众的科研汇报PPT，提供讲稿、布局指南及结构核验 |

## 安装

```bash
git clone https://github.com/SPYfighting/my-skills.git
```

Claude Code / opencode，软链你要用的那个 skill：

```bash
ln -s "$PWD/my-skills/wechat-biosci-writer" ~/.claude/skills/wechat-biosci-writer
```

Windows 上若没开开发者模式，用复制代替：

```powershell
Copy-Item -Recurse -Force .\wechat-biosci-writer "$env:USERPROFILE\.claude\skills\wechat-biosci-writer"
```

Codex 及其他只读 `AGENTS.md` 的 agent，把 skill 目录放进项目里，然后在项目的 `AGENTS.md` 里写一句指向 `<目录>/SKILL.md` 的说明。

skill 是自包含的：目录里的东西就是它需要的全部，所以软链目录就是完整安装。

## 自检

```bash
python check.py
```

按约定找出每个 skill 自带的验证并跑一遍：`tests/` 交给 pytest（没有 pytest 时退回 unittest），`scripts/` 下的 `.py` 和 `.js` 做语法检查，同时确认 `SKILL.md` 的 frontmatter 里 `name` 和目录名一致。没有任何可运行内容的 skill 会被报为「未验证」，不会静默通过。

加新 skill 不用改 `check.py`。

## 约定

仓库结构、加新 skill 的步骤、提交与版本规则、以及给 agent 的写作规范都在 [`AGENTS.md`](AGENTS.md)。

## 许可

MIT，见 [LICENSE](LICENSE)。skill 里引用到的外部方法、模板和数据各自适用其自身许可。
