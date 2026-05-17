# BURN, BABY, BURN — 主点火程序

## 点燃引擎的代码

这是控制登月舱引擎点火的文件——该程序点燃了下降推进系统（DPS），使 Neil Armstrong 和 Buzz Aldrin 得以开始向静海的动力下降。它也是整个 AGC 代码库中文化内涵最为丰富的文件之一：1960年代的反主流文化、拉丁铭文与精密的系统工程在同一页面上共存。

该程序"由 Adler 和 Eyles 构思并实现，且（NOTA BENE）由 Adler 和 Eyles 维护"——Peter Adler 和 Don Eyles 是麻省理工学院仪器实验室的两位工程师，他们为登月舱将要执行的每一次引擎点火构建了点火序列。

---

## 1. 技术功能

### 1.1 该程序实际完成的工作

BURN_BABY_BURN 是**主点火程序**——一个通用引擎点火序列器，被五个不同的 LM 程序所使用：

| 程序 | 用途 |
|---------|----------|
| **P12** | 动力上升（从表面中止） |
| **P40** | DPS 点火（通用目的） |
| **P42** | APS 点火（上升推进系统） |
| **P61** | 不在此表中，但在注释中有引用 |
| **P63** | 月球下降制动阶段——*着陆点火* |

Adler 和 Eyles 没有为每个程序分别编写点火代码，而是构建了一个**表驱动架构**。每个程序提供一张常量表和分支地址，点火程序使用可擦除寄存器 `WHICH` 索引这些表以定制其行为。

### 1.2 表驱动设计

文件中第一部分就是这些表，它们非常优雅。给定偏移量处的每个表项都有特定用途：

```
P63TABLE    VN      0662            # (0)  Verb-Noun for display
            TCF     ULLGNOT         # (1)  Ullage setup branch
            TCF     COMFAIL3        # (2)  Communication failure handler
            TCF     V99RECYC        # (3)  Response to astronaut "ENTER"
            TCF     TASKOVER        # (4)  Task termination
            TCF     P63SPOT         # (5)  Program-specific spot entry
            DEC     2240            # (6)  Ullage duration (centiseconds)
            EBANK=  WHICH
            2CADR   SERVEXIT        # (7)  AVERAGEG exit address
            TCF     DISPCHNG        # (11) Display change handler
            TCF     WAITABIT        # (12) Wait handler
            TCF     P63IGN          # (13) Program-specific ignition handler
```

程序通过 `INDEX WHICH` 后跟带表偏移量的 `TCF`、`CA` 或 `DCA` 来访问这些表。例如：

```agc
        INDEX   WHICH
        TCF     5               # Jump to program-specific spot (offset 5)
```

这是一个**虚表**——一个虚拟分派表，用1960年代的汇编语言实现。其模式在概念上与 C++ 编译器为虚方法调用生成的代码完全相同。每个程序“继承”主点火行为并“覆盖”特定槽位。

注意使多个程序共享相同入口点的别名定义：

```agc
P42SPOT     =       P40SPOT         # (5)
P12SPOT     =       P40SPOT         # (5)
P63SPOT     =       P41SPOT         # (5)  IN P63 CLOKTASK ALREADY GOING
```

### 1.3 点火时间线

该程序编排了一个精确的倒计时序列。以下是从代码中重建的时间线：

#### TIG - 45 秒：入口（`BURNBABY`）

```agc
BURNBABY    TC      PHASCHNG        # GROUP 4 RESTARTS HERE
            OCT     04024

            CAF     ZERO            # EXTIRPATE JUNK LEFT IN DVTOTAL
            TS      DVTOTAL
            TS      DVTOTAL +1
```

"EXTIRPATE"这个词——意为连根拔除、彻底摧毁——并非典型的汇编注释风格。这是 Adler 或 Eyles 的声音。他们将 `DVTOTAL`（累积的速度增量）清零，以便点火从干净的状态开始。

