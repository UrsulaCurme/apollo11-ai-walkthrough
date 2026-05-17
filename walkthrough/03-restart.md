# 拯救阿波罗11号的重启：AGC 如何从 1202 报警中恢复

## 简介

1969 年 7 月 20 日，登月舱*鹰号*正朝静海下降，AGC 的 DSKY 闪出了 **PROG 1202**——执行溢出。计算机正在被压垮。在任何较差的系统中，这个报警都意味着中止。然而，AGC 做了一件非凡的事：它重启了自身，卸载了非关键工作，并保持着陆制导继续运行。它不是只做了一次，而是在下降过程中多次如此，Neil Armstrong 全程都在计算机正常运行的情况下着陆了。

本章追踪使这一切成为可能的代码，涵盖 `Luminary099/` 中的两个文件：`FRESH_START_AND_RESTART.agc`（第 211–237 页）和 `ALARM_AND_ABORT.agc`（第 1381–1385 页）。它们共同实现了我们今天称之为*基于优先级的优雅降级系统*的机制——构建于 1960 年代，用 15 位汇编语言，只有 2K RAM。

---

## 1. 新启动与重启：同一代码的两条路径

AGC 有两条根本不同的初始化路径，代码的结构使它们共享一个公共子程序（`STARTSUB`），同时在保留哪些状态上有所不同。

### 1.1 新启动路径

新启动发生在初始上电时，或者宇航员明确请求完全重置时（通过 DSKY 的 Mark Reject + Error Reset 组合键）。入口点是 `SLAP1`：

```agc
SLAP1       INHINT              # FRESH START. COMES HERE FROM PINBALL.
            TC      STARTSUB    # SUBROUTINE DOES MOST OF THE WORK
```
*（FRESH_START_AND_RESTART.agc，约第 30 行）*

`STARTSUB` 返回后，新启动路径继续在 `SKIPSIM` 处，然后进行：

1. **关闭 DSKY 指示灯**（仅保留万向锁和无姿态指示器）：
   ```agc
   SKIPSIM     CA      DSPTAB +11D   # TURN OFF ALL DSPTAB +11D LAMPS
               MASK    BITS4&6       # EXCEPT THE GIMBAL LOCK & NO ATT ONLY ON
               AD      BIT15         # REQUESTED FRESH START.
               TS      DSPTAB +11D
   ```

2. **初始化下行链路转储计数器**，用于一次传输。

3. **清零错误计数器和故障寄存器**：
   ```agc
               CA      ZERO
               TS      ERCOUNT
               TS      FAILREG
               TS      FAILREG +1
               TS      FAILREG +2
               TS      REDOCTR
   ```
   注意：`REDOCTR`（重启计数器）仅在新启动时清零。重启时，它被*递增*。这是地面控制人员跟踪发生了多少次重启的方式。

4. **确保引擎关闭**——关键安全措施：
   ```agc
   DOFSTART    CAF     BIT14         # INSURE ENGINE IS OFF.
               EXTEND
               WRITE   DSALMOUT
               CS      ZERO
               TS      THRUST
   ```

5. **初始化 DAP**（数字自动驾驶仪）、所有标志字、开关状态表和 IMU 模式。新启动路径写入 `STATE` 到 `STATE +11D`——十二个字的标志位，跟踪系统中每个重要的软件状态：
   ```agc
               EXTEND              # INITIALIZE SWITCHES ONLY ON FRESH START.
               DCA     SWINIT
               DXCH    STATE
               CA      SWINIT +2
               TS      STATE +2
   ```

   但即便如此，代码也很小心。某些标志即使在新启动时也被*保留*：
   ```agc
               CA      REFSMBIT    # DO NOT ALTER REFSMFLG ON FRESH START.
               MASK    STATE +3
               AD      SWINIT +3
               TS      STATE +3
   ```
   ```agc
               CA      SURFFBIT    # DO NOT ALTER SURFFLAG ON FRESH START.
               AD      CMOONBIT   #            CMOONFLG
               AD      LMOONBIT   #            LMOONFLG
               MASK    STATE +8D
               AD      SWINIT +8D
               TS      STATE +8D
   ```

   参考系标志（`REFSMFLG`）、表面标志（`SURFFLAG`）和月球标志保持不变——因为无论什么重置触发，失去对自己是在绕月还是坐在月球表面的追踪都将是灾难性的。

