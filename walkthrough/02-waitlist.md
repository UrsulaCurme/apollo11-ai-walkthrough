# 等待列表：2K RAM 中的硬件驱动任务调度器

## 概述

等待列表（Waitlist）是 AGC 的实时任务调度器——一个由定时器驱动、中断触发的分派系统，与执行模块（Executive）的协作式作业调度器相互补充。执行模块管理可通过自愿优先级调度来挂起和恢复的长时运行"作业"，而等待列表则处理必须在精确时刻触发的短时、时间关键型"任务"：自动驾驶喷气点火、DSKY 显示更新、传感器读取、制导方程步骤。

整个机制占用固定内存约 200 字，使用可擦除内存中的 27 字用于其数据结构。它最多支持 9 个并发待处理任务，定时分辨率为 10 毫秒，最大单次延迟为 162.5 秒。对于更长的延迟，LONGCALL 通过迭代重调度将覆盖范围延伸至约 2.56 小时。

---

## 1. 架构

### 执行作业与等待列表任务

AGC 同时运行两种根本不同的调度系统：

| 属性 | 执行作业 | 等待列表任务 |
|------|---------|------------|
| **触发方式** | 软件请求（FINDVAC/NOVAC） | 硬件定时器中断（T3RUPT） |
| **持续时间** | 长时运行，可休眠 | 短暂——必须快速完成 |
| **抢占方式** | 协作式（自愿 CHANG1） | 抢占式（中断前台） |
| **上下文** | 拥有 VAC 区域（工作寄存器） | 无保存上下文——运行至完成 |
| **终止方式** | TC ENDOFJOB | TC TASKOVER |
| **优先级** | 1-37（八进制），按优先级调度 | 按时间先来先服务 |
| **最大并发数** | 7 个作业 | 9 个任务 |

等待列表任务在中断上下文中运行。它触发，完成工作（通常几十到几百条指令），然后通过 `TC TASKOVER` 返回。如果工作量对于中断上下文而言过大，任务的第一个动作通常是通过 `FINDVAC` 调度一个执行作业，然后立即 `TC TASKOVER`。

### 数据结构：LST1 和 LST2

等待列表在可切换可擦除内存（EBANK=LST1）中维护两个并行数组：

**LST1** — 连续任务之间*增量时间*的 8 项数组：

```
C(LST1)     = -(T2 - T1) + 1
C(LST1 +1)  = -(T3 - T2) + 1
C(LST1 +2)  = -(T4 - T3) + 1
  ...
C(LST1 +7)  = -(T9 - T8) + 1
```

每个条目存储相邻任务之间的*取反*时间差，加一。取反是 1 的补码算术和 CCS 指令行为的结果——存储取反的增量允许插入搜索循环直接将 CCS 用作"是否仍有剩余时间？"的测试。

+1 偏置的存在是因为 CCS 区分四种情况（正、+0、负、-0），加 1 确保零增量映射为 +1（正），走正确的 CCS 分支。

**LST2** — *2CADR*（双字完整地址）的 9 项数组：

```
C(LST2)      = 2CADR TASK1   (address + bank info)
C(LST2 +2)   = 2CADR TASK2
  ...
C(LST2 +16)  = 2CADR TASK9
```

每个 2CADR 占两个字：第一个字是目标 bank 内的地址，第二个是 BBCON（包含超级 bank 的组合 bank 寄存器值）。LST2 条目间隔 2 个字，因为每个 2CADR 是双字。

**TIME3** 保存直到*第一个*任务触发的时间：

```
C(TIME3) = 16384 - (T1 - T)    即 1.0 - (T1 - T)（以厘秒为单位）
```

当 TIME3 溢出（从 POSMAX 到达 +0），触发 T3RUPT，表示任务 T1 到期。

### 哨兵：ENDTASK

```agc
ENDTASK         -2CADR  SVCT3
```

（第约 1121 页）

ENDTASK 是存储在固定-固定内存（非可切换 bank）中的常量，在新启动时初始化到 LST2 的所有槽位。其关键属性是**仅凭其地址就能区分它**——插入例程通过测试被替换的条目是否等于 ENDTASK 来检查任务是否已级联到列表底部：