该程序随后：
1. 调用 `P40AUTO` 验证航天员已设置正确的控制模式（PGNCS 和 AUTO）
2. 存储名义 TIG（点火时刻）以进行倾斜角补偿
3. 通过 `ENGINOF3` 命令引擎关闭（安全措施：在开始序列前确保引擎关闭）
4. 通过 `INDEX WHICH / TCF 5` 分派到程序特定的“spot”

#### TIG - 30 秒：状态向量传播（`P41SPOT`）

对于需要此步骤的程序（P41/P63），程序进入**解释器**以传播 CSM 状态向量：

```agc
P41SPOT     TC      INTPRET         # (5)
            DLOAD   DSU
                TIG
                D29.9SEC
            STCALL  TDEC1
                INITCDUW
            BOFF    CALL
                MUNFLAG
                GOMIDAV
                CSMPREC
```

这是解释器代码——注意 `TC INTPRET` 的切换，以及随后使用的 `DLOAD`、`DSU`、`STCALL`、`BOFF`、`VLOAD`、`MXV` 等指令。它计算 TIG-29.9 秒时 CSM 的预测位置和速度，通过 `REFSMMAT` 将它们转换到参考坐标系，并将结果存储为 `V(CSM)`、`R(CSM)` 和 `G(CSM)`。

`BOFF MUNFLAG` 检测月球引力场是否相关。如果 `MUNFLAG` 未被置位，则跳过 CSM 精度积分（`CSMPREC`），直接转到 `GOMIDAV`。

如果 TIG 被延迟（积分耗时过长），代码会重置 TIG：

```agc
            EXTEND              # TIG WAS SLIPPED, SO RESET TIG TO 29.9
            DCA     PIPTIME1    # SECONDS AFTER THE TIME TO WHICH WE DID
            DXCH    TIG         # INTEGRATE.
            EXTEND
            DCA     D29.9SEC
            DAS     TIG
```

这是一个关键的安全特性：如果计算时间过长，TIG 会被向前推移，而不是尝试延迟点火。

#### TIG - 35 秒：DSKY 消隐（`TIG-35`）

```agc
TIG-35      CAF     5SEC
            TC      TWIDDLE
            ADRES   TIG-30

            ...
            CS      BLANKDEX        # BLANK DSKY FOR 5 SECONDS
            TS      DISPDEX
```

DSKY 显示被消隐5秒，向航天员发出信号：平均-G（加速度计积分服务）正在启动。这是一个**人机界面约定**——一个视觉提示，表明有重要事情正在发生。

程序在此时也检查推进剂沉降时间：

```agc
            INDEX   WHICH
            CS      6               # CHECK ULLAGE TIME.
            EXTEND
            BZMF    TASKOVER        # Skip if ullage time <= 0
```

如果偏移量6处的表项为负（如 P41 的 `-1`），则无需执行推进剂沉降。

#### TIG - 30 秒：倒计时显示与推进剂沉降设置（`TIG-30`）

```agc
TIG-30      CAF     S24.9SEC
            TC      TWIDDLE
            ADRES   TIG-5

            CS      CNTDNDEX        # START UP CLOKTASK AGAIN
            TS      DISPDEX
```

设置在 TIG-5 触发的任务，重启倒计时时钟显示，并——关键地——设置推进剂沉降任务：

```agc
            INDEX   WHICH           # PICK UP APPROPRIATE ULLAGE -- ON TIME
            CA      6
            EXTEND
            BZMF    ULLGNOT         # DON'T SET UP ULLAGE IF DT IS NEG OR ZERO
            TS      SAVET-30        # SAVE DELTA-T FOR RESTART
            TC      TWIDDLE
            ADRES   ULLGTASK
```

**推进剂沉降**是在主引擎点火前点燃小型 RCS（反应控制系统）推力器，使推进剂沉积在储箱底部的操作。没有这一步，引擎可能吸入气泡。沉降持续时间来自程序表（偏移量6）：P40 和 P63 使用 `DEC 2240`（22.40 秒，意味着沉降从 TIG-7.5 开始，在点火前约7.5秒燃烧），而 P42 使用 `DEC 2640`（26.40 秒）。