6. **通过 `ENDRSTRT` 退出**，跳转到 `DUMMYJOB +2`，在 `RELINT`（重新启用中断）处继续，而不将 `NEWJOB` 清零。

### 1.2 重启路径

当 AGC 硬件检测到需要软件重置的条件时——`GOJAM` 信号——就会发生重启。这将执行向量到地址 4000（启动向量），转移到 `GOPROG`：

```agc
# COMES HERE FROM LOCATION 4000, GOJAM, RESTART ANY PROGRAMS
# WHICH MAY HAVE BEEN RUNNING AT THE TIME.

        EBANK=  LST1
GOPROG  INCR    REDOCTR         # ADVANCE RESTART COUNTER.
```
*（FRESH_START_AND_RESTART.agc，约第 215 页）*

第一条指令就递增了 `REDOCTR`——重启计数器。这是告诉休斯顿发生了多少次重启的遥测标记。在阿波罗 11 号着陆期间，这个计数器前进了几次。

接下来，代码保存 bank 状态：
```agc
        LXCH    Q
        EXTEND
        ROR     SUPERBNK
        DXCH    RSBBQ
```
这将 Q（返回地址）和超级 bank 位保存到 `RSBBQ`，捕获重启发生时计算机所处的位置。

重启路径然后检查 IMU 是否处于粗对准模式（万向锁恢复所需）：
```agc
        CA      DSPTAB +11D
        MASK    BIT4
        EXTEND
        BZF     +4
        AD      BIT6            # SET ERROR COUNTER ENABLE
        EXTEND
        WOR     CHAN12          # ISS WAS IN COARSE ALIGN SO GO BACK TO
```

### 1.3 可擦除内存完整性检查

在继续重启之前，代码对可擦除（RAM）内存执行了一次非凡的完整性检查。`ERASCHK` 系统的工作方式如下：当系统修改可擦除内存时，它将备份副本保存在 `SKEEP5`/`SKEEP6` 中，并在 `SKEEP7` 和 `ERESTORE` 中记录正在修改的地址。重启时：

```agc
        CAF     HI5
        MASK    ERESTORE
        EXTEND
        BZF     +2              # IF ERESTORE NOT = +0 OR +N LESS THAN 2K,
        TCF     NONAVKEY +3     # DO FRESH START -- E MEMORY MIGHT BE BAD
        CS      ERESTORE
        EXTEND
        BZF     DORSTART        # = +0 CONTINUE WITH RESTART.
        AD      SKEEP7
        EXTEND
        BZF     +2              # = SKEEP7, RESTORE E MEMORY.
        TCF     NONAVKEY +3     # DO FRESH START -- E MEMORY MIGHT BE BAD
```

逻辑如下：
- 如果 `ERESTORE` 为 +0，则没有内存修改正在进行中 → 可以安全重启
- 如果 `ERESTORE` 等于 `SKEEP7` 且是有效的可擦除地址（< 2000 八进制），则内存正在修改中 → 恢复备份并重启
- 否则，内存可能已损坏 → 退到完整的新启动

这是一个**事务性内存保护方案**，用 1960 年代的汇编实现。如果重启在系统半途写入时发生，它使用保存的副本回滚部分操作：

```agc
        CA      SKEEP4
        TS      EBANK           # EBANK OF E MEMORY THAT WAS UNDER TEST.
        EXTEND
        DCA     SKEEP5
        INDEX   SKEEP7
        DXCH    0000            # E MEMORY RESTORED
        CA      ZERO
        TS      ERESTORE
DORSTART TC     STARTSUB        # DO INITIALIZATION AFTER ERASE RESTORE.
```

### 1.4 重启保留与销毁的内容

| 重启保留 | 销毁/重新初始化 |
|---------|--------------|
| 相位表条目（如果一致） | 等待列表（所有待处理的定时任务） |
| 标志字（大部分） | 执行作业表（所有 VAC 区域） |
| 引擎开/关状态 | 显示状态 |
| IMU 粗对准状态 | DSKY 寄存器 |
| 万向锁/无姿态指示灯 | 待处理 I/O |
| 导航状态向量 | DAP 瞬态状态 |
| REDOCTR（已递增） | 标记系统 |
| ERCOUNT、FAILREG | 监控显示 |

关键洞见：**程序相位被保留，但调度基础设施被彻底清除**。等待列表和执行模块从头重新初始化。然后查询相位表来确定正在运行什么以及什么需要重启。

