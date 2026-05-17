# Apollo 11 AGC 源代码模块对照

## Luminary099（登月舱 — LGC）

| 类别 | 文件名 | 行数 | 用途 |
|----------|----------|-------|---------|
| **执行程序/调度器** | EXECUTIVE.agc | 503 | 作业调度与基于优先级的多任务执行程序 |
| **执行程序/调度器** | WAITLIST.agc | 564 | 基于定时器的任务调度（等待列表，T3RUPT） |
| **执行程序/调度器** | PHASE_TABLE_MAINTENANCE.agc | 411 | 阶段表更新与 DSKY 程序编号显示 |
| **重启/故障处理** | FRESH_START_AND_RESTART.agc | 1242 | 冷启动初始化与重启恢复 |
| **重启/故障处理** | RESTART_TABLES.agc | 293 | 作业/等待列表/长调用重启恢复表 |
| **重启/故障处理** | RESTARTS_ROUTINE.agc | 323 | 重启处理逻辑 |
| **重启/故障处理** | ALARM_AND_ABORT.agc | 251 | 非中止警报显示与中止处理 |
| **制导/导航** | LUNAR_LANDING_GUIDANCE_EQUATIONS.agc | 1474 | 月面着陆的动力下降制导方程 |
| **制导/导航** | ASCENT_GUIDANCE.agc | 647 | 月面上升制导目标 |
| **制导/导航** | THE_LUNAR_LANDING.agc | 335 | 月面着陆程序排序（P63/P64/P66） |
| **制导/导航** | P20-P25.agc | 5182 | 交会导航、跟踪与状态矢量更新 |
| **制导/导航** | P30_P37.agc | 185 | 外部增量速度目标与返回地球 |
| **制导/导航** | P32-P35_P72-P75.agc | 1394 | 共面轨道序列启动（CSI/CDH）程序 |
| **制导/导航** | P34-35_P74-75.agc | 1764 | 转移段启动（TPI/TPF）程序 |
| **制导/导航** | GENERAL_LAMBERT_AIMPOINT_GUIDANCE.agc | 168 | Lambert 瞄准点目标（P31） |
| **制导/导航** | GROUND_TRACKING_DETERMINATION_PROGRAM.agc | 208 | 无通信时的地面轨迹显示（P21） |
| **制导/导航** | R30.agc | 464 | 轨道参数计算与显示（V82） |
| **制导/导航** | R31.agc | 266 | 交会参数显示 |
| **制导/导航** | STABLE_ORBIT.agc | 436 | 稳定轨道交会程序（P38/P78） |
| **制导/导航** | P70-P71.agc | 439 | 中止制导程序（DPS/APS 中止） |
| **制导/导航** | P76.agc | 161 | 另一飞行器状态矢量更新的目标增量速度程序 |
| **制导/导航** | INTEGRATION_INITIALIZATION.agc | 1102 | 轨道积分初始化与状态矢量设置 |
| **制导/导航** | ORBITAL_INTEGRATION.agc | 977 | 数值轨道积分（Encke 方法） |
| **制导/导航** | CONIC_SUBROUTINES.agc | 1864 | 圆锥轨迹解算子程序 |
| **制导/导航** | MEASUREMENT_INCORPORATION.agc | 495 | 通过统计加权进行状态矢量修正（W 矩阵） |
| **制导/导航** | LATITUDE_LONGITUDE_SUBROUTINES.agc | 306 | 径向矢量到纬度/经度/高度的转换 |
| **制导/导航** | PLANETARY_INERTIAL_ORIENTATION.agc | 385 | 行星坐标系到惯性坐标系变换（RP-TO-R） |
| **制导/导航** | LUNAR_AND_SOLAR_EPHEMERIDES_SUBROUTINES.agc | 183 | 太阳和月球位置计算 |
| **制导/导航** | TIME_OF_FREE_FALL.agc | 721 | 圆锥轨迹的飞行时间子程序 |
| **制导/导航** | POWERED_FLIGHT_SUBROUTINES.agc | 447 | 动力飞行计算支持程序 |
| **制导/导航** | INFLIGHT_ALIGNMENT_ROUTINES.agc | 300 | 飞行中 IMU 对准数学运算 |
| **推进/推力控制** | BURN_BABY_BURN--MASTER_IGNITION_ROUTINE.agc | 1059 | DPS/APS 点火的主点火排序 |
| **推进/推力控制** | P40-P47.agc | 1471 | DPS/APS 推力程序与机动设置 |
| **推进/推力控制** | P12.agc | 243 | 动力上升程序 |
| **推进/推力控制** | THROTTLE_CONTROL_ROUTINES.agc | 224 | DPS 油门指令生成 |
| **推进/推力控制** | SERVICER.agc | 1715 | 平均-G、读加速度计、增量速度累积 |
| **推进/推力控制** | LANDING_ANALOG_DISPLAYS.agc | 533 | 着陆阶段模拟显示输出（高度变化率等） |
| **自动驾驶/姿态控制** | DAPIDLER_PROGRAM.agc | 494 | DAP 初始化与空转循环（10 Hz） |
| **自动驾驶/姿态控制** | DAP_INTERFACE_SUBROUTINES.agc | 176 | DAP 接口实用子程序 |
| **自动驾驶/姿态控制** | P-AXIS_RCS_AUTOPILOT.agc | 1056 | P 轴（滚转）RCS 喷气自动驾驶 |
| **自动驾驶/姿态控制** | Q_R-AXIS_RCS_AUTOPILOT.agc | 860 | Q/R 轴（俯仰/偏航）RCS 喷气自动驾驶 |
| **自动驾驶/姿态控制** | TJET_LAW.agc | 519 | 喷气点火时间计算（相平面逻辑） |
| **自动驾驶/姿态控制** | KALMAN_FILTER.agc | 101 | DAP 状态估计滤波器 |
| **自动驾驶/姿态控制** | T6-RUPT_PROGRAMS.agc | 163 | RCS 喷气计时的 T6 中断 |
| **自动驾驶/姿态控制** | TRIM_GIMBAL_CONTROL_SYSTEM.agc | 617 | DPS 万向节配平控制 |
| **自动驾驶/姿态控制** | SPS_BACK-UP_RCS_CONTROL.agc | 196 | 对接状态下的 RCS 备份控制 |
| **自动驾驶/姿态控制** | AOSTASK_AND_AOSJOB.agc | 1069 | 1/ACCS——制导到 DAP 接口与质量特性 |
| **自动驾驶/姿态控制** | RCS_FAILURE_MONITOR.agc | 173 | RCS 隔离阀故障检测（T4RUPT） |
| **自动驾驶/姿态控制** | ATTITUDE_MANEUVER_ROUTINE.agc | 1027 | KALCMANU 自由飞行姿态机动生成 |
| **自动驾驶/姿态控制** | KALCMANU_STEERING.agc | 221 | KALCMANU 转向指令生成 |
| **自动驾驶/姿态控制** | GIMBAL_LOCK_AVOIDANCE.agc | 76 | 万向节锁死检测与规避 |
| **自动驾驶/姿态控制** | R60_62.agc | 577 | 通用姿态机动子程序（R60/R62） |
| **自动驾驶/姿态控制** | R63.agc | 156 | FDAI 球角指向 CSM（V89） |
| **自动驾驶/姿态控制** | FINDCDUW--GUIDAP_INTERFACE.agc | 743 | 指令万向节角与推力方向滤波器 |
| **DSKY/显示** | PINBALL_GAME_BUTTONS_AND_LIGHTS.agc | 3798 | 键盘与显示系统（DSKY）主程序 |
| **DSKY/显示** | PINBALL_NOUN_TABLES.agc | 906 | DSKY 名词定义表 |
| **DSKY/显示** | DISPLAY_INTERFACE_ROUTINES.agc | 1459 | 优先级/普通/扩展动词显示管理 |
| **DSKY/显示** | EXTENDED_VERBS.agc | 1681 | 扩展动词指令处理 |
| **DSKY/显示** | KEYRUPT_UPRUPT.agc | 130 | 键盘与上行链路中断处理程序 |
| **DSKY/显示** | SERVICE_ROUTINES.agc | 221 | 显示与警报服务程序 |
| **IMU/传感器** | IMU_MODE_SWITCHING_ROUTINES.agc | 1067 | IMU 通电、锁定、对准模式控制 |
| **IMU/传感器** | IMU_COMPENSATION_PACKAGE.agc | 417 | IMU PIPA 与陀螺漂移补偿 |
| **IMU/传感器** | IMU_PERFORMANCE_TEST_2.agc | 421 | 性能测试 IMU 定位程序 |
| **IMU/传感器** | IMU_PERFORMANCE_TESTS_4.agc | 362 | IMU 陀螺漂移测试滤波器 |
| **IMU/传感器** | P51-P53.agc | 2341 | IMU 对准程序（首选、名义、REFSMMAT） |
| **IMU/传感器** | AOTMARK.agc | 695 | AOT（对准光学望远镜）星标 |
| **IMU/传感器** | RADAR_LEADIN_ROUTINES.agc | 103 | 雷达接口引导程序 |
| **IMU/传感器** | LEM_GEOMETRY.agc | 206 | LM 飞行器几何定义 |
| **IMU/传感器** | S-BAND_ANTENNA_FOR_LM.agc | 200 | S 波段可控天线指向（R05） |
| **解释器/数学运算** | INTERPRETER.agc | 3075 | 解释语言分派与操作 |
| **解释器/数学运算** | INTERPRETIVE_CONSTANT.agc | 81 | 解释器常量池 |
| **解释器/数学运算** | SINGLE_PRECISION_SUBROUTINES.agc | 69 | 单精度算术子程序 |
| **解释器/数学运算** | FIXED_FIXED_CONSTANT_POOL.agc | 264 | 固定-固定内存常量定义 |
| **解释器/数学运算** | RTB_OP_CODES.agc | 236 | 返回基本模式的解释器操作码 |
| **系统基础设施** | INTER-BANK_COMMUNICATION.agc | 177 | 库间子程序调用机制 |
| **系统基础设施** | INTERRUPT_LEAD_INS.agc | 117 | 中断向量引导分派表 |
| **系统基础设施** | T4RUPT_PROGRAM.agc | 1354 | T4 中断：DSKY、导航、RCS 监控 |
| **系统基础设施** | DOWN_TELEMETRY_PROGRAM.agc | 455 | 下行遥测格式化与传输 |
| **系统基础设施** | DOWNLINK_LISTS.agc | 430 | 遥测下行链路列表定义 |
| **系统基础设施** | UPDATE_PROGRAM.agc | 556 | 上行链路状态矢量更新程序（P27） |
| **系统基础设施** | AGC_BLOCK_TWO_SELF_CHECK.agc | 513 | 计算机自检与存储库校验和显示 |
| **系统基础设施** | SYSTEM_TEST_STANDARD_LEAD_INS.agc | 125 | 系统测试入口点 |
| **任务专用** | AGS_INITIALIZATION.agc | 228 | 中止制导系统初始化（R47）——仅限 LM |
| **配置/数据** | ASSEMBLY_AND_OPERATION_INFORMATION.agc | 1069 | 程序标识、构建信息、GSOP 参考 |
| **配置/数据** | CONTROLLED_CONSTANTS.agc | 558 | DPS/APS 发动机参数与可调常量 |
| **配置/数据** | ERASABLE_ASSIGNMENTS.agc | 2635 | 可擦除内存变量分配 |
| **配置/数据** | FLAGWORD_ASSIGNMENTS.agc | 1269 | 系统标志位定义 |
| **配置/数据** | INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc | 223 | I/O 通道位域文档 |
| **配置/数据** | TAGS_FOR_RELATIVE_SETLOC.agc | 347 | 相对寻址的内存库标签 |
| **配置/数据** | MAIN.agc | 91 | 主包含文件——汇编构建顺序 |

