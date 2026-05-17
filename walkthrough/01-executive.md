# The Executive：阿波罗11号的操作系统，约500行代码

## 月球模块作业调度器逐指令详解

阿波罗制导计算机没有操作系统。没有内核，没有调度器二进制文件，也没有由特权代码管理的进程表。取而代之的是，**Executive** 模块——大约600行手写的AGC4汇编——从零开始实现了整个协作式多任务系统。阿波罗11号任务期间在LM计算机上运行的每一个作业——制导方程、自动驾驶计算、显示更新、宇航员按键处理——都由这段代码负责创建、调度、挂起和销毁。

这是对 `Luminary099/EXECUTIVE.agc` 的逐行详解，这是在人类首次登月期间运行在月球模块上的作业调度器。

---

## 1. 核心数据结构

### 1.1 什么是"核心组"？

Executive 使用**核心组**来管理作业——固定大小的可擦除内存块，作为AGC的进程控制块（PCB）等价物。每个核心组保存了挂起和恢复一个作业所需的一切信息。

核心组的数量在第~154行（第1106页）定义：

```agc
NO.CORESDEC7
```

共有**7个核心组**，编号0–6。核心组0是特殊的：它代表**当前正在运行的作业**。其寄存器（`PRIORITY`、`LOC`、`MPAC`、`PUSHLOC`等）直接通过基地址访问。其他6个核心组通过存储在 `LOCCTR` 中的偏移量来访问。

每个核心组占用12个连续的可擦除内存字，由 `COREINC` 定义：

```agc
COREINCDEC12# 12 REGISTERS PER CORE SET.
```

### 1.2 核心组字段

每个12字的核心组包含：

| 偏移 | 寄存器 | 用途 |
|--------|----------|---------|
| 0 | `PRIORITY` | 作业优先级 + VAC区域指针（低9位） |
| 1 | `LOC` | 作业当前执行地址（FCADR）。符号位编码作业类型 |
| 2 | `BANKSET` | bank寄存器状态（BBANK + superbank），用于恢复作业 |
| 3–10 | `MPAC` 到 `MPAC+7` | 多用途累加器——8个字的工作存储空间 |
| 11 | `PUSHLOC` | 解释器下推指针。符号位编码溢出状态 |

作业1–6的核心组在可擦除内存中连续排列，每个核心组从前一个偏移12个字开始。代码中普遍使用的 `INDEX LOCCTR` 模式通过将相对偏移加到基地址来访问正确的核心组。

### 1.3 PRIORITY 寄存器：一个字中的三种状态

`PRIORITY` 寄存器是 Executive 状态机的核心。它使用1's补码算术的符号约定，在一个字中编码三种不同的作业状态：

| 值 | 状态 | 含义 |
|-------|-------|---------|
| **正数（>0）** | 活跃 | 作业已准备好运行。大小编码优先级级别 |
| **负数（<-0）** | 休眠 | 作业正在等待事件。保留优先级的补码 |
| **负零（-0）** | 空闲 | 核心组可供分配 |

这种编码之所以优雅，是因为 `CCS`（计数、比较和跳过）指令通过其4路跳转自然地区分所有三种状态：

```agc
CCSPRIORITY# (page 1106, line ~153)
TCFNEXTCORE# POSITIVE: active job, skip this core set
NO.CORESDEC7# +0: (falls through — never happens for PRIORITY)
TCFNEXTCORE# NEGATIVE: sleeping job, skip this core set
# -0: falls through to CORFOUND — free core set!
```

`CCS` 指令执行以下操作：将 `DABS(K)` 加载到A（"减小的绝对值"——绝对值减一），然后根据原始值的符号和零值执行4路跳转。当 `PRIORITY` 为-0（全1，八进制 `77777`）时，代码落入 `CORFOUND`，表示该核心组可用。

### 1.4 VAC 区域

`PRIORITY` 的低9位存储指向作业 **VAC 区域**的指针——一块可擦除内存，被解释型（数学密集型）作业用作暂存区。共有5个VAC区域，由使用寄存器 `VAC1USE` 到 `VAC5USE` 跟踪：