```agc
        DXCH    LST2 +16D
        AD      ENDTASK         # END ITEM, AS CHECK FOR EXCEEDING
        EXTEND                  # THE LENGTH OF THE LIST.
        BZF     LVWTLIST        # DUMMY TASK ADRES SHOULD BE IN FIXED-
        TCF     WTABORT         # FIXED SO ITS ADRES ALONE DISTINGUISHES IT.
```

如果从最后一个 LST2 槽替换出的值是 ENDTASK（即将 ENDTASK 加到地址上得到零——它们互补），插入成功。否则，我们溢出了列表，并以警报 1203 中止。

当 ENDTASK 实际触发时（因为没有真实任务替换它），它运行 SVCT3，检查漂移标志并可能调度 IMU 补偿任务（NBDONLY）。这是一种巧妙的双重用途：哨兵同时作为周期性维护触发器。

相应的 LST1 条目初始化为 NEG1/2（八进制 40000，即 -16383）。由于 T3RUPT 在加载 TIME3 之前将 POSMAX 加到此值，得到的 TIME3 值给出哨兵触发之间约 81.91 秒的间隔——10ms 分辨率下 14 位计数器的最大单次溢出周期。

### 最大并发任务数：9

数组容纳 9 个任务（8 个 LST1 增量条目定义 9 个时间点之间的间隔，LST2 从 LST2 到 LST2+16 有 9 个双字槽）。尝试插入第 10 个任务会触发：

```agc
WTABORT         TC      FILLED
...
FILLED          DXCH    WAITEXIT
                TC      BAILOUT1        # NO ROOM IN THE INN
                OCT     01203
```

警报码 1203——程序中止。没有优雅降级；系统设计者确定 9 个待处理任务对于任务操作始终足够。这是一个具有静态分析最坏情况任务数的硬实时系统。

---

## 2. T3RUPT 与任务分派

### TIME3 如何触发 T3RUPT

TIME3 是一个 15 位 1 的补码计数器，由硬件每 10ms 递增一次。当它溢出（从 POSMAX = 37777 八进制经过 +0），硬件设置 T3RUPT 中断请求标志。如果中断已启用且没有更高优先级的条件阻止，CPU 跳转到地址 4014 八进制。

软件将 TIME3 加载为 `1.0 - (T1 - T)`，其中 T1 是下一个任务应触发的绝对时间，T 是当前时间。随着时间推进，TIME3 递增。当经过 `T1 - T` 厘秒后，TIME3 到达 POSMAX 并在下一个计时溢出。

### T3RUPT 处理程序：分派第一个任务

```agc
T3RUPT          EXTEND
                ROR     SUPERBNK        # READ CURRENT SUPERBANK VALUE AND
                TS      BANKRUPT        # SAVE WITH E AND F BANK VALUES.
                EXTEND
                QXCH    QRUPT
```

**（第 1128 页）：** ISR 入口保存上下文。`EXTEND; ROR SUPERBNK` 从 I/O 通道 7 读取 BBANK 与超级 bank 位的 OR 值——这捕获了完整的 bank 状态。保存在 BANKRUPT 中。Q 保存在 QRUPT 中。注意：A 和 L 在此处不保存，因为它们将立即被任务的 2CADR 加载。

```agc
T3RUPT2         CAF     NEG1/2          # DISPATCH WAITLIST TASK.
                XCH     LST1 +7
                XCH     LST1 +6
                XCH     LST1 +5
                XCH     LST1 +4         # 1. MOVE UP LST1 CONTENTS, ENTERING
                XCH     LST1 +3         #    A VALUE OF 1/2 +1 AT THE BOTTOM
                XCH     LST1 +2         #    FOR T6-T5, CORRESPONDING TO THE
                XCH     LST1 +1         #    INTERVAL 81.91 SEC FOR ENDTASK.
                XCH     LST1
```

这是一个*旋转链*。从 A 中的 NEG1/2 开始：
1. `XCH LST1+7` 将 A（NEG1/2）与 LST1+7 交换。现在 A = 旧 LST1+7，LST1+7 = NEG1/2（哨兵间隔）。
2. `XCH LST1+6` 将 A（旧 LST1+7）与 LST1+6 交换。现在 LST1+6 = 旧 LST1+7。
3. 继续沿链向上...
4. `XCH LST1` 将 A（旧 LST1+1）与 LST1 交换。现在 A = 旧 LST1+0（到下一个任务的增量），整个数组向上移动了一个位置，NEG1/2 插入底部。

