# AGENTS.md

给在这个仓库里工作的 agent。使用某个 skill 时，读它自己的 `SKILL.md`；这份文件只讲改仓库时的约定。

## 使用 skill

| 需求 | 完整读这个，然后照做 |
|---|---|
| 生命科学论文、技术或草稿写成微信公众号文章，或修改已有的科普草稿 | `wechat-biosci-writer/SKILL.md` |
| 长篇网络小说：开书立纲、日更写作、剧情讨论、角色代入推演、去 AI 味审稿 | `novel-writing/SKILL.md` |

skill 内部的引用路径是相对 skill 根目录写的。`references/quality-gates.md` 里写 `scripts/validate_package.py`，指的是 `wechat-biosci-writer/scripts/validate_package.py`。

## 仓库结构

一个 skill 一个一级目录，根目录只放仓库级文件和 `check.py`。

```
<skill-name>/
  SKILL.md          必需。frontmatter 里的 name 必须和目录名一致
  references/       按需加载的长内容
  assets/           模板、样式等静态文件
  scripts/          可运行的检查和工具
  tests/            scripts/ 的测试
  agents/           平台专属适配，可选
```

只有 `SKILL.md` 是必需的，其余按 skill 的实际需要存在。skill 自包含：软链目录就是完整安装。

## 加一个新 skill

1. 建 `<skill-name>/SKILL.md`，写好 `name` 和 `description` 的 frontmatter，`name` 与目录名一致。
2. 每轮都加载的是 `SKILL.md`，所以它要短。长内容放 `references/`，在 `SKILL.md` 里留一行指针说明什么时候去读。
3. 能机械核验的规则写成 `scripts/` 里的脚本，不要写成段落。脚本不进上下文，agent 只运行它；散文每轮都占 token，而且挡不住模型在赶时间时跳过。
4. `scripts/` 有测试就放 `tests/`。`check.py` 按约定找得到，无需改动它。
5. README 的技能表里加一行。

## 提交与版本约定

- 新 skill 放在独立的一级子目录中。
- 修改单个 skill 时，只暂存并提交该目录，以及与这次改动直接相关的仓库级说明，别的不带。
- 本地备份、验证临时文件、凭据和私钥不进 Git。`.gitignore` 覆盖了常见路径，其余在推送前自己确认。
- 推送前跑 `python check.py`，所有 skill 都要通过。
- 行尾在仓库里和检出时都是 LF（`.gitattributes`）。脚本要在别人的机器上跑，CRLF 会破坏 shebang。

## 写作规范

以下针对 agent 会读的文本，也就是 `SKILL.md`、`references/` 和这份文件。

1. **`SKILL.md` 保持短。** 它每轮都在上下文里，每一行都在持续付费。新增细节进 `references/`，在 `SKILL.md` 的索引里加一行指针。只有部分分支会用到的内容放指针后面，不要内联。
2. **先改指针措辞，再考虑内联。** agent 没去读某个 reference 时，问题几乎总出在指向它那句话的写法上。
3. **能写成脚本的别写成段落。**
4. **一个含义只写一处。** 术语可以反复用（`快评`、`深解`、`发布包`），术语背后的解释不要重复写。重复的规则是维护负担，还会虚抬它的分量。
5. **说该做什么，别只说不许做什么。** 禁令会把被禁的行为拉进上下文反而更显眼。只有无法正面表述的硬护栏才用禁令，且要配上正面目标。
6. **删掉无效指令。** 模型本来就会做的事，写进去只花 token 不改变行为。有分歧就跑一遍文档来判定，不要靠争论。
7. **`scripts/` 不引入第三方依赖。** 标准库能做就用标准库，方便在任何机器上直接跑。
8. **程序输出用 ASCII。** Windows 控制台和部分终端会把排印符号显示成乱码。Markdown 正文不受此限。
9. **有出处的写出处。** 引用到的方法、模板和数据注明来源和适用许可。

## 提交前

```bash
python check.py
```

两个 skill 都要通过。改了 skill 的散文，顺带确认 README 的技能表还准确。