```agc
FINDVAC2TSEXECTEM1
CCSVAC1USE# (page 1106)
TCFVACFOUND
CCSVAC2USE
TCFVACFOUND
CCSVAC3USE
TCFVACFOUND
CCSVAC4USE
TCFVACFOUND
CCSVAC5USE
TCFVACFOUND
```

这是线性扫描——依次尝试VAC1、VAC2，以此类推。如果全部5个都被占用，代码将落入带有报警码 `1201` 的 `BAILOUT1`：

```agc
TCBAILOUT1
OCT1201# NO VAC AREAS.
```

**这就是著名的1202报警的起源。** 在阿波罗11号着陆期间，来自交会雷达的硬件中断消耗了足够多的CPU时间，使 Executive 的核心组被填满，触发了1202报警（"无核心组"变体——见下文）。Executive 的设计使其能够从容恢复：低优先级作业被丢弃，而关键制导继续运行。

---

## 2. 作业创建：FINDVAC 和 NOVAC

### 2.1 两个入口点

Executive 提供两种创建作业的方式：

- **`FINDVAC`**（第1103页）：创建需要VAC区域的作业。用于需要解释器暂存区的解释型（数学密集型）作业。
- **`NOVAC`**（第1103页）：创建**不**需要VAC区域的作业。用于基本（原生汇编）作业。

两者都需要：
- 累加器（A寄存器）中新作业的**优先级**
- 紧跟调用指令之后，内存中新作业入口点的 **2CADR**（双字地址：FCADR + BBCON）

### 2.2 逐步跟踪 NOVAC

```agc
NOVACINHINT# Disable interrupts — we're modifying shared state
ADFAKEPRET# Add offset: LOC(MPAC+6) - LOC(QPRET)
TSNEWPRIO# Store priority (with NOVAC flag encoded)

EXTEND
INDEXQ# Q holds caller's return address
DCA0# Load 2CADR from the two words after the TC NOVAC call
DXCHNEWLOC# Store the job's entry address in NEWLOC, NEWLOC+1
CAFEXECBANK# Load the CADR of the Executive's bank
XCHFBANK# Switch to Executive's fixed bank, save caller's bank
TSEXECTEM1# Save caller's bank for later restoration
TCFNOVAC2# Jump into the Executive's switched bank
```

关键细节：

1. **`INHINT`** 立即禁用中断。作业创建会修改共享数据结构（优先级寄存器、核心组），必须是原子操作。

2. **`AD FAKEPRET`** 将一个偏移量加到优先级值上。`FAKEPRET` 被定义为 `ADRES MPAC -36D`，等于 `LOC(MPAC+6) - LOC(QPRET)`。这在优先级字中编码了一个标志，用于区分NOVAC作业和FINDVAC作业——具体来说，低9位将指示"无VAC区域"，而不是指向VAC区域基地址。

3. **`INDEX Q` / `DCA 0`**：这是一个关键的AGC惯用法。调用我们的 `TC NOVAC` 指令将返回地址存储在Q中。调用者代码中 `TC NOVAC` **之后**的两个字包含新作业的2CADR（双字完整地址）。`INDEX Q` 通过将Q的值加到 `DCA 0` 的地址字段来修改下一条指令，实际上使其变为 `DCA Q`——将Q及其之后的两个字加载到A和L中。然后 `DXCH NEWLOC` 存储它们。

4. **bank切换**：Executive 的核心逻辑位于Bank 01（切换固定内存），但入口点（`NOVAC`、`FINDVAC`等）位于Block 02（固定-固定内存，可从任何地方直接寻址）。`XCH FBANK` / `TCF NOVAC2` 序列切换到 Executive 的bank。

### 2.3 逐步跟踪 FINDVAC

```agc
FINDVACINHINT# Disable interrupts
TSNEWPRIO# Store priority directly (no FAKEPRET offset)
EXTEND
INDEXQ
DCA0# Load 2CADR of job entry point
SPVACINDXCHNEWLOC# Store in NEWLOC
CAFEXECBANK
XCHFBANK# Switch to Executive's bank
TCFFINDVAC2# Jump to VAC area allocation code
```