此链之后，A 包含旧 LST1[0] 的值：`-(T2 - T1) + 1`。

```agc
                AD      POSMAX          # 2. SET T3 = 1.0 - T2 - T USING LIST 1.
                ADS     TIME3           #    SO T3 WON'T TICK DURING UPDATE.
                TS      RUPTAGN
                CS      ZERO
                TS      RUPTAGN         # SETS RUPTAGN TO +1 ON OVERFLOW.
```

这段代码微妙而精妙。让我们追踪其算术：

- A = `-(T2 - T1) + 1`（来自 LST1[0]）
- `AD POSMAX` 加 16383。结果：`16383 - (T2 - T1) + 1 = 16384 - (T2 - T1)`
- `ADS TIME3` 将此值加到当前 TIME3 值。

但当前 TIME3 是什么值呢？在 T3RUPT 触发的那一刻，TIME3 刚好溢出。在 ISR 序言期间（保存上下文，执行 XCH 链），TIME3 一直在计时。设当前 TIME3 值为 `T_elapsed`（小，表示自溢出以来的计时脉冲）。

因此：`TIME3 ← T_elapsed + 16384 - (T2 - T1)`

这恰好是 `1.0 - ((T2 - T1) - T_elapsed)`——在 T2 触发的正确 TIME3 值，考虑了 ISR 期间已流逝的时间！注释"SO T3 WON'T TICK DURING UPDATE"有些轻描淡写——它意味着 TIME3 更新*本质上*是正确的，无论 ISR 期间经过了多少计时脉冲。

**RUPTAGN 与级联分派：**

```agc
                TS      RUPTAGN
                CS      ZERO
                TS      RUPTAGN         # SETS RUPTAGN TO +1 ON OVERFLOW.
```

`ADS TIME3` 后，如果 TIME3 溢出（意味着 T2 现在也到期），A 获得 +1（TS 溢出跳过行为）。`TS RUPTAGN` 存储此值。然后 `CS ZERO` = -0。`TS RUPTAGN`——如果 A 为 +1（溢出），此路径被 TS 跳过，所以 RUPTAGN 保持 +1。如果无溢出，RUPTAGN 获得 -0。

任务运行并调用 TASKOVER 后：
```agc
TASKOVER        CCS     RUPTAGN         # IF +1 RETURN TO T3RUPT, IF -0 RESUME.
                CAF     WAITBB
                TS      BBANK
                TCF     T3RUPT2         # DISPATCH NEXT TASK IF IT WAS DUE.
```

如果 RUPTAGN = +1（下一个任务也到期），我们循环回 T3RUPT2 来分派它。如果 RUPTAGN = -0，CCS 落到第四个分支（跳过 3），恢复上下文并执行 RESUME。

### LST2 分派链

```agc
                EXTEND                  # DISPATCH TASK.
                DCS     ENDTASK
                DXCH    LST2 +16D
                DXCH    LST2 +14D
                ...
                DXCH    LST2 +2
                DXCH    LST2
```

LST1 的镜像：将 -ENDTASK 加载到 A、L，然后从底部到顶部级联通过 LST2。每个 DXCH 将 A、L 对与连续的 LST2 条目交换，将整个数组向下移动一个槽，并在底部插入 -ENDTASK（取反是因为使用了 DCS；符号会隐式纠正）。链执行后，A、L 包含旧 LST2[0]——要分派任务的 2CADR。

```agc
                XCH     L
                EXTEND
                WRITE   SUPERBNK        # SET SUPERBANK FROM BBCON OF 2CADR
                XCH     L               # RESTORE TO L FOR DXCH Z.
                DTCB
```

2CADR 的 BBCON（在 L 中）包含超级 bank 位。`XCH L` 将其放入 A，`WRITE SUPERBNK` 设置超级 bank I/O 通道，`XCH L` 恢复 L。然后 `DTCB`（即 `DXCH Z`）从 A、L 加载 Z（程序计数器）和 BB（bank 寄存器）——有效地以正确设置的所有 bank 跳转到任务的入口点。

任务现在在中断上下文中运行，中断被禁止。

### TASKOVER：任务完成时发生什么

