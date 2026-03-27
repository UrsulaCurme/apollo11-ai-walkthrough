# The Waitlist: A Hardware-Driven Task Scheduler in 2K of RAM

## Overview

The Waitlist is the AGC's real-time task scheduler — a timer-driven, interrupt-triggered dispatch system that complements the Executive's cooperative job scheduler. Where the Executive manages long-running "jobs" that can be suspended and resumed through voluntary priority scheduling, the Waitlist handles short, time-critical "tasks" that must fire at precise moments: autopilot jet firings, DSKY display updates, sensor readings, guidance equation steps.

The entire mechanism fits in roughly 200 words of fixed memory and uses 27 words of erasable memory for its data structures. It supports up to 9 concurrent pending tasks with a timing resolution of 10 milliseconds and a maximum single-shot delay of 162.5 seconds. For longer delays, LONGCALL extends coverage to roughly 2.56 hours through iterative rescheduling.

---

## 1. Architecture

### Executive Jobs vs. Waitlist Tasks

The AGC runs two fundamentally different scheduling systems simultaneously:

| Property | Executive Job | Waitlist Task |
|----------|--------------|---------------|
| **Trigger** | Software request (FINDVAC/NOVAC) | Hardware timer interrupt (T3RUPT) |
| **Duration** | Long-running, may sleep | Short — must complete quickly |
| **Preemption** | Cooperative (voluntary CHANG1) | Preemptive (interrupts foreground) |
| **Context** | Has a VAC area (work registers) | No saved context — runs to completion |
| **Termination** | TC ENDOFJOB | TC TASKOVER |
| **Priority** | 1-37 (octal), priority-scheduled | First-come-first-served by time |
| **Max concurrent** | 7 jobs | 9 tasks |

A Waitlist task runs in interrupt context. It fires, does its work (typically tens to hundreds of instructions), and returns via `TC TASKOVER`. If the work is too large for interrupt context, the task's first action is typically to schedule an Executive job via `FINDVAC` and then immediately `TC TASKOVER`.

### The Data Structures: LST1 and LST2

The Waitlist maintains two parallel arrays in switched erasable memory (EBANK=LST1):

**LST1** — An 8-entry array of *delta times* between consecutive tasks:

```
C(LST1)     = -(T2 - T1) + 1
C(LST1 +1)  = -(T3 - T2) + 1
C(LST1 +2)  = -(T4 - T3) + 1
  ...
C(LST1 +7)  = -(T9 - T8) + 1
```

Each entry stores the *negated* time difference between adjacent tasks, plus one. The negation is a consequence of 1's-complement arithmetic and the CCS instruction's behavior — storing negated deltas allows the insertion search loop to use CCS directly as a "is there still time remaining?" test.

The +1 bias exists because CCS distinguishes four cases (positive, +0, negative, -0), and adding 1 ensures that a zero delta maps to +1 (positive), taking the correct CCS branch.

**LST2** — A 9-entry array of *2CADRs* (double-word complete addresses):

```
C(LST2)      = 2CADR TASK1   (address + bank info)
C(LST2 +2)   = 2CADR TASK2
  ...
C(LST2 +16)  = 2CADR TASK9
```

Each 2CADR occupies two words: the first word is the address within the target bank, the second is a BBCON (combined bank register value including superbank). LST2 entries are spaced 2 words apart because each 2CADR is a double word.

**TIME3** holds the time until the *first* task fires:

```
C(TIME3) = 16384 - (T1 - T)    i.e., 1.0 - (T1 - T) in centiseconds
```

When TIME3 overflows (reaches +0 from POSMAX), it triggers T3RUPT, meaning task T1 is due.

### The Sentinel: ENDTASK

```agc
ENDTASK         -2CADR  SVCT3
```

(Line ~page 1121)

ENDTASK is a constant stored in fixed-fixed memory (not switched bank), initialized into all slots of LST2 at fresh start. Its key property is that **its address alone distinguishes it** — the insertion routine checks whether it has cascaded a task all the way to the bottom of the list by testing whether the displaced entry equals ENDTASK:

```agc
        DXCH    LST2 +16D
        AD      ENDTASK         # END ITEM, AS CHECK FOR EXCEEDING
        EXTEND                  # THE LENGTH OF THE LIST.
        BZF     LVWTLIST        # DUMMY TASK ADRES SHOULD BE IN FIXED-
        TCF     WTABORT         # FIXED SO ITS ADRES ALONE DISTINGUISHES IT.
```