---

## 2. 重启逻辑：相位表与优先级决策

### 2.1 公共初始化子程序

新启动和重启都调用 `STARTSUB`，执行核心系统初始化：

```agc
STARTSUB  CAF     LDNPHAS1      # SET POINTER SO NEXT 20MS DOWNRUPT WILL
          TS      DNTMGOTO      # CAUSE THE CURRENT DOWNLIST TO BE
                                # INTERRUPTED AND START SENDING FROM THE
                                # BEGINNING OF THE CURRENT DOWNLIST.
```
*（第 219 页）*

`STARTSUB` 然后：

1. **重置定时器**——TIME3、TIME4、TIME5 被加载到最大值（很快触发它们的中断）：
   ```agc
   STARTSB1  CAF     POSMAX
             TS      TIME3
             AD      MINUS2
             TS      TIME4
             AD      NEGONE
             TS      TIME5
   ```
   TIME3 首先加载（驱动等待列表），然后 TIME4（DSKY）获得 POSMAX-2，再 TIME5（DAP）获得 POSMAX-3。交错排列防止三个中断处理程序互相碰撞。

2. **禁用 TIME6**（高频喷气定时计数器）：
   ```agc
             CAF     POSMAX        # DISABLE TIME6 CLOCK.  JUST IN CASE A T6
             TS      T6NEXT        #   RUPT IS ALREADY IN THE PRIORITY CHAIN,
             EXTEND                #   ENSURE THAT ITS INPUTS WILL RENDER IT
             WAND    CHAN13        #   INEFFECTUAL.
   ```

3. **将 DAP 空闲例程设置为** T5RUPT 处理程序：
   ```agc
             EXTEND              # SET T5RUPT FOR DAPIDLER PROGRAM.
             DCA     IDLEADR
             DXCH    T5ADR
   ```

然后 `STARTSB2`（在重启时调用，而非新启动的初始部分）保留引擎状态：
```agc
STARTSB2  CAF     OCT30001      # DURING SOFTWARE RESTART, DO NOT DISTURB
          EXTEND                # ENGINE ON, OFF AND ISS WARNING.
          WAND    DSALMOUT
```
`WAND`（写-与）指令屏蔽引擎控制通道，仅保留引擎开/关位和 ISS 警告。该通道上的其他所有内容都被清除。

4. **重新初始化等待列表**——所有八个任务槽被清除：
   ```agc
             CAF     NEG1/2        # INITIALIZE WAITLIST DELTA-TS.
             TS      LST1 +7
             TS      LST1 +6
             ...
             TS      LST1
   ```
   `NEG1/2`（SP 中的 -0.5）将每个槽标记为"到到期的最长时间"——实际上是空的。任务地址（`LST2` 到 `LST2 +17D`）被加载为 `ENDTASK` 的补码，这是一个意为"这里没有任务"的哨兵。

5. **清除所有执行优先级寄存器**——使所有 8 个作业槽可用：
   ```agc
             CS      ZERO          # MAKE ALL EXECUTIVE REGISTER SETS
             TS      PRIORITY      # AVAILABLE.
             TS      PRIORITY +12D
             TS      PRIORITY +24D
             TS      PRIORITY +36D
             TS      PRIORITY +48D
             TS      PRIORITY +60D
             TS      PRIORITY +72D
             TS      PRIORITY +84D
   ```
   `CS ZERO` 产生 -0（全 1），在执行模块中表示"此槽是空闲的"。每个 VAC 区域相隔 12 个字（一个优先级字 + 工作存储），所以 +12D、+24D 等偏移命中每个优先级寄存器。

6. **标记无活跃作业**：
   ```agc
             TS      DSRUPTSW
             TS      NEWJOB        # SHOWS NO ACTIVE JOBS.
   ```

7. **通过将所有 VAC 区域链入空闲列表使其可用**：
   ```agc
             CAF     VAC1ADRC      # MAKE ALL VAC AREAS AVAILABLE.
             TS      VAC1USE
             AD      LTHVACA
             TS      VAC2USE
             AD      LTHVACA
             TS      VAC3USE
             ...
   ```
   `LTHVACA` 是十进制 44——VAC 区域之间的间距。每个 `VACnUSE` 寄存器指向其 VAC 区域的起始，形成链式空闲列表。

### 2.2 相位表验证

公共初始化之后，重启路径（在 `GOPROG3`）执行关键的相位表验证：

