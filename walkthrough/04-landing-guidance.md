# 月球着陆制导方程：让人类登上月球的代码

## 概述

`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc` 是阿波罗 11 号代码库中最具决定性意义的文件。它包含程序 63、64、65、66 和 67——引导登月舱从约 50,000 英尺高度的动力下降点火到在静海着陆的制导例程。

该文件存在于 Luminary099——登月舱的飞行软件（Luminary 1A，第 099 版）。它于 **1969 年 7 月 14 日**汇编——距着陆六天前。

代码跨越 MIT 原始打印件第 798–828 页。它是原生 AGC 汇编和解释器语言的混合，计算密集型的制导数学运行在 AGC 的软件虚拟机上（通过 `TC INTPRET` 进入），而时间关键型控制流、显示逻辑和阶段切换则以原生汇编运行。

---

## 1. 架构：飞行序列表

着陆制导围绕由变量 `WCHPHASE` 驱动的**状态机**组织：

```
WCHPHASE = -1  →  IGNALG    （点火算法）
WCHPHASE =  0  →  BRAKQUAD  （制动阶段——P63）
WCHPHASE =  1  →  APPRQUAD  （进近阶段——P64）
WCHPHASE =  2  →  VERTICAL  （垂直下降——P65/P66/P67）
```

代码不使用 if-else 链，而使用**跳转表**——以 `WCHPHASE` 为索引的 `TCF`（转移控制到固定地址）指令数组。每次制导过程经历固定的阶段流水线，在每个阶段通过索引相关表来选择适当的处理程序：

```agc
# ROUTINES FOR STARTING NEW GUIDANCE PHASES:
        TCF     TTFINCR         # IGNALG
NEWPHASE TCF    TTFINCR         # BRAKQUAD
        TCF     STARTP64        # APPRQUAD
        TCF     P65START        # VERTICAL

# PRE-GUIDANCE COMPUTATIONS:
        TCF     CALCRGVG        # IGNALG
PREGUIDE TCF    RGVGCALC        # BRAKQUAD
        TCF     REDESIG         # APPRQUAD
        TCF     RGVGCALC        # VERTICAL

# GUIDANCE EQUATIONS:
        TCF     TTF/8CL         # IGNALG
WHATGUID TCF    TTF/8CL         # BRAKQUAD
        TCF     TTF/8CL         # APPRQUAD
        TCF     VERTGUID        # VERTICAL

# POST GUIDANCE EQUATION COMPUTATIONS:
        TCF     CGCALC          # IGNALG
AFTRGUID TCF    CGCALC          # BRAKQUAD
        TCF     CGCALC          # APPRQUAD
        TCF     STEER?          # VERTICAL
```

流水线是：

1. **NEWPHASE**——阶段转换逻辑
2. **PREGUIDE**——制导前计算（坐标变换、重新瞄准）
3. **WHATGUID**——实际制导方程
4. **AFTRGUID**——制导后（油门、转向）
5. **WHATEXIT**——退出和窗口向量计算
6. **WHATDISP**——DSKY 显示更新

这种表驱动架构很优雅：添加新阶段意味着在每个表中添加一个条目，而不是重构控制流。`INDEX WCHPHASE` 指令将 WCHPHASE 的值加到下一条指令的地址，从表中选择正确的 `TCF`。

---

## 2. 入口点

### 普通入口：LUNLAND

制导循环从 SERVOUT（服务程序——以约 2 Hz 处理 IMU 和 PIPA 数据的例程）调用：

```agc
LUNLAND     TC      PHASCHNG
            OCT     00035           # GROUP 5: RETAIN ONLY PIPA TASK
            TC      PHASCHNG
            OCT     05023           # GROUP 3: PROTECT GUIDANCE WITH PRIO 21
            OCT     21000           #   JUST HIGHER THAN SERVICER'S PRIORITY
```

第一个动作是重启保护。AGC 没有现代意义上的操作系统，但有一个协作多任务系统（执行模块）和一个重启/恢复系统。`PHASCHNG` 记录当前程序阶段，以便在硬件重启发生时，系统能从已知状态恢复。

优先级 21 是"刚好高于 SERVICER 优先级"——制导必须抢占服务程序，但不能抢占关键中断处理程序。

### 点火算法入口：?GUIDSUB

```agc
?GUIDSUB    EXIT
            CAF     TWO            # N = 3
            TS      NGUIDSUB
            TCF     GUILDRET +2
```

这在点火算法阶段（制动开始之前）调用。它提供 N=3 次二次制导迭代以收敛到初始轨迹。`EXIT` 指令从解释器返回到原生 AGC 代码。标签 `?GUIDSUB` 值得注意——`?` 前缀在 AGC 标签中是合法的，按惯例用于从其他模块调用的子程序。

---

## 3. GUILDENSTERN：自动模式监视器（R13）

整个阿波罗软件中最具辨识度的部分之一，以莎士比亚《哈姆雷特》（以及后来斯托帕德《罗森克兰兹和吉尔登斯特恩已死》）中的人物命名：

```agc
# HERE IS THE PHILOSOPHY OF GUILDENSTERN: ON EVERY APPEARANCE OR
# DISAPPEARANCE OF THE MANUAL THROTTLE DISCRETE TO SELECT P67 OR P66
# RESPECTIVELY: ON EVERY APPEARANCE OF THE ATTITUDE-HOLD DISCRETE
# TO SELECT P66 UNLESS THE CURRENT PROGRAM IS P67 IN WHICH CASE
# THERE IS NO CHANGE

GUILDEN     EXTEND              # IS UN-AUTO-THROTTLE DISCRETE PRESENT?
# STERN                         # RSB 2009: Not originally a comment.
            READ CHAN30
            MASK    BIT5
            CCS     A
            TCF     STARTP67    # YES
```

标签 `GUILDENSTERN` 被分成两行——第一行是 `GUILDEN`，第二行是 `STERN`。转录说明指出 `STERN`"原本不是注释"——在原始源代码中，它只是下一行上标签的延续，这在 YUL 汇编语法中是合法的，但在现代 yaYUL 中不合法，所以转录者将其注释掉了。

### GUILDENSTERN 的功能

每个制导周期，在计算制导命令之前，GUILDENSTERN 通过读取 I/O 通道的离散输入来检查宇航员的控制模式：

1. **通道 30，第 5 位**："非自动油门"离散。如果存在 → 启动 P67（手动油门）
2. **通道 31，第 13 位**："非姿态保持"离散。如果存在且选择了姿态保持 → 启动 P66（下降率模式）

逻辑流程：

```
手动油门离散是否存在？
  是 → STARTP67（手动油门，始终）
  否 → 我们在 P67 吗？
    是 → STARTP66（宇航员释放了手动油门，切换到 ROD 模式）
    否 → 姿态保持离散是否存在？
      是 → GUILDRET（一切正常，继续当前程序）
      否 → 我们在 P66 吗？
        是 → 是否发生了重启？
          是 → 重新初始化 P66 但保留 VDGVERT
          否 → 继续 ROD
        否 → ROD 开关是否被点击？
          是 → STARTP66
          否 → GUILDRET（继续自动着陆）
```

### 启动 P66

```agc
STARTP66    TC      FASTCHNG
            TC      NEWMODEX
DEC66       DEC     66
            EXTEND
            DCA     HDOTDISP    # SET DESIRED ALTITUDE RATE = CURRENT
            DXCH    VDGVERT     #   ALTITUDE RATE.
```