```agc
TASKOVER        CCS     RUPTAGN         # IF +1 RETURN TO T3RUPT, IF -0 RESUME.
                CAF     WAITBB
                TS      BBANK
                TCF     T3RUPT2         # DISPATCH NEXT TASK IF IT WAS DUE.

                CA      BANKRUPT
                EXTEND
                WRITE   SUPERBNK        # RESTORE SUPERBANK BEFORE RESUME IS DONE

RESUME          EXTEND
                QXCH    QRUPT
NOQRSM          CA      BANKRUPT
                XCH     BBANK
NOQBRSM         DXCH    ARUPT
                RELINT
                RESUME
```

CCS RUPTAGN 有四个路径：
- **RUPTAGN > 0（具体为 +1）：** 另一个任务到期。切换到 WAITLIST bank，循环到 T3RUPT2。
- **RUPTAGN = +0：** 落到 `CAF WAITBB`——与正值相同，分派下一个任务。
- **RUPTAGN < 0：** 再经过两条指令落到恢复路径。
- **RUPTAGN = -0：** 也落到恢复路径（CCS 的跳过 3）。

恢复路径从保存位置恢复超级 bank、Q、BBANK 和 A、L，用 RELINT 重新启用中断，然后执行硬件 RESUME 指令，从 ZRUPT 恢复 Z——返回到被中断的代码。

注意多个入口点：NOQRSM 跳过 Q 恢复（用于 Q 已处理的情况），NOQBRSM 跳过 Q 和 bank 恢复。

---

## 3. 任务插入

### WAITLIST 入口点

调用约定：
```agc
        CA      DELTAT          # Time in centiseconds (1-16250)
        TC      WAITLIST
        2CADR   DESIRED TASK    # Two words: address + BBCON
        RELINT                  # Returns here
```

```agc
WAITLIST        INHINT
                XCH     Q               # SAVE DELTA T IN Q AND RETURN IN
                TS      WAITEXIT        # WAITEXIT.
                EXTEND
                INDEX   WAITEXIT        # IF TWIDDLING, THE TS SKIPS TO HERE
                DCA     0               # PICK UP 2CADR OF TASK.
 -1             TS      WAITADR         # BBCON WILL REMAIN IN L
```

让我们仔细追踪：

1. **入口时：** A = 增量时间，Q = 返回地址（指向 2CADR）。
2. `INHINT`——禁用中断。关键区段开始。
3. `XCH Q`——A ↔ Q。现在 A = 返回地址，Q = 增量时间。
4. `TS WAITEXIT`——保存返回地址。不可能溢出（它是内存地址），所以不跳过。
5. `EXTEND; INDEX WAITEXIT; DCA 0`——使用 INDEX 通过返回地址偏移 DCA。由于 WAITEXIT 指向调用方中 `TC WAITLIST` 之后的字，而那个字是 2CADR 的第一半，所以 `DCA 0` 以 WAITEXIT 为索引将 2CADR 加载到 A、L 中。
6. `TS WAITADR`——将地址部分（来自 A）保存到 WAITADR。BBCON 留在 L 中。

### TWIDDLE：优化的入口点

```agc
TWIDDLE         INHINT
                TS      L               # SAVE DELAY TIME IN L
                CA      POSMAX
                ADS     Q               # CREATING OVERFLOW AND Q-1 IN Q
                CA      BBANK
                EXTEND
                ROR     SUPERBNK
                XCH     L
```

TWIDDLE 是一个优化方案，用于任务地址与调用方在同一 bank 的情况。调用约定：
```agc
        CA      DELTAT
        TC      TWIDDLE
        ADRES   DESIRED TASK    # Single word — no BBCON needed
        RELINT                  # Returns here
```

追踪：
1. A = 增量时间。`TS L` 将其保存在 L 中。
2. `CA POSMAX; ADS Q`——将 16383 加到 Q。由于 Q 指向 ADRES 字（一个小地址），这会产生溢出。当 ADS 溢出时，它存储溢出纠正后的值（Q-1），并将 A 设为 +1。
3. `CA BBANK; EXTEND; ROR SUPERBNK`——读取当前 BBANK 与超级 bank 的 OR 值。这是调用方自己的 BBCON。
4. `XCH L`——将此 BBCON 与 L（保存了增量时间）交换。现在 A = 增量时间，L = BBCON。

