# The Restart That Saved Apollo 11: How the AGC Recovered from 1202

## Introduction

On July 20, 1969, with the Lunar Module *Eagle* descending toward the Sea of Tranquility, the AGC's DSKY flashed **PROG 1202** — executive overflow. The computer was being overwhelmed. In any lesser system, that alarm would have meant an abort. Instead, the AGC did something extraordinary: it restarted itself, shed non-essential work, and kept the landing guidance running. It did this not once but several times during the descent, and Neil Armstrong landed with the computer functioning correctly throughout.

This chapter traces the code that made that possible, across two files in `Luminary099/`: `FRESH_START_AND_RESTART.agc` (pages 211–237) and `ALARM_AND_ABORT.agc` (pages 1381–1385). Together, they implement what we would today call a *priority-based graceful degradation system* — built in the 1960s, in 15-bit assembly, with 2K of RAM.

---

## 1. Fresh Start vs. Restart: Two Paths Through the Same Code

The AGC has two fundamentally different initialization paths, and the code is structured so they share a common subroutine (`STARTSUB`) while diverging on what state they preserve.

### 1.1 The Fresh Start Path

A fresh start occurs on initial power-up or when the astronaut explicitly requests a full reset (via the DSKY key combination of Mark Reject + Error Reset). The entry point is `SLAP1`:

```agc
SLAP1       INHINT              # FRESH START. COMES HERE FROM PINBALL.
            TC      STARTSUB    # SUBROUTINE DOES MOST OF THE WORK
```
*(FRESH_START_AND_RESTART.agc, ~line 30)*

After `STARTSUB` returns, the fresh start path continues at `SKIPSIM`, which proceeds to:

1. **Turn off DSKY lamps** (preserving only gimbal lock and no-attitude indicators):
   ```agc
   SKIPSIM     CA      DSPTAB +11D   # TURN OFF ALL DSPTAB +11D LAMPS
               MASK    BITS4&6       # EXCEPT THE GIMBAL LOCK & NO ATT ONLY ON
               AD      BIT15         # REQUESTED FRESH START.
               TS      DSPTAB +11D
   ```

2. **Initialize the downlink dump counter** for one pass.

3. **Zero out the error counters and failure registers**:
   ```agc
               CA      ZERO
               TS      ERCOUNT
               TS      FAILREG
               TS      FAILREG +1
               TS      FAILREG +2
               TS      REDOCTR
   ```
   Note: `REDOCTR` (the restart counter) is zeroed only on fresh start. On a restart, it is *incremented*. This is how ground controllers could track how many restarts had occurred.

4. **Ensure the engine is off** — a critical safety measure:
   ```agc
   DOFSTART    CAF     BIT14         # INSURE ENGINE IS OFF.
               EXTEND
               WRITE   DSALMOUT
               CS      ZERO
               TS      THRUST
   ```

5. **Initialize the DAP** (Digital Autopilot), all flag words, switch state tables, and IMU modes. The fresh start path writes to `STATE` through `STATE +11D` — twelve words of flag bits that track every significant software state in the system:
   ```agc
               EXTEND              # INITIALIZE SWITCHES ONLY ON FRESH START.
               DCA     SWINIT
               DXCH    STATE
               CA      SWINIT +2
               TS      STATE +2
   ```

   But even here, the code is careful. Certain flags are *preserved* even across a fresh start:
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
   The reference frame flag (`REFSMFLG`), the surface flag (`SURFFLAG`), and the moon flags are left untouched — because losing track of whether you're orbiting the Moon or sitting on its surface would be catastrophic regardless of what reset triggered.

6. **Exit through `ENDRSTRT`**, which jumps to `DUMMYJOB +2`, picking up at `RELINT` (re-enabling interrupts) without zeroing `NEWJOB`.

### 1.2 The Restart Path

A restart occurs when the AGC hardware detects a condition requiring a software reset — the `GOJAM` signal. This vectors execution to address 4000 (the boot vector), which transfers to `GOPROG`:

```agc
# COMES HERE FROM LOCATION 4000, GOJAM, RESTART ANY PROGRAMS
# WHICH MAY HAVE BEEN RUNNING AT THE TIME.

        EBANK=  LST1
GOPROG  INCR    REDOCTR         # ADVANCE RESTART COUNTER.
```
*(FRESH_START_AND_RESTART.agc, ~page 215)*

The very first instruction increments `REDOCTR` — the restart counter. This is the telemetry breadcrumb that told Houston how many restarts had occurred. During the Apollo 11 landing, this counter advanced several times.

Next, the code saves the bank state:
```agc
        LXCH    Q
        EXTEND
        ROR     SUPERBNK
        DXCH    RSBBQ
```
This preserves Q (return address) and the superbank bits into `RSBBQ`, capturing where the computer was when the restart hit.

The restart path then checks whether the IMU was in coarse align (needed for gimbal lock recovery):
```agc
        CA      DSPTAB +11D
        MASK    BIT4
        EXTEND
        BZF     +4
        AD      BIT6            # SET ERROR COUNTER ENABLE
        EXTEND
        WOR     CHAN12          # ISS WAS IN COARSE ALIGN SO GO BACK TO
```

### 1.3 The Erasable Memory Integrity Check

Before proceeding with restart, the code performs a remarkable integrity check on erasable (RAM) memory. The `ERASCHK` system works like this: when the system is modifying erasable memory, it saves backup copies in `SKEEP5`/`SKEEP6` and records what address is being modified in `SKEEP7` and `ERESTORE`. On restart:

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

The logic is:
- If `ERESTORE` is +0, no memory modification was in progress → safe to restart
- If `ERESTORE` equals `SKEEP7` and is a valid erasable address (< 2000 octal), then memory was mid-modification → restore the backup and restart
- Otherwise, memory might be corrupted → fall through to a full fresh start

This is a **transactional memory protection scheme**, implemented in 1960s assembly. If a restart catches the system mid-write, it rolls back the partial operation using the saved copies:

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

### 1.4 What Restart Preserves vs. Destroys

| Preserved Across Restart | Destroyed / Reinitialized |
|--------------------------|---------------------------|
| Phase table entries (if consistent) | Waitlist (all pending timed tasks) |
| Flag words (mostly) | Executive job table (all VAC areas) |
| Engine on/off state | Display state |
| IMU coarse align state | DSKY registers |
| Gimbal lock / no-attitude lamps | Pending I/O |
| Navigation state vectors | DAP transient state |
| REDOCTR (incremented) | Mark system |
| ERCOUNT, FAILREG | Monitor displays |

The key insight: **program phases are preserved, but the scheduling infrastructure is wiped clean**. The waitlist and executive are reinitialized from scratch. Then the phase table is consulted to figure out what was running and what needs to be restarted.

---

## 2. The Restart Logic: Phase Tables and Priority Decisions

### 2.1 The Common Initialization Subroutine

Both fresh start and restart call `STARTSUB`, which performs the core system initialization:

```agc
STARTSUB  CAF     LDNPHAS1      # SET POINTER SO NEXT 20MS DOWNRUPT WILL
          TS      DNTMGOTO      # CAUSE THE CURRENT DOWNLIST TO BE
                                # INTERRUPTED AND START SENDING FROM THE
                                # BEGINNING OF THE CURRENT DOWNLIST.
```
*(page 219)*

`STARTSUB` then:

1. **Resets the timers** — TIME3, TIME4, TIME5 are loaded to their maximum values (triggering their interrupts shortly):
   ```agc
   STARTSB1  CAF     POSMAX
             TS      TIME3
             AD      MINUS2
             TS      TIME4
             AD      NEGONE
             TS      TIME5
   ```
   TIME3 is loaded first (drives the Waitlist), then TIME4 (DSKY) gets POSMAX-2, then TIME5 (DAP) gets POSMAX-3. The staggering prevents all three interrupt handlers from colliding.