这是关键：切换到 P66 时，期望高度率（`VDGVERT`）被初始化为**当前**高度率（`HDOTDISP`）。这意味着宇航员不会感受到冲击——制导无缝过渡到维持切换时刻的下降速率。

初始化以解释器模式继续：

```agc
STRTP66A    TC      INTPRET
            SLOAD   PUSH
                    PBIASZ
            SLOAD   PUSH
                    PBIASY
            SLOAD   VDEF
                    PBIASX
            VXSC    SET
                    BIASFACT
                    RODFLAG
            STOVL   VBIAS
                    TEMX
            VCOMP
            STOVL   OLDPIPAX
                    ZEROVECS
            STODL   DELVROD
                    RODSCALE
            STODL   RODSCAL1
                    PIPTIME
            STORE   LASTTPIP
            EXIT
```

这将 PIPA（加速度计）偏置作为向量加载，以 `BIASFACT`（655.36 B-28）缩放，将结果存为 `VBIAS`，并初始化 ROD 计算状态。偏置校正至关重要——PIPA 有已知偏置，必须在软件中补偿。

### "临时"注释

```agc
            TC      BANKCALL        # TEMPORARY, I HOPE HOPE HOPE
            CADR    STOPRATE        # TEMPORARY, I HOPE HOPE HOPE
```

这是代码库中最著名的注释之一。对 `STOPRATE`（将姿态角速率命令清零）的调用是作为临时修复添加的，程序员希望它能被正式解决方案替换。它没有被替换。它就这样飞上了月球。三重"HOPE"传达了程序员的无奈意识：飞行软件中的临时代码往往会变成永久代码。

---

## 4. 阶段初始化

### TTFINCR：剩余时间和着陆点更新

每次制导过程从 `TTFINCR` 开始，它执行两个关键操作：

**1. 更新 TTF/8（剩余时间除以 8）：**

```agc
# TTF/8 UPDATED FOR TIME SINCE LAST PASS:
#     TTF/8 = TTF/8 + (TPIP - TPIPOLD)/8
```

剩余时间被存储为除以 8——这样可以保持数值足够小，以适应 AGC 的小数算术而不溢出。

**2. 更新月球自转的着陆点向量：**

```agc
# LANDING SITE VECTOR UPDATED FOR LUNAR ROTATION:
#     ____               ____   ____                   __
#     LAND = /LAND/ UNIT(LAND - LAND(TPIP - TPIPOLD) * WM)
```

下降过程中月球在登月舱下方旋转。`WM` 是月球角速度向量。代码计算 `LAND` 与 `WM` 的叉积，按经过时间缩放，从 `LAND` 中减去，归一化，并重新缩放到原始量级（`/LAND/`）。这在月球旋转时将着陆点向量保持在正确的惯性位置。

解释器代码中的实现：

```agc
TTFINCR     TC      INTPRET
            DLOAD   DSU
                    TPIP
                    TPIPOLD
            SLR     PUSH          # SHIFT SCALES DELTA TIME TO 2(17) CSECS
                    11D
            VXSC    VXV
                    LAND
                    WM
            BVSU    RTB
                    LAND
                    NORMUNIT
            VXSC    VSL1
                    /LAND/
            STODL   LANDTEMP
            EXIT
```

在 `LANDTEMP` 中计算旋转后的着陆向量后，代码退出解释器，并使用带 `FASTCHNG`（重启保护）的原生 AGC 指令原子地更新实时 `LAND` 向量：

```agc
            EXTEND
            DCA     LANDTEMP
            DXCH    LAND
            EXTEND
            DCA     LANDTEMP +2
            DXCH    LAND     +2
            EXTEND
            DCA     LANDTEMP +4
            DXCH    LAND     +4
```

向量有三个 DP 分量（x、y、z），每个存储为两个连续字。`DXCH`（双交换）原子地在 A、L 寄存器对与内存之间交换两个字——六次 `DXCH` 操作更新完整的三维向量。

---

## 5. P63——制动阶段

### 制导前：CALCRGVG 和 RGVGCALC

P63 在第一次制导过程（来自点火算法）使用 `CALCRGVG`，在后续过程使用 `RGVGCALC`。区别在于 `CALCRGVG` 首先通过积分输出加修正计算速度：

```agc
CALCRGVG    TC      INTPRET
            VLOAD   MXV
                    VATT1
                    REFSMMAT
            VSR1    VAD
                    UNFC/2
            STORE   V
            EXIT
```

`VATT1` 是积分例程的速度，`REFSMMAT` 是参考到稳定构件的矩阵，`UNFC/2` 是上一次制导过程计算的修正项。

`RGVGCALC` 然后在制导坐标中计算状态：

```agc
# VELOCITY RELATIVE TO THE SURFACE:
#     ANGTERM = V + R × WM
# STATE IN GUIDANCE COORDINATES:
#     RGU = CG*(R - LAND)
#     VGU = CG*(V - WM × R)
```

其中：
- `CG` 是制导到平台的坐标变换矩阵
- `R` 是位置向量
- `V` 是速度向量
- `WM` 是月球角速度
- `LAND` 是着陆点向量
- `RGU` 和 `VGU` 是制导坐标系中的位置和速度

代码还计算显示用的水平速度：

```agc
# HORIZONTAL VELOCITY FOR DISPLAY:
#     VHORIZ = 8 ABVAL(0, VG₂, VG₁)
```

这从制导速度的两个水平分量（将垂直分量清零）形成向量，取绝对值，乘以 8。这是在 P65 期间显示给宇航员的值。

### 俯角（LOOKANGL）

```agc
# DEPRESSION ANGLE FOR DISPLAY:
#     LOOKANGL = ARCSIN(UNIT(R - LAND) · XNBPIP)
```

代码计算到着陆点视线与登月舱 X 轴（指向上方穿出上升级的机体轴）之间的夹角。这是在 P64 期间显示的 LPD（着陆点指示器）角度。

```agc
            CA      MPAC            # COMPUTE LOOKANGLE ITSELF
            DOUBLE
            TC      BANKCALL
            CADR    SPARCSIN -1
            AD      1/2DEG
            EXTEND
            MP      180DEGS
            TS      LOOKANGL        # LOOKANGL FOR DISPLAY DURING P64
```

正弦值（来自点积的 MPAC）被加倍，然后 `SPARCSIN` 计算反正弦。加上半度偏移（`1/2DEG = +.00278`）——可能是 LPD 窗口刻度的校准校正。结果乘以 180，将 AGC 的小数圆表示转换为度数。

### TTF/8 计算：求根器

制动制导的核心是 TTF/8（剩余时间除以 8）的计算。这通过找到三次多项式的根来实现：

```agc
# TTF/8 COMPUTATION

TTF/8CL     TC      INTPRETX
            DLOAD*
                    JDG2TTF,1
            STODL*  TABLTTF +6      # A(3) = 8 JDG₂ TO TABLTTF
                    ADG2TTF,1
            STODL   TABLTTF +4      # A(2) = 6 ADG₂ TO TABLTTF
                    VGU     +4
            DMP     DAD*
                    3/4DP
                    VDG2TTF,1
            STODL*  TABLTTF +2      # A(1) = (6 VGU₂ + 18 VDG₂)/8
                    RDG +4,1
            DSU     DMP
                    RGU +4
                    3/8DP
            STORE   TABLTTF         # A(0) = -24(RGU₂ - RDG₂)/64
            EXIT
```