If the value displaced from the last LST2 slot is ENDTASK (i.e., adding ENDTASK to the address gives zero — they are complements), the insertion succeeded. If not, we've overflowed the list and abort with alarm 1203.

When ENDTASK actually fires (because no real task replaced it), it runs SVCT3, which checks the drift flag and potentially schedules an IMU compensation task (NBDONLY). This is a clever dual-use: the sentinel doubles as a periodic housekeeping trigger.

The corresponding LST1 entries are initialized to NEG1/2 (octal 40000, i.e., -16383). Since T3RUPT adds POSMAX to this value before loading TIME3, the resulting TIME3 value gives a roughly 81.91-second interval between sentinel firings — the maximum single overflow period of a 14-bit counter at 10ms resolution.

### Maximum Concurrent Tasks: 9

The arrays hold 9 tasks (8 LST1 delta entries define intervals between 9 time points, and LST2 has 9 double-word slots from LST2 through LST2+16). Attempting to insert a 10th task triggers:

```agc
WTABORT         TC      FILLED
...
FILLED          DXCH    WAITEXIT
                TC      BAILOUT1        # NO ROOM IN THE INN
                OCT     01203
```

Alarm code 1203 — a program abort. There is no graceful degradation; the system designers determined that 9 pending tasks would always be sufficient for mission operations. This is a hard real-time system with statically analyzed worst-case task counts.

---

## 2. T3RUPT and Task Dispatch

### How TIME3 Triggers T3RUPT

TIME3 is a 15-bit 1's-complement counter incremented every 10ms by hardware. When it overflows (transitions from POSMAX = 37777 octal through +0), the hardware sets the T3RUPT interrupt request flag. If interrupts are enabled and no higher-priority conditions prevent it, the CPU vectors to address 4014 octal.

The software loads TIME3 with `1.0 - (T1 - T)` where T1 is the absolute time the next task should fire and T is the current time. As time advances, TIME3 counts up. When `T1 - T` centiseconds have elapsed, TIME3 reaches POSMAX and overflows on the next tick.

### The T3RUPT Handler: Dispatching the First Task

```agc
T3RUPT          EXTEND
                ROR     SUPERBNK        # READ CURRENT SUPERBANK VALUE AND
                TS      BANKRUPT        # SAVE WITH E AND F BANK VALUES.
                EXTEND
                QXCH    QRUPT
```

**Lines (page 1128):** The ISR entry saves context. `EXTEND; ROR SUPERBNK` reads BBANK OR'd with the superbank bit from I/O channel 7 — this captures the full bank state. It's saved in BANKRUPT. Q is saved in QRUPT. Note: A and L are NOT saved here because they'll be loaded with the task's 2CADR momentarily.

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

This is a *rotation chain*. Starting with NEG1/2 in A:
1. `XCH LST1+7` swaps A (NEG1/2) with LST1+7. Now A = old LST1+7, and LST1+7 = NEG1/2 (sentinel interval).
2. `XCH LST1+6` swaps A (old LST1+7) with LST1+6. Now LST1+6 = old LST1+7.
3. Continue up the chain...
4. `XCH LST1` swaps A (old LST1+1) with LST1. Now A = old LST1+0 (the delta to the NEXT task), and the entire array has shifted up by one position with NEG1/2 inserted at the bottom.

After this chain, A contains the old LST1[0] value: `-(T2 - T1) + 1`.

```agc
                AD      POSMAX          # 2. SET T3 = 1.0 - T2 - T USING LIST 1.
                ADS     TIME3           #    SO T3 WON'T TICK DURING UPDATE.
                TS      RUPTAGN
                CS      ZERO
                TS      RUPTAGN         # SETS RUPTAGN TO +1 ON OVERFLOW.
```

This is subtle and brilliant. Let's trace the arithmetic:

- A = `-(T2 - T1) + 1` (from LST1[0])
- `AD POSMAX` adds 16383. Result: `16383 - (T2 - T1) + 1 = 16384 - (T2 - T1)`
- `ADS TIME3` adds this to the current TIME3 value.