---

## Comanche055（指令舱 — CMC）

| 类别 | 文件名 | 行数 | 用途 |
|----------|----------|-------|---------|
| **执行程序/调度器** | EXECUTIVE.agc | 496 | 作业调度与基于优先级的多任务执行程序 |
| **执行程序/调度器** | WAITLIST.agc | 556 | 基于定时器的任务调度（等待列表，T3RUPT） |
| **执行程序/调度器** | PHASE_TABLE_MAINTENANCE.agc | 416 | 阶段表更新与 DSKY 程序编号显示 |
| **重启/故障处理** | FRESH_START_AND_RESTART.agc | 1480 | 冷启动初始化与重启恢复 |
| **重启/故障处理** | RESTART_TABLES.agc | 549 | 作业/等待列表/长调用重启恢复表 |
| **重启/故障处理** | RESTARTS_ROUTINE.agc | 337 | 重启处理逻辑 |
| **重启/故障处理** | ALARM_AND_ABORT.agc | 230 | 非中止警报显示与中止处理 |
| **制导/导航** | P20-P25.agc | 3529 | 交会导航、跟踪（六分仪）与状态矢量 |
| **制导/导航** | P30-P37.agc | 611 | 外部增量速度、返回地球、中止程序 |
| **制导/导航** | P32-P33_P72-P73.agc | 1415 | 共面轨道序列启动（CSI/CDH）程序 |
| **制导/导航** | P34-35_P74-75.agc | 1739 | 转移段启动（TPI/TPF）程序 |
| **制导/导航** | P37_P70.agc | 1950 | 返回地球（P37）与中止（P70）程序 |
| **制导/导航** | P11.agc | 928 | 地球轨道插入监控 |
| **制导/导航** | TPI_SEARCH.agc | 552 | 最小增量速度 TPI 搜索（S17.1/S17.2） |
| **制导/导航** | GROUND_TRACKING_DETERMINATION_PROGRAM.agc | 205 | 无通信时的地面轨迹显示（P21） |
| **制导/导航** | R30.agc | 485 | 轨道参数计算与显示（V82） |
| **制导/导航** | R31.agc | 290 | 交会参数显示 |
| **制导/导航** | STABLE_ORBIT.agc | 422 | 稳定轨道交会程序（P38/P78） |
| **制导/导航** | P76.agc | 162 | 另一飞行器状态矢量更新的目标增量速度程序 |
| **制导/导航** | INTEGRATION_INITIALIZATION.agc | 1174 | 轨道积分初始化与状态矢量设置 |
| **制导/导航** | ORBITAL_INTEGRATION.agc | 944 | 数值轨道积分（Encke 方法） |
| **制导/导航** | CONIC_SUBROUTINES.agc | 1922 | 圆锥轨迹解算子程序 |
| **制导/导航** | MEASUREMENT_INCORPORATION.agc | 496 | 通过统计加权进行状态矢量修正（W 矩阵） |
| **制导/导航** | LATITUDE_LONGITUDE_SUBROUTINES.agc | 317 | 径向矢量到纬度/经度/高度的转换 |
| **制导/导航** | PLANETARY_INERTIAL_ORIENTATION.agc | 386 | 行星坐标系到惯性坐标系变换（RP-TO-R） |
| **制导/导航** | LUNAR_AND_SOLAR_EPHEMERIDES_SUBROUTINES.agc | 198 | 太阳和月球位置/速度计算 |
| **制导/导航** | TIME_OF_FREE_FALL.agc | 683 | 圆锥轨迹的飞行时间子程序 |
| **制导/导航** | POWERED_FLIGHT_SUBROUTINES.agc | 371 | 动力飞行计算支持程序 |
| **制导/导航** | INFLIGHT_ALIGNMENT_ROUTINES.agc | 304 | 飞行中 IMU 对准数学运算 |
| **制导/导航** | ENTRY_LEXICON.agc | 299 | 进入变量定义与换算——仅限 CM |
| **制导/导航** | REENTRY_CONTROL.agc | 1609 | 进入制导与控制律——仅限 CM |
| **推进/推力控制** | P40-P47.agc | 2429 | SPS 推力程序，TVC DAP 启动 |
| **推进/推力控制** | SERVICER207.agc | 824 | CM 的平均-G、读加速度计、SERVICER |
| **自动驾驶/姿态控制** | RCS-CSM_DIGITAL_AUTOPILOT.agc | 975 | CSM RCS 数字自动驾驶（T5 中断） |
| **自动驾驶/姿态控制** | RCS-CSM_DAP_EXECUTIVE_PROGRAMS.agc | 85 | AMGB/AMBG 矩阵计算（1 Hz） |
| **自动驾驶/姿态控制** | JET_SELECTION_LOGIC.agc | 920 | CSM RCS 喷气选择算法 |
| **自动驾驶/姿态控制** | CM_ENTRY_DIGITAL_AUTOPILOT.agc | 1273 | CM 大气再入的进入 DAP |
| **自动驾驶/姿态控制** | AUTOMATIC_MANEUVERS.agc | 504 | 自动姿态机动执行 |
| **自动驾驶/姿态控制** | KALCMANU_STEERING.agc | 265 | KALCMANU 转向指令生成 |
| **自动驾驶/姿态控制** | GIMBAL_LOCK_AVOIDANCE.agc | 98 | 万向节锁死检测与规避 |
| **自动驾驶/姿态控制** | R60_62.agc | 385 | 通用姿态机动子程序（R60/R62） |
| **自动驾驶/姿态控制** | ANGLFIND.agc | 626 | 由期望姿态计算万向节角 |
| **自动驾驶/姿态控制** | CM_BODY_ATTITUDE.agc | 301 | CM 本体姿态计算 |
| **自动驾驶/姿态控制** | TVCDAPS.agc | 784 | SPS 发动机万向节的 TVC 俯仰/偏航 DAP |
| **自动驾驶/姿态控制** | TVCEXECUTIVE.agc | 276 | TVC 执行程序：增益、重心修正、指针更新 |
| **自动驾驶/姿态控制** | TVCINITIALIZE.agc | 414 | TVC DAP 初始化与系数加载 |
| **自动驾驶/姿态控制** | TVCMASSPROP.agc | 245 | TVC 质量特性计算 |
| **自动驾驶/姿态控制** | TVCRESTARTS.agc | 256 | TVC 重启恢复 |
| **自动驾驶/姿态控制** | TVCROLLDAP.agc | 619 | TVC 滚转自动驾驶 |
| **自动驾驶/姿态控制** | TVCSTROKETEST.agc | 260 | TVC 弯曲模态行程测试 |
| **自动驾驶/姿态控制** | MYSUBS.agc | 93 | 杂项 DAP 子程序 |
| **DSKY/显示** | PINBALL_GAME_BUTTONS_AND_LIGHTS.agc | 3809 | 键盘与显示系统（DSKY）主程序 |
| **DSKY/显示** | PINBALL_NOUN_TABLES.agc | 861 | DSKY 名词定义表 |
| **DSKY/显示** | DISPLAY_INTERFACE_ROUTINES.agc | 1476 | 优先级/普通/扩展动词显示管理 |
| **DSKY/显示** | EXTENDED_VERBS.agc | 1315 | 扩展动词指令处理 |
| **DSKY/显示** | KEYRUPT_UPRUPT.agc | 136 | 键盘与上行链路中断处理程序 |
| **DSKY/显示** | SERVICE_ROUTINES.agc | 279 | 显示与警报服务程序 |
| **IMU/传感器** | IMU_MODE_SWITCHING_ROUTINES.agc | 1066 | IMU 通电、锁定、对准模式控制 |
| **IMU/传感器** | IMU_COMPENSATION_PACKAGE.agc | 368 | IMU PIPA 与陀螺漂移补偿 |
| **IMU/传感器** | IMU_CALIBRATION_AND_ALIGNMENT.agc | 1406 | IMU 性能测试与校准——仅限 CM |
| **IMU/传感器** | P51-P53.agc | 2213 | IMU 对准程序（首选、名义、REFSMMAT） |
| **IMU/传感器** | SXTMARK.agc | 659 | 六分仪/SCT 星标——仅限 CM |
| **IMU/传感器** | CSM_GEOMETRY.agc | 415 | CSM 飞行器几何定义 |
| **IMU/传感器** | S-BAND_ANTENNA_FOR_CM.agc | 128 | CM 的 S 波段天线指向 |
| **IMU/传感器** | STAR_TABLES.agc | 193 | 星表数据——仅限 CM |
| **IMU/传感器** | LUNAR_LANDMARK_SELECTION_FOR_CM.agc | 35 | 月球地标数据占位符——仅限 CM |
| **解释器/数学运算** | INTERPRETER.agc | 3063 | 解释语言分派与操作 |
| **解释器/数学运算** | INTERPRETIVE_CONSTANTS.agc | 82 | 解释器常量池 |
| **解释器/数学运算** | SINGLE_PRECISION_SUBROUTINES.agc | 67 | 单精度算术子程序 |
| **解释器/数学运算** | FIXED_FIXED_CONSTANT_POOL.agc | 263 | 固定-固定内存常量定义 |
| **解释器/数学运算** | RT8_OP_CODES.agc | 358 | 返回基本模式的解释器操作码 |
| **系统基础设施** | INTER-BANK_COMMUNICATION.agc | 183 | 库间子程序调用机制 |
| **系统基础设施** | INTERRUPT_LEAD_INS.agc | 122 | 中断向量引导分派表 |
| **系统基础设施** | T4RUPT_PROGRAM.agc | 1467 | T4 中断：DSKY、光学系统、DAP 监控 |
| **系统基础设施** | DOWN-TELEMETRY_PROGRAM.agc | 441 | 下行遥测格式化与传输 |
| **系统基础设施** | DOWNLINK_LISTS.agc | 411 | 遥测下行链路列表定义 |
| **系统基础设施** | UPDATE_PROGRAM.agc | 555 | 上行链路状态矢量更新程序（P27） |
| **系统基础设施** | AGC_BLOCK_TWO_SELF-CHECK.agc | 513 | 计算机自检与存储库校验和显示 |
| **系统基础设施** | SYSTEM_TEST_STANDARD_LEAD_INS.agc | 150 | 系统测试入口点 |
| **任务专用** | P61-P67.agc | 1225 | 进入程序（P61-P67）——仅限 CM |
| **配置/数据** | CONTRACT_AND_APPROVALS.agc | 73 | 合同标识与批准——仅限 CM |
| **配置/数据** | ASSEMBLY_AND_OPERATION_INFORMATION.agc | 1010 | 程序标识、构建信息、GSOP 参考 |
| **配置/数据** | ERASABLE_ASSIGNMENTS.agc | 3785 | 可擦除内存变量分配 |
| **配置/数据** | TAGS_FOR_RELATIVE_SETLOC.agc | 435 | 相对寻址的内存库标签 |
| **配置/数据** | MAIN.agc | 99 | 主包含文件——汇编构建顺序 |