#### TIG - 7.5 秒：推进剂沉降启动（`ULLGTASK`）

```agc
ULLGTASK    TC      ONULLAGE        # THIS COMES AT TIG-7.5 OR TIG-3.5
            TC      PHASCHNG
            OCT     1
            TCF     TASKOVER
```

`ONULLAGE` 在 `DAPBOOLS` 中设置沉降位，告知数字自动驾驶仪点燃 RCS 喷气装置：

```agc
ONULLAGE    CS      DAPBOOLS        # TURN ON ULLAGE.
            MASK    ULLAGER
            ADS     DAPBOOLS
            TC      Q
```

#### TIG - 5 秒：引擎使能请求（`TIG-5`）

```agc
TIG-5       EXTEND
            DCA     NEG0            # INSURE THAT GROUP 3 IS INACTIVE.
            DXCH    -PHASE3

            CAF     5SEC
            TC      TWIDDLE
            ADRES   TIG-0

            TC      DOWNFLAG        # RESET IGNFLAG AND ASINFLAG
            ADRES   IGNFLAG
            TC      DOWNFLAG
            ADRES   ASTNFLAG
```

清除 `IGNFLAG` 和 `ASTNFLAG`（航天员标志），然后分派到偏移量11处的程序特定处理器。对于 P40/P42，这可能会启动 S40.13 目标程序。显示切换到 verb 99（“请使能引擎”）——请求航天员授权点燃引擎。

#### TIG - 0：点火决策（`TIG-0`）

```agc
TIG-0       CS      FLAGWRD7        # SET IGNFLAG SINCE TIG HAS ARRIVED
            MASK    IGNFLBIT
            ADS     FLAGWRD7

            ...

IGNYET?     CAF     ASTNBIT         # CHECK ASTNFLAG: HAS ASTRONAUT RESPONDED
            MASK    FLAGWRD7        # TO OUR ENGINE ENABLE REQUEST?
            EXTEND
            INDEX   WHICH
            BZF     12              # BRANCH IF HE HAS NOT RESPONDED YET
```

这是**关键安全门控**：代码检查 `ASTNFLAG`，以确认航天员是否已按下 PROCEED 以响应 V99“请使能引擎”的显示。如果航天员尚未响应，则分支到 `WAITABIT`（偏移量12），后者会终止第4组并等待。没有航天员确认，引擎**不会点火**。

### 1.4 引擎接口——实际点火

当航天员已确认且 TIG 到达时，执行到达 `IGNITION`：

```agc
IGNITION    CS      FLAGWRD5        # INSURE ENGONFLG IS SET.
            MASK    ENGONBIT
            ADS     FLAGWRD5
            CS      PRIO30          # TURN ON THE ENGINE.
            EXTEND
            RAND    DSALMOUT
            AD      BIT13
            EXTEND
            WRITE   DSALMOUT
```

这就是那一刻。让我们追踪 I/O 操作：

1. **`CS PRIO30`** — 加载优先级30的补码（八进制 37777 减去 30000 = 一个掩码）。实际上，`PRIO30` 是八进制 37777 作为优先级常量；`CS` 对其取补码以创建清除特定位的掩码。
2. **`RAND DSALMOUT`** — 读取 I/O 通道 `DSALMOUT`（通道11，引擎命令通道）并与 A 进行与运算，在清除引擎位位置的同时保留现有位。
3. **`AD BIT13`** — 设置第13位，即**引擎开启**命令。
4. **`WRITE DSALMOUT`** — 将结果写回通道，命令引擎点火。

引擎通过 **I/O 通道11（DSALMOUT）**，第13位点火。这是一个读-改-写模式，避免干扰通道上的其他位（这些位控制其他离散输出，如 DSKY 告警）。

点火后，代码立即为事件打上时间戳并更新 TIG：

