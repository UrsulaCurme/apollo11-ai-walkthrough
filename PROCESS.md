# PROCESS.md — 本演练的构建过程

_使用 AI 分析 Apollo 11 AGC 源代码的完整记录，包括每一个提示词、每一个工具决策以及每一个错误。_

---

## 项目目标

1. **记录** Apollo 11 AGC 源代码，使现代开发者能够理解
2. **证明** 没有任何代码库因为太古老或太晦涩而无法进行 AI 辅助分析
3. **发布** 以 GitHub 上的 markdown 文件形式呈现演练内容
4. **撰写** 一篇关于该方法论的博客文章，发布于 [The AI Realist](https://juliensimon.substack.com/)

## 使用的工具

- **Claude Code**（Anthropic）— 主要分析工具，针对克隆的代码仓库运行
- **Claude.ai**（Opus）— 用于项目规划、提示词设计和编辑审查
- **GitHub** — 托管演练内容和原始源代码仓库
- **Virtual AGC Assembly Language Manual** — 主要架构参考资料

## 时间线

| 日期 | 阶段 | 状态 |
|------|-------|--------|
| 2026-03-26 | 项目设置、参考资料收集、第 1 阶段提示词 | ✅ |
| 2026-03-26 | 第 2 阶段：代码仓库结构侦察 | ✅ |
| 2026-03-26 | 第 3 阶段：深度分析 — BURN_BABY_BURN、Executive、Restart | ✅ |
| 2026-03-27 | 第 3 阶段：深度分析 — 着陆制导、解释器、等待列表、Executive（重新运行）、DSKY | ✅ |
| 2026-03-27 | 第 4 阶段：综合分析 | ✅ |
| 2026-03-27 | 第 5 阶段：质量检查 | ✅ |
| 2026-03-27 | 第 6 阶段：博客文章、审查、发布 | ✅ |

---

## 第 0 阶段：研究与规划（2026-03-26）

### 我做了什么

首先询问是否已有人对 Apollo 11 源代码进行过 AI 辅助演练。经过大量搜索——未发现先例。已有不少人工撰写的解说文章（Simon Allardice 的 Pluralsight 课程、Borja Sotomayor 关于 FLAGORGY 的 Medium 文章、BrightCoding 概述），但没有人系统地将该代码库输入 LLM 进行分析。

### 确定的主要参考资料

1. **Virtual AGC Assembly Language Manual** — `https://www.ibiblio.org/apollo/assembly_language_manual.html`
   - 这是权威参考资料。由 Ron Burkey 撰写，他构建了 Virtual AGC 模拟器。涵盖完整的 Block II 指令集、内存映射、解释器语言和 I/O 通道
   - 源自 MIT 原始文档：E-2052（Savage & Drake，1967 年）和 AGC4 备忘录 #9（Blair-Smith，1966 年）

2. **Wikipedia AGC 条目** — 完整的指令集摘要表，适合交叉参考

3. **Charles Averill 的《AGC 简要分析》** — 简洁的现代参考资料，引用了 Blair-Smith 备忘录和 Burkey 的手册

4. **Borja Sotomayor 的 Medium 文章** — 解释了解释器的压缩指令格式（7 位操作码、15 位地址）以及为何子程序库方式被放弃

### 为何该项目重要

AGC 代码是公共领域资源，晦涩程度令大多数开发者难以解读，AI 角度也真正具有创新性。该代码在最坏情况下考验了 AI 的代码理解能力：没有语法高亮、没有语言服务器、已淘汰的架构、1 的补数算术、定点数学，以及 1966 年的命名约定。如果 Claude Code 能够驾驭这些，那么"AI 只能处理现代语言"的质疑便不攻自破。

---

## 第 1 阶段：上下文提示词设计（2026-03-26）

### 问题

Claude Code（以及所有 LLM）的训练数据绝大多数来自现代代码——x86、ARM、C、Python、JavaScript。AGC4 汇编是一门几乎没有出现在训练数据中的死语言。若缺乏架构背景，模型将会：
- 假设使用 2 的补数算术（AGC 使用 1 的补数）
- 将 CCS 误解为简单的条件跳转（实际上是带 DABS 的四路跳过）
- 忽略 TS 溢出跳过模式（主要的溢出处理惯用法）
- 混淆 AGC 原生指令与解释器伪指令
- 无法理解存储体切换

### 解决方案

构建了一个约 3,500 字的上下文提示词，预先加载关键架构知识。来源：Virtual AGC Assembly Language Manual，与 Wikipedia 及 MIT 原始文档交叉参考。

### 提示词结构

第 1 阶段提示词（`prompts/phase1-context.md`）包含：

1. **硬件概述** — 字长、算术模型、时钟频率、内存大小
2. **数据表示** — SP/DP/TP 格式、小数缩放、双零问题
3. **中央寄存器** — A、L、Q、EB、FB、Z、BB 以及地址 07 处的硬连线零
4. **编辑寄存器** — CYR、SR、CYL、EDOP 及其自动转换行为
5. **计数器/定时器寄存器** — TIME1-6、CDU、PIPA 及其中断触发
6. **内存映射** — 4 个内存区域、存储体切换、重叠区域
7. **中断系统** — 全部 11 个向量、屏蔽、延迟条件、保存/恢复协议
8. **基本指令集** — 每条原生操作码及其八进制编码和行为说明
9. **扩展码** — 所有 EXTEND 前缀指令
10. **派生指令** — RETURN、NOOP、COM、RESUME、INHINT、RELINT 等别名
11. **解释器** — TC INTPRET 如何切换模式、压缩操作码格式、关键伪指令
12. **源代码格式** — 注释语法、文件包含、标签约定
13. **两个程序** — Comanche055（CM）与 Luminary099（LM），各自的职责
14. **分析规则** — 6 条具体指令，说明如何分析每个文件

### 设计决策

- **包含八进制编码**：若缺少这些，Claude Code 无法验证源代码中的原始数字操作数
- **明确指出 TS 跳过和 CCS 四路分支**：这些是 AGC 的 if/else 和 switch——若不理解它们，控制流分析将无从展开
- **省略伪操作符表**：ERASE、EQUALS、2DEC、SETLOC、BANK 等对汇编器工作很重要，但对演练来说会增加噪音，可按需查阅
- **省略完整 I/O 通道映射**：同样的理由。通道 5-7 用于存储体切换，已涵盖；其余可按需获取
- **以方法论结尾，而非仅是参考资料**：6 条分析规则给了 Claude Code 一套*流程*，而不仅仅是数据

### 需要注意的事项

尽管有上下文，模型仍可能在以下已知风险领域出现问题：
- 存储体切换逻辑（FB/EB/BB/超存储体交互）
- 解释器通过 EDOP 寄存器进行压缩操作码解码
- 定点缩放约定（隐式二进制点追踪）
- 中断时序及"非编程序列"（PINC、MINC 等）
- DSKY 动词/名词显示系统

---

## 第 2 阶段：代码仓库结构侦察

### 使用的提示词

```
Clone https://github.com/chrislgarry/Apollo-11. Map the repo structure. For both 
Luminary099/ and Comanche055/, list every .agc file with its stated purpose from 
the header comments. Group them into functional categories: navigation, guidance, 
propulsion control, DSKY interface, executive/scheduler, restart/fault handling, 
math/utility. Output a markdown table.
```

### 结果

_执行后填写。_

### 观察

_执行后填写。_

---

## 第 3 阶段：深度分析

### 模块选择依据

根据叙事价值与技术深度选择了 5 个关键文件：

1. **FRESH_START_AND_RESTART.agc** — 拯救 Apollo 11 的代码（1202 警报）。最具戏剧性价值
2. **LUNAR_LANDING_GUIDANCE_EQUATIONS.agc** — P63/P64/P66，实际的着陆数学计算。技术核心
3. **BURN_BABY_BURN--MASTER_IGNITION_ROUTINE.agc** — 发动机点火 + 文化彩蛋。人文兴趣
4. **EXECUTIVE.agc + WAITLIST.agc** — 作业调度器。展示"隐藏的操作系统"。架构故事
5. **INTERPRETER.agc** — 机器中的虚拟机。计算机科学故事

### 使用的提示词

完整提示词见 `prompts/phase3-deep-dives.md`。每条提示词都通过 `claude -p` 注入 Claude Code，以第 1 阶段上下文 + 缓存的 AGC 手册作为系统上下文。

### 运行日志

所有运行均通过 Claude Code CLI 使用 **claude-opus-4-6**（带扩展思考的 Opus 4.6）。

| 深度分析 | 源文件 | 提示词大小 | 输出 | 时间 | 备注 |
|------|-------------|-------------|--------|------|-------|
| 3d BURN_BABY_BURN | 22K 字符 | 97K 字符 | 29K 字符 | 222 秒 | 首次运行失败（329 字符）——Claude 试图写入文件而非响应。修改提示词为"直接以 markdown 形式响应" |
| 3a Executive | 12K 字符 | 87K 字符 | 30K 字符 | 225 秒 | 从合并的 Executive+Waitlist 拆分后重新运行 |
| 3a2 Waitlist | 15K 字符 | 90K 字符 | 33K 字符 | 243 秒 | 正常运行 |
| 3b Restart/1202 | 33K 字符 | 108K 字符 | 33K 字符 | 232 秒 | 正常运行 |
| 3c 着陆制导 | 32K 字符 | 108K 字符 | 57K 字符 | 401 秒 | 最长输出——1,419 行 |
| 3e 解释器 | 75K 字符 | 160K 字符 | 39K 字符 | 273 秒 | 最大输入（INTERPRETER.agc 共 3,075 行） |
| 3f DSKY/Pinball | 130K 字符 | 207K 字符 | 40K 字符 | 346 秒 | 两个源文件共约 4,700 行 |
| 综合分析 | 所有演练文件 | 264K 字符 | 38K 字符 | 792 秒 | 将全部 7 个演练文件作为输入 |
| **合计** | | | **~299K 字符** | **~47 分钟** | |

### AI 做对了什么

- **指令语义。** CCS 四路跳过、TS 溢出跳过、INDEX 修改——在每个文件中均被正确识别和解释
- **控制流追踪。** BURN_BABY_BURN 中的虚表模式、EXECUTIVE 中的 EJSCAN 优先级扫描、WAITLIST 中的 T3RUPT 分发链——均通过实际指令序列准确追踪
- **文化典故。** 每一处拉丁铭文、文学典故和程序员笑话均被识别并语境化（HONI SOIT QUI MAL Y PENSE、NOLI SE TANGERE、EXTIRPATE、ASSASSINATE CLOKTASK、GOTOPOOH）
- **解释器架构。** EDOP 寄存器作为硬件操作码解包器、压缩的 7+7+1 位格式、三级分发级联——均被正确解释
- **现代类比。** FreeRTOS 对比表、崩溃即设计（Candea/Fox 2003）、Erlang"让它崩溃"、DSPTAB 的虚拟 DOM 类比——均言之有物，而非流于表面
- **诚实的不确定性。** 解释器演练明确标注了不确定的解释（存储码编码、POLY 系数验证、下推溢出保护）

### AI 做错了什么

1. **BURN_BABY_BURN 首次运行只产生了 329 字符。** Claude Code 试图使用文件写入工具而非响应到标准输出。响应内容竟是"文件写入一直被权限阻止"。根本原因：提示词中写了"不要使用任何工具"，这让模型误以为也无法输出文本。修复方式：将提示词改为"直接在文本响应中输出完整的 markdown 文档"。

2. **核心组数量歧义（7 与 8）。** Executive 演练最初表示 `DEC 7` 意味着"共 8 组核心"（将其解释为 CCS 循环计数器）。Waitlist 和综合分析则表示"7 组核心"。两种解释均有据可依——共有 7 个可调度槽位加上正在运行作业的寄存器。统一为"7 组核心用于待处理/休眠作业"。

3. **I/O 通道 14 的描述。** BURN_BABY_BURN 演练将通道 14 描述为"控制 DPS 油门"——过于简化。通道 14 是一个多功能输出通道，同时处理 IMU CDU 驱动、陀螺仪活动和发动机命令。第 4 位具体是发动机开启命令。已更正为更精确的描述。

4. **"世界上最早的动词-名词命令行界面。"** DSKY 演练提出了这一强烈主张。鉴于日期（DSKY 于 1966 年投入飞行，早于 Unix shell）可以辩护，但无法证明是"最早的"。已软化为"最早的之一"。

5. **首次尝试超时。** 最初的 900 秒超时对于带扩展思考的 Opus 4.6 进行复杂分析来说太短。第一次 BURN_BABY_BURN 运行在 890 秒时超时。已增加至 1800 秒。

### 已应用的更正

所有更正记录于 `QUALITY_CHECK.md`。摘要：
- 修正了 01-executive.md 中的标题行数（600 → ~500）
- 软化了 07-dsky-interface.md 中的"世界上最早的"说法
- 在 05-burn-baby-burn.md 中阐明了 I/O 通道 14 的描述
- 统一了各文件中核心组数量的表述

---

## 第 4 阶段：综合分析

### 使用的提示词

将全部 7 个已完成的演练文件及第 1 阶段上下文作为输入。提示词要求围绕三个主题进行综合分析：（1）AGC 做对了哪些我们已经遗忘的事；（2）约束条件迫使产生了什么；（3）哪些内容会让现代开发者感到惊讶。输出：`walkthrough/08-lessons.md`，273 行，38K 字符，792 秒。

### 确定的关键主题

- 协作式多任务作为绿色线程（Go goroutine、Python asyncio）
- 检查点/重启作为崩溃即设计（比 Candea/Fox 2003 和 Erlang 早数十年）
- 解释器作为最早的字节码虚拟机之一
- 动词-名词作为原始命令行界面（DSPTAB 脏标志作为原始虚拟 DOM）
- 固定池分配与动态分配——"最坏情况是可知的"

---

## 第 5 阶段：博客文章

### 角度

"我用 AI 走读了将人类送上月球的代码。以下是发生的事情。"

文章应展示：
- 使其正常工作所需的提示词工程（第 1 阶段上下文）
- AI 做对了什么（在陌生汇编中的模式识别、跨模块交叉参考）
- AI 做错了什么（具体示例及更正）
- AGC 代码揭示了哪些我们已遗忘的软件工程知识
- 为何这对"AI 取代开发者"的讨论很重要——AI 作为*阅读*工具，而非写作工具

### 目标

Substack（The AI Realist）+ LinkedIn 推广。可能配有 YouTube 视频。

### 草稿

见 `blog/blog-post.md`。

---

## 第 6 阶段：审查与发布

### 事实核查方法

将 AI 输出与以下内容交叉核对：
- Virtual AGC Assembly Language Manual（ibiblio.org）
- Wikipedia AGC 条目（指令集表、硬件规格）
- 运行日志数据（scripts/run_log.jsonl）
- 全部 8 个演练文件的内部一致性

完整结果见 `QUALITY_CHECK.md`。

### 更正日志

见上方第 3 阶段中的"已应用的更正"。发现并修复了五个问题：
1. 首次 BURN_BABY_BURN 运行时的工具使用混乱（提示词修复）
2. 核心组数量歧义 7 与 8（已统一）
3. I/O 通道 14 过度简化（已阐明）
4. "世界上最早的"命令行界面说法（已软化）
5. Opus 4.6 超时时间过短（已增加）

---

## 经验教训

1. **上下文预热对于死语言至关重要。** 若没有 3,500 字的第 1 阶段提示词，模型会默认使用现代汇编约定并产生幻觉。有了它，指令语义在数千行分析中均保持正确。

2. **原始参考手册很重要。** 第 1 阶段提示词是我的精简摘要；将 ibiblio 手册的实际章节作为基本事实注入，捕捉到了摘要遗漏的边缘情况（EDOP 移位行为、CCS 分支顺序）。

3. **带扩展思考的 Opus 4.6 对于这种深度是必要的。** Sonnet 用于仓库侦察（分类任务）已足够。但深度分析——追踪 1960 年代汇编中的控制流、识别文化典故、进行现代类比——需要 Opus。质量差异显著。

4. **Claude Code 的 `-p` 模式需要仔细的提示词工程。** 模型试图使用文件写入工具而非响应到标准输出。修复方式很明确："直接在文本响应中输出完整的 markdown 文档"。这是 Claude Code 特有的陷阱。

5. **总成本：Max 计划下约 47 分钟的 Opus 计算时间。** 无 API 计费。整个项目——8 个演练文件共约 6,000 行 / ~300K 字符的技术分析——在两天内累计不到一小时的计算时间内完成。

6. **LLM 真正助力遗留代码的地方：阅读，而非编写。** AI 没有编写任何 AGC 汇编。它*阅读*了它——并将其翻译成现代开发者能够理解的内容。这是被低估的用例：AI 作为阅读早于其训练数据的代码的工具。


---

## 自动化设置（2026-03-26）

### 脚本

两个 Python 脚本自动化基于 API 的方法：

**`scripts/run_phase2_recon.py`** — 第 2 阶段仓库侦察
- 扫描 Luminary099/ 和 Comanche055/ 中的所有 .agc 文件
- 提取头部注释（每个文件的前约 40 行）
- 将完整清单发送给 Claude 进行分类
- 默认使用 Sonnet（足以完成分类任务，成本更低）

**`scripts/run_deep_dives.py`** — 第 3 阶段深度分析
- 从 ibiblio.org 获取并缓存 Virtual AGC Assembly Language Manual
- 提取关键章节（指令集、内存映射、中断、解释器）
- 对于每次深度分析：组装系统提示词（第 1 阶段上下文 + 原始手册章节）+ 用户消息（源文件 + 特定深度分析提示词）
- 调用启用了扩展思考的 Claude API（10K 思考预算）
- 保存演练输出、思考追踪和结构化运行日志（JSONL）
- 默认使用 Opus（AGC 汇编准确分析所必需）

### 为何使用两层参考资料

系统提示词包含**两种形式**的 AGC 架构参考：

1. **第 1 阶段上下文**（`prompts/phase1-context.md`）— 我的精简摘要。为模型提供框架：寄存器名称、指令行为、需要注意的关键惯用法。约 3,500 字
2. **原始手册章节**（从 ibiblio.org 缓存）— 实际的 Virtual AGC Assembly Language Manual 文本。基本事实。提示词明确表示："若精简摘要与本材料冲突，以本材料为准。"

精简摘要帮助模型高效推理。原始手册防止在 CCS 分支顺序、TS 溢出行为或 EDOP 移位语义等细节上产生幻觉。

### 便捷封装器

`./run.sh` 提供简单的命令行界面：
```
./run.sh setup      # clone repo, install deps, cache manual
./run.sh recon      # Phase 2: scan repo structure
./run.sh dive 3a    # single deep dive
./run.sh dive all   # all 5 deep dives
./run.sh status     # show what's been generated
```

### Token 预算估计

| 深度分析 | 源文件 | 预计输入 Token | 备注 |
|------|-------------|-------------------|-------|
| 3a | EXECUTIVE + WAITLIST | ~25K | 两个中等大小的文件 |
| 3b | FRESH_START_AND_RESTART + ALARM_AND_ABORT | ~30K | 较大的重启文件 |
| 3c | LUNAR_LANDING_GUIDANCE_EQUATIONS | ~20K | 密集的解释器代码 |
| 3d | BURN_BABY_BURN | ~15K | 最短的深度分析 |
| 3e | INTERPRETER + INTER-BANK_COMMUNICATION | ~35K | 最大的单个文件 |

系统提示词（第 1 阶段 + 手册）为每次调用额外增加约 15-20K token。
输出预算：每次深度分析 16K token。思考预算：10K token。