2. **Disables TIME6** (the high-frequency jet timing counter):
   ```agc
             CAF     POSMAX        # DISABLE TIME6 CLOCK.  JUST IN CASE A T6
             TS      T6NEXT        #   RUPT IS ALREADY IN THE PRIORITY CHAIN,
             EXTEND                #   ENSURE THAT ITS INPUTS WILL RENDER IT
             WAND    CHAN13        #   INEFFECTUAL.
   ```

3. **Sets up the DAP idle routine** as the T5RUPT handler:
   ```agc
             EXTEND              # SET T5RUPT FOR DAPIDLER PROGRAM.
             DCA     IDLEADR
             DXCH    T5ADR
   ```

Then `STARTSB2` (called on restart but not the initial part of fresh start) preserves engine state:
```agc
STARTSB2  CAF     OCT30001      # DURING SOFTWARE RESTART, DO NOT DISTURB
          EXTEND                # ENGINE ON, OFF AND ISS WARNING.
          WAND    DSALMOUT
```
The `WAND` (Write-AND) instruction masks the engine control channel, preserving only the engine on/off bit and the ISS warning. Everything else on that channel is cleared.

4. **Reinitializes the Waitlist** — all eight task slots are cleared:
   ```agc
             CAF     NEG1/2        # INITIALIZE WAITLIST DELTA-TS.
             TS      LST1 +7
             TS      LST1 +6
             ...
             TS      LST1
   ```
   `NEG1/2` (-0.5 in SP) marks each slot as "maximum time until expiry" — effectively empty. The task addresses (`LST2` through `LST2 +17D`) are loaded with the complement of `ENDTASK`, a sentinel that means "no task here."

5. **Clears all Executive priority registers** — making all 8 job slots available:
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
   `CS ZERO` produces -0 (all ones), which in the Executive means "this slot is free." Each VAC area is 12 words apart (one priority word + working storage), so the +12D, +24D, etc. offsets hit each priority register.

6. **Marks no active job**:
   ```agc
             TS      DSRUPTSW
             TS      NEWJOB        # SHOWS NO ACTIVE JOBS.
   ```

7. **Makes all VAC areas available** by linking them into a free list:
   ```agc
             CAF     VAC1ADRC      # MAKE ALL VAC AREAS AVAILABLE.
             TS      VAC1USE
             AD      LTHVACA
             TS      VAC2USE
             AD      LTHVACA
             TS      VAC3USE
             ...
   ```
   `LTHVACA` is 44 decimal — the spacing between VAC areas. Each `VACnUSE` register points to the start of its VAC area, forming a linked free list.

### 2.2 Phase Table Verification

After the common initialization, the restart path (at `GOPROG3`) performs the critical phase table verification:

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
*(page 216–217)*

This is an integrity check. For each restart group (1 through 5, since `NUMGRPS` equals `FIVE`), the system stores *two* copies of the phase: `PHASEn` and `-PHASEn`. The `-PHASEn` value should be the 1's complement of `PHASEn`. The check works as follows:

1. `DCA -PHASEn` loads the complement into A and the direct value into L
2. `RXOR LCHAN` XORs A with L (via the L "channel")
3. If they're proper complements, the XOR produces -0 (all ones)
4. `CCS A` on -0 falls through to the fourth case (the -0 case), which continues the loop

If any phase pair disagrees, the CCS falls into one of the first three cases → `PTBAD`:
```agc
PTBAD       TC      ALARM         # SET ALARM TO SHOW PHASE TABLE FAILURE.
            OCT     1107
            TCF     DOFSTRT1
```
Alarm 1107 is raised and the system falls back to `DOFSTRT1` — essentially a fresh start (but without turning off the engine, which is the distinction between `DOFSTART` and `DOFSTRT1`).

### 2.3 Restarting Active Programs

If all phase tables are consistent, the code proceeds to restart whatever was running:

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
*(page 217)*