然后执行落入 WAITLIST。WAITLIST 中的 `XCH Q; TS WAITEXIT` 保存返回地址。`INDEX WAITEXIT; DCA 0`——因为 TWIDDLE 调整了 Q 使其指向前一个字，这拾取了单个 ADRES 字（到 A）和后续字（RELINT，成为 L 中不关心的值——实际上 L 已经有了来自 TWIDDLE 设置的 BBCON）。

### Bank 切换和核心插入逻辑

```agc
DLY2            CAF     WAITBB          # ENTRY FROM FIXDELAY AND VARDELAY.
                XCH     BBANK
                TCF     WAIT2
```

切换到包含 WAIT2（Bank 01）的 bank，保存调用方的 BBANK。

```agc
WAIT2           TS      WAITBANK        # BBANK OF CALLING PROGRAM.
                CA      Q
                EXTEND
                BZMF    WAITPOOH
```

保存调用方的 bank。检查 Q 中的增量时间是否为零或负——如果是，分支到 WAITPOOH（错误处理器）。

### TIME3 竞争条件检查

```agc
                CS      TIME3
                AD      BIT8            # BIT 8 = OCT 200
                CCS     A               # TEST 200 - C(TIME3).
```

这是插入代码中最微妙的部分。它处理一个竞争条件：TIME3 可能在我们读取它和更新它之间*溢出*。代码测试 TIME3 是否小于 200（八进制）。如果 TIME3 < 200，它可能刚刚溢出，其值表示 `T - T1`（自上次任务到期以来的时间）而非 `1.0 - (T1 - T)`。

四路 CCS 分支处理两种情况：

```agc
                AD      OCT40001        # OVERFLOW HAS OCCURRED. SET C(A) =
                CS      A               # T - T1 + 1.0 - 201

                AD      OCT40201
                AD      Q               # RESULT = TD - T1 + 1.
```

经过这些算术运算（我将省略完整的追踪——它精心构建以产生相同结果，无论竞争如何），A 包含 `TD - T1 + 1`，其中 TD 是期望的触发时间，T1 是当前调度的第一个任务的时间。

### 插入搜索：WTLST5

```agc
                CCS     A               # TEST TD - T1 + 1.

                AD      LST1            # IF TD - T1 POS, GO TO WTLST5 WITH
                TCF     WTLST5          # C(A) = (TD - T1) + C(LST1) = TD-T2+1

                NOOP
                CS      Q
```

如果 TD > T1（新任务在当前第一个任务之后触发），我们进入 WTLST5——排序插入搜索。

如果 TD ≤ T1（新任务在当前第一个任务*之前*触发），我们走下方分支：新任务成为新的第一个任务，TIME3 被更新，旧的第一个任务被推入列表。

**WTLST5——展开的搜索循环：**

```agc
WTLST5          CCS     A               # TEST TD - T2 + 1
                AD      LST1 +1
                TCF     +4
                AD      ONE
                TC      WTLST2
                OCT     1

 +4             CCS     A               # TEST TD - T3 + 1
                AD      LST1 +2
                TCF     +4
                AD      ONE
                TC      WTLST2
                OCT     2
```

这是一个完全展开的类二分搜索扫描。每个块：
1. 通过 CCS 测试 `TD - T(n) + 1`。
2. 如果为正（TD > T(n)）：加下一个 LST1 增量，计算 `TD - T(n+1) + 1`，继续到下一块。
3. 如果为零或负（TD ≤ T(n)）：找到插入点。以内联常量作为后续内容调用 `TC WTLST2`。

展开消除了循环开销——在每条指令需要 11.72µs、并在 INHINT 内运行的系统中至关重要。九次迭代 × 6 字/次 = 54 字 ROM，但保证了最坏情况的时序。

### WTLST2：实际插入

```agc
WTLST2          TS      WAITTEMP        # C(A) = -(TD - T + 1)
                INDEX   Q
                CAF     0
                TS      Q               # INDEX VALUE INTO Q.

                CAF     ONE
                AD      WAITTEMP
                INDEX   Q               # C(A) = -(TD - T ) + 1.
                ADS     LST1 -1         #                N
```