系数 A(0) 到 A(3) 编码制导约束方程。下标 `2` 表示垂直分量（制导坐标系中的第三分量，由 `+4` 索引，因为每个 DP 值占两个字）。

然后通过 `ROOTPSRS` 使用牛顿法求解多项式：

```agc
            EXTEND
            DCA     TTF/8
            DXCH    MPAC            # LOADS TTF/8 (INITIAL GUESS) INTO MPAC
            CAF     TWO             # DEGREE - ONE
            TS      L
            CAF     TABLTTFL
            TC      ROOTPSRS        # YIELDS TTF/8 IN MPAC
```

`ROOTPSRS` 是 Allan Klumpp 编写的通用双精度求根器（在注释中有署名）。它使用牛顿法进行收敛检查，8 次迭代后放弃。代码文档异常详尽：

```agc
# ROOTPSRS FINDS ONE ROOT OF THE POWER SERIES A(N)X^N + A(N-1)X^(N-1) + ... + A(1)X + A(0)
# USING NEWTON'S METHOD STARTING WITH AN INITIAL GUESS FOR THE ROOT.
```

返回约定值得注意：正常返回到 `TC ROOTPSRS + 3`（跳过两个字），而无法收敛则返回到 `TC ROOTPSRS + 1`。这种"成功跳过"模式允许报警处理程序位于"直通"位置：

```agc
            INDEX   WCHPHASE
            TCF     WHATALM         # BAD RETURN: alarm
            
            EXTEND                  # GOOD RETURN
            DCA     MPAC
            DXCH    TTF/8           # CORRECTED TTF/8
```

---

## 6. 主制导方程（QUADGUID）

这是核心制导律，在源注释中有文档说明：

```
AS PUBLISHED:
                  6(VDG + VG)   12(RDG - RG)
    ACG = ADG + ------------- + -------------
                     TTF          TTF × TTF

AS HERE PROGRAMMED:
          3   (1/4(RDG - RG)             )
          - × (------------- + VDG + VG  )
    ACG = 4   (    TTF/8                 )     ADG
          --------------------------------  +  ---
                      TTF/8
```

这是一个**二次制导律**——它将指令加速度（`ACG`）计算为以下量的函数：
- `ADG`——期望（目标）加速度
- `VDG`——期望（目标）速度
- `VG`——当前速度（制导坐标系）
- `RDG`——期望（目标）位置
- `RG`——当前位置（制导坐标系）
- `TTF`——剩余时间（TTF/8 × 8）

两种形式在代数上是等价的。"如编程所示"的形式通过嵌套除以 TTF/8 来避免显式 TTF² 计算，3/4 因子吸收了比例差异。

### 超前时间补偿

在主方程之前，有一个微妙的修正：

```agc
QUADGUID    CS      TTF/8
            AD      LEADTIME        # LEADTIME IS A NEGATIVE NUMBER
            AD      POSMAX          # SAFEGUARD COMPUTATIONS
            TS      L
            CS      L
            AD      L
            ZL
            EXTEND
            DV      TTF/8
            TS      BUF             # -RATIO OF LAG-DIMINISHED TTF TO TTF
```

这计算了一个比率，用于补偿计算延迟——传感器数据采样到计算出的推力命令生效之间的时间。`LEADTIME` 是负数（表示制导应该"向前看"多远）。`POSMAX` 加法后跟 `CS L / AD L` 习语将负值夹零——防止比率在接近着陆时变为负值的保障。

比率和其平方然后用于计算制导方程每个项的系数：

```agc
            EXTEND
            SQUARE
            TS      BUF +1
            AD      BUF
            XCH     BUF +1          # RATIO SQUARED - RATIO
            AD      BUF +1
            TS      MPAC            # COEFFICIENT FOR VGU TERM
            AD      BUF +1
            INDEX   FIXLOC
            TS      26D             # COEFFICIENT FOR RDG-RGU TERM
            AD      BUF +1
            INDEX   FIXLOC
            TS      28D             # COEFFICIENT FOR VDG TERM
            AD      BUF
            AD      POSMAX
            AD      BUF +1
            AD      BUF +1
            INDEX   FIXLOC
            TS      30D             # COEFFICIENT FOR ADG TERM
```

这串加法从比率和比率²的组合构建出四个不同的系数。这些系数修改标准制导方程以补偿计算延迟，有效地"向前预测"，使推力命令在实际生效时是正确的。

> **不确定性标记：** 我能跟随产生这四个系数的代数运算，但如果没有原始制导系统操作计划（GSOP）推导，我无法独立验证 `BUF`（比率）和 `BUF+1`（比率²）的特定组合是否产生了正确的超前时间补偿制导律。该模式与在 `t + lead_time` 而非 `t` 处评估的制导律的泰勒展开一致。

### 制导计算本身

```agc
            TC      INTPRETX
            VXSC    PDDL
                    VGU
                    28D
            VXSC*   PDVL*
                    VDG,1
                    RDG,1
            VSU     V/SC
                    RGU
                    TTF/8
            VSR2    VXSC
                    26D
            VAD     VAD
            V/SC    VXSC
                    TTF/8
                    3/4DP
            PDDL    VXSC*
                    30D
                    ADG,1
            VAD
```

用解释器伪代码表示，这计算：

1. `coeff_vgu × VGU`——压入栈
2. `coeff_vdg × VDG`——压入栈
3. `(RDG - RGU) / TTF/8`——缩放后的剩余距离速率
4. 以 `coeff_rdg` 缩放，加入累积项
5. 再除以 `TTF/8`，以 3/4 缩放
6. 加 `coeff_adg × ADG`——目标加速度

结果是制导坐标系中的指令加速度向量。

### 重力补偿（AFCCALC1）

```agc
AFCCALC1    VXM     VSL1            # VERGUID COMES HERE
                    CG
            PDVL    V/SC
                    GDT/2
                    GSCALE
            BVSU    STADR
            STORE   UNFC/2          # UNFC/2 NEED NOT BE UNITIZED
```

指令加速度通过 `CG` 矩阵从制导坐标转换到稳定构件坐标（`VXM` = 向量×矩阵，`VSL1` = 向量左移 1 位用于缩放）。然后减去引力加速度（`GDT/2`，以 `GSCALE = 100 B-11` 缩放）。结果 `UNFC/2` 是引擎必须产生的力命令——它是制导命令减去重力，因为重力是"免费的"（引擎不需要产生它）。

### 推力限制（AFCCALC2）

```agc
AFCCALC2    STODL   /AFC/           # MAGNITUDE OF AFC FOR THROTTLE
                    UNFC/2          # VERTICAL COMPONENT
            DSQ     PDDL
                    UNFC/2 +2       # OUT-OF-PLANE
            DSQ     PDDL
                    HIGHESTF
            DDV     DSQ
                    MASS
            DSU     DSU             # AMAXHORIZ = SQRT(ATOTAL² - A₁² - A₀²)
            BPL     DLOAD
                    AFCCALC3
                    ZEROVECS
AFCCALC3    SQRT    DAD
                    UNFC/2 +4
```