---

## 共有文件与专有文件

### 两个模块共有的文件（共享基础设施）

以下文件同时存在于 Luminary099 和 Comanche055 中，实现相同的核心 AGC 功能，并针对各模块进行了调整：

| 文件名 | Luminary099 行数 | Comanche055 行数 |
|----------|-------------------|-------------------|
| AGC_BLOCK_TWO_SELF_CHECK / SELF-CHECK | 513 | 513 |
| ALARM_AND_ABORT.agc | 251 | 230 |
| ASSEMBLY_AND_OPERATION_INFORMATION.agc | 1069 | 1010 |
| CONIC_SUBROUTINES.agc | 1864 | 1922 |
| DISPLAY_INTERFACE_ROUTINES.agc | 1459 | 1476 |
| DOWNLINK_LISTS.agc | 430 | 411 |
| DOWN_TELEMETRY_PROGRAM.agc | 455 | 441 |
| ERASABLE_ASSIGNMENTS.agc | 2635 | 3785 |
| EXECUTIVE.agc | 503 | 496 |
| EXTENDED_VERBS.agc | 1681 | 1315 |
| FIXED_FIXED_CONSTANT_POOL.agc | 264 | 263 |
| FRESH_START_AND_RESTART.agc | 1242 | 1480 |
| GIMBAL_LOCK_AVOIDANCE.agc | 76 | 98 |
| GROUND_TRACKING_DETERMINATION_PROGRAM.agc | 208 | 205 |
| IMU_COMPENSATION_PACKAGE.agc | 417 | 368 |
| IMU_MODE_SWITCHING_ROUTINES.agc | 1067 | 1066 |
| INFLIGHT_ALIGNMENT_ROUTINES.agc | 300 | 304 |
| INTEGRATION_INITIALIZATION.agc | 1102 | 1174 |
| INTER-BANK_COMMUNICATION.agc | 177 | 183 |
| INTERPRETER.agc | 3075 | 3063 |
| INTERPRETIVE_CONSTANT(S).agc | 81 | 82 |
| INTERRUPT_LEAD_INS.agc | 117 | 122 |
| KALCMANU_STEERING.agc | 221 | 265 |
| KEYRUPT_UPRUPT.agc | 130 | 136 |
| LATITUDE_LONGITUDE_SUBROUTINES.agc | 306 | 317 |
| LUNAR_AND_SOLAR_EPHEMERIDES_SUBROUTINES.agc | 183 | 198 |
| MAIN.agc | 91 | 99 |
| MEASUREMENT_INCORPORATION.agc | 495 | 496 |
| ORBITAL_INTEGRATION.agc | 977 | 944 |
| P20-P25.agc | 5182 | 3529 |
| P34-35_P74-75.agc | 1764 | 1739 |
| P40-P47.agc | 1471 | 2429 |
| P51-P53.agc | 2341 | 2213 |
| P76.agc | 161 | 162 |
| PHASE_TABLE_MAINTENANCE.agc | 411 | 416 |
| PINBALL_GAME_BUTTONS_AND_LIGHTS.agc | 3798 | 3809 |
| PINBALL_NOUN_TABLES.agc | 906 | 861 |
| PLANETARY_INERTIAL_ORIENTATION.agc | 385 | 386 |
| POWERED_FLIGHT_SUBROUTINES.agc | 447 | 371 |
| R30.agc | 464 | 485 |
| R31.agc | 266 | 290 |
| R60_62.agc | 577 | 385 |
| RESTART_TABLES.agc | 293 | 549 |
| RESTARTS_ROUTINE.agc | 323 | 337 |
| RTB_OP_CODES / RT8_OP_CODES.agc | 236 | 358 |
| SERVICE_ROUTINES.agc | 221 | 279 |
| SINGLE_PRECISION_SUBROUTINES.agc | 69 | 67 |
| STABLE_ORBIT.agc | 436 | 422 |
| SYSTEM_TEST_STANDARD_LEAD_INS.agc | 125 | 150 |
| T4RUPT_PROGRAM.agc | 1354 | 1467 |
| TAGS_FOR_RELATIVE_SETLOC.agc | 347 | 435 |
| TIME_OF_FREE_FALL.agc | 721 | 683 |
| UPDATE_PROGRAM.agc | 556 | 555 |
| WAITLIST.agc | 564 | 556 |

