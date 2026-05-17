# Apollo 11 AGC 源代码 — AI 导读

一个使用 Anthropic [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 进行 AI 辅助深度解析的项目，探索 Apollo 11 制导计算机的原始源代码。

## 这是什么

Apollo 11 AGC 源代码——约 40,000 行 1960 年代汇编语言，运行于一台 15 位、1 的补码计算机，拥有 72 KB 内存——是历史上最重要的代码库之一。对现代开发者来说，这些代码几乎完全无法阅读。

本项目使用 AI 弥合这一鸿沟：一个结构化的、逐模块的导读，解释代码的功能、实现方式，以及这些工程决策为何至今仍有意义。

**没有任何代码会老到让 AI 无法分析。**

## 导读模块

### [00 — 代码库结构](walkthrough/00-repo-structure.md)
Luminary099 代码库中全部 175 个 `.agc` 文件的地图，按功能分组：导航、制导、自动驾驶、系统管理和操作系统层。

### [01 — 执行程序](walkthrough/01-executive.md)
AGC 没有操作系统——执行程序（Executive）*就是*操作系统。它在约 600 行汇编代码中，跨 7 个固定核心集实现了基于优先级调度的协作式多任务。这一设计比 Go 的 goroutine 调度器和 Python 的 asyncio 早了数十年。通过固定资源池和静态分析，可以证明该调度器永远不会耗尽槽位——这是任何拥有 10,000 个 goroutine 的现代系统都无法声称的。

### [02 — 等待列表](walkthrough/02-waitlist.md)
驱动 AGC 实时心跳的定时器任务调度器。等待列表使用硬件 TIME3 计数器以精确的时间间隔触发任务，管理多达 9 个并发定时事件，并在源代码注释中包含了手工计算的最坏情况执行时间分析——写于 1966 年，彼时实时系统理论作为一门学科尚未诞生。

### [03 — 冷启动与重启](walkthrough/03-restart.md)
拯救了 Apollo 11 的模块。当下降过程中 1202 警报触发时，这段代码重启了计算机，验证了带校验和的阶段表的完整性，重新初始化了所有调度，并在几毫秒内恢复了制导方程——而此时下降发动机仍在点火。这是只崩溃设计（crash-only design）和"让它崩溃"（let it crash）哲学的实现，比 Erlang 早了 20 年，比这一模式被正式描述早了 37 年。

### [04 — 着陆制导方程](walkthrough/04-landing-guidance.md)
将登月舱飞向月面的数学方法。程序 P63（制动）、P64（带重新指定的接近）和 P66（手动下降速率）实现了一种以 2 Hz 运行于解释字节码中的重力转向制导算法。我们了解了代码如何处理从自动控制到手动控制的切换——Armstrong 操控摇杆绕过陨石坑的那一刻。

### [05 — BURN_BABY_BURN](walkthrough/05-burn-baby-burn.md)
启动任务中每次发动机点火的主点火程序。它使用表驱动的虚函数分派——结构上与 C++ 虚表（vtable）完全相同——使一个通用程序能处理下降、上升和轨道点火。这也是代码库中文化内涵最丰富的文件：拉丁文铭文、嘉德勋章的引用，以及在现代程序员写"clear"（清除）的地方使用了"EXTIRPATE"（根除）一词。

### [06 — 解释器](walkthrough/06-interpreter.md)
飞行软件若以原生汇编形式编写，将无法装入 36K 字的 ROM，因此 MIT 在 AGC 内部构建了一个字节码虚拟机。它将两个 7 位操作码打包进一个 15 位字中，提供向量/矩阵运算和三角函数，运行速度比原生代码慢 10–25 倍——但估计节省了 15,000–40,000 字的 ROM。没有它，就没有登月。这比 Java JVM 早了近 30 年。

### [07 — 弹球游戏（DSKY 接口）](walkthrough/07-dsky-interface.md)
宇航员与 AGC 的唯一接口：19 个按键和一组七段数码管显示器。动词-名词命令语言是最早的结构化人机交互界面之一。显示缓冲区（`DSPTAB`）使用符号位作为脏标记来差异比较变化——与 React 虚拟 DOM 的原理相同，用 1966 年的 14 个汇编字实现。该模块约有 3,800 行，是 Luminary 中最大的模块之一。

### [08 — 2026 年的启示](walkthrough/08-lessons.md)
基于全部七个导读的综合论文。涵盖领先于时代的架构模式（协作式多任务、检查点/重启、字节码虚拟机、命令语言）、约束作为设计驱动力、1202 事件作为优雅降级的案例研究、注释中的人文因素，以及 2026 年构建安全关键系统的工程师仍可从为 15 位、2K RAM 计算机编写的代码中学到什么。

## 制作方法

有关方法论的详细记录，请参阅 [PROCESS.md](PROCESS.md)：所使用的提示词、涉及的工具、什么有效、什么无效，以及 AI 哪里出了错。

另请参阅[博客文章](blog/blog-post.md)获取叙事版本。

## 参考资料

- [Apollo 11 AGC 源代码](https://github.com/chrislgarry/Apollo-11) — Chris Garry 的 GitHub 仓库（公共领域）
- [Virtual AGC 汇编语言手册](https://www.ibiblio.org/apollo/assembly_language_manual.html) — Ron Burkey 的综合参考
- [AGC4 基础培训手册 (E-2052)](https://www.ibiblio.org/apollo/NARA-SW/E-2052.pdf) — MIT 1967 年原版培训文档
- [Virtual AGC 项目](https://www.ibiblio.org/apollo/) — 模拟器、扫描件、文档
- [AGC4 备忘录 #9](https://www.ibiblio.org/apollo/Documents/agc4_memo9_rev_june1967.pdf) — Block II 指令集，作者 Hugh Blair-Smith

## 作者

[Julien Simon](https://www.linkedin.com/in/juliensimon/) — [Fortino Capital](https://www.fortinocapital.com/) 的 AI 运营合伙人。在 [The AI Realist](https://juliensimon.substack.com/) 写作。

## 许可证

Apollo 11 源代码为公共领域（美国政府作品）。本导读及所有原创分析文本依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 授权。