与NOVAC的关键区别：**没有 `AD FAKEPRET`**。优先级直接存储，控制转移到 `FINDVAC2` 而非 `NOVAC2`。`FINDVAC2` 首先扫描空闲的VAC区域（上面显示的 `CCS VAC1USE` ... 链），然后落入 `NOVAC2` 使用的相同核心组分配代码。

### 2.4 VAC 区域分配（VACFOUND）

当找到空闲的VAC区域时：

```agc
VACFOUNDADTWO# CCS left DABS(VACnUSE) in A; add 2 to get
ZL#   the address of the VAC area's first word
INDEXA# Use that address as an index
LXCH0 -1# Exchange L (zero) with VACnUSE — zeroing
#   the use register marks it as "in use"
ADSNEWPRIO# Add VAC area address into low 9 bits of priority
```

这是一段精妙的代码。找到空闲VAC区域的 `CCS` 指令在A中留下了 `DABS(VACnUSE)`——减小的绝对值。加2恢复原始地址（CCS减少1，我们需要VAC区域的基地址，而不是使用寄存器本身）。然后 `LXCH 0 -1` 同时将使用寄存器清零（标记为已分配）并获取旧值。最后，`ADS NEWPRIO` 将VAC区域地址打包到优先级字的低9位。

### 2.5 核心组分配（NOVAC2 / NOVAC3）

在VAC区域分配之后（或对于NOVAC作业直接），代码扫描空闲的核心组：

```agc
NOVAC2CAFZERO# Start scanning from core set 0
TSLOCCTR# LOCCTR = offset to current core set
CAFNO.CORES# Loop counter = 7
NOVAC3TSEXECTEM2# Save loop counter
INDEXLOCCTR
CCSPRIORITY# Check this core set's priority register
TCFNEXTCORE# Positive: active job, try next
NO.CORESDEC7# (constant embedded in the CCS skip chain)
TCFNEXTCORE# Negative: sleeping job, try next
# -0: free! Fall through to CORFOUND
```

循环为每个核心组将 `LOCCTR` 增加 `COREINC`（12）：

```agc
NEXTCORECAFCOREINC# 12 registers per core set
ADSLOCCTR# Move to next core set
CCSEXECTEM2# Decrement and test loop counter
TCFNOVAC3# More core sets to check
...
TCBAILOUT1# NO CORE SETS AVAILABLE.
OCT1202# <<< THE FAMOUS 1202 ALARM
```

如果全部7个核心组都被占用，**1202**报警触发。这就是阿波罗11号着陆期间响起的报警。由于交会雷达（本应关闭）产生了中断，作业产生速度超过了完成速度，Executive 无法找到空闲的核心组。

### 2.6 核心组初始化（CORFOUND）

当找到空闲的核心组时：

```agc
CORFOUNDCANEWPRIO# Load the new job's priority
INDEXLOCCTR# Index into the found core set
TSPRIORITY# Set its priority register
MASKLOW9# Extract low 9 bits (VAC area pointer)
INDEXLOCCTR
TSPUSHLOC# Set the push-down pointer for the interpreter
```

然后进行关键检查——这是核心组0（"运行"位置）吗？

```agc
CCSLOCCTR# If LOCCTR = 0, we're loading core set 0
TCFSETLOC# Non-zero: normal setup
TSOVFIND# Zero: set up OVFIND and FIXLOC immediately
CAPUSHLOC#   because this job runs NOW
TSFIXLOC
```

### 2.7 优先级比较（SETLOC）

如果新作业被放置在非零核心组中，Executive 必须确定它是否应该抢占当前作业：

```agc
SETLOCDXCHNEWLOC# Store entry address in the core set's LOC registers
INDEXLOCCTR
DXCHLOC
INDEXNEWJOB# NEWJOB points to highest-waiting-priority core set
CSPRIORITY# Negate that priority
ADNEWPRIO# Add new priority: result > 0 means new is higher
EXTEND
BZMFENDFIND# If new ≤ current highest, don't preempt
CALOCCTR# New job IS higher priority:
TSNEWJOB# Set NEWJOB to point to the new core set
TCFENDFIND
```

这是调度决策。`NEWJOB` 是一个全局变量，始终指向优先级最高的等待作业。当新创建的作业优先级高于 `NEWJOB` 当前引用的作业时，`NEWJOB` 会被更新。实际的上下文切换发生在稍后，当运行中的作业通过 `CHANG1`/`CHANG2` 主动让出时。