这计算最大可用水平加速度：在给定总可用推力（`HIGHESTF / MASS`）和已承诺的垂直及平面外分量的情况下，下行距离方向还有多少加速度可用？如果答案将为负值（引擎无法提供足够推力满足垂直和平面外需求），水平分量被夹零。

`HIGHESTF = 4.34546769 B-12`——这是 AGC 内部单位中登月舱下降引擎的最大推力。

---

## 7. CG 矩阵：制导坐标系

`CGCALC` 建立制导到稳定构件的变换矩阵：

```agc
CGCALC      CAF     EBANK5
            TS      EBANK
            EBANK=  TCGIBRAK
            EXTEND
            INDEX   WCHPHASE
            INDEX   TARGTDEX
            DCA     TCGFBRAK
```

这个双重索引查找检索取决于当前阶段（制动对进近）的时间参数。代码然后检查这个时间是否已到达：

```agc
            AD      TTF/8
            XCH     L
            AD      TTF/8
            CCS     A
            CCS     L
            TCF     EXTLOGIC
            TCF     EXTLOGIC
            NOOP
```

这是 AGC 中测试 DP 值是否非负的习语。双重 `CCS` 测试两个字——如果任何一个为正，控制转到 `EXTLOGIC`（跳过矩阵更新）。只有当两个字都是非正时（时间已到），矩阵才会更新。

矩阵构建本身使用着陆点向量作为主轴：

```agc
            VLOAD   UNIT
                    LAND
            STODL   CG              # First row = UNIT(LAND)
                    TTF/8
            DMP*    VXSC
                    GAINBRAK,1      # NUMERO MYSTERIOSO
                    ANGTERM
            VAD
                    LAND
            VSU     RTB
                    R
                    NORMUNIT
            VXV     RTB
                    LAND
                    NORMUNIT
            STOVL   CG +6           # SECOND ROW
                    CG
            VXV     VSL1
                    CG +6
            STORE   CG +14          # THIRD ROW
```

`CG` 的第一行是 `UNIT(LAND)`——指向着陆点的单位向量，在制导坐标系中定义"向下"。

第二行由调整后的距离向量与 `LAND` 的叉积构成，然后归一化。"NUMERO MYSTERIOSO"注释指的是 `GAINBRAK`——一个增益常量，其推导对程序员来说显然也是神秘的。

第三行是第 1 行和第 2 行的叉积，形成右手正交坐标系。

> **不确定性标记：** 仅从代码来看，`GAINBRAK` 增益在第二行计算中的确切目的不清楚。它似乎根据角动量项（`ANGTERM`）旋转制导坐标系，可能是为了将坐标系与期望的轨迹曲率对齐。没有 GSOP 推导，我无法验证这一解释。

---

## 8. 阶段转换：P63 → P64 → P65/P66/P67

### EXTLOGIC：阶段切换

```agc
EXTLOGIC    INDEX   WCHPHASE
            CA      TENDBRAK        # WCHPHASE = 0: BRAKQUAD
                                    # WCHPHASE = 1: APPRQUAD (offset by TARGTDEX)
            AD      TTF/8

EXSPOT1     EXTEND
            INDEX   WCHPHASE
            BZMF    WHATEXIT        # IF TTF/8 + TEND ≤ 0, TIME TO SWITCH

            TC      FASTCHNG

            CA      WCHPHOLD
            AD      ONE
            TS      WCHPHASE        # INCREMENT WCHPHASE
            CA      ZERO
            TS      FLPASS0         # RESET PASS COUNTER
```

转换条件很简单：当 `TTF/8 + TENDBRAK ≤ 0`（通过 `BZMF`——零或负分支到固定地址——测试），当前阶段的剩余时间已过期，`WCHPHASE` 递增。`TENDBRAK` 是一个负数，表示转换应在目标时间之前多早发生。

- **P63 → P64**：`WCHPHASE` 从 0 到 1。调用 `STARTP64`，将程序号设置为 64，将 TTF/8 增加 `DELTTFAP`，启用 RUPT10（用于重新瞄准手动控制器），并初始化重新瞄准标志。
- **P64 → P65**：`WCHPHASE` 从 1 到 2。`P65START` 设置程序号为 65 并启用 X 轴超控。

### P65 → P66/P67

从 P65 到 P66 或 P67 的转换不是基于时间的——它由宇航员输入驱动，由 GUILDENSTERN 处理（见第 3 节）。当宇航员接通姿态保持或手动油门离散时，GUILDENSTERN 切换程序模式，同时保持 `WCHPHASE = 2`。

在 `WCHPHASE = 2` 内，变量 `WCHVERT` 在 P65、P66 和 P67 之间选择：

```agc
VERTGUID    CCS     WCHVERT
            TCF     P67VERT         # POSITIVE NON-ZERO → P67
            TCF     P66VERT         # +0
# P65 falls through to P65VERT
```

这使用 CCS（计数、比较和跳过）四路分支：
- `WCHVERT > 0` → P67（手动油门；`WCHVERT` 由 `STARTP67` 设置为 10）
- `WCHVERT = +0` → P66（下降率）
- `WCHVERT < 0` → P65 直通（自动垂直下降；`WCHVERT` 由 `P65START` 设置为 -2）

---

## 9. P64——带重新瞄准的进近阶段

### 着陆点重新瞄准（REDESIG）

在 P64 期间，宇航员可以使用手动控制器重新瞄准着陆点。重新瞄准逻辑是进近阶段的制导前计算：

```agc
REDESIG     CA      FLAGWRD6        # IS REDFLAG SET?
            MASK    REDFLBIT
            EXTEND
            BZF     RGVGCALC        # NO: SKIP REDESIGNATION LOGIC

            CA      TREDES          # YES: HAS TREDES REACHED ZERO?
            EXTEND
            BZF     RGVGCALC        # YES: SKIP REDESIGNATION LOGIC
```

必须满足两个条件：`REDFLAG` 必须被设置（当宇航员在闪烁显示上"继续"时由 P64CEED 启用），并且 `TREDES` 必须非零（随着 TTF 减小倒计时到零——在进近末段重新瞄准被禁用）。

重新瞄准本身修改 `LAND` 向量：

```agc
            INHINT
            CA      ELINCR1
            TS      ELINCR
            CA      AZINCR1
            TS      AZINCR
            TC      FASTCHNG

            CA      ZERO
            TS      ELINCR1
            TS      AZINCR1
```

`ELINCR1` 和 `AZINCR1` 是来自手动控制器的累积仰角和方位角增量（由下面讨论的 PITFALL 中断处理程序累积）。它们在中断禁止（`INHINT`）下原子地传输到工作副本并清零。这是安全地将数据从中断处理程序传递到主循环计算的经典双缓冲模式。

重新瞄准数学沿视线（LOS）移动着陆点：

```agc
            VLOAD   VSU
                    LAND
                    R
            RTB     PUSH            # PUSH DOWN UNIT(LAND - R)
                    NORMUNIT
            VXV     VSL1
                    YNBPIP          # -ELINCR(YNB × UNIT(LAND - R))
            VXSC    PDDL
                    ELINCR
                    AZINCR
            VXSC    VSU
                    YNBPIP
            VAD     PUSH            # RESULTING VECTOR IS 1/2 REAL SIZE
```

仰角增量围绕登月舱的 Y 机体轴（交叉方向）旋转 LOS，而方位角增量沿 Y 机体轴移动它。俯角检查防止重新瞄准点太靠近地平线：