For each restart group, `CCS PHASE1` (indexed by group number) tests the phase value:
- If positive (group is active), execution goes to `PACTIVE`
- If +0, the group is not running → `PINACT`

`PACTIVE` calls `RESTARTS` (via `RACTCADR`, which is `CADR RESTARTS`) through `SWCALL`. The `RESTARTS` routine (defined elsewhere) uses the phase value to determine exactly where in the program to resume. Each program registers its restart points by storing a phase number, and the restart dispatcher uses that number to vector to the correct recovery point.

The phase mechanism works like **checkpoints**: a program periodically calls `PHASCHNG` to update its phase, saying "I've reached step N." If a restart occurs, the system looks at the phase and re-enters the program at the checkpoint corresponding to that phase.

After processing all groups:
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

If *any* group had an active phase (`MPAC +6` > 0), the system proceeds to `ENDRSTRT` — normal operation resumes. If *no* groups were active but the mode register is -0, it also proceeds. Otherwise, it goes to `GOTOPOOH` (P00) — the idle program.

### 2.4 Engine State Preservation on Restart

One of the most critical aspects of the restart logic is engine management. At `SETINFL` (the restart-specific path after `DORSTART`), the code explicitly checks and preserves engine state:

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
*(page 216)*

The code checks `ENGONBIT` in `FLAGWRD5`. If the engine was on before the restart, it turns it back on. If it was off, it turns it off. **The engine state survives the restart.** During the landing, the descent engine was firing continuously — if a restart had killed the engine, the LM would have crashed.

---

## 3. The 1202/1201 Alarm: Executive Overflow

### 3.1 Where the Alarm Originates

The 1202 alarm is **not generated in either of these two files**. It originates in the Executive module (specifically in `EXEC` or `FINDVAC`) when a call to schedule a new job finds all VAC areas occupied. The Executive would call:

```agc
        TC      ALARM
        OCT     1202
```

or for 1201 (no VAC areas available for a different scheduling path):

```agc
        TC      ALARM
        OCT     1201
```

What we *can* trace in `ALARM_AND_ABORT.agc` is exactly what happens when that `TC ALARM` executes.

### 3.2 The ALARM Subroutine

```agc
ALARM       INHINT

            CA      Q
ALARM2      TS      ALMCADR
            INDEX   Q
            CA      0
BORTENT     TS      L
```
*(ALARM_AND_ABORT.agc, page 1381)*

Step by step:

1. **`INHINT`** — Disable interrupts immediately. This is critical: you don't want another interrupt firing while you're in the middle of recording the alarm.

2. **`CA Q` / `TS ALMCADR`** — Save the return address. Q holds the address of the word *after* `TC ALARM`, which is the alarm code itself. Saving Q to `ALMCADR` records where the alarm came from.

3. **`INDEX Q` / `CA 0`** — This is an elegant AGC idiom. `INDEX Q` modifies the next instruction by adding Q to its address. `CA 0` becomes `CA Q` effectively loading the word at address Q — which is the octal alarm code (e.g., `OCT 1202`). The alarm code is now in A.

4. **`TS L`** — Store the alarm code in L (the lower register).

### 3.3 Recording the Alarm

```agc
PRIOENT     CA      BBANK
 +1         EXTEND
            ROR     SUPERBNK      # ADD SUPER BITS.
            TS      ALMCADR +1

LARMENT     CA      Q             # STORE RETURN FOR ALARM
            TS      ITEMP1
```

The current bank state (BBANK + superbank bits) is saved to `ALMCADR +1`, forming a complete 2CADR (double-word address) of where the alarm originated. This is the "who called me" record that would appear in telemetry.

### 3.4 The Failure Register Cascade

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

There are three failure registers. The code tries to store the alarm code (still in L) into the first empty one:

1. `CCS FAILREG` — if FAILREG is non-zero (positive), it already has an alarm → try the next register
2. If FAILREG is +0 (empty), `LXCH FAILREG` swaps L (alarm code) into FAILREG → go light the lamp
3. Same pattern for `FAILREG +1` and `FAILREG +2`

If all three are full:
```agc
MULTFAIL    CA      L
            AD      BIT15
            TS      FAILREG +2
```
The current alarm code is OR'd with BIT15 (setting the sign bit) and stored in `FAILREG +2`, overwriting whatever was there. The set sign bit serves as a flag meaning "multiple alarms have occurred — this register has been overwritten."

### 3.5 The Program Alarm Light

For the *first* alarm, `PROGLARM` lights the PROG lamp on the DSKY:

```agc
PROGLARM    CS      DSPTAB +11D
            MASK    OCT40400
            ADS     DSPTAB +11D
```

`OCT40400` = bits 9 and 15. The `CS`/`MASK`/`ADS` sequence sets these bits in the display table, which turns on the PROGRAM alarm indicator on the DSKY. This is the light that Armstrong and Aldrin saw.

### 3.6 Return to Caller

```agc
MULTEXIT    XCH     ITEMP1        # OBTAIN RETURN ADDRESS IN A
            RELINT
            INDEX   A
            TC      1
```

The return address (saved earlier in `ITEMP1`) is restored, interrupts are re-enabled (`RELINT`), and execution returns to the instruction *after* the alarm code. `INDEX A` / `TC 1` is the AGC idiom for "jump to A+1" — i.e., the word after the `OCT 1202` constant.

**This is the critical point: `ALARM` returns to the caller.** For a 1202, the Executive would then typically invoke `BAILOUT` or proceed to a restart via other means. But `ALARM` itself is non-abortive — it records and returns.

### 3.7 BAILOUT vs. POODOO: Abortive Alarm Paths

The file provides two *abortive* alarm paths for more severe situations:

**BAILOUT** — Used when a program hits an unrecoverable but non-fatal error:
```agc
BAILOUT     INHINT
            CA      Q
            TS      ALMCADR
            INDEX   Q
            CAF     0
            TC      BORTENT
```
After recording the alarm, it falls through to:
```agc
WHIMPER     CA      TWO
            AD      Z
            TS      BRUPT
            RESUME
            TC      POSTJUMP      # RESUME SENDS CONTROL HERE
            CADR    ENEMA
```

This is a clever trick. `RESUME` is the "return from interrupt" instruction, but BAILOUT isn't an ISR. By setting `BRUPT` to point to the `TC POSTJUMP` instruction and then executing `RESUME`, the code forces a jump to `ENEMA` — which does a partial restart (`STARTSB1` + `GOPROG2A`), preserving more state than a full restart but still reinitializing the scheduler.

**POODOO** — The "abort" path (note the label `ABORT EQUALS WHIMPER`):
```agc
POODOO      INHINT
            CA      Q
ABORT2      TS      ALMCADR
            INDEX   Q
            CAF     0
            TC      BORTENT
```
After recording the alarm, POODOO sets up restart group 4:
```agc
            CAF     OCT35         # 4.35SPOT FOR GOPOODOO
            TS      L
            COM
            DXCH    -PHASE4
```
This registers `GOPOODOO` as the phase-4 restart point. Then `GOPOODOO` does the cleanup:
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

The `FLAGS` subroutine (page 1385) clears `STATEBIT`, `REINTBIT`, and `NODOBIT`:
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

### 3.8 The MR.KLEAN Hierarchy

Back in `FRESH_START_AND_RESTART.agc`, the phase-clearing routines reveal the priority hierarchy:

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
*(page 213–214)*

Three nested entry points provide three levels of cleanup:

| Entry Point | Groups Cleared | Use Case |
|-------------|---------------|----------|
| `V37KLEAN` | 1, 3, 5, 6 | Kill navigation/misc but keep P20/P25 and current program |
| `P00KLEAN` | 4, 1, 3, 5, 6 | Kill current program too, keep only P20/P25 |
| `MR.KLEAN` | 2, 4, 1, 3, 5, 6 | Kill everything |