```agc
GOPROG3     CAF     NUMGRPS       # VERIFY PHASE TABLE AGREEMENTS
PCLOOP      TS      MPAC +5
            DOUBLE
            EXTEND
            INDEX   A
            DCA     -PHASE1       # COMPLEMENT INTO A, DIRECT INTO L.
            EXTEND
            RXOR    LCHAN         # RESULT MUST BE -0 FOR AGREEMENT.
            CCS     A
            TCF     PTBAD         # RESTART FAILURE.
            TCF     PTBAD
            TCF     PTBAD
```
*（第 216–217 页）*

这是完整性检查。对于每个重启组（1 到 5，因为 `NUMGRPS` 等于 `FIVE`），系统存储相位的*两个*副本：`PHASEn` 和 `-PHASEn`。`-PHASEn` 的值应该是 `PHASEn` 的 1 的补码。检查工作如下：

1. `DCA -PHASEn` 将补码加载到 A，直接值加载到 L
2. `RXOR LCHAN` 将 A 与 L 进行 XOR（通过 L "通道"）
3. 如果它们是适当的补码，XOR 产生 -0（全 1）
4. `-0` 上的 `CCS A` 落到第四种情况（-0 情况），继续循环

如果任何相位对不一致，CCS 落入前三种情况之一 → `PTBAD`：
```agc
PTBAD       TC      ALARM         # SET ALARM TO SHOW PHASE TABLE FAILURE.
            OCT     1107
            TCF     DOFSTRT1
```
触发警报 1107，系统回退到 `DOFSTRT1`——本质上是新启动（但不关闭引擎，这是 `DOFSTART` 和 `DOFSTRT1` 之间的区别）。

### 2.3 重启活跃程序

如果所有相位表都一致，代码继续重启正在运行的内容：

```agc
            CAF     NUMGRPS       # SEE IF ANY GROUPS RUNNING.
NXTRST      TS      MPAC +5
            DOUBLE
            INDEX   A
            CCS     PHASE1
            TCF     PACTIVE       # PNZ -- GROUP ACTIVE.
            TCF     PINACT        # +0 -- GROUP NOT RUNNING.

PACTIVE     TS      MPAC
            INCR    MPAC          # ABS OF PHASE.
            INCR    MPAC +6       # INDICATE GROUP DEMANDS PRESENT.
            CA      RACTCADR
            TC      SWCALL        # MUST RETURN TO SWRETURN.
```
*（第 217 页）*

对于每个重启组，`CCS PHASE1`（以组编号为索引）测试相位值：
- 如果为正（组是活跃的），执行转到 `PACTIVE`
- 如果为 +0，组未运行 → `PINACT`

`PACTIVE` 通过 `SWCALL` 调用 `RESTARTS`（通过 `RACTCADR`，即 `CADR RESTARTS`）。`RESTARTS` 例程（在其他地方定义）使用相位值来确定程序在哪里恢复。每个程序通过存储相位号来注册其重启点，重启分派器使用该号码向量到正确的恢复点。

相位机制像**检查点**一样工作：程序定期调用 `PHASCHNG` 来更新其相位，说"我已到达步骤 N"。如果发生重启，系统查看相位并在对应于该相位的检查点重新进入程序。

处理完所有组后：
```agc
PINACT      CCS     MPAC +5       # PROCESS ALL RESTART GROUPS.
            TCF     NXTRST

            CCS     MPAC +6       # NO, CHECK PHASE ACTIVITY FLAG
            TCF     ENDRSTRT      # PHASE ACTIVE
            CAF     BIT15         # IS MODE -0
            MASK    MODREG
            EXTEND
            BZF     GOTOPOOH      # NO
            TCF     ENDRSTRT      # YES
```

如果*任何*组有活跃相位（`MPAC +6` > 0），系统继续到 `ENDRSTRT`——恢复正常操作。如果*没有*组活跃但模式寄存器为 -0，也继续。否则，转到 `GOTOPOOH`（P00）——空闲程序。

### 2.4 重启时的引擎状态保留

重启逻辑最关键的方面之一是引擎管理。在 `SETINFL`（`DORSTART` 后的重启特定路径），代码明确检查并保留引擎状态：