---

## 3. 调度与上下文切换

### 3.1 NEWJOB 的作用

`NEWJOB` 是 Executive 的核心调度变量。它可以持有三种值：

| 值 | 含义 |
|-------|---------|
| **正数** | 指向优先级高于运行中作业的核心组的偏移量 |
| **+0** | 当前运行中的作业（核心组0）具有最高优先级 |
| **-0** | 没有活跃作业；计算机应进入空闲状态 |

Executive 从不抢占运行中的作业。相反，它设置 `NEWJOB` 并等待运行中的作业主动检查。这就是**协作式多任务**——作业必须显式让出。

### 3.2 主动让出：CHANG1 和 CHANG2

作业通过调用以下之一来让出：

- **`CHANG1`**（第1103页）：用于基本（原生汇编）作业
- **`CHANG2`**（第1103页）：用于解释型作业

```agc
# Basic job yield:
CHANG1LXCHQ# Save return address in L
CAFEXECBANK# Load Executive's bank address
XCHBBANK# Switch to Executive's bank, save current bank
TCFCHANJOB# Enter the context switch routine

# Interpretive job yield:
CHANG2CSLOC# Negate LOC — negative LOC signals "interpretive"
TSL
 +2CAFEXECBANK
TSBBANK
TCFCHANJOB -1
```

`LOC` 的符号至关重要：**正LOC = 基本作业，负LOC = 解释型作业**。这就是 Executive 在恢复作业时知道使用哪种分发机制的方式。

### 3.3 上下文切换（CHANJOB）

`CHANJOB` 例程（第1108–1109页）是 Executive 的核心。它将核心组0中的每个寄存器与 `NEWJOB` 指向的核心组进行交换：

```agc
CHANJOBINHINT# Disable interrupts during the swap
EXTEND
RORSUPERBNK# Pick up current superbank for BBCON
XCHL# LOC in A, BBCON in L
 +4INDEXNEWJOB
DXCHLOC# Swap LOC and BANKSET between core set 0
DXCHLOC#   and the NEWJOB core set
```

然后使用 `DXCH` 两字一组交换8字的MPAC区域：

```agc
DXCHMPAC# Swap MPAC+0,+1
INDEXNEWJOB
DXCHMPAC
DXCHMPAC
DXCHMPAC +2# Swap MPAC+2,+3
INDEXNEWJOB
DXCHMPAC +2
DXCHMPAC +2
DXCHMPAC +4# Swap MPAC+4,+5
INDEXNEWJOB
DXCHMPAC +4
DXCHMPAC +4
DXCHMPAC +6# Swap MPAC+6,+7
INDEXNEWJOB
DXCHMPAC +6
DXCHMPAC +6
```

这是一种**三次DXCH交换**模式。每组三条 `DXCH` 指令的工作方式如下：
1. `DXCH MPAC` — 将核心组0的MPAC加载到A,L，同时将A,L（保存了上一次交换的内容）存储到MPAC中
2. `INDEX NEWJOB` / `DXCH MPAC` — 将A,L（现在是核心组0的旧值）与新作业的MPAC交换
3. `DXCH MPAC` — 将新作业的旧MPAC值存储到核心组0中

结果：核心组0现在拥有新作业的MPAC值，而NEWJOB核心组拥有旧作业的值。

### 3.4 溢出标志处理

MPAC交换之后，代码处理 `OVFIND` / `PUSHLOC` 状态——解释器的溢出指示符被编码在 `PUSHLOC` 的符号位中：

```agc
CAFZERO
XCHOVFIND# Get current overflow flag, clear it
EXTEND
BZF+3# If zero, skip
CSPUSHLOC# If non-zero, negate PUSHLOC
TSPUSHLOC#   (negative PUSHLOC = overflow was set)

DXCHPUSHLOC# Swap PUSHLOC and PRIORITY
INDEXNEWJOB
DXCHPUSHLOC
DXCHPUSHLOC
```

然后恢复FIXLOC，并从传入的PUSHLOC中解码溢出标志：