这修改了插入点*之前*的 LST1 条目。旧值为 `-(T(n+1) - T(n)) + 1`。加上 `-(TD - T(n+1)) + 1` 后，结果为 `-(TD - T(n)) + 1`——从 T(n) 到 TD 的新增量。

```agc
                CS      WAITTEMP
                INDEX   Q
                TCF     WTLST4
```

然后以 A = `-(T(n+1) - TD) + 1` 落入 WTLST4——从 TD 到 T(n+1) 的增量，成为 TD 之后插入的新条目。

### XCH/DXCH 旋转链：WTLST4

```agc
WTLST4          XCH     LST1
                XCH     LST1 +1
                ...
                XCH     LST1 +7
```

从索引的入口点开始（`INDEX Q; TCF WTLST4` 跳入链的*中间*），每个 XCH 将当前 A 值推入槽并取出旧值，将所有内容向下级联。INDEX 导致在链中的位置 Q 处入口，所以只有插入点及以下的条目被移动。

LST2 的相同模式用 DXCH（双交换）重复，移动 2CADR 条目：

```agc
                CA      WAITADR
                INDEX   Q
                TCF     +1

                DXCH    LST2
                DXCH    LST2 +2
                ...
                DXCH    LST2 +16D
```

`INDEX Q; TCF +1` 导致在正确位置跳入 DXCH 链的中间。

### 溢出检查

```agc
                DXCH    LST2 +16D
                AD      ENDTASK
                EXTEND
                BZF     LVWTLIST        # SUCCESS
                TCF     WTABORT         # OVERFLOW — ALARM 1203
```

级联之后，从 LST2+16（最后一个槽）替换出来的内容应该是 ENDTASK。由于 ENDTASK 在固定-固定内存中，`AD ENDTASK` 将 ENDTASK 常量加到被替换的地址。如果它们互补（即被替换的值确实是 ENDTASK），结果为 ±0，BZF 分支到成功返回。如果不是，一个真实的任务被替换出来——列表已满。

### 返回到调用方

```agc
LVWTLIST        DXCH    WAITEXIT
                AD      TWO
                DTCB
```

加载保存的返回地址和 bank 信息。`AD TWO` 跳过 2CADR（2 个字）到达 L+3——调用方代码中 2CADR 之后的指令。`DTCB`（DXCH Z）在 bank 恢复后跳转到那里。

---

## 4. FIXDELAY、VARDELAY 和 LONGCALL

### FIXDELAY：内联延迟常量

```agc
FIXDELAY        INDEX   Q               # BOTH ROUTINES MUST BE CALLED UNDER
                CAF     0               # WAITLIST CONTROL AND TERMINATE THE TASK
                INCR    Q               # IN WHICH THEY WERE CALLED.
```

从运行中的任务（在中断上下文中）调用。Q 指向返回地址——程序员在那里放置了一个延迟常量。`INDEX Q; CAF 0` 加载该常量。`INCR Q` 将 Q 前进超过常量，使任务在正确位置恢复。

落入 VARDELAY。

### VARDELAY：A 中的延迟值

```agc
VARDELAY        XCH     Q               # DT TO Q. TASK ADRES TO WAITADR.
                TS      WAITADR
                CA      BBANK           # BBANK IS SAVED DURING DELAY.
                EXTEND
                ROR     SUPERBNK        # ADD SBANK TO BBCON.
                TS      L
                CAF     DELAYEX
                TS      WAITEXIT        # GO TO TASKOVER AFTER TASK ENTRY.
                TCF     DLY2
```

这建立了一个自引用的 WAITLIST 调用：被调度的"任务"是*当前任务的延续*（Q 保存返回地址，成为 WAITADR）。当前 BBANK+超级 bank 被捕获为 BBCON。WAITEXIT 设置为 DELAYEX（`TCF TASKOVER -2`），所以任务插入等待列表后，控制转到 TASKOVER 而非返回到调用方。

使用模式：
```agc
MYTASK          ...                     # Do some work
                CA      DT100MS         # 100ms delay
                TC      VARDELAY        # Reschedule self
                ...                     # Continues here after delay
                TC      TASKOVER        # Done
```

或使用 FIXDELAY：
```agc
MYTASK          ...                     # Do some work
                TC      FIXDELAY
                DEC     100             # 1 second delay (100 centiseconds)
                ...                     # Continues here after delay
                TC      TASKOVER
```