### Luminary099（登月舱）专有文件

| 文件名 | 行数 | 仅限 LM 的原因 |
|----------|-------|-------------|
| AGS_INITIALIZATION.agc | 228 | 中止制导系统仅存在于 LM |
| AOSTASK_AND_AOSJOB.agc | 1069 | LM 配置的 1/ACCS 制导-DAP 接口 |
| AOTMARK.agc | 695 | 对准光学望远镜（LM 专用仪器） |
| ASCENT_GUIDANCE.agc | 647 | 月面上升——LM 任务阶段 |
| ATTITUDE_MANEUVER_ROUTINE.agc | 1027 | LM 自由飞行机动的 KALCMANU |
| BURN_BABY_BURN--MASTER_IGNITION_ROUTINE.agc | 1059 | DPS/APS 发动机主点火 |
| CONTROLLED_CONSTANTS.agc | 558 | DPS/APS 发动机参数 |
| DAP_INTERFACE_SUBROUTINES.agc | 176 | LM DAP 接口实用程序 |
| DAPIDLER_PROGRAM.agc | 494 | LM DAP 空转/初始化 |
| FINDCDUW--GUIDAP_INTERFACE.agc | 743 | 制导到 DAP 推力方向接口 |
| FLAGWORD_ASSIGNMENTS.agc | 1269 | LM 专用标志定义 |
| GENERAL_LAMBERT_AIMPOINT_GUIDANCE.agc | 168 | LM 的 Lambert 制导（P31） |
| IMU_PERFORMANCE_TEST_2.agc | 421 | LM IMU 测试程序 |
| IMU_PERFORMANCE_TESTS_4.agc | 362 | LM 陀螺漂移滤波器 |
| INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc | 223 | LM 专用 I/O 通道文档 |
| KALMAN_FILTER.agc | 101 | LM DAP 卡尔曼滤波器 |
| LANDING_ANALOG_DISPLAYS.agc | 533 | 着陆阶段模拟显示 |
| LEM_GEOMETRY.agc | 206 | LM 飞行器几何 |
| LUNAR_LANDING_GUIDANCE_EQUATIONS.agc | 1474 | 动力下降制导 |
| P-AXIS_RCS_AUTOPILOT.agc | 1056 | LM P 轴 RCS 自动驾驶 |
| P12.agc | 243 | 动力上升程序 |
| P30_P37.agc | 185 | LM 专用 P30/P37 变体 |
| P32-P35_P72-P75.agc | 1394 | LM CSI/CDH 交会程序 |
| P70-P71.agc | 439 | 中止程序（仅限 LM） |
| Q_R-AXIS_RCS_AUTOPILOT.agc | 860 | LM Q/R 轴 RCS 自动驾驶 |
| R63.agc | 156 | LM 轴指向 CSM（V89） |
| RADAR_LEADIN_ROUTINES.agc | 103 | LM 雷达接口 |
| RCS_FAILURE_MONITOR.agc | 173 | LM RCS 阀故障监控 |
| S-BAND_ANTENNA_FOR_LM.agc | 200 | LM 可控 S 波段天线 |
| SERVICER.agc | 1715 | LM 专用 SERVICER/平均-G |
| SPS_BACK-UP_RCS_CONTROL.agc | 196 | 对接状态下的 RCS 备份控制 |
| T6-RUPT_PROGRAMS.agc | 163 | LM 喷气计时的 T6 中断 |
| THE_LUNAR_LANDING.agc | 335 | 着陆排序 |
| THROTTLE_CONTROL_ROUTINES.agc | 224 | DPS 油门控制 |
| TJET_LAW.agc | 519 | LM 喷气点火时间律 |
| TRIM_GIMBAL_CONTROL_SYSTEM.agc | 617 | DPS 万向节配平 |