```agc
            EXTEND              # SET TEVENT FOR DOWNLINK
            DCA     TIME2
            DXCH    TEVENT

            EXTEND              # UPDATE TIG USING TGO FROM S40.13
            DCA     TGO
            DXCH    TIG
            EXTEND
            DCA     TIME2
            DAS     TIG
```

### 1.5 程序特定的点火后处理：P63（月球着陆）

对于月球着陆点火（P63），点火后序列尤为复杂：

```agc
P63IGN      EXTEND              # (13) INITIATE BURN DISPLAYS
            DCA     DSP2CADR
            DXCH    AVGEXIT

            CA      Z               # ASSASSINATE CLOKTASK
            TS      DISPDEX
```

"ASSASSINATE CLOKTASK"——他们不只是停止它，而是*暗杀*它。将 `DISPDEX` 设置为 Z 的当前值（由于是程序计数器地址，所以为正值）会导致 `CLOKTASK` 在下次唤醒时检测到该正值并自行终止。

P63 点火处理器随后：
- 在 `FLAGWRD9` 中设置 `LETABBIT`——启用 P70/P71（中止程序）
- 在 `FLAGWRD7` 中设置 `SWANDBIT`——启用 R10 着陆显示（高度/高度变化率）
- 清除 `DAPBOOLS` 中的最小脉冲模式——确保 DAP 使用正常推力
- 初始化 `WCHPHASE` 和 `FLPASS0` 以进入下降制导阶段
- 落入 `P42IGN`

### 1.6 节流推力提升：P63ZOOM 和 P40ZOOM

对于 P63，在 TIG-0 时会安排延迟节流推力提升：

```agc
            CA      ZOOMTIME
            TC      WAITLIST
            EBANK=  DVCNTR
            2CADR   P63ZOOM
```

当 `P63ZOOM` 触发时（根据文件头注释，在点火后26秒）：

```agc
P63ZOOM     EXTEND
            DCA     LUNLANAD
            DXCH    AVEGEXIT        # Connect LUNLAND to the guidance loop

            TC      IBNKCALL
            CADR    FLATOUT         # Command full (flat-out) throttle
            TCF     P40ZOOMA
```

这将 `LUNLAND` 制导程序（著名的月球着陆制导方程）连接到 AVERAGEG 服务循环，然后通过 `FLATOUT` 命令全推力。

对于 P40：

```agc
P40ZOOM     CAF     BIT13
            TS      THRUST          # Set thrust command
            CAF     BIT4
            EXTEND
            WOR     CHAN14          # Write to I/O channel 14
```

这写入 **I/O 通道14**，这是一个多功能输出通道，控制（除其他功能外）LM 的引擎命令。`BIT13` 设置推力命令寄存器，通道14上的 `BIT4` 是 DPS 的引擎开启位。

### 1.7 安全特性摘要

该程序实现了多层安全保障：

1. **航天员同意门控** — V99“请使能引擎”必须用 PROCEED 响应后才能点火
2. **序列前关闭引擎** — 入口处调用 `ENGINOF3` 以确保初始状态干净
3. **TIG 延迟保护** — 如果状态向量传播运行时间过长，TIG 会被向前推移
4. **推进剂沉降验证** — 主引擎点火前点燃沉降喷管以沉积推进剂
5. **模式验证** — `P40AUTO` 检查 PGNCS 和 AUTO 模式是否已设置；若未设置，则显示检查表203
6. **通信失败处理** — `COMFAIL` 路径处理与地面失联的情况
7. **重启保护** — 广泛使用 `PHASCHNG` 确保每个关键状态转换在计算机重启后都能恢复
8. **中止路径** — `ABRTABLE` 提供紧急点火路径，未使用的槽位用 `NOOP` 占位
9. **DVMON 连接** — 点火后，`DVMONCON` 连接速度增量监视器，监测引擎故障
10. **推进剂沉降关闭** — `ULLAGOFF` 在主引擎点火后0.5秒关闭 RCS 沉降

### 1.8 倒计时时钟