### LONGCALL：超越 162.5 秒

最大 WAITLIST 延迟为 16250 厘秒（162.5 秒），受单精度值的 14 位量值限制。LONGCALL 使用迭代方法将覆盖范围扩展到约 2.56 小时。

```agc
LONGCALL        DXCH    LONGTIME        # OBTAIN THE DELTA TIME
```

以 A、L 中的双精度增量时间（以 TIME2、TIME1 为比例——高字在 A，低字在 L）调用。目标任务的 2CADR 内联于后。

```agc
LONGCYCL        EXTEND                  # CAN WE SUCCESFULLY TAKE ABOUT 1.25
                DCS     DPBIT14         # MINUTES OFF OF LONGTIME
                DAS     LONGTIME
```

每次迭代从 LONGTIME 中减去 BIT14（八进制 20000 = 十进制 8192，低字中，高字为 0）。以厘秒计的 BIT14 = 81.92 秒 ≈ 1.37 分钟。

```agc
                CCS     LONGTIME +1     # THE REASONING BEHIND THIS PART IS
                TCF     MUCHTIME        # INVOLVED...
                NOOP                    # CAN'T GET HERE
                TCF     +1
                CCS     LONGTIME
                TCF     MUCHTIME
```

如果还有大量时间剩余（减法后 LONGTIME 仍为正），分支到 MUCHTIME：

```agc
MUCHTIME        CA      BIT14           # WE HAVE OVER OUR ABOUT 1.25 MINUTES
                TC      WAITLIST        # SO SET UP FOR ANOTHER CYCLE THROUGH HERE
                EBANK=  LST1
                2CADR   LONGCYCL

                TCF     LONGRTRN        # NOW EXIT PROPERLY
```

这将 LONGCYCL 本身调度为延迟 81.92 秒的 WAITLIST 任务。当它触发时，从 LONGTIME 再减去一个 BIT14 并重复，直到剩余时间可以放入单个 WAITLIST 调用。

```agc
LASTTIME        CA      BIT14           # GET BACK THE CORRECT DELTA T FOR WAITLIST
                ADS     LONGTIME +1
                TC      WAITLIST
                EBANK=  LST1
                2CADR   GETCADR         # THE ENTRY TO OUR LONGCADR
```

当剩余时间足够小时，加回最后一次 BIT14 减法（因为我们多减了一次），并调度 GETCADR——它简单地加载保存的 LONGCADR 并跳转到实际的目标任务。

### 时序约束摘要

| 参数 | 值 | 注释 |
|------|-----|-----|
| 最小延迟 | 1 厘秒（10ms） | 一个 TIME3 计时脉冲 |
| 最大 WAITLIST 延迟 | 16250 厘秒（162.5 秒） | 头部的 `DTMAX` |
| 最大 LONGCALL 延迟 | ~2^28 × 10ms ≈ 31 天 | DP 计数器范围 |
| 实际 LONGCALL 最大值 | ~2.56 小时 | 受任务时间线限制 |
| 定时器分辨率 | 10ms（TIME3 计时率） | 硬件决定 |
| 插入时间（最坏情况） | ~147µs + 计数器增量 | 头部分析 |

---

## 5. 时序分析

### 手写的 WCET 分析

模块头部（第 1117-1118 页）包含一个极具现代感的最坏情况执行时间（WCET）分析：

```
LET T0  = THE TIME OF THE TC WAITLIST
LET TS  = T0 + 147U + COUNTER INCREMENTS (SET UP TIME)
LET X   = TS - (100TS)/100  (VARIANCE FROM COUNTERS)
LET Y   = LENGTH OF TIME OF INHIBIT INTERRUPT AFTER T3RUPT
LET Z   = LENGTH OF TIME TO PROCESS TASKS WHICH ARE DUE THIS T3RUPT
          BUT DISPATCHED EARLIER. (Z=0, USUALLY).
LET DELTD = THE ACTUAL TIME TAKEN TO GIVE CONTROL TO 2CADR
THEN DELTD = TS + DELTA T - X + Y + Z + 1.05MS* + COUNTERS*
```

分解如下：