But what *is* the current TIME3? At the moment T3RUPT fired, TIME3 had just overflowed. During the ISR preamble (saving context, doing the XCH chain), TIME3 has been ticking. Let's call the current TIME3 value `T_elapsed` (small, representing ticks since overflow).

So: `TIME3 ← T_elapsed + 16384 - (T2 - T1)`

This is exactly `1.0 - ((T2 - T1) - T_elapsed)` — the correct TIME3 value for firing at T2, accounting for time already elapsed during the ISR! The comment "SO T3 WON'T TICK DURING UPDATE" is a slight understatement — it means the TIME3 update is *inherently correct* regardless of how many ticks elapsed during the ISR.

**RUPTAGN and cascading dispatch:**

```agc
                TS      RUPTAGN
                CS      ZERO
                TS      RUPTAGN         # SETS RUPTAGN TO +1 ON OVERFLOW.
```

After `ADS TIME3`, if TIME3 overflows (meaning T2 is also due NOW), A gets +1 (the TS skip-on-overflow behavior). `TS RUPTAGN` stores this. Then `CS ZERO` = -0. `TS RUPTAGN` — if A had been +1 (overflow), this path was skipped by the TS skip, so RUPTAGN stays at +1. If no overflow, RUPTAGN gets -0.

After the task runs and calls TASKOVER:
```agc
TASKOVER        CCS     RUPTAGN         # IF +1 RETURN TO T3RUPT, IF -0 RESUME.
                CAF     WAITBB
                TS      BBANK
                TCF     T3RUPT2         # DISPATCH NEXT TASK IF IT WAS DUE.
```

If RUPTAGN = +1 (next task was also due), we loop back to T3RUPT2 to dispatch it. If RUPTAGN = -0, the CCS falls through to the fourth branch (skip 3), restoring context and executing RESUME.

### The LST2 Dispatch Chain

```agc
                EXTEND                  # DISPATCH TASK.
                DCS     ENDTASK
                DXCH    LST2 +16D
                DXCH    LST2 +14D
                ...
                DXCH    LST2 +2
                DXCH    LST2
```

Mirror image of LST1: loads -ENDTASK into A,L, then cascades through LST2 from bottom to top. Each DXCH swaps the A,L pair with consecutive LST2 entries, shifting the entire array down by one slot and inserting -ENDTASK (negated because DCS was used; the sign gets corrected implicitly) at the bottom. After the chain, A,L contain the old LST2[0] — the 2CADR of the task to dispatch.

```agc
                XCH     L
                EXTEND
                WRITE   SUPERBNK        # SET SUPERBANK FROM BBCON OF 2CADR
                XCH     L               # RESTORE TO L FOR DXCH Z.
                DTCB
```

The 2CADR's BBCON (in L) contains the superbank bit. `XCH L` puts it in A, `WRITE SUPERBNK` sets the superbank I/O channel, `XCH L` restores L. Then `DTCB` (which is `DXCH Z`) loads both Z (program counter) and BB (bank registers) from A,L — effectively jumping to the task's entry point with all banks correctly set.

The task now runs in interrupt context with interrupts inhibited.

### TASKOVER: What Happens When a Task Finishes

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

CCS RUPTAGN has four paths:
- **RUPTAGN > 0 (specifically +1):** Another task is due. Switch to WAITLIST bank, loop to T3RUPT2.
- **RUPTAGN = +0:** Falls to `CAF WAITBB` — same as positive, dispatches next task.
- **RUPTAGN < 0:** Falls through two more instructions to the resume path.
- **RUPTAGN = -0:** Also falls to the resume path (skip 3 from CCS).

The resume path restores superbank, Q, BBANK, and A,L from their saved locations, re-enables interrupts with RELINT, then executes the hardware RESUME instruction which restores Z from ZRUPT — returning to whatever code was interrupted.

Note the multiple entry points: NOQRSM skips Q restoration (for cases where Q was already handled), and NOQBRSM skips both Q and bank restoration.

---

## 3. Task Insertion

### The WAITLIST Entry Point

Calling convention:
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

Let's trace this carefully:

1. **On entry:** A = delta time, Q = return address (points to the 2CADR).
2. `INHINT` — disable interrupts. Critical section begins.
3. `XCH Q` — A ↔ Q. Now A = return address, Q = delta time.
4. `TS WAITEXIT` — save return address. No overflow possible (it's a memory address), so no skip.
5. `EXTEND; INDEX WAITEXIT; DCA 0` — uses INDEX to offset DCA by the return address. Since WAITEXIT points to the word after `TC WAITLIST` in the caller, and that word is the first half of the 2CADR, `DCA 0` indexed by WAITEXIT loads the 2CADR into A,L.
6. `TS WAITADR` — saves the address portion (from A) into WAITADR. The BBCON remains in L.

### TWIDDLE: The Optimized Entry Point

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

TWIDDLE is an optimization for when the task address is in the same bank as the caller. Calling convention:
```agc
        CA      DELTAT
        TC      TWIDDLE
        ADRES   DESIRED TASK    # Single word — no BBCON needed
        RELINT                  # Returns here
```

Trace:
1. A = delta time. `TS L` saves it in L.
2. `CA POSMAX; ADS Q` — adds 16383 to Q. Since Q points to the ADRES word (a small address), this creates overflow. When ADS overflows, it stores the overflow-corrected value (Q-1) and sets A to +1, *skipping the next instruction* via the TS-skip behavior. Wait — ADS stores to Q AND to A. Actually, `ADS Q` adds A to Q, stores result in both A and Q. The overflow causes Q to get the corrected value (the original Q minus 1, approximately), and A gets +1.

   But actually the key insight: after `ADS Q`, Q now equals the return address minus 1 (since POSMAX + small address overflows, leaving the address decremented by 1 after overflow correction). This sets up Q so that when WAITLIST does `INDEX WAITEXIT; DCA 0`, the INDEX will be off by -1 from the normal case.

3. `CA BBANK; EXTEND; ROR SUPERBNK` — reads current BBANK OR'd with superbank. This is the caller's own BBCON.
4. `XCH L` — swaps this BBCON with L (which held the delta time). Now A = delta time, L = BBCON.

Then execution falls through into WAITLIST. The `XCH Q; TS WAITEXIT` in WAITLIST saves the return address. The `INDEX WAITEXIT; DCA 0` — because TWIDDLE adjusted Q to point one word earlier, this picks up the single ADRES word (into A) and the following word (the RELINT, which becomes a don't-care in L — actually, L already has the BBCON from TWIDDLE's setup).

Actually, let me re-examine. The `TS` skip in WAITLIST's line `-1 TS WAITADR` is labeled `-1`, meaning it's address WAITADR-1... No, the label `-1` is just a relative label. Let me re-read:

```agc
                INDEX   WAITEXIT        # IF TWIDDLING, THE TS SKIPS TO HERE
                DCA     0               # PICK UP 2CADR OF TASK.
 -1             TS      WAITADR
```

The comment "IF TWIDDLING, THE TS SKIPS TO HERE" on the INDEX line is explaining that when coming from TWIDDLE, the `TS L` in TWIDDLE doesn't skip (no overflow from storing a delay time), so TWIDDLE falls through normally. The actual mechanism is that TWIDDLE has already set up A with the delta time and L with the BBCON, so when WAITLIST's code runs, everything is correctly positioned.

### Bank Switching and the Core Insertion Logic

```agc
DLY2            CAF     WAITBB          # ENTRY FROM FIXDELAY AND VARDELAY.
                XCH     BBANK
                TCF     WAIT2
```

This switches to the bank containing WAIT2 (Bank 01), saving the caller's BBANK.

```agc
WAIT2           TS      WAITBANK        # BBANK OF CALLING PROGRAM.
                CA      Q
                EXTEND
                BZMF    WAITPOOH
```

Saves the caller's bank. Checks if delta time (in Q) is zero or negative — if so, branches to WAITPOOH (error handler).

### The TIME3 Race Condition Check

```agc
                CS      TIME3
                AD      BIT8            # BIT 8 = OCT 200
                CCS     A               # TEST 200 - C(TIME3).
```

This is the most subtle part of the insertion code. It handles a race condition: TIME3 might overflow *between* the time we read it and the time we update it. The code tests whether TIME3 is less than 200 (octal). If TIME3 < 200, it probably just overflowed and its value represents `T - T1` (time since the last task was due) rather than `1.0 - (T1 - T)`.

The four-way CCS branch handles both cases:

```agc
                AD      OCT40001        # OVERFLOW HAS OCCURRED. SET C(A) =
                CS      A               # T - T1 + 1.0 - 201

                AD      OCT40201
                AD      Q               # RESULT = TD - T1 + 1.
```

After this arithmetic (which I'll spare the full trace — it's carefully constructed to yield the same result regardless of the race), A contains `TD - T1 + 1`, where TD is the desired firing time and T1 is the currently-scheduled first task's time.

### The Insertion Search: WTLST5

```agc
                CCS     A               # TEST TD - T1 + 1.

                AD      LST1            # IF TD - T1 POS, GO TO WTLST5 WITH
                TCF     WTLST5          # C(A) = (TD - T1) + C(LST1) = TD-T2+1

                NOOP
                CS      Q
```

If TD > T1 (new task fires after the current first task), we enter WTLST5 — the sorted insertion search.

If TD ≤ T1 (new task fires BEFORE the current first task), we take the lower branch: the new task becomes the new first task, TIME3 is updated, and the old first task gets pushed into the list.

**WTLST5 — The Unrolled Search Loop:**

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

This is a fully unrolled binary-search-like scan. Each block:
1. Tests `TD - T(n) + 1` via CCS.
2. If positive (TD > T(n)): adds the next LST1 delta, computing `TD - T(n+1) + 1`, and continues to the next block.
3. If zero or negative (TD ≤ T(n)): the insertion point is found. Calls `TC WTLST2` with the index following as an inline constant.

The unrolling eliminates loop overhead — critical in a system where every instruction takes 11.72µs and you're running inside INHINT. Nine iterations × 6 words each = 54 words of ROM, but guaranteed worst-case timing.

### WTLST2: The Actual Insertion

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

This modifies the LST1 entry *before* the insertion point. The old value was `-(T(n+1) - T(n)) + 1`. After adding `-(TD - T(n+1)) + 1`, the result is `-(TD - T(n)) + 1` — the new delta from T(n) to TD.

```agc
                CS      WAITTEMP
                INDEX   Q
                TCF     WTLST4
```

Then falls into WTLST4 with A = `-(T(n+1) - TD) + 1` — the delta from TD to T(n+1), which becomes the new entry inserted after TD.

### The XCH/DXCH Rotation Chain: WTLST4

```agc
WTLST4          XCH     LST1
                XCH     LST1 +1
                ...
                XCH     LST1 +7
```

Starting from the INDEX'd entry point (INDEX Q; TCF WTLST4 jumps into the *middle* of this chain), each XCH pushes the current A value into the slot and picks up the old value, cascading everything down. The INDEX causes entry at position Q within the chain, so only entries at and below the insertion point are shifted.

The same pattern repeats for LST2 with DXCH (double exchange), shifting the 2CADR entries:

```agc
                CA      WAITADR
                INDEX   Q
                TCF     +1

                DXCH    LST2
                DXCH    LST2 +2
                ...
                DXCH    LST2 +16D
```

The INDEX Q; TCF +1 causes a jump into the middle of the DXCH chain at the correct position.

### Overflow Check

```agc
                DXCH    LST2 +16D
                AD      ENDTASK
                EXTEND
                BZF     LVWTLIST        # SUCCESS
                TCF     WTABORT         # OVERFLOW — ALARM 1203
```

After the cascade, whatever was displaced from LST2+16 (the last slot) should be ENDTASK. Since ENDTASK is in fixed-fixed memory, `AD ENDTASK` adds the ENDTASK constant to the displaced address. If they're complements (meaning the displaced value WAS ENDTASK), the result is ±0, and BZF branches to the success return. If not, a real task was displaced — the list is full.

### Return to Caller

```agc
LVWTLIST        DXCH    WAITEXIT
                AD      TWO
                DTCB
```

Loads the saved return address and bank info. `AD TWO` skips past the 2CADR (2 words) to reach L+3 — the instruction after the 2CADR in the caller's code. `DTCB` (DXCH Z) jumps there with banks restored.

---

## 4. FIXDELAY, VARDELAY, and LONGCALL

### FIXDELAY: Inline Delay Constant

```agc
FIXDELAY        INDEX   Q               # BOTH ROUTINES MUST BE CALLED UNDER
                CAF     0               # WAITLIST CONTROL AND TERMINATE THE TASK
                INCR    Q               # IN WHICH THEY WERE CALLED.
```

Called from within a running task (which is in interrupt context). Q points to the return address — which the programmer has placed a delay constant at. `INDEX Q; CAF 0` loads that constant. `INCR Q` advances Q past the constant so the task resumes at the right point.

Falls through to VARDELAY.

### VARDELAY: Delay Value in A

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

This builds a self-referential WAITLIST call: the "task" being scheduled is the *continuation* of the current task (Q holds the return address, which becomes WAITADR). The current BBANK+superbank is captured as the BBCON. WAITEXIT is set to DELAYEX (`TCF TASKOVER -2`), so after the task is inserted into the wait list, control goes to TASKOVER instead of returning to a caller.

Usage pattern:
```agc
MYTASK          ...                     # Do some work
                CA      DT100MS         # 100ms delay
                TC      VARDELAY        # Reschedule self
                ...                     # Continues here after delay
                TC      TASKOVER        # Done
```

Or with FIXDELAY:
```agc
MYTASK          ...                     # Do some work
                TC      FIXDELAY
                DEC     100             # 1 second delay (100 centiseconds)
                ...                     # Continues here after delay
                TC      TASKOVER
```

### LONGCALL: Beyond 162.5 Seconds

The maximum WAITLIST delay is 16250 centiseconds (162.5 seconds), limited by the 14-bit magnitude of a single-precision value. LONGCALL extends this to approximately 2.56 hours using an iterative approach.

```agc
LONGCALL        DXCH    LONGTIME        # OBTAIN THE DELTA TIME
```

Called with a double-precision delta time in A,L (scaled as TIME2,TIME1 — the high word in A, low word in L). The 2CADR of the target task follows inline.

```agc
LONGCYCL        EXTEND                  # CAN WE SUCCESFULLY TAKE ABOUT 1.25
                DCS     DPBIT14         # MINUTES OFF OF LONGTIME
                DAS     LONGTIME
```

Each iteration subtracts BIT14 (octal 20000 = 8192 decimal in the low word, with 0 in the high word) from LONGTIME. BIT14 in centiseconds = 81.92 seconds ≈ 1.37 minutes.

```agc
                CCS     LONGTIME +1     # THE REASONING BEHIND THIS PART IS
                TCF     MUCHTIME        # INVOLVED...
                NOOP                    # CAN'T GET HERE
                TCF     +1
                CCS     LONGTIME
                TCF     MUCHTIME
```

If significant time remains (LONGTIME still positive after subtraction), branch to MUCHTIME:

```agc
MUCHTIME        CA      BIT14           # WE HAVE OVER OUR ABOUT 1.25 MINUTES
                TC      WAITLIST        # SO SET UP FOR ANOTHER CYCLE THROUGH HERE
                EBANK=  LST1
                2CADR   LONGCYCL

                TCF     LONGRTRN        # NOW EXIT PROPERLY
```

This schedules LONGCYCL itself as a WAITLIST task with an 81.92-second delay. When it fires, it subtracts another BIT14 from LONGTIME and repeats until the remaining time fits in a single WAITLIST call.

```agc
LASTTIME        CA      BIT14           # GET BACK THE CORRECT DELTA T FOR WAITLIST
                ADS     LONGTIME +1
                TC      WAITLIST
                EBANK=  LST1
                2CADR   GETCADR         # THE ENTRY TO OUR LONGCADR
```

When the remaining time is small enough, adds back the last BIT14 subtraction (since we subtracted one too many), and schedules GETCADR — which simply loads the saved LONGCADR and jumps to the actual target task.

### Timing Constraints Summary

| Parameter | Value | Notes |
|-----------|-------|-------|
| Minimum delay | 1 centisecond (10ms) | One TIME3 tick |
| Maximum WAITLIST delay | 16250 centiseconds (162.5 sec) | `DTMAX` per header |
| Maximum LONGCALL delay | ~2^28 × 10ms ≈ 31 days | DP counter range |
| Practical LONGCALL max | ~2.56 hours | Limited by mission timeline |
| Timer resolution | 10ms (TIME3 tick rate) | Hardware-determined |
| Insertion time (worst case) | ~147µs + counter increments | Per header analysis |

---

## 5. Timing Analysis

### The Hand-Written WCET Analysis

The module header (pages 1117-1118) contains a remarkably modern worst-case execution time (WCET) analysis:

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

Breaking this down:

- **147µs setup time (TS):** The time from `TC WAITLIST` to completing the list insertion. At 11.72µs per MCT, this is ~12.5 instructions — consistent with the critical path through WAITLIST → WAIT2 → insertion.

- **X (counter variance):** TIME3 ticks every 10ms. The task's actual start time is quantized to the nearest 10ms boundary. X represents the sub-tick variance — how far into a 10ms period the insertion happened.

- **Y (interrupt inhibit time):** If interrupts are inhibited (by INHINT) when T3RUPT fires, the dispatch is delayed until RELINT. This is the most significant source of jitter in practice — a long INHINT section elsewhere in the code directly delays all Waitlist tasks.

- **Z (task queue drain time):** If multiple tasks are due simultaneously (RUPTAGN cascade), earlier tasks must complete before later ones start. Usually zero because simultaneous-due tasks are rare.

- **1.05ms (Waitlist processing):** The T3RUPT handler's own execution time — the LST1/LST2 rotation chains, TIME3 update, and DTCB dispatch. At ~90 instructions × 11.72µs ≈ 1.05ms.

- **Counters:** Unprogrammed sequences (PINC, MINC, etc.) steal CPU cycles for counter updates. Each takes 1 MCT (11.72µs), and multiple counters may need servicing.

### Real-Time Guarantees

The Waitlist provides **soft real-time** guarantees with bounded worst-case jitter:

1. **Deterministic insertion:** The unrolled search loop has fixed worst-case timing regardless of list occupancy (always traverses all 9 slots).

2. **Bounded dispatch latency:** Task dispatch occurs within one T3RUPT handler execution of the scheduled time, plus any INHINT delays from foreground code.

3. **No priority inversion:** Tasks execute in strict time order. There is no concept of task priority within the Waitlist — only the Executive has priorities.

4. **Atomic list operations:** All list manipulations run with interrupts inhibited (INHINT at entry, running within the ISR for dispatch). No concurrent modification is possible.

5. **Guaranteed overflow detection:** The ENDTASK sentinel check ensures list overflow is always detected and aborted (alarm 1203) rather than silently corrupting data.

### Comparison to Modern RTOS Timer Systems

| Aspect | AGC Waitlist | Modern RTOS (e.g., FreeRTOS) |
|--------|-------------|------------------------------|
| **Data structure** | Sorted array, linear insertion | Typically a delta list or timer wheel |
| **Insertion complexity** | O(n) worst case, n=9 max | O(1) to O(log n) depending on structure |
| **Dispatch complexity** | O(1) — always the first entry | O(1) — head of queue |
| **Timer resolution** | 10ms (hardware-fixed) | Configurable (typically 1ms or less) |
| **Max pending timers** | 9 (compile-time fixed) | Dynamic (heap-allocated) |
| **Overflow handling** | Hard abort (alarm 1203) | Typically returns error code |
| **Memory cost** | 27 words fixed | Per-timer overhead, heap fragmentation risk |
| **Cascade dispatch** | RUPTAGN loop for simultaneous tasks | Typically processes all expired in one ISR |
| **Long delays** | LONGCALL (iterative rescheduling) | 32/64-bit timers, no workaround needed |
| **Jitter sources** | INHINT sections, counter servicing | Interrupt latency, higher-priority ISRs |

The AGC Waitlist's most striking characteristic is its extreme economy. The entire scheduler — insertion, dispatch, cascading, overflow detection, self-rescheduling, and long-delay support — fits in under 200 words of ROM. The sorted delta-list approach with fixed-size arrays was optimal for the constraints: a tiny number of tasks (never more than 9), hard real-time requirements, and an absolute premium on memory.

Modern timer wheels and hierarchical timing facilities are designed for thousands of concurrent timers. The AGC never needed that scale — 9 tasks were sufficient because the entire system was designed from the ground up with that constraint in mind. Every subsystem knew exactly how many Waitlist slots it could consume, and the total was verified by static analysis during development.

The WCET analysis in the header — written by hand in 1966 — anticipates techniques that wouldn't be formalized in real-time systems research until the 1980s. The MIT Instrumentation Lab engineers were doing what we'd now call schedulability analysis, by hand, in assembler, for a one-off computer architecture, with a margin of error measured in microseconds. The Waitlist is perhaps the most elegant piece of real-time systems engineering in the entire AGC codebase.