```agc
CAFLOW9# Extract VAC area pointer
MASKPRIORITY
TSFIXLOC# Set FIXLOC for the new job

CCSPUSHLOC# Check sign of incoming PUSHLOC
CAFZERO# Positive: no overflow
TCFENDPRCHG -1# (skip to dispatch)
CSPUSHLOC# Negative: overflow was set
TSPUSHLOC#   un-negate PUSHLOC
CAFONE#   set OVFIND = 1
XCHOVFIND
TSNEWJOB# (NEWJOB gets the old OVFIND value — effectively resets)
```

### 3.5 作业分发（ENDPRCHG）

最后一步分发新作业：

```agc
ENDPRCHGRELINT# Re-enable interrupts
DXCHLOC# Load job's address into A,L
EXTEND
BZMF+2# If LOC is negative, job is interpretive
DTCB# Positive LOC: basic job — DTCB dispatches
#   (DTCB = DXCH Z, jumps to address in A,L
#    while switching both banks)
```

对于解释型作业：

```agc
COM# Negate the (negative) LOC
ADONE# Add 1 to get the true address
TSLOC# Store it back
TCFINTRSM# Jump to interpreter resume routine
```

`DTCB` 指令（`DXCH Z`）非常紧凑——它在单条指令中同时从A和L加载程序计数器（Z）和bank寄存器，实际上执行了一次带bank切换的完整远跳转。

### 3.6 优先级扫描（EJSCAN）

当作业结束或休眠时，Executive 必须找到优先级最高的活跃作业。`EJSCAN`（第1113–1115页）对所有7个核心组的 `PRIORITY` 寄存器执行线性扫描：

```agc
EJSCANCCSPRIORITY +12D# Core set 1 (offset 12 from base)
TCEJ1# If positive (active), evaluate priority
TCCCSHOLE# +0: shouldn't happen
TCF+1# Negative or -0: skip

CCSPRIORITY +24D# Core set 2 (offset 24)
TCEJ1
TCCCSHOLE
TCF+1

CCSPRIORITY +36D# Core set 3
TCEJ1
-CCSPR-CCSPRIORITY# (This label stores -CCS PRIORITY for address calc)
TCF+1

CCSPRIORITY +48D# Core set 4
...
CCSPRIORITY +60D# Core set 5
...
CCSPRIORITY +72D# Core set 6
...
CCSPRIORITY +84D# Core set 7 (if it exists — note: 84/12 = 7)
```

`EJ1` 子例程将当前候选者与当前最佳候选者进行比较：

```agc
EJ1TSBUF +2# Save DABS(PRIORITY) — this is the candidate
ADBUF +1# Add negative of current best (BUF+1 holds -best)
CCSA
CSBUF +2# A > 0: new candidate is higher priority
TCFEJ2# Take the new candidate
NOOP# A = +0 or negative: keep current best
INDEXQ
TC2# Continue scan (skip 2 words to next CCS)
```

`EJ2` 记录新的最佳候选者：

```agc
EJ2TSBUF +1# Store -new_best_priority
EXTEND
QXCHBUF# Save Q (points back into the scan loop)
INDEXBUF
TC2# Continue scan from where Q pointed
```

扫描完成后，`BUF` 包含获胜的 `CCS PRIORITY+nD` 指令的Q值（指令地址）。代码对该地址进行算术运算以计算核心组偏移量：

```agc
INDEXA
CAF0 -1# Load the instruction at BUF-1
AD-CCSPR# Subtract the base address (-CCS PRIORITY)
TSNEWJOB# Result = offset to the winning core set
TCFCHANJOB -2# Perform the context switch
```

这是一个非凡的技巧：扫描循环自身的指令地址编码了核心组偏移量。通过减去已知的参考点（`-CCSPR`），代码恢复了哪个核心组获胜——无需单独的数据结构。

---

## 4. 作业生命周期

### 4.1 作业休眠（JOBSLEEP）

作业通过调用 `JOBSLEEP`（A中存放唤醒地址）来主动休眠：

```agc
JOBSLEEPTSLOC# Save wake-up address in LOC
CAFEXECBANK
TSFBANK
TCFJOBSLP1# Switch to Executive's bank
```

在 Executive 的bank中：