- **147µs 设置时间（TS）：** 从 `TC WAITLIST` 到完成列表插入的时间。以每 MCT 11.72µs 计，约为 12.5 条指令——与 WAITLIST → WAIT2 → 插入的关键路径一致。

- **X（计数器方差）：** TIME3 每 10ms 计时一次。任务的实际开始时间被量化到最近的 10ms 边界。X 表示亚计时脉冲方差——插入发生在 10ms 周期内的位置。

- **Y（中断禁止时间）：** 如果当 T3RUPT 触发时中断被禁止（通过 INHINT），分派会延迟到 RELINT。这在实践中是抖动最重要的来源——代码其他地方的长 INHINT 区段直接延迟所有等待列表任务。

- **Z（任务队列清空时间）：** 如果多个任务同时到期（RUPTAGN 级联），较早的任务必须在较晚的任务开始之前完成。通常为零，因为同时到期的任务很少见。

- **1.05ms（等待列表处理）：** T3RUPT 处理程序自身的执行时间——LST1/LST2 旋转链、TIME3 更新和 DTCB 分派。约 90 条指令 × 11.72µs ≈ 1.05ms。

- **计数器：** 未编程序列（PINC、MINC 等）占用 CPU 周期进行计数器更新。每次需要 1 MCT（11.72µs），可能需要服务多个计数器。

### 实时保证

等待列表提供具有有界最坏情况抖动的**软实时**保证：

1. **确定性插入：** 展开的搜索循环具有固定的最坏情况时序，与列表占用率无关（始终遍历所有 9 个槽）。

2. **有界分派延迟：** 任务分派在计划时间的一个 T3RUPT 处理程序执行内发生，加上前台代码的任何 INHINT 延迟。

3. **无优先级反转：** 任务严格按时间顺序执行。等待列表中没有任务优先级的概念——只有执行模块有优先级。

4. **原子列表操作：** 所有列表操作都在中断禁止下运行（入口时 INHINT，ISR 内运行以进行分派）。不可能并发修改。

5. **保证溢出检测：** ENDTASK 哨兵检查确保列表溢出总是被检测并中止（警报 1203），而不是无声地破坏数据。

### 与现代 RTOS 定时器系统的比较

| 方面 | AGC 等待列表 | 现代 RTOS（如 FreeRTOS） |
|------|------------|------------------------|
| **数据结构** | 排序数组，线性插入 | 通常是增量列表或定时器轮 |
| **插入复杂度** | O(n) 最坏情况，n=9 最大 | O(1) 到 O(log n) 取决于结构 |
| **分派复杂度** | O(1)——始终是第一个条目 | O(1)——队列头 |
| **定时器分辨率** | 10ms（硬件固定） | 可配置（通常 1ms 或更少） |
| **最大待处理定时器** | 9（编译时固定） | 动态（堆分配） |
| **溢出处理** | 硬中止（警报 1203） | 通常返回错误码 |
| **内存开销** | 27 字固定 | 每定时器开销，堆碎片风险 |
| **级联分派** | RUPTAGN 循环处理同时任务 | 通常在一个 ISR 中处理所有过期 |
| **长延迟** | LONGCALL（迭代重调度） | 32/64 位定时器，无需变通 |
| **抖动来源** | INHINT 区段，计数器服务 | 中断延迟，高优先级 ISR |

AGC 等待列表最显著的特点是其极度的经济性。整个调度器——插入、分派、级联、溢出检测、自重调度和长延迟支持——全部压缩在不到 200 字的 ROM 中。排序增量列表与固定大小数组的方法对于约束条件而言是最优的：极少数量的任务（从未超过 9 个）、硬实时要求，以及对内存的绝对节约。

现代定时器轮和分层时序设施是为数千个并发定时器设计的。AGC 从未需要这种规模——9 个任务就足够了，因为整个系统从一开始就是在这种约束下设计的。每个子系统都清楚地知道它可以消耗多少等待列表槽，并且总数在开发期间通过静态分析得到验证。

头部中的 WCET 分析——1966 年手写——预示了直到 1980 年代才在实时系统研究中被正式化的技术。MIT 仪器实验室的工程师们正在做我们现在称为可调度性分析的工作，手工完成，用汇编语言，针对一种一次性计算机架构，误差以微秒计。等待列表可能是整个 AGC 代码库中最优雅的实时系统工程作品。