`CLOKTASK`/`CLOKJOB` 对实现倒计时显示：

```agc
CLOKTASK    CS      TIME1           # SET TBASE6 FOR GROUP 6 RESTART
            TS      TBASE6

            CCS     DISPDEX
            TCF     KILLCLOK        # Positive DISPDEX = kill the clock
            NOOP                    # +0 case (falls through)
            CAF     PRIO27
            TC      NOVAC           # Start CLOKJOB
            ...
            TC      FIXDELAY
            DEC     100             # Wait 1 second (100 centiseconds)
            TCF     CLOKTASK        # Loop
```

`CLOKTASK` 作为 Waitlist 任务运行，每秒触发一次。它生成 `CLOKJOB`，后者计算 `TTOGO = TIME2 - TIG`，并使用 `DISPDEX` 作为负索引进入显示分派表。

该分派表非常巧妙——`-35`、`-25`、`-17`、`-13`、`-2` 等标签对应的 `DISPDEX` 值在倒计时不同阶段选择不同的显示：

| DISPDEX | 显示内容 |
|---------|----------|
| -35 (VB97DEX) | Verb 97 粘贴（通信失败） |
| -25 | V06N61 — 事件计时器复位显示 |
| -17 (CNTDNDEX) | 正常倒计时显示（来自表偏移量0的 V/N） |
| -13 (VB99DEX) | Verb 99 — “请使能引擎” |
| -2 (BLANKDEX) | DSKY 消隐 |

注释明确指出一个关键不变量：

```agc
            COM
            RELINT          # ***** DISPDEX MUST NEVER B -0 *****
```

在1的补码中，`-0`（全1，八进制77777）是一个有效的 `DISPDEX` 值，但在 `CCS`/`COM` 序列后会导致错误索引。五个星号的强调表明这是一个已知的陷阱。

---

## 2. 文化考古

### 2.1 名称："Burn, Baby! BURN!"

文件头部包含一段引人注目的历史说明，由现代转录团队根据 Don Eyles 在 AGC 开发者40周年聚会上的讲述添加：

> 这可以追溯到1965年的洛杉矶骚乱，灵感来自出色的唱片骑师兼电台老板 Magnificent Montague。Magnificent Montague 在播放最热门的新唱片时会喊"Burn, baby! BURN!"这句话。Magnificent Montague 是从1950年代中期到1960年代中期在芝加哥、纽约和洛杉矶灵魂乐的魅力之声。

Nathaniel "Magnificent" Montague 是一位电台 DJ，每当一张唱片特别出色时就会高喊"Burn, baby! BURN!"——这是最高赞扬的说法。在1965年8月洛杉矶瓦茨骚乱期间，这句话被暴动者借用，带上了更黑暗的含义。据报道，Montague 对此深感震惊，并试图改变他的口头禅。

Adler 和 Eyles 为主点火程序——字面意义上点燃火箭引擎的代码——选择这个短语，展示了麻省理工学院仪器实验室团队的不羁幽默。这个短语在多个层面上都有效：它是对引擎的命令，是 DJ 表达卓越的感叹，也是一个黑暗的历史回响，所有这些都压缩在一个子程序标签里。

次要入口点处的审查变体 `B*RNB*B*` 可能是对该名称接近粗口性质的玩笑，也可能有实际用途（一个与 `P40AUTO` 之后入口点不同的标签，便于在清单中查找）。

### 2.2 "HONI SOIT QUI MAL Y PENSE"

```
#            HONI SOIT QUI MAL Y PENSE
```

这是嘉德勋章的格言，嘉德勋章是英国最古老、最负盛名的骑士勋章，可追溯至1348年。这句话从古法语译为：**"心存邪念者蒙羞。"**

紧接在声明该程序"由 Adler 和 Eyles 构思并实现，且（NOTA BENE）由 Adler 和 Eyles 维护"之后，这读起来像是一个挑衅性的宣言：*如果你认为我们的代码有问题，那羞耻在于你。* 这是以中世纪纹章包装的领地骄傲——两位年轻工程师插下的旗帜。