```agc
JOBSLP1INHINT# Disable interrupts
CSPRIORITY# Negate the priority
TSPRIORITY# Negative priority = sleeping job
CAFLOW7
MASKBBANK
EXTEND
RORSUPERBNK# Save current bank state
TSBANKSET
CSZERO# Load -0
JOBSLP2TSBUF +1# Initialize best-priority to -0 (worst)
TCFEJSCAN# Scan for highest priority active job
```

休眠作业的优先级被取反——这就是 Executive 将作业标记为休眠的方式。然后扫描找到下一个优先级最高的活跃作业来运行。

### 4.2 作业唤醒（JOBWAKE）

要唤醒一个休眠的作业，调用者在A中提供休眠作业 `LOC` 值的CADR：

```agc
JOBWAKEINHINT
TSNEWLOC# Save the CADR to match against
CSTWO# Adjust Q to point past the 2CADR that follows
ADSQ
CAFEXECBANK
XCHFBANK
TCFJOBWAKE2
```

`JOBWAKE2` 扫描所有核心组，寻找 `LOC` 匹配的休眠作业：

```agc
JOBWAKE2TSEXECTEM1
CAFZERO
TSLOCCTR# Start at core set 0
CAFNO.CORES
JOBWAKE4TSEXECTEM2
INDEXLOCCTR
CCSPRIORITY
TCFJOBWAKE3# Active job — skip
COREINCDEC12
TCFWAKETEST# Sleeping job — check if it matches
```

匹配测试：

```agc
WAKETESTCSNEWLOC
INDEXLOCCTR
ADLOC# Compare LOC with target CADR
EXTEND
BZF+2# If they match (difference = ±0), wake it
TCFJOBWAKE3# No match, try next core set
```

当找到匹配时，优先级被反取反（重新补码为正数），作业重新进入调度系统：

```agc
INDEXLOCCTR
CSPRIORITY# Re-complement: negative → positive
TSNEWPRIO
INDEXLOCCTR
TSPRIORITY# Job is now active again
```

代码随后从存储的LOC和BANKSET值重建完整的2CADR（地址+bank状态），然后调用 `SETLOC` 检查被唤醒的作业是否应该抢占当前作业。

如果没有找到匹配的休眠作业，`LOCCTR` 被设置为-1作为给调用者的信号：

```agc
CSONE
TSLOCCTR# -1 means "job not found"
TCFENDFIND
```

### 4.3 作业终止（ENDOFJOB）

作业通过调用 `ENDOFJOB` 来终止：

```agc
ENDOFJOBCAFEXECBANK
TSFBANK
TCFENDJOB1
```

在 Executive 的bank中：

```agc
ENDJOB1INHINT
CSZERO# Load -0
TSBUF +1# Initialize scan with worst priority
XCHPRIORITY# Clear core set 0's priority (set to -0 = free)
MASKLOW9# Extract VAC area pointer from old priority
TSL

CSFAKEPRET# Check if this job had a VAC area
ADL
EXTEND
BZMFEJSCAN# No VAC area (NOVAC job) — go to scan

CCSL# Has VAC area — free it
INDEXA
TS0# Zero out the VACnUSE register
```

VAC区域的释放很微妙：`L` 包含旧优先级的低9位（VAC区域地址）。`CCS L` / `INDEX A` / `TS 0` 序列使用CCS的减小值作为索引，将对应的 `VACnUSE` 寄存器清零，标记VAC区域为空闲。

清理后，`EJSCAN` 找到下一个要运行的作业。

### 4.4 空闲循环（DUMMYJOB）

当 `EJSCAN` 找不到活跃作业时（所有 `BUF+1` 检查都落入），控制到达 `DUMMYJOB`：

```agc
DUMMYJOBCSZERO# Load -0
TSNEWJOB# NEWJOB = -0 means "idle"
RELINT# Enable interrupts — we need them to wake us
CSTWO# Turn off the activity light
EXTEND
WANDDSALMOUT# AND complement of bit 2 with DSALMOUT channel
ADVANCCSNEWJOB# Check if a new job has arrived
TCFNUCHANG2# Positive: a job is waiting — switch to it
CAFTWO# +0: current job (core set 0) is ready
TCFNUDIRECT# Execute it directly
```