### Comanche055（指令舱）专有文件

| 文件名 | 行数 | 仅限 CM 的原因 |
|----------|-------|-------------|
| ANGLFIND.agc | 626 | CM 万向节角计算 |
| AUTOMATIC_MANEUVERS.agc | 504 | CM 自动机动执行 |
| CM_BODY_ATTITUDE.agc | 301 | CM 本体姿态计算 |
| CM_ENTRY_DIGITAL_AUTOPILOT.agc | 1273 | 大气再入 DAP |
| CONTRACT_AND_APPROVALS.agc | 73 | CM 程序合同页 |
| CSM_GEOMETRY.agc | 415 | CSM 飞行器几何 |
| ENTRY_LEXICON.agc | 299 | 进入变量定义/换算 |
| IMU_CALIBRATION_AND_ALIGNMENT.agc | 1406 | CM IMU 校准与对准测试 |
| JET_SELECTION_LOGIC.agc | 920 | CSM RCS 喷气选择 |
| LUNAR_LANDMARK_SELECTION_FOR_CM.agc | 35 | CM 月球地标数据 |
| MYSUBS.agc | 93 | CM DAP 杂项子程序 |
| P11.agc | 928 | 地球轨道插入监控 |
| P30-P37.agc | 611 | CM 专用 P30-P37 变体 |
| P32-P33_P72-P73.agc | 1415 | CM CSI/CDH 交会程序 |
| P37_P70.agc | 1950 | 返回地球与 CM 中止 |
| P61-P67.agc | 1225 | 进入程序（P61-P67） |
| RCS-CSM_DAP_EXECUTIVE_PROGRAMS.agc | 85 | CSM DAP 执行程序（AMGB/AMBG） |
| RCS-CSM_DIGITAL_AUTOPILOT.agc | 975 | CSM RCS 数字自动驾驶 |
| REENTRY_CONTROL.agc | 1609 | 进入制导控制律 |
| S-BAND_ANTENNA_FOR_CM.agc | 128 | CM S 波段天线 |
| SERVICER207.agc | 824 | CM 专用 SERVICER |
| STAR_TABLES.agc | 193 | SXT 导航星表 |
| SXTMARK.agc | 659 | 六分仪/SCT 标记程序 |
| TPI_SEARCH.agc | 552 | 最小增量速度 TPI 搜索 |
| TVCDAPS.agc | 784 | TVC 俯仰/偏航 DAP |
| TVCEXECUTIVE.agc | 276 | TVC 执行程序任务 |
| TVCINITIALIZE.agc | 414 | TVC 初始化 |
| TVCMASSPROP.agc | 245 | TVC 质量特性 |
| TVCRESTARTS.agc | 256 | TVC 重启处理 |
| TVCROLLDAP.agc | 619 | TVC 滚转自动驾驶 |
| TVCSTROKETEST.agc | 260 | TVC 弯曲行程测试 |