```agc
            DLOAD   DSU             # MAKE SURE REDESIGNATION IS NOT
                    0               #   TOO CLOSE TO THE HORIZON.
                    DEPRCRIT
            BMN     DLOAD
                    REDES1
                    DEPRCRIT
            STORE   0
```

`DEPRCRIT = -.02 B-1`——临界俯角。如果计算出的俯角低于此阈值，则被夹住。

### PITFALL 中断处理程序：重新瞄准陷阱

```agc
PITFALL     XCH     BANKRUPT
            EXTEND
            QXCH    QRUPT

            TC      CHECKMM         # IF NOT IN P64, NO REASON TO CONTINUE
            DEC     64
            TCF     RESUME
```

`PITFALL` 是 RUPT10 处理程序——当宇航员移动重新瞄准手动控制器时触发。它首先检查我们是否确实在 P64（在其他程序中处理重新瞄准输入没有意义），如果不是则恢复。

如果在 P64 中，它读取控制器位，设置监视任务，并返回：

```agc
            EXTEND
            READ    CHAN31
            COM
            MASK    ALL4BITS
            TS      ELVIRA
            CAF     TWO
            TS      ZERLINA
            CAF     FIVE
            TC      TWIDDLE
            ADRES   REDESMON
            TCF     RESUME
```

名字 `ELVIRA` 和 `ZERLINA` 是歌剧角色引用——`ELVIRA` 来自莫扎特的《唐·乔瓦尼》，`ZERLINA` 来自同一部歌剧。`ELVIRA` 保存控制器位的当前状态；`ZERLINA` 是超时计数器。

`REDESMON`（重新瞄准监视器）定期轮询控制器，等待宇航员释放开关：

```agc
REDESMON    EXTEND
            READ    31
            COM
            MASK    ALL4BITS
            XCH     ELVIRA
            TS      L
            CCS     ELVIRA          # DO ANY BITS APPEAR THIS PASS?
            TCF     PREMON2         # Y: CONTINUE MONITOR

            CCS     L               # N: ANY LAST PASS?
            TCF     COUNT'EM        # Y: COUNT 'EM, RESET RUPT, TERMINATE
```

当开关释放（位消失）时，`COUNT'EM` 累积方位角和仰角增量：

```agc
COUNT'EM    ...
            CA      L
            MASK    -AZBIT
            CCS     A
-AZ         CS      AZEACH
            ADS     AZINCR1
            ...
            CA      L
            MASK    +ELBIT
            CCS     A
+EL         CA      ELEACH
            ADS     ELINCR1
```

控制器每次"点击"添加固定增量：
- `AZEACH = .03491`——每次点击 2 度方位角
- `ELEACH = .00873`——每次点击 0.5 度仰角

位分配有文档说明：

```agc
+ELBIT      =       BIT2            # -PITCH
-ELBIT      =       BIT1            # +PITCH
+AZBIT      =       BIT5
-AZBIT      =       BIT6
```

注意反转：`+ELBIT` 对应 `-PITCH`。LPD 窗口刻度被校准，使"俯仰向下"（负俯仰）将着陆点移得更远（LPD 坐标系中的正仰角）。

---

## 10. P66——下降率模式

P66 是半自动着陆模式。计算机控制姿态以保持垂直下降；宇航员通过 ROD（下降率）开关控制下降率。

### ROD 任务

```agc
RODTASK     CAF     PRIO22
            TC      FINDVAC
            EBANK=  DVCNTR
            2CADR   RODCOMP

            TCF     TASKOVER
```

`RODTASK` 每秒运行一次（由 `TWIDDLE` 以 1 秒延迟调度），优先级 22。它生成 `RODCOMP` 作业来计算 ROD 制导。

### RODCOMP：ROD 计算

```agc
RODCOMP     INHINT
            CAF     ZERO
            XCH     RODCOUNT
            EXTEND
            MP      RODSCAL1
            DAS     VDGVERT         # UPDATE DESIRED ALTITUDE RATE.
```

`RODCOUNT` 累积来自 ROD 开关的点击（通过 `DESCBITS` 中断处理程序）。每次点击从期望垂直速率 `VDGVERT` 中增加或减少。计数在中断禁止下原子地读取和清零。

ROD 陷阱处理程序优雅地简单：

```agc
DESCBITS    MASK    BIT7            # BIT 7 = - RATE INCREMENT
            CCS     A               # BIT 6 = + INCREMENT
            CS      TWO
            AD      ONE
            ADS     RODCOUNT
            TCF     RESUME          # TRAP IS RESET WHEN SWITCH IS RELEASED
```

第 7 位表示"降低速率"（下降更快），第 6 位表示"提高速率"（下降更慢或上升）。`CCS / CS TWO / AD ONE` 模式转换：如果第 7 位存在，`CCS` 后 A 为正，所以 `CS TWO` = -2，`AD ONE` = -1；如果第 7 位不存在（第 6 位必须存在），`CCS` 后 A 为零，所以跳到 `AD ONE` = +1。每次点击将 `RODCOUNT` 变化 ±1。

### P66 制导律

P66 制导律比 P63/P64 复杂得多。它在 `RODCOMP` 中运行，执行：

1. **PIPA 读取和偏置校正**——读取三个加速度计通道，应用偏置校正
2. **速度更新**——积分加速度得到当前速度，应用重力补偿
3. **高度率计算**——将速度与单位位置向量点积得到 HDOT（高度率）
4. **高度更新**——计算当前高度
5. **油门命令**——计算实现期望下降率所需的推力

油门律：

```agc
            STODL   HDOTDISP
                    30D
            SL      DMP
                    11D
                    HDOTDISP
            DAD     DSU
                    36D
                    /LAND/
            STODL   HCALC1          # UPDATE HCALC1 FOR NOUN 63.
                    HDOTDISP
            BDSU    DDV
                    VDGVERT
                    TAUROD
```

高度率误差（`VDGVERT - HDOTDISP`）除以 `TAUROD`（时间常数）得到指令加速度。这是一个简单的比例控制器：如果实际下降率与期望速率不同，命令与误差成比例的加速度。

油门计算还包括推力限制：

```agc
            PDDL    DDV
                    MAXFORCE
                    MASS
            PDDL    DDV
                    MINFORCE
                    MASS
            PUSH    BDSU
                    2D
            BMN     DLOAD
                    AFCSPOT
            DLOAD   PUSH
            BDSU    BPL
                    2D
                    AFCSPOT
            DLOAD
AFCSPOT     DLOAD
            SETPD
                    2D
            STODL   /AFC/
```

指令加速度被夹在 `MINFORCE/MASS` 和 `MAXFORCE/MASS` 之间——登月舱下降引擎有最小油门设置（约 10%——引擎无法在不失稳的情况下节流到此以下）和最大值。

> **不确定性标记：** P66 制导律涉及多个中间计算（`ITRPNT1` 和 `ITRPNT2` 标签表明这是迭代开发的）。PIPA 读数的精确缩放、通过 `LAG/TAU` 的滞后补偿以及 `SHFTFACT`/`SCALEFAC` 常量需要与 GSOP 和 PIPA 校准数据交叉参考才能完全验证。整体结构——带推力限制的比例高度率控制——是清楚的，但每个中间步骤的数值精度仅从代码来看难以验证。