### 2.3 "NOLI SE TANGERE"

```
#            NOLI SE TANGERE
```

紧接在程序表开始之前。这是拉丁语"Noli me tangere"的轻微变体——**"勿触碰我"**（在此形式中，更接近"请勿触碰它"）。该短语源自《约翰福音》，复活的基督对抹大拉的马利亚说了这句话。

在此语境中，这是对其他程序员的警告：**不要修改这些表。** 表结构是整个点火程序的骨干，改变一个偏移量会悄悄破坏所有使用它的程序。这是1960年代版的 `// DO NOT EDIT` 注释，但具有相当更强的庄严感。

### 2.4 "NOTA BENE"

```
# THE MASTER IGNITION ROUTINE WAS CONCEIVED AND EXECUTED, AND (NOTA BENE) IS MAINTAINED BY ADLER AND EYLES.
```

拉丁语，意为"请注意"。对"由……维护"的括号强调向团队其他成员传达了一个明确信息：*如果你对这段代码有异议，来找我们。* 结合"HONI SOIT QUI MAL Y PENSE"和"NOLI SE TANGERE"，描绘出两位工程师的形象：他们为自己的工作感到骄傲，守护其完整性，且不惮于用古老语言来强制维权。

### 2.5 "EXTIRPATE"

```agc
            CAF     ZERO        # EXTIRPATE JUNK LEFT IN DVTOTAL
```

*extirpate* 的意思是连根拔除、彻底摧毁。现代程序员可能会写 `// clear delta-V accumulator`，而 Adler 和 Eyles 却写"EXTIRPATE JUNK"。措辞既传达了精确性（这不只是清除一个变量，而是摧毁污染性残留），也体现了个性。

### 2.6 "ASSASSINATE CLOKTASK"

```agc
            CA      Z           # ASSASSINATE CLOKTASK
            TS      DISPDEX
```

不是"停止"，不是"终止"，不是"杀死"——是*暗杀*。`CLOKTASK` 并不知道自己即将死去。它将在下次唤醒时发现自己的死亡，当时它会发现 `DISPDEX` 已被设置为正值。这在技术上是精确的（这是延迟终止，而非立即终止），在语言上也生动形象。

### 2.7 "HELLO THERE" 与 "GOODBYE. COME AGAIN SOON."

在 `P40AUTO` 子程序中：

```agc
P40AUTO     TC      MAKECADR    # HELLO THERE.
            TS      TEMPR60
```

在结尾处：

```agc
GOBACK      CA      TEMPR60
            TC      BANKJUMP    # GOODBYE.  COME AGAIN SOON.
```

子程序在入口处问候调用者，在退出时道别。这是纯粹的个性——代码在表现*好客*。它也提供了微妙的文档辅助：这些注释在控制流复杂的文件中标记了一个自包含子程序的边界。

### 2.8 "?" = GOTOPOOH

```agc
?           =       GOTOPOOH
```

这个等价定义将标签 `?` 定义为 `GOTOPOOH` 的别名（转到 P00，即空闲程序——"POOH"如小熊维尼，因为 P00 → "Pooh"）。问号作为标签本身就是个笑话——它是指向"什么都不做"程序的"我们该怎么办？"符号。AGC 标签几乎可以包含任何字符，团队充分利用了这一点。

### 2.9 缺席的文化引用

用户提问中提到了"OFF TO SEE THE WIZARD"和"HAS THE LITTLE OLD LADY LEFT?"——**这些注释并不出现在本文件中。** 它们可能存在于其他模块（可能在执行程序或等待列表代码中，或在制导方程中）。它们在此处的缺席值得注意：BURN_BABY_BURN 有其独特的个性。其文化基调是拉丁铭文和灵魂乐，而非绿野仙踪的引用。

### 2.10 航天员检查表引用