如果NEWJOB为-0（无作业），代码落入运行**自检**例程：

```agc
CASELFRET# Load self-check return address
TSL
CAFSELFBANK# Load self-check bank
TCFSUPDXCHZ +1# Dispatch to self-check
```

这是AGC的空闲循环：当没有作业需要CPU时，它运行硬件自检。自检例程定期通过 `ADVAN` 标签重新检查 `NEWJOB`，并分发到任何新创建的作业。活动指示灯（DSKY上的绿色"COMP ACTY"指示器）在空闲时关闭，在作业启动时重新打开：

```agc
NUCHANG2INHINT
CCSNEWJOB
TCF+3# NEWJOB still positive
RELINT# NEWJOB changed to +0 — rare race condition
TCFADVAN +2

CAFTWO
EXTEND
WORDSALMOUT# Turn ON activity light
```

### 4.5 SPVAC 入口点

还有第三个不太常用的作业创建入口点：

```agc
SPVACXCHQ# Caller has already set NEWPRIO and INHINT
ADNEG2# Adjust Q to skip past the 2CADR
XCHQ
TCFSPVACIN# Enter FINDVAC midstream
```

`SPVAC` 在调用者已经将优先级存储在 `NEWPRIO` 中并禁用中断的情况下使用。它将Q（返回地址）向后调整2以处理紧跟其后的2CADR，然后在优先级设置之后跳入 `FINDVAC` 的流程。

### 4.6 优先级更改（PRIOCHNG）

运行中的作业可以更改自身优先级：

```agc
PRIOCHNGINHINT
TSNEWPRIO# New priority in A
CAFEXECBANK
XCHBBANK
TSBANKSET# Save bank state
CAQ
TCFPRIOCH2
```

在 `PRIOCH2` 中：

```agc
PRIOCH2TSLOC# Save return address
CAFZERO
TSBUF# Flag: set to 0 to indicate "priochng mode"
CAFLOW9
MASKPRIORITY# Preserve VAC area pointer
ADNEWPRIO# Combine with new priority
TSPRIORITY# Update priority register
COM# Negate for scan comparison
TCFJOBSLP2# Scan for highest priority (like sleep)
```

扫描可能确定该作业即使以新优先级仍是最高的——在这种情况下立即返回。或者可能找到优先级更高的作业并执行上下文切换。

---

## 5. SUPDXCHZ 分发例程

文件底部，一个用于全bank切换分发到任意地址的工具例程：

```agc
SUPDXCHZXCHL# Put bank info in A, address in L
 +1EXTEND
WRITESUPERBNK# Set the superbank from A
TSBBANK# Set BBANK (which sets EB and FB) from A
TCL# Jump to address in L
```

`DUMMYJOB` 用它分发到自检例程，`NUDIRECT` 用它启动已在核心组0中的作业。

---

## 6. 现代对比与惊喜

### 6.1 与 FreeRTOS 的比较

| 概念 | Apollo Executive | FreeRTOS |
|---------|-----------------|----------|
| **任务控制块** | 12字"核心组" | `TCB_t` 结构体（约60+字节） |
| **最大任务数** | 7（编译时固定） | 可配置，堆分配 |
| **调度方式** | 仅协作式 | 抢占式 + 协作式 |
| **优先级扫描** | 7个寄存器的线性扫描 | 每优先级级别一个链表 |
| **上下文切换** | 手动逐寄存器交换 | 硬件辅助（ARM上的PendSV） |
| **栈** | 无栈——Q寄存器 + 手动保存 | 每任务独立栈 |
| **空闲任务** | `DUMMYJOB` 运行自检 | 可配置空闲钩子 |
| **任务创建** | FINDVAC/NOVAC——固定池 | `xTaskCreate`——堆分配 |
| **休眠/唤醒** | JOBSLEEP/JOBWAKE——CADR匹配 | `vTaskDelay` / `xTaskNotify` |
| **过载处理** | 1202报警，优雅降级 | 栈溢出钩子，看门狗 |

### 6.2 会让现代开发者惊讶的地方