---

## 11. P65——自动垂直下降

P65 是最简单的制导模式——线性速度跟踪律：

```agc
# THE P65 GUIDANCE EQUATION IS AS FOLLOWS:
#           V2FG - VGU
#     ACG = ----------
#            TAUVERT

P65VERT     TC      INTPRET
            VLOAD   VSU
                    V2FG
                    VGU
            V/SC    GOTO
                    TAUVERT
                    AFCCALC1
```

指令加速度简单地是速度误差除以时间常数。`V2FG` 是垂直下降的目标速度向量，`VGU` 是制导坐标系中的当前速度，`TAUVERT` 是制导时间常数。这驱动登月舱向期望的垂直下降速度剖面趋近。

`GOTO AFCCALC1` 与二次制导共用重力补偿和推力计算。

---

## 12. P67——手动油门

P67 给宇航员完全手动控制：

```agc
P67VERT     TC      PHASCHNG        # TERMINATE GROUP 3.
            OCT     00003

            TC      INTPRET
            VLOAD   GOTO
                    V
                    VHORCOMP
```

P67 终止制导组（第 3 组——不再有自动制导），直接转到 `VHORCOMP`，后者只计算用于显示的水平速度。宇航员手动控制姿态和油门。计算机唯一的作用是计算和显示 `VHORIZ`（水平速度），使宇航员知道何时关闭引擎。

---

## 13. 显示更新

### P63 显示：V06N63

```agc
P63DISPS    CAF     V06N63
DISPCOMN    TC      BANKCALL
            CADR    REGODSPR
```

Verb 06 Noun 63 显示：
- R1：高度率（HDOTDISP）
- R2：高度（HCALC1）
- R3：（飞行特定，通常是横向速度）

### P64 显示：V06N64（闪烁）

```agc
P64DISPS    CA      TREDES          # HAS TREDES REACHED ZERO?
            EXTEND
            BZF     RED-OVER        # YES: CLEAR REDESIGNATION FLAG

            CS      FLAGWRD6        # NO: IS REDFLAG SET?
            MASK    REDFLBIT
            EXTEND
            BZF     REDES-OK        # YES: DO STATIC DISPLAY

            CAF     V06N64          # OTHERWISE USE FLASHING DISPLAY
            TC      BANKCALL
            CADR    REFLASHR
            TCF     GOTOPOOH        # TERMINATE
            TCF     P64CEED         # PROCEED: PERMIT REDESIGNATIONS
            TCF     P64DISPS        # RECYCLE
            TCF     ENDLLJOB
```

P64 显示是**闪烁的**，直到宇航员"继续"（在 DSKY 上按 PRO），这启用重新瞄准逻辑。这是一个刻意的人因设计：宇航员必须主动确认他们想要控制着陆点选择。继续后，显示变为静态（不闪烁）。

`REFLASHR` 根据宇航员的响应返回三个位置之一：
- 终止（第一个返回）→ `GOTOPOOH`（中止到空闲）
- 继续（第二个返回）→ `P64CEED`（启用重新瞄准）
- 刷新（第三个返回）→ `P64DISPS`（刷新显示）

### P65/P66/P67 显示：V06N60

```agc
VERTDISP    CAF     V06N60
            TCF     DISPCOMN
```

Verb 06 Noun 60 显示高度率、高度和（对于 P66）当前下降率命令。

### 显示抑制

```agc
DISPEXIT    EXTEND
            DCA     NEG0
            DXCH    -PHASE3

 +3         CS      FLAGWRD8        # IF FLUNDISP IS SET, NO DISPLAY THIS PASS
            MASK    FLUNDBIT
            EXTEND
            BZF     ENDLLJOB
```

每个周期显示都被终止（`-PHASE3` 设置为 -0，终止第 3 组的重启保护），并由下一个制导周期恢复。`FLUNDISP` 标志可以完全抑制显示——在关键阶段使用，此时显示更新会浪费宝贵的 CPU 时间。

---

## 14. 窗口向量和转向

### EXBRAK：制动阶段退出

```agc
EXBRAK      TC      INTPRET
            VLOAD
                    UNIT/R/
            STORE   UNWC/2
            EXIT
            TCF     STEER?
```

在制动过程中，窗口指向向量简单地是 `UNIT(R)`——将登月舱窗口直接朝上（远离月球）。这是制动燃烧期间使用的"窗口朝上"姿态。

### EXNORM：正常退出（P64）

```agc
EXNORM      TC      INTPRET
            VLOAD   VSU
                    LAND
                    R
            RTB
                    NORMUNIT
            STORE   UNWC/2          # UNIT(LAND - R) IS TENTATIVE CHOICE
            VXV     DOT
                    XNBPIP
                    CG +6
            EXIT
```

在进近过程中，窗口向量是 `UNIT(LAND - R)`——指向着陆点。然后根据投影角与备用向量混合：

```agc
            CS      MPAC            # GET COEFFICIENT FOR CG +14
            AD      PROJMAX
            AD      POSMAX
            TS      BUF
            CS      BUF
            ADS     BUF             # RESULT IS 0 IF PROJMAX - PROJ NEGATIVE

            CS      PROJMIN         # GET COEFFICIENT FOR UNIT(LAND - R)
            AD      MPAC
            AD      POSMAX
            TS      BUF +1
            CS      BUF +1
            ADS     BUF +1          # RESULT IS 0 IF PROJ - PROJMIN NEGATIVE
```

混合使用 `PROJMAX`（sin 25°/8）和 `PROJMIN`（sin 15°/8）在朝向着陆点的向量和备用向量（CG 矩阵的第 3 行）之间创建平滑过渡，当观察角在 15° 到 25° 之间时。低于 15° 时，着陆点太靠近地平线，备用向量完全接管。

实际混合循环：

```agc
            CAF     FOUR
UNWCLOOP    MASK    SIX
            TS      Q
            ...
            INDEX   Q
            MP      CG +14
            ...
            INDEX   Q
            DAS     UNWC/2
            CCS     Q
            TCF     UNWCLOOP
```

这循环遍历窗口向量的三个分量（Q = 4、2、0），用各自的系数混合两个候选向量。

### 转向和油门

```agc
STEER?      CA      FLAGWRD2        # IF STEERSW DOWN NO OUTPUTS
            MASK    STEERBIT
            EXTEND
            BZF     RATESTOP

EXVERT      CA      OVFIND          # IF OVERFLOW ANYWHERE IN GUIDANCE
            EXTEND                  #   DON'T CALL THROTTLE OR FINDCDUW
            BZF     +13

EXOVFLOW    TC      ALARM           # SOUND THE ALARM NON-ABORTIVELY
            OCT     01410
```

如果转向开关关闭，或者制导计算任何地方发生溢出，则不发出命令。报警码 01410 表示制导溢出——这是非中止的（系统在下一个周期继续而不触发中止）。

如果一切正常：

```agc
GDUMP1      TC      THROTTLE
            TC      INTPRET
            CALL
                    FINDCDUW -2
            EXIT
```

`THROTTLE` 命令下降引擎，`FINDCDUW` 计算 CDU（耦合显示单元）命令以将登月舱转向期望姿态。

---

## 15. 求根器（ROOTPSRS）

Allan Klumpp 的双精度牛顿法求根器值得特别关注。它是一个通用子程序，用于找到 N 次多项式的一个根。着陆制导用它来求解三次剩余时间方程。

