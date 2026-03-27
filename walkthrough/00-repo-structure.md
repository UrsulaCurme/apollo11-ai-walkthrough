# Apollo 11 AGC Source Code Module Comparison

## Luminary099 (Lunar Module — LGC)

| Category | Filename | Lines | Purpose |
|----------|----------|-------|---------|
| **Executive/Scheduler** | EXECUTIVE.agc | 503 | Job scheduling and priority-based multitasking executive |
| **Executive/Scheduler** | WAITLIST.agc | 564 | Timer-based task scheduling (waitlist, T3RUPT) |
| **Executive/Scheduler** | PHASE_TABLE_MAINTENANCE.agc | 411 | Phase table updates and DSKY program number display |
| **Restart/Fault Handling** | FRESH_START_AND_RESTART.agc | 1242 | Cold start initialization and restart recovery |
| **Restart/Fault Handling** | RESTART_TABLES.agc | 293 | Job/waitlist/longcall restart recovery tables |
| **Restart/Fault Handling** | RESTARTS_ROUTINE.agc | 323 | Restart processing logic |
| **Restart/Fault Handling** | ALARM_AND_ABORT.agc | 251 | Non-abortive alarm display and abort handling |
| **Guidance/Navigation** | LUNAR_LANDING_GUIDANCE_EQUATIONS.agc | 1474 | Powered descent guidance equations for lunar landing |
| **Guidance/Navigation** | ASCENT_GUIDANCE.agc | 647 | Lunar ascent guidance targeting |
| **Guidance/Navigation** | THE_LUNAR_LANDING.agc | 335 | Lunar landing sequencing (P63/P64/P66) |
| **Guidance/Navigation** | P20-P25.agc | 5182 | Rendezvous navigation, tracking, and state vector updates |
| **Guidance/Navigation** | P30_P37.agc | 185 | External delta-V targeting and return-to-Earth |
| **Guidance/Navigation** | P32-P35_P72-P75.agc | 1394 | Coelliptic sequence initiation (CSI/CDH) programs |
| **Guidance/Navigation** | P34-35_P74-75.agc | 1764 | Transfer phase initiation (TPI/TPF) programs |
| **Guidance/Navigation** | GENERAL_LAMBERT_AIMPOINT_GUIDANCE.agc | 168 | Lambert aimpoint targeting (P31) |
| **Guidance/Navigation** | GROUND_TRACKING_DETERMINATION_PROGRAM.agc | 208 | Ground track display without comm (P21) |
| **Guidance/Navigation** | R30.agc | 464 | Orbital parameter calculation and display (V82) |
| **Guidance/Navigation** | R31.agc | 266 | Rendezvous parameter display |
| **Guidance/Navigation** | STABLE_ORBIT.agc | 436 | Stable orbit rendezvous programs (P38/P78) |
| **Guidance/Navigation** | P70-P71.agc | 439 | Abort guidance programs (DPS/APS abort) |
| **Guidance/Navigation** | P76.agc | 161 | Target delta-V program for other vehicle state vector update |
| **Guidance/Navigation** | INTEGRATION_INITIALIZATION.agc | 1102 | Orbital integration initialization and state vector setup |
| **Guidance/Navigation** | ORBITAL_INTEGRATION.agc | 977 | Numerical orbital integration (Encke's method) |
| **Guidance/Navigation** | CONIC_SUBROUTINES.agc | 1864 | Conic trajectory solution subroutines |
| **Guidance/Navigation** | MEASUREMENT_INCORPORATION.agc | 495 | State vector deviation via statistical weighting (W-matrix) |
| **Guidance/Navigation** | LATITUDE_LONGITUDE_SUBROUTINES.agc | 306 | Radial vector to lat/long/alt conversion |
| **Guidance/Navigation** | PLANETARY_INERTIAL_ORIENTATION.agc | 385 | Planetary-to-inertial coordinate transforms (RP-TO-R) |
| **Guidance/Navigation** | LUNAR_AND_SOLAR_EPHEMERIDES_SUBROUTINES.agc | 183 | Sun and Moon position computation |
| **Guidance/Navigation** | TIME_OF_FREE_FALL.agc | 721 | Time-of-flight subroutines for conic trajectories |
| **Guidance/Navigation** | POWERED_FLIGHT_SUBROUTINES.agc | 447 | Powered flight computation support routines |
| **Guidance/Navigation** | INFLIGHT_ALIGNMENT_ROUTINES.agc | 300 | In-flight IMU alignment mathematics |
| **Propulsion/Thrust Control** | BURN_BABY_BURN--MASTER_IGNITION_ROUTINE.agc | 1059 | Master ignition sequencing for DPS/APS burns |
| **Propulsion/Thrust Control** | P40-P47.agc | 1471 | DPS/APS thrusting programs and maneuver setup |
| **Propulsion/Thrust Control** | P12.agc | 243 | Powered ascent program |
| **Propulsion/Thrust Control** | THROTTLE_CONTROL_ROUTINES.agc | 224 | DPS throttle command generation |
| **Propulsion/Thrust Control** | SERVICER.agc | 1715 | Average-G, READACCS, delta-V accumulation |
| **Propulsion/Thrust Control** | LANDING_ANALOG_DISPLAYS.agc | 533 | Landing phase analog display outputs (altitude rate, etc.) |
| **Autopilot/Attitude Control** | DAPIDLER_PROGRAM.agc | 494 | DAP initialization and idle-loop (10 Hz) |
| **Autopilot/Attitude Control** | DAP_INTERFACE_SUBROUTINES.agc | 176 | DAP interface utility routines |
| **Autopilot/Attitude Control** | P-AXIS_RCS_AUTOPILOT.agc | 1056 | P-axis (roll) RCS jet autopilot |
| **Autopilot/Attitude Control** | Q_R-AXIS_RCS_AUTOPILOT.agc | 860 | Q/R-axis (pitch/yaw) RCS jet autopilot |
| **Autopilot/Attitude Control** | TJET_LAW.agc | 519 | Jet firing time calculation (phase plane logic) |
| **Autopilot/Attitude Control** | KALMAN_FILTER.agc | 101 | DAP state estimation filter |
| **Autopilot/Attitude Control** | T6-RUPT_PROGRAMS.agc | 163 | T6 interrupt for RCS jet timing |
| **Autopilot/Attitude Control** | TRIM_GIMBAL_CONTROL_SYSTEM.agc | 617 | DPS gimbal trim control |
| **Autopilot/Attitude Control** | SPS_BACK-UP_RCS_CONTROL.agc | 196 | RCS backup control in docked configuration |
| **Autopilot/Attitude Control** | AOSTASK_AND_AOSJOB.agc | 1069 | 1/ACCS — guidance-to-DAP interface and mass properties |
| **Autopilot/Attitude Control** | RCS_FAILURE_MONITOR.agc | 173 | RCS isolation valve failure detection (T4RUPT) |
| **Autopilot/Attitude Control** | ATTITUDE_MANEUVER_ROUTINE.agc | 1027 | KALCMANU free-fall attitude maneuver generation |
| **Autopilot/Attitude Control** | KALCMANU_STEERING.agc | 221 | Steering command generation for KALCMANU |
| **Autopilot/Attitude Control** | GIMBAL_LOCK_AVOIDANCE.agc | 76 | Gimbal lock detection and avoidance |
| **Autopilot/Attitude Control** | R60_62.agc | 577 | General attitude maneuver subroutine (R60/R62) |
| **Autopilot/Attitude Control** | R63.agc | 156 | FDAI ball angles to point at CSM (V89) |
| **Autopilot/Attitude Control** | FINDCDUW--GUIDAP_INTERFACE.agc | 743 | Commanded gimbal angles and thrust direction filter |
| **DSKY/Display** | PINBALL_GAME_BUTTONS_AND_LIGHTS.agc | 3798 | Keyboard and display system (DSKY) main program |
| **DSKY/Display** | PINBALL_NOUN_TABLES.agc | 906 | Noun definition tables for DSKY |
| **DSKY/Display** | DISPLAY_INTERFACE_ROUTINES.agc | 1459 | Priority/normal/extended verb display management |
| **DSKY/Display** | EXTENDED_VERBS.agc | 1681 | Extended verb command processing |
| **DSKY/Display** | KEYRUPT_UPRUPT.agc | 130 | Keyboard and uplink interrupt handlers |
| **DSKY/Display** | SERVICE_ROUTINES.agc | 221 | Display and alarm service routines |
| **IMU/Sensors** | IMU_MODE_SWITCHING_ROUTINES.agc | 1067 | IMU power-up, cage, align mode control |
| **IMU/Sensors** | IMU_COMPENSATION_PACKAGE.agc | 417 | IMU PIPA and gyro drift compensation |
| **IMU/Sensors** | IMU_PERFORMANCE_TEST_2.agc | 421 | IMU positioning routines for performance tests |
| **IMU/Sensors** | IMU_PERFORMANCE_TESTS_4.agc | 362 | IMU gyro drift test filter |
| **IMU/Sensors** | P51-P53.agc | 2341 | IMU alignment programs (preferred, nominal, REFSMMAT) |
| **IMU/Sensors** | AOTMARK.agc | 695 | AOT (Alignment Optical Telescope) star marking |
| **IMU/Sensors** | RADAR_LEADIN_ROUTINES.agc | 103 | Radar interface lead-in routines |
| **IMU/Sensors** | LEM_GEOMETRY.agc | 206 | LM vehicle geometry definitions |
| **IMU/Sensors** | S-BAND_ANTENNA_FOR_LM.agc | 200 | S-band steerable antenna pointing (R05) |
| **Interpreter/Math** | INTERPRETER.agc | 3075 | Interpretive language dispatcher and operations |
| **Interpreter/Math** | INTERPRETIVE_CONSTANT.agc | 81 | Interpreter constant pool |
| **Interpreter/Math** | SINGLE_PRECISION_SUBROUTINES.agc | 69 | Single-precision arithmetic subroutines |
| **Interpreter/Math** | FIXED_FIXED_CONSTANT_POOL.agc | 264 | Fixed-fixed memory constant definitions |
| **Interpreter/Math** | RTB_OP_CODES.agc | 236 | Return-to-basic interpreter op codes |
| **System Infrastructure** | INTER-BANK_COMMUNICATION.agc | 177 | Bank-to-bank subroutine call mechanism |
| **System Infrastructure** | INTERRUPT_LEAD_INS.agc | 117 | Interrupt vector lead-in dispatch table |
| **System Infrastructure** | T4RUPT_PROGRAM.agc | 1354 | T4 interrupt: DSKY, navigation, RCS monitoring |
| **System Infrastructure** | DOWN_TELEMETRY_PROGRAM.agc | 455 | Downlink telemetry formatting and transmission |
| **System Infrastructure** | DOWNLINK_LISTS.agc | 430 | Telemetry downlink list definitions |
| **System Infrastructure** | UPDATE_PROGRAM.agc | 556 | Uplink state vector update program (P27) |
| **System Infrastructure** | AGC_BLOCK_TWO_SELF_CHECK.agc | 513 | Computer self-test and bank checksum display |
| **System Infrastructure** | SYSTEM_TEST_STANDARD_LEAD_INS.agc | 125 | System test entry points |
| **Mission-Specific** | AGS_INITIALIZATION.agc | 228 | Abort Guidance System initialization (R47) — LM only |
| **Configuration/Data** | ASSEMBLY_AND_OPERATION_INFORMATION.agc | 1069 | Program identification, build info, GSOP reference |
| **Configuration/Data** | CONTROLLED_CONSTANTS.agc | 558 | DPS/APS engine parameters and tunable constants |
| **Configuration/Data** | ERASABLE_ASSIGNMENTS.agc | 2635 | Erasable memory variable allocation |
| **Configuration/Data** | FLAGWORD_ASSIGNMENTS.agc | 1269 | System flag bit definitions |
| **Configuration/Data** | INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc | 223 | I/O channel bit field documentation |
| **Configuration/Data** | TAGS_FOR_RELATIVE_SETLOC.agc | 347 | Memory bank tags for relative addressing |
| **Configuration/Data** | MAIN.agc | 91 | Master include file — assembly build order |

---

## Comanche055 (Command Module — CMC)

| Category | Filename | Lines | Purpose |
|----------|----------|-------|---------|
| **Executive/Scheduler** | EXECUTIVE.agc | 496 | Job scheduling and priority-based multitasking executive |
| **Executive/Scheduler** | WAITLIST.agc | 556 | Timer-based task scheduling (waitlist, T3RUPT) |
| **Executive/Scheduler** | PHASE_TABLE_MAINTENANCE.agc | 416 | Phase table updates and DSKY program number display |
| **Restart/Fault Handling** | FRESH_START_AND_RESTART.agc | 1480 | Cold start initialization and restart recovery |
| **Restart/Fault Handling** | RESTART_TABLES.agc | 549 | Job/waitlist/longcall restart recovery tables |
| **Restart/Fault Handling** | RESTARTS_ROUTINE.agc | 337 | Restart processing logic |
| **Restart/Fault Handling** | ALARM_AND_ABORT.agc | 230 | Non-abortive alarm display and abort handling |
| **Guidance/Navigation** | P20-P25.agc | 3529 | Rendezvous navigation, tracking (SXT-based), state vectors |
| **Guidance/Navigation** | P30-P37.agc | 611 | External delta-V, return-to-Earth, abort programs |
| **Guidance/Navigation** | P32-P33_P72-P73.agc | 1415 | Coelliptic sequence initiation (CSI/CDH) programs |
| **Guidance/Navigation** | P34-35_P74-75.agc | 1739 | Transfer phase initiation (TPI/TPF) programs |
| **Guidance/Navigation** | P37_P70.agc | 1950 | Return-to-Earth (P37) and abort (P70) programs |
| **Guidance/Navigation** | P11.agc | 928 | Earth orbit insertion monitor |
| **Guidance/Navigation** | TPI_SEARCH.agc | 552 | Minimum delta-V TPI search (S17.1/S17.2) |
| **Guidance/Navigation** | GROUND_TRACKING_DETERMINATION_PROGRAM.agc | 205 | Ground track display without comm (P21) |
| **Guidance/Navigation** | R30.agc | 485 | Orbital parameter calculation and display (V82) |
| **Guidance/Navigation** | R31.agc | 290 | Rendezvous parameter display |
| **Guidance/Navigation** | STABLE_ORBIT.agc | 422 | Stable orbit rendezvous programs (P38/P78) |
| **Guidance/Navigation** | P76.agc | 162 | Target delta-V program for other vehicle state vector update |
| **Guidance/Navigation** | INTEGRATION_INITIALIZATION.agc | 1174 | Orbital integration initialization and state vector setup |
| **Guidance/Navigation** | ORBITAL_INTEGRATION.agc | 944 | Numerical orbital integration (Encke's method) |
| **Guidance/Navigation** | CONIC_SUBROUTINES.agc | 1922 | Conic trajectory solution subroutines |
| **Guidance/Navigation** | MEASUREMENT_INCORPORATION.agc | 496 | State vector deviation via statistical weighting (W-matrix) |
| **Guidance/Navigation** | LATITUDE_LONGITUDE_SUBROUTINES.agc | 317 | Radial vector to lat/long/alt conversion |
| **Guidance/Navigation** | PLANETARY_INERTIAL_ORIENTATION.agc | 386 | Planetary-to-inertial coordinate transforms (RP-TO-R) |
| **Guidance/Navigation** | LUNAR_AND_SOLAR_EPHEMERIDES_SUBROUTINES.agc | 198 | Sun and Moon position/velocity computation |
| **Guidance/Navigation** | TIME_OF_FREE_FALL.agc | 683 | Time-of-flight subroutines for conic trajectories |
| **Guidance/Navigation** | POWERED_FLIGHT_SUBROUTINES.agc | 371 | Powered flight computation support routines |
| **Guidance/Navigation** | INFLIGHT_ALIGNMENT_ROUTINES.agc | 304 | In-flight IMU alignment mathematics |
| **Guidance/Navigation** | ENTRY_LEXICON.agc | 299 | Entry variable definitions and scaling — CM only |
| **Guidance/Navigation** | REENTRY_CONTROL.agc | 1609 | Entry guidance and control laws — CM only |
| **Propulsion/Thrust Control** | P40-P47.agc | 2429 | SPS thrusting programs, TVC DAP startup |
| **Propulsion/Thrust Control** | SERVICER207.agc | 824 | Average-G, READACCS, SERVICER for CM |
| **Autopilot/Attitude Control** | RCS-CSM_DIGITAL_AUTOPILOT.agc | 975 | CSM RCS digital autopilot (T5 interrupt) |
| **Autopilot/Attitude Control** | RCS-CSM_DAP_EXECUTIVE_PROGRAMS.agc | 85 | AMGB/AMBG matrix calculation (1 Hz) |
| **Autopilot/Attitude Control** | JET_SELECTION_LOGIC.agc | 920 | CSM RCS jet selection algorithms |
| **Autopilot/Attitude Control** | CM_ENTRY_DIGITAL_AUTOPILOT.agc | 1273 | Entry DAP for CM atmospheric reentry |
| **Autopilot/Attitude Control** | AUTOMATIC_MANEUVERS.agc | 504 | Automatic attitude maneuver execution |
| **Autopilot/Attitude Control** | KALCMANU_STEERING.agc | 265 | Steering command generation for KALCMANU |
| **Autopilot/Attitude Control** | GIMBAL_LOCK_AVOIDANCE.agc | 98 | Gimbal lock detection and avoidance |
| **Autopilot/Attitude Control** | R60_62.agc | 385 | General attitude maneuver subroutine (R60/R62) |
| **Autopilot/Attitude Control** | ANGLFIND.agc | 626 | Gimbal angle computation from desired attitude |
| **Autopilot/Attitude Control** | CM_BODY_ATTITUDE.agc | 301 | CM body attitude computation |
| **Autopilot/Attitude Control** | TVCDAPS.agc | 784 | TVC pitch/yaw DAP for SPS engine gimbaling |
| **Autopilot/Attitude Control** | TVCEXECUTIVE.agc | 276 | TVC executive: gains, CG correction, needle updates |
| **Autopilot/Attitude Control** | TVCINITIALIZE.agc | 414 | TVC DAP initialization and coefficient loading |
| **Autopilot/Attitude Control** | TVCMASSPROP.agc | 245 | TVC mass properties computation |
| **Autopilot/Attitude Control** | TVCRESTARTS.agc | 256 | TVC restart recovery |
| **Autopilot/Attitude Control** | TVCROLLDAP.agc | 619 | TVC roll autopilot |
| **Autopilot/Attitude Control** | TVCSTROKETEST.agc | 260 | TVC bending mode stroke test |
| **Autopilot/Attitude Control** | MYSUBS.agc | 93 | Miscellaneous DAP subroutines |
| **DSKY/Display** | PINBALL_GAME_BUTTONS_AND_LIGHTS.agc | 3809 | Keyboard and display system (DSKY) main program |
| **DSKY/Display** | PINBALL_NOUN_TABLES.agc | 861 | Noun definition tables for DSKY |
| **DSKY/Display** | DISPLAY_INTERFACE_ROUTINES.agc | 1476 | Priority/normal/extended verb display management |
| **DSKY/Display** | EXTENDED_VERBS.agc | 1315 | Extended verb command processing |
| **DSKY/Display** | KEYRUPT_UPRUPT.agc | 136 | Keyboard and uplink interrupt handlers |
| **DSKY/Display** | SERVICE_ROUTINES.agc | 279 | Display and alarm service routines |
| **IMU/Sensors** | IMU_MODE_SWITCHING_ROUTINES.agc | 1066 | IMU power-up, cage, align mode control |
| **IMU/Sensors** | IMU_COMPENSATION_PACKAGE.agc | 368 | IMU PIPA and gyro drift compensation |
| **IMU/Sensors** | IMU_CALIBRATION_AND_ALIGNMENT.agc | 1406 | IMU performance tests and calibration — CM only |
| **IMU/Sensors** | P51-P53.agc | 2213 | IMU alignment programs (preferred, nominal, REFSMMAT) |
| **IMU/Sensors** | SXTMARK.agc | 659 | Sextant/SCT star marking — CM only |
| **IMU/Sensors** | CSM_GEOMETRY.agc | 415 | CSM vehicle geometry definitions |
| **IMU/Sensors** | S-BAND_ANTENNA_FOR_CM.agc | 128 | S-band antenna pointing for CM |
| **IMU/Sensors** | STAR_TABLES.agc | 193 | Star catalog data tables — CM only |
| **IMU/Sensors** | LUNAR_LANDMARK_SELECTION_FOR_CM.agc | 35 | Lunar landmark data placeholder — CM only |
| **Interpreter/Math** | INTERPRETER.agc | 3063 | Interpretive language dispatcher and operations |
| **Interpreter/Math** | INTERPRETIVE_CONSTANTS.agc | 82 | Interpreter constant pool |
| **Interpreter/Math** | SINGLE_PRECISION_SUBROUTINES.agc | 67 | Single-precision arithmetic subroutines |
| **Interpreter/Math** | FIXED_FIXED_CONSTANT_POOL.agc | 263 | Fixed-fixed memory constant definitions |
| **Interpreter/Math** | RT8_OP_CODES.agc | 358 | Return-to-basic interpreter op codes |
| **System Infrastructure** | INTER-BANK_COMMUNICATION.agc | 183 | Bank-to-bank subroutine call mechanism |
| **System Infrastructure** | INTERRUPT_LEAD_INS.agc | 122 | Interrupt vector lead-in dispatch table |
| **System Infrastructure** | T4RUPT_PROGRAM.agc | 1467 | T4 interrupt: DSKY, optics, DAP monitoring |
| **System Infrastructure** | DOWN-TELEMETRY_PROGRAM.agc | 441 | Downlink telemetry formatting and transmission |
| **System Infrastructure** | DOWNLINK_LISTS.agc | 411 | Telemetry downlink list definitions |
| **System Infrastructure** | UPDATE_PROGRAM.agc | 555 | Uplink state vector update program (P27) |
| **System Infrastructure** | AGC_BLOCK_TWO_SELF-CHECK.agc | 513 | Computer self-test and bank checksum display |
| **System Infrastructure** | SYSTEM_TEST_STANDARD_LEAD_INS.agc | 150 | System test entry points |
| **Mission-Specific** | P61-P67.agc | 1225 | Entry programs (P61-P67) — CM only |
| **Configuration/Data** | CONTRACT_AND_APPROVALS.agc | 73 | Contract identification and approvals — CM only |
| **Configuration/Data** | ASSEMBLY_AND_OPERATION_INFORMATION.agc | 1010 | Program identification, build info, GSOP reference |
| **Configuration/Data** | ERASABLE_ASSIGNMENTS.agc | 3785 | Erasable memory variable allocation |
| **Configuration/Data** | TAGS_FOR_RELATIVE_SETLOC.agc | 435 | Memory bank tags for relative addressing |
| **Configuration/Data** | MAIN.agc | 99 | Master include file — assembly build order |

---

## Shared vs. Unique Files

### Files Present in Both Modules (Shared Infrastructure)

These files appear in both Luminary099 and Comanche055, implementing the same core AGC functions with module-specific tuning:

| Filename | Luminary099 Lines | Comanche055 Lines |
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

### Files Unique to Luminary099 (Lunar Module)

| Filename | Lines | Why LM-Only |
|----------|-------|-------------|
| AGS_INITIALIZATION.agc | 228 | Abort Guidance System exists only on LM |
| AOSTASK_AND_AOSJOB.agc | 1069 | 1/ACCS guidance-DAP interface for LM configuration |
| AOTMARK.agc | 695 | Alignment Optical Telescope (LM-specific instrument) |
| ASCENT_GUIDANCE.agc | 647 | Lunar ascent — LM mission phase |
| ATTITUDE_MANEUVER_ROUTINE.agc | 1027 | KALCMANU for LM free-fall maneuvers |
| BURN_BABY_BURN--MASTER_IGNITION_ROUTINE.agc | 1059 | Master ignition for DPS/APS engines |
| CONTROLLED_CONSTANTS.agc | 558 | DPS/APS engine parameters |
| DAP_INTERFACE_SUBROUTINES.agc | 176 | LM DAP interface utilities |
| DAPIDLER_PROGRAM.agc | 494 | LM DAP idler/initialization |
| FINDCDUW--GUIDAP_INTERFACE.agc | 743 | Guidance-to-DAP thrust direction interface |
| FLAGWORD_ASSIGNMENTS.agc | 1269 | LM-specific flag definitions |
| GENERAL_LAMBERT_AIMPOINT_GUIDANCE.agc | 168 | Lambert guidance (P31) for LM |
| IMU_PERFORMANCE_TEST_2.agc | 421 | LM IMU test routines |
| IMU_PERFORMANCE_TESTS_4.agc | 362 | LM gyro drift filter |
| INPUT_OUTPUT_CHANNEL_BIT_DESCRIPTIONS.agc | 223 | LM-specific I/O channel documentation |
| KALMAN_FILTER.agc | 101 | LM DAP Kalman filter |
| LANDING_ANALOG_DISPLAYS.agc | 533 | Landing-phase analog displays |
| LEM_GEOMETRY.agc | 206 | LM vehicle geometry |
| LUNAR_LANDING_GUIDANCE_EQUATIONS.agc | 1474 | Powered descent guidance |
| P-AXIS_RCS_AUTOPILOT.agc | 1056 | LM P-axis RCS autopilot |
| P12.agc | 243 | Powered ascent program |
| P30_P37.agc | 185 | LM-specific P30/P37 variant |
| P32-P35_P72-P75.agc | 1394 | LM CSI/CDH rendezvous programs |
| P70-P71.agc | 439 | Abort programs (LM-only) |
| Q_R-AXIS_RCS_AUTOPILOT.agc | 860 | LM Q/R-axis RCS autopilot |
| R63.agc | 156 | Point LM axis at CSM (V89) |
| RADAR_LEADIN_ROUTINES.agc | 103 | LM radar interface |
| RCS_FAILURE_MONITOR.agc | 173 | LM RCS valve failure monitor |
| S-BAND_ANTENNA_FOR_LM.agc | 200 | LM steerable S-band antenna |
| SERVICER.agc | 1715 | LM-specific SERVICER/Average-G |
| SPS_BACK-UP_RCS_CONTROL.agc | 196 | Docked RCS backup control |
| T6-RUPT_PROGRAMS.agc | 163 | LM T6 interrupt for jet timing |
| THE_LUNAR_LANDING.agc | 335 | Landing sequencing |
| THROTTLE_CONTROL_ROUTINES.agc | 224 | DPS throttle control |
| TJET_LAW.agc | 519 | LM jet firing time law |
| TRIM_GIMBAL_CONTROL_SYSTEM.agc | 617 | DPS gimbal trim |

### Files Unique to Comanche055 (Command Module)

| Filename | Lines | Why CM-Only |
|----------|-------|-------------|
| ANGLFIND.agc | 626 | CM gimbal angle computation |
| AUTOMATIC_MANEUVERS.agc | 504 | CM automatic maneuver execution |
| CM_BODY_ATTITUDE.agc | 301 | CM body attitude computation |
| CM_ENTRY_DIGITAL_AUTOPILOT.agc | 1273 | Atmospheric reentry DAP |
| CONTRACT_AND_APPROVALS.agc | 73 | CM program contract page |
| CSM_GEOMETRY.agc | 415 | CSM vehicle geometry |
| ENTRY_LEXICON.agc | 299 | Entry variable definitions/scaling |
| IMU_CALIBRATION_AND_ALIGNMENT.agc | 1406 | CM IMU calibration and alignment tests |
| JET_SELECTION_LOGIC.agc | 920 | CSM RCS jet selection |
| LUNAR_LANDMARK_SELECTION_FOR_CM.agc | 35 | CM lunar landmark data |
| MYSUBS.agc | 93 | CM DAP miscellaneous subroutines |
| P11.agc | 928 | Earth orbit insertion monitor |
| P30-P37.agc | 611 | CM-specific P30-P37 variant |
| P32-P33_P72-P73.agc | 1415 | CM CSI/CDH rendezvous programs |
| P37_P70.agc | 1950 | Return-to-Earth and CM abort |
| P61-P67.agc | 1225 | Entry programs (P61-P67) |
| RCS-CSM_DAP_EXECUTIVE_PROGRAMS.agc | 85 | CSM DAP executive (AMGB/AMBG) |
| RCS-CSM_DIGITAL_AUTOPILOT.agc | 975 | CSM RCS digital autopilot |
| REENTRY_CONTROL.agc | 1609 | Entry guidance control laws |
| S-BAND_ANTENNA_FOR_CM.agc | 128 | CM S-band antenna |
| SERVICER207.agc | 824 | CM-specific SERVICER |
| STAR_TABLES.agc | 193 | Star catalog for SXT navigation |
| SXTMARK.agc | 659 | Sextant/SCT marking routines |
| TPI_SEARCH.agc | 552 | Minimum delta-V TPI search |
| TVCDAPS.agc | 784 | TVC pitch/yaw DAP |
| TVCEXECUTIVE.agc | 276 | TVC executive task |
| TVCINITIALIZE.agc | 414 | TVC initialization |
| TVCMASSPROP.agc | 245 | TVC mass properties |
| TVCRESTARTS.agc | 256 | TVC restart handling |
| TVCROLLDAP.agc | 619 | TVC roll autopilot |
| TVCSTROKETEST.agc | 260 | TVC bending stroke test |