```agc
TURNITON    CAF     P40A/PMD    # DISPLAYS V50N25 R1=203 PLEASE PERFORM
            TC      BANKCALL    # CHECKLIST 203 TURN ON PGNCS ETC.
            CADR    GOPERF1
```

`P40A/PMD` 解析为 `OCT 00203`——检查表项目203。这显示“V50N25”（Verb 50 Noun 25：“请在 R1 中执行检查表项目”），R1=203。检查表203指示航天员验证主制导、导航和控制系统（PGNCS）已开启，且飞船处于 AUTO 模式。代码无法拨动那些物理开关——它必须请求人工操作。

---

## 3. 代码质量与结构

### 3.1 几乎完全是原生 AGC

与制导方程文件（LUNAR_LANDING_GUIDANCE_EQUATIONS、THE_LUNAR_LANDING 等）以解释器代码为主不同，BURN_BABY_BURN **绝大部分是原生 AGC 汇编**。唯一的解释器块是 `P41SPOT` 中的状态向量传播：

```agc
P41SPOT     TC      INTPRET         # Enter interpreter
            DLOAD   DSU
                TIG
                D29.9SEC
            ...
            CALRB
                MIDTOAV1            # Return to basic (native) mode
```

这从架构上来说是合理的：点火程序是一个**实时序列器**，而非计算密集型程序。它需要精确的时序控制、直接 I/O 访问、中断管理和等待列表任务调度——这些都需要原生 AGC 指令。解释器约10-25倍的性能损耗对于时间关键的点火序列是不可接受的。

### 3.2 控制流架构

控制流复杂但有规律。有三种相互交织的机制：

**1. 等待列表任务（时间驱动）：**

```
TIG-35 → (5 sec) → TIG-30 → (24.9 sec) → TIG-5 → (5 sec) → TIG-0 → IGNITION
```

每个任务通过 `TWIDDLE`（等待列表便利程序）调度下一个。这条链是倒计时的骨干。

**2. 作业（优先级驱动）：**

`CLOKJOB`、`S40.13`、`P41BLANK` 和 `POSTBURN` 等作业在执行程序的协作调度器下运行。它们处理耗时较长的计算工作（显示更新、目标计算），这些工作对于等待列表任务来说太长了。

**3. 表分派（程序驱动）：**

`INDEX WHICH / TCF n` 在整个程序中用于分支到程序特定行为。这是多态层。

这三种机制相互交织：等待列表任务可能生成一个作业，该作业可能使用表分派。理解代码中的任何单一路径都需要同时追踪这三种机制。

### 3.3 重启保护

代码对重启保护极为重视。几乎每次状态转换都被 `PHASCHNG` 调用所包围：

```agc
BURNBABY    TC      PHASCHNG        # GROUP 4 RESTARTS HERE
            OCT     04024
```

八进制常量编码了要设置的重启组和阶段。如果计算机复位（正如阿波罗11号著名的1202告警期间发生的那样），执行程序可以在点火序列的正确位置恢复执行，而不是从头开始。这至关重要——当你距离点火只有20秒时，无法从零重启倒计时。

本文件中使用的重启组：
- **第1组**：推进剂沉降任务保护
- **第3组**：节流提升保护、S40.13 保护
- **第4组**：主点火序列（主链）
- **第6组**：倒计时时钟（`CLOKTASK`）

### 3.4 与制导方程的比较

| 方面 | BURN_BABY_BURN | 制导方程 |
|--------|---------------|-------------------|
| 语言 | ~95% 原生 AGC | ~80% 解释器 |
| 主要关注点 | 时序、序列、I/O | 数学计算 |
| 数据类型 | 标志、地址、时间值 | 向量、矩阵、角度 |
| 控制流 | 任务链 + 表分派 | 解释器中的 CALL/GOTO |
| 重启保护 | 广泛（每次转换） | 适中（主要阶段） |
| 注释 | 个性丰富 | 简洁到适中 |
| 复杂性来源 | 多路径状态机 | 数值算法 |

### 3.5 `KILLTASK` 程序