`DCA NEG0` / `DXCH -PHASEn` stores -0 in both the phase and its complement — marking the group as inactive. The order matters: group 4 (which typically holds the currently running major program) is cleared before groups 1/3/5/6, but *after* the caller has already registered its own restart point in group 4.

---

## 4. Tracing the 1202 Path During the Landing

### 4.1 The Scenario

During the Apollo 11 descent, the rendezvous radar was left in a mode that generated excessive interrupts (a RUPT10 every radar cycle). Each interrupt consumed CPU time for the unprogrammed counter-increment sequences. The Executive's job queue filled up because:

1. The landing guidance (P63, then P64) was running as a high-priority job
2. The Servicer (which computed navigation updates) was running
3. Radar processing tasks were being scheduled
4. The waitlist was firing tasks that needed VAC areas
5. With all 8 VAC areas occupied, the next `FINDVAC` call generated alarm 1202

### 4.2 Why the Landing Survived

The chain of survival works through several mechanisms:

**1. ALARM is non-abortive.** The `ALARM` subroutine (page 1381) only records the alarm and lights the PROG lamp. It returns to the caller. The Executive could then decide what to do — typically, it would fail to schedule the low-priority task (the one that overflowed) while the high-priority task (landing guidance) continued to hold its VAC area.

**2. The restart preserves program phases.** When a restart occurs (whether triggered by the overflow or by BAILOUT), `STARTSUB` clears the waitlist and executive but leaves the phase table intact. The landing guidance had registered its phase before the overflow occurred.

**3. Priority-based restart.** The `PACTIVE`/`NXTRST` loop in `GOPROG3` processes all restart groups. Each group's restart handler (`RESTARTS`) would re-schedule its job via `FINDVAC`. But now the system is clean — all 8 VAC areas are free. The high-priority landing program gets its VAC area first. Lower-priority tasks that caused the overflow may or may not fit, but the system no longer cares — the essential work runs.

**4. Engine state survives.** The descent engine continues firing because the restart path at `SETINFL` explicitly preserves `ENGONBIT` and restores the engine command to the hardware channel.

**5. Flags preserve context.** The flag words (`FLAGWRD0` through `FLAGWRD11`) survive the restart. They tell the restarted programs what state they were in — for example, whether the landing radar had been incorporated, whether guidance was in the P63 braking phase or P64 approach phase.

### 4.3 The V37 Mechanism and Priority Shedding

The Verb 37 (program change) mechanism in `V37` (page 227) reveals how the system manages program priority. When deciding whether to keep or kill programs during a mode change, the code checks specific flags:

```agc
V37RET      CS      FLAGWRD0      # IS P20 OR P22 RUNNING?
            MASK    RNDVZBIT
            CCS     A
            TCF     +2            # NO. CHECK FOR P25.
            TCF     2.7SPT        # YES. DO 2.7SPOT
```

P20 (rendezvous tracking) and P25 run in restart group 2. The landing guidance runs in group 4. During the 1202 restarts, the group structure meant:

- Group 4 (landing) → restarted at its registered phase → P63/P64 resumes
- Group 2 (if P20 was running) → also restarted, but radar processing tasks that hadn't registered phases were lost
- Unphased tasks (the ones causing the overflow) → gone, which is exactly what you want

---

## 5. The Design Philosophy

### 5.1 Asynchronous Restart Architecture

Hamilton's team designed the system around a principle that was radical for the 1960s and remains uncommon today: **any computation should be interruptible and restartable at any point, with the system automatically recovering to a known-good state.**

This required:
- **Phase registration**: Every significant program checkpoint writes a phase number, creating a trail of breadcrumbs
- **Dual-copy integrity**: Phase values are stored twice (as value and complement), allowing the restart code to detect corruption
- **Idempotent recovery**: Restart handlers must be safe to call even if the original computation partially completed
- **Priority-based triage**: When resources are scarce, the system sheds low-priority work automatically