### 设置

```agc
ROOTPSRS    EXTEND
            QXCH    RETROOT         # SAVE RETURN ADDRESS
            TS      PWRPTR          # POWER TABLE POINTER
            DXCH    MPAC +3         # PWR TABLE ADRES, N-1
            CA      DERTABLL
            TS      DERPTR          # DERIVATIVE TABLE POINTER
```

### 导数系数表

在迭代之前，ROOTPSRS 通过将每个 A(i) 乘以 i 来预计算导数系数：

```agc
DERCLOOP    TS      PWRCNT
            AD      ONE
            TC      DMPNSUB         # YIELDS DERCOF = I × A(I)
            EXTEND
            INDEX   PWRPTR
            DCA     1
            DXCH    MPAC            # (I-1) TO MPAC, FETCHING DERCOF
            INDEX   DERPTR
            DXCH    3               # DERCOF TO DER TABLE
            CS      TWO
            ADS     PWRPTR          # DECREMENT PWR POINTER
            CS      TWO
            ADS     DERPTR          # DECREMENT DER POINTER
            CCS     PWRCNT
            TCF     DERCLOOP
```

### 牛顿迭代

```agc
ROOTLOOP    EXTEND
            DCA     ROOTPS          # CURRENT ROOT
            DXCH    MPAC
            EXTEND
            DCA     MPAC +5         # DER TABLE ADRES, N-2
            TC      POWRSERS        # EVALUATE DERIVATIVE

            EXTEND
            DCA     ROOTPS
            DXCH    MPAC            # ROOT TO MPAC, DERIVATIVE TO BUF
            DXCH    BUF
            EXTEND
            DCA     MPAC +3         # PWR TABLE ADRES, N-1
            TC      POWRSERS        # EVALUATE RESIDUAL

            TC      USPRCADR
            CADR    DDV/BDDV        # -DX = RESIDUAL / DERIVATIVE

            EXTEND
            DCS     MPAC            # DX (negated)
            DAS     ROOTPS          # CORRECTED ROOT
```

每次迭代：在当前猜测处评估多项式及其导数，计算牛顿步 `dx = -f(x)/f'(x)`，并更新根。

### 收敛检查

```agc
            CA      MODE
            MASK    BIT4            # GIVE UP AFTER 8 PASSES
            CCS     A
BADROOT     TC      RETROOT         # FAIL: RETURN TO CALLER + 1

            INCR    MODE
            CCS     MPAC            # TEST |DX| AGAINST CRITERION
            TCF     ROOTLOOP        # NOT CONVERGED
            TCF     TESTLODX
            TCF     ROOTSTOR        # CONVERGED
```

`MODE` 用作迭代计数器。测试 `BIT4`（值为 8）——当 MODE 达到 8 时，掩码产生非零值，`CCS` 分支到 `BADROOT`。收敛测试通过高字和低字的 CCS 四路跳过检查 `|DX| - DXCRIT ≤ 0`。

注释中记录的预防措施对于 1960 年代的软件来说是非凡的：

```
# PRECAUTION: ROOTPSRS MAKES NO CHECKS FOR OVERFLOW OR FOR IMPROPER 
# USAGE. IMPROPER USAGE COULD PRECLUDE CONVERGENCE OR REQUIRE EXCESSIVE 
# ITERATIONS.
```

这本质上是一个"此处有龙"警告——该例程信任其调用方提供良好缩放的输入。

---

## 16. FASTCHNG 子程序

这个微小的子程序在文件中随处可见，值得解释：

```agc
            EBANK=  PHSNAME2
FASTCHNG    CA      EBANK3
            XCH     EBANK
            DXCH    L
            TS      PHSNAME3
            LXCH    EBANK
            EBANK=  E2DPS
            TC      A
```

这是一个"专用 PHASCHNG 例程"——避免完整 PHASCHNG 子程序开销的快速版本相位变更保护。它将当前位置作为重启点存储在 PHSNAME3（第 3 组的阶段名）中。诀窍是 `DXCH L` 将 A、L 对与 L 寄存器及其后一个字交换——由于 A 被加载了 EBANK3，返回地址在 Q 中（隐式，因为使用了 TC 调用 FASTCHNG），这原子地记录了重启点。

末尾的 `TC A` 是返回——A 包含保存的 EBANK 值，`TC A` 将控制转移到 A 中的地址。

> **不确定性标记：** FASTCHNG 中精确的寄存器舞蹈很棘手。净效果是清楚的——它将调用方的地址记录为第 3 组重启点——但 A、L 和 Q 寄存器参与的 DXCH 的精确流程需要仔细的逐周期分析，我可能有某些细节不对。关键点是这是一个性能优化：它用约 7 条指令完成了通用 `PHASCHNG` 子程序更多指令才能完成的事。

---

## 17. 常量和缩放

```agc
HIGHESTF    2DEC    4.34546769 B-12
```

登月舱下降引擎的最大推力，以 2^-12 缩放。在 AGC 的小数算术中，这以内部单位表示推力（可能是成千上万磅，缩放以适应 0-1 范围）。

```agc
GSCALE      2DEC    100 B-11
```

重力缩放因子。100 × 2^-11——用于将重力向量转换为制导单位。

```agc
3/8DP       2DEC    .375
3/4DP       2DEC    .750
```

制导方程中使用的小数常量。这些避免了整数乘法（会使小数表示溢出），通过将其表达为小数。

```agc
DEPRCRIT    2DEC    -.02 B-1
```

重新瞄准限制的俯角判据——约 -1.15 度（-.02 弧度，以 B-1 = 2^-1 缩放）。

```agc
PROJMAX     DEC     .42262 B-3      # SIN(25°)/8
PROJMIN     DEC     .25882 B-3      # SIN(15°)/8
```

窗口向量混合阈值。B-3 缩放意味着这些实际上是 sin(angle)/8，与投影计算中使用的 1/8 缩放相匹配。

```agc
AZEACH      DEC     .03491          # 2 DEGREES
ELEACH      DEC     .00873          # 1/2 DEGREE
```

每次手动控制器点击的重新瞄准增量。这些是弧度值（0.03491 弧度 ≈ 2°，0.00873 弧度 ≈ 0.5°）。不对称是刻意的：方位角（左右）变化需要更大的增量，因为每度方位角变化时着陆点移动较少，而仰角（近远）更敏感。

```agc
BIASFACT    2DEC    655.36 B-28
```

PIPA 偏置缩放因子。655.36 × 2^-28——将 PIPA 偏置值转换为 ROD 计算中使用的速度单位。

---

## 18. 历史注记和彩蛋

### GUILDENSTERN（以及其他地方的 ROSENSTERN）

莎士比亚/斯托帕德的引用是代码库中最著名的命名。监视自动模式切换的例程以那些被超出自己控制的事件所左右的人物命名——这是对必须响应宇航员任何操作的模式切换逻辑的恰当比喻。

### "临时性，我希望希望希望"

```agc
            TC      BANKCALL        # TEMPORARY, I HOPE HOPE HOPE
            CADR    STOPRATE        # TEMPORARY, I HOPE HOPE HOPE
```