文件以一个通用工具程序 `KILLTASK` 结束，该程序从等待列表中移除一个已调度的任务。其头部注释在 AGC 代码库中异常详尽——包含完整的调用序列、退出条件、可擦存储器初始化、输出和副作用（被破坏的寄存器）：

```
# KILLTASK IS USED TO REMOVE A TASK FROM THE WAITLIST BY SUBSTITUTING
# A NULL TASK CALLED `NULLTASK' (OF COURSE), WHICH MERELY DOES A
# TC TASKOVER.
```

"(OF COURSE)"是 Covelli（在文件头中被提及）的一点个性展示。实现方法是扫描 `LST2` 等待列表数组，将每个条目的 GENADR 和 FBANK 与目标任务进行比较。找到后，用 `TCTSKOVR`（一条 `TC TASKOVER` 指令）覆盖该条目——任务槽现在包含一个将无害执行并终止的空操作。

扫描循环：

```agc
ADRSCAN     INDEX   L
            CS      LST2
            AD      ITEMP4          # COMPARE GENADRS
            EXTEND
            BZF     TSTFBANK        # IF THEY MATCH, COMPARE FBANKS
LETITLIV    CS      LSTLIM
            AD      L
            EXTEND
            BZF     DEAD            # ARE WE DONE?
            INCR    L
            INCR    L               # Entries are 2 words apart
            TCF     ADRSCAN
```

`LETITLIV`（让它活着）标签用于"不匹配，继续"情况，`KILLDEAD` 标签用于成功移除，延续了文件中生动命名的传统。

注意 `KILLTASK` 保持中断禁止状态（入口处 `INHINT`，无 `RELINT`），如文档所述："KILLTASK LEAVES INTERRUPTS INHIBITED SO CALLER MUST RELINT。"这是一个刻意的设计选择——调用者可能需要在重新启用中断前执行额外的原子操作。

---

## 4. 着陆的那一刻

要理解这个文件在历史上的地位，请追踪 P63 路径：

1. `BURNBABY` 以 `WHICH` 指向 `P63TABLE` 进入
2. 倒计时经过 TIG-35、TIG-30、TIG-5
3. 在 TIG-5，DSKY 显示 V99："请使能引擎"
4. Aldrin 按下 PROCEED
5. 在 TIG-0，`IGNITION` 点火——第13位写入 DSALMOUT
6. 下降引擎在月球上空约50,000英尺处点火
7. 26秒后，`P63ZOOM` 节流至全功率并连接 `LUNLAND`——着陆制导方程接管
8. `CLOKTASK` 被"暗杀"；着陆显示取而代之

从这一刻起，登月舱已无退路。BURN_BABY_BURN 将控制权移交给制导方程，后者将引导 Armstrong 和 Aldrin 降落到月球表面。

执行这一序列的代码在发射前数月被编织进核心绳式存储器。它无法被修补。它必须在第一次运行时就成功，在人类阿波罗11号着陆的唯一尝试中。而它做到了。

---

## 不确定性说明

- **I/O 通道细节**：DSALMOUT（通道11）上的确切位分配是从代码模式推断的（`RAND` 读取，`AD BIT13` 设置，`WRITE` 提交）。通道编号和位功能与 LM 文档一致，但我未与本代码库中的 I/O 通道表进行交叉核实。

- **ZOOMTIME 值**：文件头说明 DPS 程序的节流提升发生在"TIG + 26秒"，但 `ZOOMTIME` 的实际值未在本文件中定义。它可能在可擦存储器初始化中或调用程序中定义。

- **"OFF TO SEE THE WIZARD"和"HAS THE LITTLE OLD LADY LEFT?"**：分析提示中提到了这些注释，但**它们不出现在本文件中**。它们存在于 Luminary 代码库的其他地方。

- **P61TABLE**：在文件头注释中作为点火程序的使用者被引用，但本文件中没有 `P61TABLE`。它可能在 P61 源模块中定义，并简单地将 `WHICH` 寄存器指向内存中其他地方的自有表。