```agc
            CA      BIT4          # TURN ON THROTTLE COUNTER
            EXTEND
            WOR     CHAN14        # TURN ON THRUST DRIVE
            CS      FLAGWRD5
            MASK    ENGONBIT
            CCS     A
            TCF     +5
            CAF     BIT13
            EXTEND
            WOR     DSALMOUT      # TURN ENGINE ON
            TCF     GOPROG3
 +5         CAF     BIT14
            EXTEND
            WOR     DSALMOUT      # TURN ENGINE OFF
            TCF     GOPROG3
```
*（第 216 页）*

代码检查 `FLAGWRD5` 中的 `ENGONBIT`。如果引擎在重启前处于开启状态，则重新打开它。如果处于关闭状态，则关闭它。**引擎状态在重启后得以保留。** 在着陆期间，下降引擎持续点火——如果重启终止了引擎，登月舱将会坠毁。

---

## 3. 1202/1201 报警：执行溢出

### 3.1 报警的起源

1202 报警**不在这两个文件中生成**。它起源于执行模块（具体在 `EXEC` 或 `FINDVAC` 中），当调度新作业的请求发现所有 VAC 区域都被占用时。执行模块会调用：

```agc
        TC      ALARM
        OCT     1202
```

或对于 1201（不同调度路径没有 VAC 区域可用）：

```agc
        TC      ALARM
        OCT     1201
```

我们*能在* `ALARM_AND_ABORT.agc` 中追踪的，正是当该 `TC ALARM` 执行时发生了什么。

### 3.2 ALARM 子程序

```agc
ALARM       INHINT

            CA      Q
ALARM2      TS      ALMCADR
            INDEX   Q
            CA      0
BORTENT     TS      L
```
*（ALARM_AND_ABORT.agc，第 1381 页）*

逐步分析：

1. **`INHINT`**——立即禁用中断。这至关重要：在记录报警的过程中，你不希望另一个中断触发。

2. **`CA Q` / `TS ALMCADR`**——保存返回地址。Q 持有 `TC ALARM` *之后*那个字的地址，即报警代码本身。将 Q 保存到 `ALMCADR` 记录了报警的来源。

3. **`INDEX Q` / `CA 0`**——这是一个优雅的 AGC 习语。`INDEX Q` 通过将 Q 加到下一条指令的地址来修改它。`CA 0` 有效地变为 `CA Q`，加载地址 Q 处的字——即八进制报警代码（例如 `OCT 1202`）。现在 A 中是报警代码。

4. **`TS L`**——将报警代码存入 L（低寄存器）。

### 3.3 记录报警

```agc
PRIOENT     CA      BBANK
 +1         EXTEND
            ROR     SUPERBNK      # ADD SUPER BITS.
            TS      ALMCADR +1

LARMENT     CA      Q             # STORE RETURN FOR ALARM
            TS      ITEMP1
```

当前 bank 状态（BBANK + 超级 bank 位）保存到 `ALMCADR +1`，形成报警起源处的完整 2CADR（双字地址）。这是将出现在遥测数据中的"谁调用了我"记录。

### 3.4 故障寄存器级联

```agc
CHKFAIL1    CCS     FAILREG       # IS ANYTHING IN FAILREG
            TCF     CHKFAIL2      # YES TRY NEXT REG
            LXCH    FAILREG
            TCF     PROGLARM      # TURN ALARM LIGHT ON FOR FIRST ALARM

CHKFAIL2    CCS     FAILREG +1
            TCF     FAIL3
            LXCH    FAILREG +1
            TCF     MULTEXIT

FAIL3       CA      FAILREG +2
            MASK    POSMAX
            CCS     A
            TCF     MULTFAIL
            LXCH    FAILREG +2
            TCF     MULTEXIT
```

有三个故障寄存器。代码尝试将报警代码（仍在 L 中）存入第一个空的：

1. `CCS FAILREG`——如果 FAILREG 非零（正值），则已有报警 → 尝试下一个寄存器
2. 如果 FAILREG 为 +0（空），`LXCH FAILREG` 将 L（报警代码）交换到 FAILREG → 点亮指示灯
3. `FAILREG +1` 和 `FAILREG +2` 同样模式

如果三个都满：
```agc
MULTFAIL    CA      L
            AD      BIT15
            TS      FAILREG +2
```
当前报警代码与 BIT15 进行 OR（设置符号位），存入 `FAILREG +2`，覆盖原来的内容。设置符号位作为标志，表示"已发生多次报警——此寄存器已被覆盖"。

### 3.5 程序报警指示灯