### 5.2 Comparison to Modern Approaches

| AGC Approach | Modern Equivalent |
|-------------|-------------------|
| Phase table registration | Transaction logging / Write-Ahead Log |
| ERESTORE backup/restore | Database savepoints / journaling |
| Dual-copy phase check | Checksummed metadata |
| Priority-based restart | Kubernetes pod priority / preemption |
| ALARM (non-abortive) | Circuit breaker pattern (half-open) |
| BAILOUT → WHIMPER | Graceful degradation / bulkhead pattern |
| MR.KLEAN hierarchy | Cascading circuit breakers |
| GOJAM → GOPROG | Erlang supervisor restart strategies |

The closest modern analog is Erlang's supervisor tree: "let it crash, then restart in a known-good state." But the AGC predates Erlang by 30 years, and does it with 2K of RAM and no hardware stack.

### 5.3 What Would Have Happened Without This Design

**Scenario A: Simple watchdog timer (restart everything on overflow)**
The engine would have been shut off. The navigation state would be lost. The astronauts would abort.

**Scenario B: Halt on error (modern assertion/panic)**
The computer stops. The engine stops. The LM crashes.

**Scenario C: Ignore and continue (swallow the error)**
The Executive's job table becomes corrupt. Subsequent job scheduling produces undefined behavior. The guidance equations stop updating. The LM drifts off course.

**What actually happened:** The system restarted, shed the excess radar processing, and the landing guidance resumed within milliseconds. Armstrong and Aldrin saw the PROG light and heard "1202" called out, but the computer was already recovered by the time Houston said "we're go on that alarm." The 60-second delay in Houston's response wasn't the computer waiting — it was the humans catching up to the machine.

---

## 6. The CURTAINS Subroutine: When Even Restart Can't Help

There's one more notable routine in `ALARM_AND_ABORT.agc`:

```agc
CURTAINS    INHINT
            CA      Q
            TC      ALARM2
OCT217      OCT     00217
            TC      ALMCADR       # RETURN TO USER
```
*(page 1383)*

`CURTAINS` generates alarm 00217 and *returns to the caller*. Despite its dramatic name, it's actually a non-fatal alarm — it records the issue and lets the calling program decide what to do. The name suggests the developers had a sense of humor about catastrophic situations.

And then there's `CCSHOLE`:
```agc
CCSHOLE     INHINT
            CA      Q
            TC      ABORT2
OCT1103     OCT     1103
```

This handles the case where a `CCS` instruction encounters an impossible value — a "hole" in the four-way skip logic. Alarm 1103: "the laws of arithmetic have been violated." If this ever fires, something has gone deeply wrong at the hardware level.

---

## Summary

The code in these two files represents one of the most sophisticated error-handling systems ever built for its era. The key architectural decisions — phase-based checkpointing, priority-aware restart, non-abortive alarms, and transactional memory protection — combined to create a system that could recover from overload in milliseconds. On July 20, 1969, with everything on the line, it worked exactly as designed.

The 1202 alarm wasn't a bug. It was the system *working correctly under abnormal load* — detecting the overload, shedding non-essential work, preserving the critical path, and resuming before anyone on the ground fully understood what had happened.

> **Note on uncertainty:** The exact path from Executive overflow → 1202 alarm → restart depends on code in the Executive module (`EXEC.agc`) and the Waitlist (`WAITLIST.agc`), which are not included in the source files provided here. The analysis of the alarm generation point and the specific FINDVAC overflow path is inferred from the architectural context and the alarm-handling code we can see. The restart recovery path through `GOPROG` → `STARTSUB` → phase table verification → `RESTARTS` is fully traceable in the provided source. The interaction between restart group assignments and specific programs (which group P63/P64 uses, how the radar processing registers its phases) would require examining additional modules like `P63-P68.agc` and the rendezvous radar routines.