**没有抢占。** Executive 从不强制从运行中的作业夺取CPU。如果作业未能调用 `CHANG1`/`CHANG2`，系统将挂起。每个作业都被信任会定期让出。这是最纯粹形式的协作式多任务——没有强制上下文切换的定时器中断。

**没有栈。** AGC没有硬件栈，只有一个返回地址寄存器（Q）。Executive 不为每个作业创建栈。相反，每个作业获得一个固定的12字核心组和可选的VAC区域。作业内的子程序调用必须手动保存和恢复Q。这就是解释器存在的原因——它在内部提供自己的调用栈。

**CCS 指令作为通用条件分支。** 现代CPU有几十条条件分支指令。AGC只有一条：`CCS`，它根据正/+0/负/-0执行4路跳转。整个 Executive 都围绕这一点构建——"空闲"核心组的-0编码、活跃/休眠作业的正/负编码，以及减小的绝对值既作为测试又作为有用的输出值。

**数据嵌入在指令流中。** `NO.CORES`（`DEC 7`）既是一个常量，又占据了 `CCS` 指令的"+0"跳过槽（第1106页）。类似地，`COREINC`（`DEC 12`）位于JOBWAKE扫描中某个CCS的"+0"槽（第1111页）。这不是偶然的——程序员刻意将常量放在永远不会被执行到的CCS跳过位置，节省了宝贵的内存字。

**`-CCS PRIORITY` 作为地址标签。** 标签 `-CCSPR`（第1113页）标记扫描循环中间的指令 `-CCS PRIORITY`。这条指令从不被执行——它的目的是为将扫描循环位置转换为核心组偏移量的算术提供参考地址。指令的**地址**才是数据，而不是其**操作**。

**三次 `DXCH` 交换模式。** 没有硬件栈或临时寄存器，交换两个内存位置需要三条双交换指令——内存等价于经典的三变量交换 `temp = a; a = b; b = temp`，但使用A,L寄存器对作为临时存储。

**报警恢复是有意设计的。** 1202报警不是崩溃——它是有意设计的过载响应。当 Executive 找不到空闲的核心组时，它调用 `BAILOUT1`，在DSKY上显示报警码，但允许系统继续运行。无法调度的低优先级作业被简单丢弃。优先级更高的制导方程继续运行。这就是阿波罗11号着陆尽管有报警仍然成功的原因——Executive 的优先级系统确保最重要的工作总是优先完成。

**约69KB装下一切。** 整个 Executive——作业创建、调度、上下文切换、休眠/唤醒、优先级管理、空闲循环——大约600行汇编，占用约400字固定内存（约750字节）。现代RTOS内核通常有1万到10万行C代码。AGC团队通过不懈优化实现了这种密度：每条指令都身兼多职，每个常量的放置都是为了节省一个字，每种编码的选择都是为了最小化解释它所需的代码。

---

## 附录：关键符号快速参考

| 符号 | 类型 | 用途 |
|--------|------|---------|
| `NEWJOB` | 可擦除 | 指向优先级最高的等待核心组的偏移量（+0 = 当前，-0 = 空闲） |
| `NEWPRIO` | 可擦除 | 正在创建的作业的优先级 |
| `NEWLOC` | 可擦除（DP） | 正在创建的作业的2CADR |
| `LOCCTR` | 可擦除 | 扫描期间当前核心组的偏移量 |
| `EXECTEM1` | 可擦除 | 作业创建期间保存的调用者bank |
| `EXECTEM2` | 可擦除 | 核心组扫描期间的循环计数器 |
| `EXECBANK` | 固定 | Executive 所在bank的CADR（用于切换） |
| `FAKEPRET` | 固定 | 标记NOVAC作业的偏移量（无VAC区域） |
| `COREINC` | 固定 | 核心组大小：12字 |
| `NO.CORES` | 固定 | 核心组数量：7 |
| `LOW9` | 固定 | 用于从PRIORITY中提取VAC区域指针的掩码 |
| `OVFIND` | 可擦除 | 当前作业的解释器溢出指示符 |
| `FIXLOC` | 可擦除 | 当前作业VAC区域的基地址 |
| `PUSHLOC` | 可擦除 | 解释器下推指针（符号位 = 保存时的溢出标志） |