对于*第一个*报警，`PROGLARM` 点亮 DSKY 上的 PROG 灯：

```agc
PROGLARM    CS      DSPTAB +11D
            MASK    OCT40400
            ADS     DSPTAB +11D
```

`OCT40400` = 第 9 位和第 15 位。`CS`/`MASK`/`ADS` 序列在显示表中设置这些位，打开 DSKY 上的程序报警指示器。这就是 Armstrong 和 Aldrin 看到的那盏灯。

### 3.6 返回调用方

```agc
MULTEXIT    XCH     ITEMP1        # OBTAIN RETURN ADDRESS IN A
            RELINT
            INDEX   A
            TC      1
```

返回地址（之前保存在 `ITEMP1` 中）被恢复，中断被重新启用（`RELINT`），执行返回到报警代码*之后*的指令。`INDEX A` / `TC 1` 是 AGC 的"跳转到 A+1"习语——即 `OCT 1202` 常量之后的字。

**这是关键点：`ALARM` 返回到调用方。** 对于 1202，执行模块通常会调用 `BAILOUT` 或通过其他方式进行重启。但 `ALARM` 本身是非中止的——它记录并返回。

### 3.7 BAILOUT 与 POODOO：中止报警路径

该文件为更严重的情况提供了两条*中止*报警路径：

**BAILOUT**——当程序遇到不可恢复但非致命的错误时使用：
```agc
BAILOUT     INHINT
            CA      Q
            TS      ALMCADR
            INDEX   Q
            CAF     0
            TC      BORTENT
```
记录报警后，落入：
```agc
WHIMPER     CA      TWO
            AD      Z
            TS      BRUPT
            RESUME
            TC      POSTJUMP      # RESUME SENDS CONTROL HERE
            CADR    ENEMA
```

这是一个巧妙的技巧。`RESUME` 是"从中断返回"指令，但 BAILOUT 不是 ISR。通过将 `BRUPT` 设置为指向 `TC POSTJUMP` 指令然后执行 `RESUME`，代码强制跳转到 `ENEMA`——执行部分重启（`STARTSB1` + `GOPROG2A`），保留比完全重启更多的状态，同时仍然重新初始化调度器。

**POODOO**——"中止"路径（注意标签 `ABORT EQUALS WHIMPER`）：
```agc
POODOO      INHINT
            CA      Q
ABORT2      TS      ALMCADR
            INDEX   Q
            CAF     0
            TC      BORTENT
```
记录报警后，POODOO 设置重启组 4：
```agc
            CAF     OCT35         # 4.35SPOT FOR GOPOODOO
            TS      L
            COM
            DXCH    -PHASE4
```
这将 `GOPOODOO` 注册为相位 4 的重启点。然后 `GOPOODOO` 进行清理：
```agc
GOPOODOO    INHINT
            TC      BANKCALL      # RESET STATEFLG, REINTFLG, AND NODOFLAG.
            CADR    FLAGS
            CA      FLAGWRD7      # IS SERVICER CURRENTLY IN OPERATION?
            MASK    V37FLBIT
            CCS     A
            TCF     STRTIDLE
            TC      BANKCALL      # TERMINATE GRPS 1, 3, 5, AND 6
            CADR    V37KLEAN
            TC      BANKCALL      # TERMINATE GRPS 2, 4, 1, 3, 5, AND 6
            CADR    MR.KLEAN      #   (I.E., GRP 4 LAST)
            TCF     WHIMPER
```

`FLAGS` 子程序（第 1385 页）清除 `STATEBIT`、`REINTBIT` 和 `NODOBIT`：
```agc
FLAGS       CS      STATEBIT
            MASK    FLAGWRD3
            TS      FLAGWRD3
            CS      REINTBIT
            MASK    FLGWRD10
            TS      FLGWRD10
            CS      NODOBIT
            MASK    FLAGWRD2
            TS      FLAGWRD2
            TC      Q
```

### 3.8 MR.KLEAN 层次结构

回到 `FRESH_START_AND_RESTART.agc`，相位清除例程揭示了优先级层次结构：

```agc
MR.KLEAN    INHINT
            EXTEND
            DCA     NEG0
            DXCH    -PHASE2
P00KLEAN    EXTEND
            DCA     NEG0
            DXCH    -PHASE4
V37KLEAN    EXTEND
            DCA     NEG0
            DXCH    -PHASE1
            EXTEND
            DCA     NEG0
            DXCH    -PHASE3
            EXTEND
            DCA     NEG0
            DXCH    -PHASE5
            EXTEND
            DCA     NEG0
            DXCH    -PHASE6
            TC      Q
```
*（第 213–214 页）*