在垂直下降初始化开始时对 `STOPRATE` 的调用本意是临时的——一个将姿态角速率清零以进入 P65/P66/P67 的快速修复。程序员三重"HOPE"表达了普世程序员的哀叹：没有什么比临时修复更持久的了。它就这样在阿波罗 11 号上飞行。

### ELVIRA 和 ZERLINA

重新瞄准监视器使用歌剧角色名称作为其状态变量——`ELVIRA` 保存当前控制器状态，`ZERLINA` 是去抖超时计数器。两个角色都来自莫扎特的《唐·乔瓦尼》。这种命名约定在 MIT 仪器实验室代码中很常见——变量名被选为令人难忘且有特色的，而非描述性的。

### "神秘数字"

```agc
            DMP*    VXSC
                    GAINBRAK,1      # NUMERO MYSTERIOSO
```

写这条注释的程序员不完全理解这个增益常量的来源——它来自轨迹分析，只是作为一个魔法数字提供。这种坦诚令人耳目一新：他们没有假装理解它，而是诚实地标记了出来。

### 报警码 01406

```agc
1406P00     TC      POODOO
            OCT     01406
1406ALM     TC      ALARM
            OCT     01406
            TCF     RATESTOP
```

报警 1406 表示 TTF/8 求根器未能收敛。在点火算法（IGNALG）期间，这是致命的——`POODOO` 触发程序报警并转到 P00（空闲）。在制动或进近期间，它是非致命的——报警被触发，但制导以速率阻尼（`RATESTOP`）继续。

致命错误处理程序的名字 `POODOO` 是 MIT IL 丰富命名的另一个例子。它在整个代码库中用于不可恢复的错误。

---

## 19. 控制流摘要

```
LUNLAND（来自 SERVOUT，约 2 Hz）
  │
  ├── GUILDENSTERN：检查宇航员模式开关
  │     ├── 手动油门？→ P67
  │     ├── 姿态保持 + 曾是 P67？→ P66
  │     ├── 姿态保持 + ROD 点击？→ P66
  │     └── 继续当前程序
  │
  ├── GUILDRET：初始化过程
  │     ├── 保存 TPIP 时间戳
  │     ├── 将 TTF/8 复制到工作副本
  │     └── 检查 FLPASS0
  │
  ├── NEWPHASE[WCHPHASE]：如需则开始新阶段
  │     ├── IGNALG/BRAKQUAD → TTFINCR
  │     ├── APPRQUAD → STARTP64
  │     └── VERTICAL → P65START
  │
  ├── TTFINCR：更新剩余时间和着陆点
  │
  ├── PREGUIDE[WCHPHASE]：制导前
  │     ├── IGNALG → CALCRGVG（从积分计算 V）
  │     ├── BRAKQUAD/VERTICAL → RGVGCALC
  │     └── APPRQUAD → REDESIG → RGVGCALC
  │
  ├── WHATGUID[WCHPHASE]：制导方程
  │     ├── IGNALG/BRAKQUAD/APPRQUAD → TTF/8CL → QUADGUID
  │     └── VERTICAL → VERTGUID
  │           ├── P65VERT（线性速度跟踪）
  │           ├── P66VERT → RODCOMP（下降率）
  │           └── P67VERT（仅显示）
  │
  ├── AFTRGUID[WCHPHASE]：制导后
  │     ├── IGNALG/BRAKQUAD/APPRQUAD → CGCALC → EXTLOGIC
  │     └── VERTICAL → STEER?
  │
  ├── WHATEXIT[WCHPHASE]：退出/窗口向量
  │     ├── EXGSUB（点火算法返回）
  │     ├── EXBRAK（窗口 = UNIT(R)）
  │     └── EXNORM（窗口 = 混合朝向 LAND）
  │
  ├── STEER? → THROTTLE → FINDCDUW
  │
  └── WHATDISP[WCHPHASE]：显示
        ├── P63DISPS → V06N63
        ├── P64DISPS → V06N64（闪烁直到按 PROCEED）
        └── VERTDISP → V06N60
```

---

## 20. 1969 年 7 月 20 日这段代码实际做了什么

UTC 时间 20:05，登月舱*鹰号*开始动力下降。P63（制动）点燃下降引擎以从轨道速度减速。`QUADGUID` 中的二次制导律每约 2 秒计算一次推力命令，而 `TTFINCR` 跟踪剩余时间并补偿月球自转。

在大约 7,000 英尺高度，P64（进近）接管。Neil Armstrong 通过 LPD 窗口看到计算机正在瞄准西克陨石坑边缘的一片巨石区。他使用重新瞄准手动控制器——由 `PITFALL` 和 `REDESMON` 处理，累积在 `ELINCR1`/`AZINCR1` 中，并在 `REDESIG` 中应用——移动了着陆点。DSKY 通过 Noun 64 显示 LPD 角度（`LOOKANGL`）。

在大约 500 英尺高度，P66（下降率）接合。Armstrong 使用 ROD 开关——由 `DESCBITS` 处理，累积在 `RODCOUNT` 中，在 `RODCOMP` 中应用——控制下降率，而计算机保持姿态。`VDGVERT` 跟踪他的期望速率；`TAUROD` 控制计算机达到该速率的积极程度。

下降过程中发生的"1202"和"1201"程序报警不在此文件中——它们来自执行模块的作业溢出检测。但此文件中的制导在这些报警中持续运行，因为重启保护（`PHASCHNG`、`FASTCHNG`）确保每个制导周期都能从已知状态重启。

UTC 时间 20:17，在大约还有 25 秒燃料时，Armstrong 听到"接触灯"，悬挂在着陆腿上的 67 英寸探针触碰了地面。他按下了发动机停止按钮。此文件中的代码完成了它的使命。

---

## 附录：关键变量词汇表

| 变量 | 类型 | 描述 |
|------|------|------|
| `WCHPHASE` | SP | 阶段选择器：-1=IGNALG，0=制动，1=进近，2=垂直 |
| `WCHVERT` | SP | 垂直模式：<0=P65，0=P66，>0=P67 |
| `TTF/8` | DP | 剩余时间/8（厘秒，缩放） |
| `LAND` | 向量（3×DP） | 着陆点位置向量（惯性，月球固定） |
| `/LAND/` | DP | LAND 向量的量级 |
| `R` | 向量 | 当前登月舱位置 |
| `V` | 向量 | 当前登月舱速度 |
| `RGU` | 向量 | 制导坐标系中的位置 |
| `VGU` | 向量 | 制导坐标系中的速度 |
| `CG` | 矩阵（3×3） | 制导到稳定构件的变换 |
| `ANGTERM` | 向量 | V + R × WM（相对表面速度） |
| `UNFC/2` | 向量 | 指令力/2（推力命令的一半） |
| `/AFC/` | DP | 指令加速度的量级（用于油门） |
| `UNWC/2` | 向量 | 窗口指向向量/2 |
| `VDGVERT` | DP | 期望垂直速度（P66 ROD 目标） |
| `HDOTDISP` | DP | 当前高度率（用于显示） |
| `RODCOUNT` | SP | 累积的 ROD 开关点击数 |
| `ELINCR1` | DP | 累积的仰角重新瞄准增量 |
| `AZINCR1` | DP | 累积的方位角重新瞄准增量 |
| `FLPASS0` | SP | 当前阶段内的过程计数器 |
| `WM` | 向量 | 月球角速度 |
| `REFSMMAT` | 矩阵 | 参考到稳定构件矩阵 |