三个嵌套入口点提供三个级别的清理：

| 入口点 | 清除的组 | 使用情况 |
|--------|---------|---------|
| `V37KLEAN` | 1、3、5、6 | 终止导航/杂项，保留 P20/P25 和当前程序 |
| `P00KLEAN` | 4、1、3、5、6 | 也终止当前程序，仅保留 P20/P25 |
| `MR.KLEAN` | 2、4、1、3、5、6 | 终止所有 |

`DCA NEG0` / `DXCH -PHASEn` 在相位和其补码中都存储 -0——将组标记为非活跃。顺序很重要：组 4（通常持有当前运行的主程序）在组 1/3/5/6 之前被清除，但在调用方已经在组 4 中注册了自己的重启点*之后*。

---

## 4. 追踪着陆期间的 1202 路径

### 4.1 场景

在阿波罗 11 号下降过程中，交会雷达被留在了一种会产生过多中断的模式中（每个雷达周期一次 RUPT10）。每次中断都消耗 CPU 时间用于未编程计数器增量序列。执行模块的作业队列填满是因为：

1. 着陆制导（P63，然后 P64）作为高优先级作业运行
2. 服务程序（计算导航更新的程序）在运行
3. 雷达处理任务正在被调度
4. 等待列表正在触发需要 VAC 区域的任务
5. 所有 8 个 VAC 区域被占用后，下一次 `FINDVAC` 调用产生了 1202 报警

### 4.2 为什么着陆得以幸存

生存链通过几种机制发挥作用：

**1. ALARM 是非中止的。** `ALARM` 子程序（第 1381 页）只记录报警并点亮 PROG 灯。它返回给调用方。执行模块然后可以决定做什么——通常，它无法调度低优先级任务（溢出的那个），而高优先级任务（着陆制导）继续持有其 VAC 区域。

**2. 重启保留程序相位。** 当重启发生（无论是由溢出触发还是由 BAILOUT 触发），`STARTSUB` 清除等待列表和执行模块，但保留相位表完整。着陆制导在溢出发生之前已经注册了其相位。

**3. 基于优先级的重启。** `GOPROG3` 中的 `PACTIVE`/`NXTRST` 循环处理所有重启组。每个组的重启处理程序（`RESTARTS`）会通过 `FINDVAC` 重新调度其作业。但现在系统是干净的——所有 8 个 VAC 区域都是空闲的。高优先级着陆程序首先获得其 VAC 区域。导致溢出的低优先级任务可能适合也可能不适合，但系统不再关心——基本工作在运行。

**4. 引擎状态得以保留。** 下降引擎继续点火，因为 `SETINFL` 处的重启路径明确保留了 `ENGONBIT` 并将引擎命令恢复到硬件通道。

**5. 标志保留上下文。** 标志字（`FLAGWRD0` 到 `FLAGWRD11`）在重启后仍然存在。它们告诉重启的程序它们所处的状态——例如，着陆雷达是否已被纳入，制导是否处于 P63 制动阶段或 P64 进近阶段。

### 4.3 V37 机制与优先级卸载

`V37`（第 227 页）中的 Verb 37（程序更改）机制揭示了系统如何管理程序优先级。在决定模式更改时是否保留或终止程序时，代码检查特定标志：

```agc
V37RET      CS      FLAGWRD0      # IS P20 OR P22 RUNNING?
            MASK    RNDVZBIT
            CCS     A
            TCF     +2            # NO. CHECK FOR P25.
            TCF     2.7SPT        # YES. DO 2.7SPOT
```

P20（交会跟踪）和 P25 在重启组 2 中运行。着陆制导在组 4 中运行。在 1202 重启期间，组结构意味着：

- 组 4（着陆）→ 在其注册相位处重启 → P63/P64 恢复
- 组 2（如果 P20 正在运行）→ 也重启，但未注册相位的雷达处理任务丢失
- 未注册相位的任务（导致溢出的那些）→ 消失，这正是你想要的

---

## 5. 设计哲学

### 5.1 异步重启架构

Hamilton 的团队围绕一个在 1960 年代是激进的、今天仍然罕见的原则设计了系统：**任何计算都应该在任何点可中断和可重启，系统自动恢复到已知良好状态。**

这需要：
- **相位注册**：每个重要的程序检查点写入相位号，创建面包屑踪迹
- **双副本完整性**：相位值存储两次（作为值和补码），允许重启代码检测损坏
- **幂等恢复**：重启处理程序即使在原始计算部分完成的情况下也必须可以安全调用
- **基于优先级的分类**：当资源稀缺时，系统自动卸载低优先级工作

### 5.2 与现代方法的比较

| AGC 方法 | 现代等价物 |
|---------|---------|
| 相位表注册 | 事务日志/预写日志 |
| ERESTORE 备份/恢复 | 数据库保存点/日志记录 |
| 双副本相位检查 | 带校验和的元数据 |
| 基于优先级的重启 | Kubernetes Pod 优先级/抢占 |
| ALARM（非中止） | 断路器模式（半开） |
| BAILOUT → WHIMPER | 优雅降级/舱壁模式 |
| MR.KLEAN 层次结构 | 级联断路器 |
| GOJAM → GOPROG | Erlang 监督器重启策略 |

最接近的现代类比是 Erlang 的监督树："让它崩溃，然后在已知良好状态重启。"但 AGC 比 Erlang 早 30 年，而且只用 2K RAM 和没有硬件堆栈实现了这一切。

### 5.3 没有这种设计会发生什么

**场景 A：简单的看门狗定时器（溢出时重启一切）**
引擎将被关闭。导航状态将丢失。宇航员将中止任务。

**场景 B：遇到错误时停机（现代断言/恐慌）**
计算机停止。引擎停止。登月舱坠毁。

**场景 C：忽略并继续（吞掉错误）**
执行模块的作业表损坏。后续作业调度产生未定义行为。制导方程停止更新。登月舱偏离航线。

**实际发生的事情：** 系统重启，卸载了多余的雷达处理，着陆制导在毫秒内恢复。Armstrong 和 Aldrin 看到了 PROG 灯，听到了"1202"被呼出，但当休斯顿说"我们对那个报警放行"时，计算机已经恢复了。休斯顿 60 秒的响应延迟不是计算机在等待——而是人类在追赶机器。

---

## 6. CURTAINS 子程序：当重启也无济于事时

`ALARM_AND_ABORT.agc` 中还有一个值得注意的例程：

```agc
CURTAINS    INHINT
            CA      Q
            TC      ALARM2
OCT217      OCT     00217
            TC      ALMCADR       # RETURN TO USER
```
*（第 1383 页）*

`CURTAINS` 产生报警 00217 并*返回给调用方*。尽管名字听起来很戏剧化，它实际上是一个非致命报警——它记录问题并让调用程序决定如何处理。这个名字表明开发者对灾难性情况有一定的幽默感。

还有 `CCSHOLE`：
```agc
CCSHOLE     INHINT
            CA      Q
            TC      ABORT2
OCT1103     OCT     1103
```

这处理了 `CCS` 指令遇到不可能值的情况——四路跳过逻辑中的"洞"。报警 1103："算术定律已被违反。"如果这个报警触发，则硬件层面出了严重问题。

---

## 总结

这两个文件中的代码代表了那个时代最复杂的错误处理系统之一。关键的架构决策——基于相位的检查点、优先级感知重启、非中止报警和事务性内存保护——共同创建了一个可以在毫秒内从过载中恢复的系统。1969 年 7 月 20 日，一切悬于一线，它完全按照设计工作。

1202 报警不是一个错误。它是系统在*异常负载下正确运行*——检测到过载，卸载非关键工作，保留关键路径，并在地面上任何人充分理解发生了什么之前恢复。

> **不确定性说明：** 从执行溢出 → 1202 报警 → 重启的确切路径取决于执行模块（`EXEC.agc`）和等待列表（`WAITLIST.agc`）中的代码，这些代码不包含在此处提供的源文件中。报警生成点和特定 FINDVAC 溢出路径的分析是从架构上下文和我们可以看到的报警处理代码推断的。通过 `GOPROG` → `STARTSUB` → 相位表验证 → `RESTARTS` 的重启恢复路径在提供的源代码中是完全可追踪的。重启组分配与特定程序之间的交互（P63/P64 使用哪个组，雷达处理如何注册其相位）需要检查 `P63-P68.agc` 和交会雷达例程等其他模块。
