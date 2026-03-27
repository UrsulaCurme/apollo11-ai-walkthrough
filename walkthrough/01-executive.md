# The Executive: Apollo 11's Operating System in ~500 Lines

## How the Lunar Module's Job Scheduler Works, Instruction by Instruction

The Apollo Guidance Computer had no operating system. No kernel, no scheduler binary, no process table managed by privileged code. Instead, the **Executive** module — roughly 600 lines of hand-written AGC4 assembly — implemented the entire cooperative multitasking system from scratch. Every job that ran on the LM's computer during the Apollo 11 mission — guidance equations, autopilot calculations, display updates, astronaut key handling — was created, scheduled, suspended, and destroyed by this code.

This is a line-by-line walkthrough of `Luminary099/EXECUTIVE.agc`, the job scheduler that ran on the Lunar Module during the first Moon landing.

---

## 1. Core Data Structures

### 1.1 What Is a "Core Set"?

The Executive manages jobs using **core sets** — fixed-size blocks of erasable memory that serve as the AGC's equivalent of a process control block (PCB). Each core set holds everything needed to suspend and resume a job.

The number of core sets is defined at line ~154 (page 1106):

```agc
NO.CORES	DEC	7
```

There are **7 core sets**, numbered 0–6. Core set 0 is special: it represents the **currently running job**. Its registers (`PRIORITY`, `LOC`, `MPAC`, `PUSHLOC`, etc.) are accessed directly at their base addresses. The other 6 core sets are accessed via an offset stored in `LOCCTR`.

Each core set occupies 12 consecutive erasable memory words, as defined by `COREINC`:

```agc
COREINC		DEC	12		# 12 REGISTERS PER CORE SET.
```

### 1.2 Core Set Fields

Each 12-word core set contains:

| Offset | Register | Purpose |
|--------|----------|---------|
| 0 | `PRIORITY` | Job priority + VAC area pointer (low 9 bits) |
| 1 | `LOC` | Job's current execution address (FCADR). Sign encodes job type |
| 2 | `BANKSET` | Bank register state (BBANK + superbank) for resuming the job |
| 3–10 | `MPAC` through `MPAC+7` | Multi-purpose accumulator — 8 words of working storage |
| 11 | `PUSHLOC` | Interpreter push-down pointer. Sign encodes overflow state |

The core sets for jobs 1–6 are laid out consecutively in erasable memory, each starting 12 words after the previous one. The `INDEX LOCCTR` pattern used throughout the code accesses the correct core set by adding the relative offset to the base address.

### 1.3 The PRIORITY Register: Three States in One Word

The `PRIORITY` register is the heart of the Executive's state machine. It encodes three distinct job states using the sign conventions of 1's-complement arithmetic:

| Value | State | Meaning |
|-------|-------|---------|
| **Positive (>0)** | Active | Job is ready to run. The magnitude encodes the priority level |
| **Negative (<-0)** | Sleeping | Job is waiting for an event. The complement of the priority is preserved |
| **Negative zero (-0)** | Free | Core set is available for allocation |

This encoding is elegant because the `CCS` (Count, Compare, and Skip) instruction naturally distinguishes all three states with its 4-way skip:

```agc
		CCS	PRIORITY	# (page 1106, line ~153)
		TCF	NEXTCORE	# POSITIVE: active job, skip this core set
NO.CORES	DEC	7		# +0: (falls through — never happens for PRIORITY)
		TCF	NEXTCORE	# NEGATIVE: sleeping job, skip this core set
					# -0: falls through to CORFOUND — free core set!
```

The `CCS` instruction does the following: it loads `DABS(K)` into A (the "diminished absolute value" — the absolute value minus one), then performs a 4-way skip based on the original value's sign and zero-ness. When `PRIORITY` is -0 (all ones, `77777` octal), the code falls through to `CORFOUND`, signaling that this core set is available.

### 1.4 VAC Areas

The low 9 bits of `PRIORITY` store a pointer to the job's **VAC area** — a block of erasable memory used as a scratchpad by interpretive (math-heavy) jobs. There are 5 VAC areas, tracked by use-registers `VAC1USE` through `VAC5USE`:

```agc
FINDVAC2	TS	EXECTEM1
		CCS	VAC1USE		# (page 1106)
		TCF	VACFOUND
		CCS	VAC2USE
		TCF	VACFOUND
		CCS	VAC3USE
		TCF	VACFOUND
		CCS	VAC4USE
		TCF	VACFOUND
		CCS	VAC5USE
		TCF	VACFOUND
```

This is a linear scan — try VAC1, then VAC2, and so on. If all 5 are taken, the code falls through to a `BAILOUT1` with alarm code `1201`:

```agc
		TC	BAILOUT1
		OCT	1201		# NO VAC AREAS.
```

**This is the origin of the famous 1202 alarm.** During the Apollo 11 landing, a hardware interrupt from the rendezvous radar was consuming enough CPU time that the Executive's core sets filled up, triggering alarm 1202 (the "no core sets" variant — see below). The Executive's design allowed it to recover gracefully: lower-priority jobs were shed while critical guidance continued.

---

## 2. Job Creation: FINDVAC and NOVAC

### 2.1 The Two Entry Points

The Executive provides two ways to create a job:

- **`FINDVAC`** (page 1103): Creates a job that needs a VAC area. Used for interpretive (math-heavy) jobs that require the interpreter's scratchpad.
- **`NOVAC`** (page 1103): Creates a job that does NOT need a VAC area. Used for basic (native assembly) jobs.

Both expect:
- The **priority** of the new job in the accumulator (A register)
- The **2CADR** (double-word address: FCADR + BBCON) of the job's entry point immediately following the calling instruction in memory

### 2.2 Tracing NOVAC Step by Step

```agc
NOVAC		INHINT			# Disable interrupts — we're modifying shared state
		AD	FAKEPRET	# Add offset: LOC(MPAC+6) - LOC(QPRET)
		TS	NEWPRIO		# Store priority (with NOVAC flag encoded)

		EXTEND
		INDEX	Q		# Q holds caller's return address
		DCA	0		# Load 2CADR from the two words after the TC NOVAC call
		DXCH	NEWLOC		# Store the job's entry address in NEWLOC, NEWLOC+1
		CAF	EXECBANK	# Load the CADR of the Executive's bank
		XCH	FBANK		# Switch to Executive's fixed bank, save caller's bank
		TS	EXECTEM1	# Save caller's bank for later restoration
		TCF	NOVAC2		# Jump into the Executive's switched bank
```

Key details:

1. **`INHINT`** disables interrupts immediately. Job creation modifies shared data structures (priority registers, core sets) and must be atomic.

2. **`AD FAKEPRET`** adds an offset to the priority value. `FAKEPRET` is defined as `ADRES MPAC -36D`, which equals `LOC(MPAC+6) - LOC(QPRET)`. This encodes a flag in the priority word that distinguishes NOVAC jobs from FINDVAC jobs — specifically, the low 9 bits will indicate "no VAC area" rather than pointing to a VAC area base address.

3. **`INDEX Q` / `DCA 0`**: This is a critical AGC idiom. The `TC NOVAC` instruction that called us stored the return address in Q. The two words *after* the `TC NOVAC` in the caller's code contain the 2CADR (double-word complete address) of the new job. `INDEX Q` modifies the next instruction by adding Q's value to the address field of `DCA 0`, effectively making it `DCA Q` — loading the two words at and after Q into A and L. Then `DXCH NEWLOC` stores them.

4. **Bank switching**: The Executive's core logic lives in Bank 01 (switched fixed memory), but the entry points (`NOVAC`, `FINDVAC`, etc.) live in Block 02 (fixed-fixed memory, directly addressable from anywhere). The `XCH FBANK` / `TCF NOVAC2` sequence switches to the Executive's bank.

### 2.3 Tracing FINDVAC Step by Step

```agc
FINDVAC		INHINT			# Disable interrupts
		TS	NEWPRIO		# Store priority directly (no FAKEPRET offset)
		EXTEND
		INDEX	Q
		DCA	0		# Load 2CADR of job entry point
SPVACIN		DXCH	NEWLOC		# Store in NEWLOC
		CAF	EXECBANK
		XCH	FBANK		# Switch to Executive's bank
		TCF	FINDVAC2	# Jump to VAC area allocation code
```

The key difference from NOVAC: **no `AD FAKEPRET`**. The priority is stored directly, and control transfers to `FINDVAC2` instead of `NOVAC2`. `FINDVAC2` first scans for a free VAC area (the `CCS VAC1USE` ... chain shown above), then falls through to the same core set allocation code that `NOVAC2` uses.

### 2.4 VAC Area Allocation (VACFOUND)

When a free VAC area is found:

```agc
VACFOUND	AD	TWO		# CCS left DABS(VACnUSE) in A; add 2 to get
		ZL			#   the address of the VAC area's first word
		INDEX	A		# Use that address as an index
		LXCH	0 	-1	# Exchange L (zero) with VACnUSE — zeroing
					#   the use register marks it as "in use"
		ADS	NEWPRIO		# Add VAC area address into low 9 bits of priority
```

This is a beautiful piece of code density. The `CCS` instruction that found the free VAC area left `DABS(VACnUSE)` — the diminished absolute value — in A. Adding 2 recovers the original address (CCS decrements by 1, and we need the base of the VAC area, not the use-register itself). Then `LXCH 0 -1` simultaneously zeroes the use-register (marking it allocated) and grabs the old value. Finally, `ADS NEWPRIO` packs the VAC area address into the low 9 bits of the priority word.

### 2.5 Core Set Allocation (NOVAC2 / NOVAC3)

After VAC area allocation (or directly for NOVAC jobs), the code scans for a free core set:

```agc
NOVAC2		CAF	ZERO		# Start scanning from core set 0
		TS	LOCCTR		# LOCCTR = offset to current core set
		CAF	NO.CORES	# Loop counter = 7
NOVAC3		TS	EXECTEM2	# Save loop counter
		INDEX	LOCCTR
		CCS	PRIORITY	# Check this core set's priority register
		TCF	NEXTCORE	# Positive: active job, try next
NO.CORES	DEC	7		# (constant embedded in the CCS skip chain)
		TCF	NEXTCORE	# Negative: sleeping job, try next
					# -0: free! Fall through to CORFOUND
```

The loop increments `LOCCTR` by `COREINC` (12) for each core set:

```agc
NEXTCORE	CAF	COREINC		# 12 registers per core set
		ADS	LOCCTR		# Move to next core set
		CCS	EXECTEM2	# Decrement and test loop counter
		TCF	NOVAC3		# More core sets to check
		...
		TC	BAILOUT1	# NO CORE SETS AVAILABLE.
		OCT	1202		# <<< THE FAMOUS 1202 ALARM
```

If all 7 core sets are occupied, alarm **1202** fires. This is the alarm that sounded during the Apollo 11 landing. The Executive couldn't find a free core set because the rendezvous radar (which should have been off) was generating interrupts that spawned jobs faster than they could complete.

### 2.6 Core Set Initialization (CORFOUND)

When a free core set is found:

```agc
CORFOUND	CA	NEWPRIO		# Load the new job's priority
		INDEX	LOCCTR		# Index into the found core set
		TS	PRIORITY	# Set its priority register
		MASK	LOW9		# Extract low 9 bits (VAC area pointer)
		INDEX	LOCCTR
		TS	PUSHLOC		# Set the push-down pointer for the interpreter
```

Then a critical check — is this core set 0 (the "run" position)?

```agc
		CCS	LOCCTR		# If LOCCTR = 0, we're loading core set 0
		TCF	SETLOC		# Non-zero: normal setup
		TS	OVFIND		# Zero: set up OVFIND and FIXLOC immediately
		CA	PUSHLOC		#   because this job runs NOW
		TS	FIXLOC
```

### 2.7 Priority Comparison (SETLOC)

If the new job was placed in a non-zero core set, the Executive must determine whether it should preempt the current job:

```agc
SETLOC		DXCH	NEWLOC		# Store entry address in the core set's LOC registers
		INDEX	LOCCTR
		DXCH	LOC
		INDEX	NEWJOB		# NEWJOB points to highest-waiting-priority core set
		CS	PRIORITY	# Negate that priority
		AD	NEWPRIO		# Add new priority: result > 0 means new is higher
		EXTEND
		BZMF	ENDFIND		# If new ≤ current highest, don't preempt
		CA	LOCCTR		# New job IS higher priority:
		TS	NEWJOB		# Set NEWJOB to point to the new core set
		TCF	ENDFIND
```

This is the scheduling decision. `NEWJOB` is a global variable that always points to the highest-priority waiting job. When a newly created job has higher priority than whatever `NEWJOB` currently references, `NEWJOB` is updated. The actual context switch happens later, when the running job voluntarily yields via `CHANG1`/`CHANG2`.

---

## 3. Scheduling and Context Switching

### 3.1 The Role of NEWJOB

`NEWJOB` is the Executive's central scheduling variable. It can hold three values:

| Value | Meaning |
|-------|---------|
| **Positive** | Offset to a core set that has higher priority than the running job |
| **+0** | The currently running job (core set 0) IS the highest priority |
| **-0** | No active jobs exist; the computer should idle |

The Executive never preempts a running job. Instead, it sets `NEWJOB` and waits for the running job to voluntarily check it. This is **cooperative multitasking** — jobs must explicitly yield.

### 3.2 Voluntary Yielding: CHANG1 and CHANG2

A job yields by calling either:

- **`CHANG1`** (page 1103): For basic (native assembly) jobs
- **`CHANG2`** (page 1103): For interpretive jobs

```agc
# Basic job yield:
CHANG1		LXCH	Q		# Save return address in L
		CAF	EXECBANK	# Load Executive's bank address
		XCH	BBANK		# Switch to Executive's bank, save current bank
		TCF	CHANJOB		# Enter the context switch routine

# Interpretive job yield:
CHANG2		CS	LOC		# Negate LOC — negative LOC signals "interpretive"
		TS	L
 +2		CAF	EXECBANK
		TS	BBANK
		TCF	CHANJOB -1
```

The sign of `LOC` is critical: **positive LOC = basic job, negative LOC = interpretive job**. This is how the Executive knows which dispatch mechanism to use when resuming the job.

### 3.3 The Context Switch (CHANJOB)

The `CHANJOB` routine (pages 1108–1109) is the heart of the Executive. It swaps every register in core set 0 with the core set pointed to by `NEWJOB`:

```agc
CHANJOB		INHINT			# Disable interrupts during the swap
		EXTEND
		ROR	SUPERBNK	# Pick up current superbank for BBCON
		XCH	L		# LOC in A, BBCON in L
 +4		INDEX	NEWJOB
		DXCH	LOC		# Swap LOC and BANKSET between core set 0
		DXCH	LOC		#   and the NEWJOB core set
```

Then the 8-word MPAC area is swapped, two words at a time using `DXCH`:

```agc
		DXCH	MPAC		# Swap MPAC+0,+1
		INDEX	NEWJOB
		DXCH	MPAC
		DXCH	MPAC
		DXCH	MPAC +2		# Swap MPAC+2,+3
		INDEX	NEWJOB
		DXCH	MPAC +2
		DXCH	MPAC +2
		DXCH	MPAC +4		# Swap MPAC+4,+5
		INDEX	NEWJOB
		DXCH	MPAC +4
		DXCH	MPAC +4
		DXCH	MPAC +6		# Swap MPAC+6,+7
		INDEX	NEWJOB
		DXCH	MPAC +6
		DXCH	MPAC +6
```

This is a **three-way DXCH swap** pattern. Each group of three `DXCH` instructions works like this:
1. `DXCH MPAC` — loads core set 0's MPAC into A,L while storing A,L (which held something from a previous swap) into MPAC
2. `INDEX NEWJOB` / `DXCH MPAC` — swaps A,L (now core set 0's old value) with the new job's MPAC
3. `DXCH MPAC` — stores the new job's old MPAC value into core set 0

The result: core set 0 now has the new job's MPAC values, and the NEWJOB core set has the old job's values.

### 3.4 Overflow Flag Handling

After the MPAC swap, the code handles the `OVFIND` / `PUSHLOC` state — the interpreter's overflow indicator is encoded in the sign of `PUSHLOC`:

```agc
		CAF	ZERO
		XCH	OVFIND		# Get current overflow flag, clear it
		EXTEND
		BZF	+3		# If zero, skip
		CS	PUSHLOC		# If non-zero, negate PUSHLOC
		TS	PUSHLOC		#   (negative PUSHLOC = overflow was set)

		DXCH	PUSHLOC		# Swap PUSHLOC and PRIORITY
		INDEX	NEWJOB
		DXCH	PUSHLOC
		DXCH	PUSHLOC
```

Then FIXLOC is restored and the overflow flag is decoded from the incoming PUSHLOC:

```agc
		CAF	LOW9		# Extract VAC area pointer
		MASK	PRIORITY
		TS	FIXLOC		# Set FIXLOC for the new job

		CCS	PUSHLOC		# Check sign of incoming PUSHLOC
		CAF	ZERO		# Positive: no overflow
		TCF	ENDPRCHG -1	# (skip to dispatch)
		CS	PUSHLOC		# Negative: overflow was set
		TS	PUSHLOC		#   un-negate PUSHLOC
		CAF	ONE		#   set OVFIND = 1
		XCH	OVFIND
		TS	NEWJOB		# (NEWJOB gets the old OVFIND value — effectively resets)
```

### 3.5 Job Dispatch (ENDPRCHG)

The final step dispatches the new job:

```agc
ENDPRCHG	RELINT			# Re-enable interrupts
		DXCH	LOC		# Load job's address into A,L
		EXTEND
		BZMF	+2		# If LOC is negative, job is interpretive
		DTCB			# Positive LOC: basic job — DTCB dispatches
					#   (DTCB = DXCH Z, jumps to address in A,L
					#    while switching both banks)
```

For interpretive jobs:

```agc
		COM			# Negate the (negative) LOC
		AD	ONE		# Add 1 to get the true address
		TS	LOC		# Store it back
		TCF	INTRSM		# Jump to interpreter resume routine
```

The `DTCB` instruction (`DXCH Z`) is remarkably compact — it simultaneously loads the program counter (Z) and bank registers from A and L, effectively performing a full far-jump with bank switching in a single instruction.

### 3.6 The Priority Scan (EJSCAN)

When a job ends or sleeps, the Executive must find the highest-priority active job. `EJSCAN` (pages 1113–1115) performs a linear scan of all 7 core sets' `PRIORITY` registers:

```agc
EJSCAN		CCS	PRIORITY +12D	# Core set 1 (offset 12 from base)
		TC	EJ1		# If positive (active), evaluate priority
		TC	CCSHOLE		# +0: shouldn't happen
		TCF	+1		# Negative or -0: skip

		CCS	PRIORITY +24D	# Core set 2 (offset 24)
		TC	EJ1
		TC	CCSHOLE
		TCF	+1

		CCS	PRIORITY +36D	# Core set 3
		TC	EJ1
-CCSPR		-CCS	PRIORITY	# (This label stores -CCS PRIORITY for address calc)
		TCF	+1

		CCS	PRIORITY +48D	# Core set 4
		...
		CCS	PRIORITY +60D	# Core set 5
		...
		CCS	PRIORITY +72D	# Core set 6
		...
		CCS	PRIORITY +84D	# Core set 7 (if it exists — note: 84/12 = 7)
```

The `EJ1` subroutine compares the current candidate against the running best:

```agc
EJ1		TS	BUF +2		# Save DABS(PRIORITY) — this is the candidate
		AD	BUF +1		# Add negative of current best (BUF+1 holds -best)
		CCS	A
		CS	BUF +2		# A > 0: new candidate is higher priority
		TCF	EJ2		# Take the new candidate
		NOOP			# A = +0 or negative: keep current best
		INDEX	Q
		TC	2		# Continue scan (skip 2 words to next CCS)
```

`EJ2` records the new best:

```agc
EJ2		TS	BUF +1		# Store -new_best_priority
		EXTEND
		QXCH	BUF		# Save Q (points back into the scan loop)
		INDEX	BUF
		TC	2		# Continue scan from where Q pointed
```

After the scan completes, `BUF` contains the Q value (instruction address) of the winning `CCS PRIORITY+nD` instruction. The code uses arithmetic on this address to compute the core set offset:

```agc
		INDEX	A
		CAF	0 -1		# Load the instruction at BUF-1
		AD	-CCSPR		# Subtract the base address (-CCS PRIORITY)
		TS	NEWJOB		# Result = offset to the winning core set
		TCF	CHANJOB -2	# Perform the context switch
```

This is an extraordinary trick: the scan loop's own instruction addresses encode the core set offsets. By subtracting a known reference point (`-CCSPR`), the code recovers which core set won — without needing a separate data structure.

---

## 4. Job Lifecycle

### 4.1 Job Sleep (JOBSLEEP)

A job voluntarily sleeps by calling `JOBSLEEP` with its wake-up address in A:

```agc
JOBSLEEP	TS	LOC		# Save wake-up address in LOC
		CAF	EXECBANK
		TS	FBANK
		TCF	JOBSLP1		# Switch to Executive's bank
```

In the Executive's bank:

```agc
JOBSLP1		INHINT			# Disable interrupts
		CS	PRIORITY	# Negate the priority
		TS	PRIORITY	# Negative priority = sleeping job
		CAF	LOW7
		MASK	BBANK
		EXTEND
		ROR	SUPERBNK	# Save current bank state
		TS	BANKSET
		CS	ZERO		# Load -0
JOBSLP2		TS	BUF +1		# Initialize best-priority to -0 (worst)
		TCF	EJSCAN		# Scan for highest priority active job
```

The sleeping job's priority is negated — this is how the Executive marks a job as sleeping. The scan then finds the next highest-priority active job to run.

### 4.2 Job Wake (JOBWAKE)

To wake a sleeping job, the caller provides the CADR of the sleeping job's `LOC` value in A:

```agc
JOBWAKE		INHINT
		TS	NEWLOC		# Save the CADR to match against
		CS	TWO		# Adjust Q to point past the 2CADR that follows
		ADS	Q
		CAF	EXECBANK
		XCH	FBANK
		TCF	JOBWAKE2
```

`JOBWAKE2` scans all core sets for a sleeping job whose `LOC` matches:

```agc
JOBWAKE2	TS	EXECTEM1
		CAF	ZERO
		TS	LOCCTR		# Start at core set 0
		CAF	NO.CORES
JOBWAKE4	TS	EXECTEM2
		INDEX	LOCCTR
		CCS	PRIORITY
		TCF	JOBWAKE3	# Active job — skip
COREINC		DEC	12
		TCF	WAKETEST	# Sleeping job — check if it matches
```

The match test:

```agc
WAKETEST	CS	NEWLOC
		INDEX	LOCCTR
		AD	LOC		# Compare LOC with target CADR
		EXTEND
		BZF	+2		# If they match (difference = ±0), wake it
		TCF	JOBWAKE3	# No match, try next core set
```

When a match is found, the priority is un-negated (re-complemented to positive) and the job re-enters the scheduling system:

```agc
		INDEX	LOCCTR
		CS	PRIORITY	# Re-complement: negative → positive
		TS	NEWPRIO
		INDEX	LOCCTR
		TS	PRIORITY	# Job is now active again
```

The code then reconstructs the full 2CADR (address + bank state) from the stored LOC and BANKSET values before calling into `SETLOC` to check if the woken job should preempt the current one.

If no matching sleeping job is found, `LOCCTR` is set to -1 as a signal to the caller:

```agc
		CS	ONE
		TS	LOCCTR		# -1 means "job not found"
		TCF	ENDFIND
```

### 4.3 Job Termination (ENDOFJOB)

A job terminates by calling `ENDOFJOB`:

```agc
ENDOFJOB	CAF	EXECBANK
		TS	FBANK
		TCF	ENDJOB1
```

In the Executive's bank:

```agc
ENDJOB1		INHINT
		CS	ZERO		# Load -0
		TS	BUF +1		# Initialize scan with worst priority
		XCH	PRIORITY	# Clear core set 0's priority (set to -0 = free)
		MASK	LOW9		# Extract VAC area pointer from old priority
		TS	L

		CS	FAKEPRET	# Check if this job had a VAC area
		AD	L
		EXTEND
		BZMF	EJSCAN		# No VAC area (NOVAC job) — go to scan

		CCS	L		# Has VAC area — free it
		INDEX	A
		TS	0		# Zero out the VACnUSE register
```

The VAC area deallocation is subtle: `L` contains the low 9 bits of the old priority (the VAC area address). The `CCS L` / `INDEX A` / `TS 0` sequence uses the diminished value from CCS as an index to zero the corresponding `VACnUSE` register, marking the VAC area as free.

After cleanup, `EJSCAN` finds the next job to run.

### 4.4 The Idle Loop (DUMMYJOB)

When `EJSCAN` finds no active jobs (all `BUF+1` checks fall through), control reaches `DUMMYJOB`:

```agc
DUMMYJOB	CS	ZERO		# Load -0
		TS	NEWJOB		# NEWJOB = -0 means "idle"
		RELINT			# Enable interrupts — we need them to wake us
		CS	TWO		# Turn off the activity light
		EXTEND
		WAND	DSALMOUT	# AND complement of bit 2 with DSALMOUT channel
ADVAN		CCS	NEWJOB		# Check if a new job has arrived
		TCF	NUCHANG2	# Positive: a job is waiting — switch to it
		CAF	TWO		# +0: current job (core set 0) is ready
		TCF	NUDIRECT	# Execute it directly
```

If NEWJOB is -0 (no jobs), the code falls through to run the **self-check** routine:

```agc
		CA	SELFRET		# Load self-check return address
		TS	L
		CAF	SELFBANK	# Load self-check bank
		TCF	SUPDXCHZ +1	# Dispatch to self-check
```

This is the AGC's idle loop: when no jobs need the CPU, it runs hardware self-tests. The self-check routine periodically re-checks `NEWJOB` (via the `ADVAN` label) and dispatches to any newly created job. The activity light (the green "COMP ACTY" indicator on the DSKY) is turned off during idle and back on when a job starts:

```agc
NUCHANG2	INHINT
		CCS	NEWJOB
		TCF	+3		# NEWJOB still positive
		RELINT			# NEWJOB changed to +0 — rare race condition
		TCF	ADVAN +2

		CAF	TWO
		EXTEND
		WOR	DSALMOUT	# Turn ON activity light
```

### 4.5 The SPVAC Entry Point

There's a third, less common entry point for job creation:

```agc
SPVAC		XCH	Q		# Caller has already set NEWPRIO and INHINT
		AD	NEG2		# Adjust Q to skip past the 2CADR
		XCH	Q
		TCF	SPVACIN		# Enter FINDVAC midstream
```

`SPVAC` is used when the caller has already stored the priority in `NEWPRIO` and disabled interrupts. It adjusts Q (the return address) backward by 2 to account for the 2CADR that follows, then jumps into `FINDVAC`'s flow after the priority setup.

### 4.6 Priority Change (PRIOCHNG)

A running job can change its own priority:

```agc
PRIOCHNG	INHINT
		TS	NEWPRIO		# New priority in A
		CAF	EXECBANK
		XCH	BBANK
		TS	BANKSET		# Save bank state
		CA	Q
		TCF	PRIOCH2
```

In `PRIOCH2`:

```agc
PRIOCH2		TS	LOC		# Save return address
		CAF	ZERO
		TS	BUF		# Flag: set to 0 to indicate "priochng mode"
		CAF	LOW9
		MASK	PRIORITY	# Preserve VAC area pointer
		AD	NEWPRIO		# Combine with new priority
		TS	PRIORITY	# Update priority register
		COM			# Negate for scan comparison
		TCF	JOBSLP2		# Scan for highest priority (like sleep)
```

The scan may determine that this job, even with its new priority, is still the highest — in which case it returns immediately. Or it may find a higher-priority job and perform a context switch.

---

## 5. The SUPDXCHZ Dispatch Routine

At the bottom of the file, a utility routine for dispatching to any address with full bank switching:

```agc
SUPDXCHZ	XCH	L		# Put bank info in A, address in L
 +1		EXTEND
		WRITE	SUPERBNK	# Set the superbank from A
		TS	BBANK		# Set BBANK (which sets EB and FB) from A
		TC	L		# Jump to address in L
```

This is used by `DUMMYJOB` to dispatch to the self-check routine and by `NUDIRECT` to start jobs that are already in core set 0.

---

## 6. Modern Parallels and Surprises

### 6.1 Comparison to FreeRTOS

| Concept | Apollo Executive | FreeRTOS |
|---------|-----------------|----------|
| **Task control block** | 12-word "core set" | `TCB_t` struct (~60+ bytes) |
| **Max tasks** | 7 (compile-time fixed) | Configurable, heap-allocated |
| **Scheduling** | Cooperative only | Preemptive + cooperative |
| **Priority scan** | Linear scan of 7 registers | Linked list per priority level |
| **Context switch** | Manual register-by-register swap | Hardware-assisted (PendSV on ARM) |
| **Stack** | No stack — Q register + manual save | Per-task stack |
| **Idle task** | `DUMMYJOB` runs self-check | Configurable idle hook |
| **Task creation** | FINDVAC/NOVAC — fixed pool | `xTaskCreate` — heap allocation |
| **Sleep/wake** | JOBSLEEP/JOBWAKE — CADR matching | `vTaskDelay` / `xTaskNotify` |
| **Overload handling** | Alarm 1202, graceful degradation | Stack overflow hook, watchdog |

### 6.2 What Would Surprise a Modern Developer

**No preemption.** The Executive never forcibly takes the CPU from a running job. If a job fails to call `CHANG1`/`CHANG2`, the system hangs. Every job is trusted to yield regularly. This is cooperative multitasking in its purest form — there is no timer interrupt that forces a context switch.

**No stack.** The AGC has no hardware stack and only one return-address register (Q). The Executive doesn't create per-job stacks. Instead, each job gets a fixed 12-word core set and optionally a VAC area. Subroutine calls within a job must manually save and restore Q. This is why the interpreter exists — it provides its own call stack internally.

**The CCS instruction as the universal conditional.** Modern CPUs have dozens of conditional branch instructions. The AGC has one: `CCS`, which performs a 4-way skip based on positive/+0/negative/-0. The entire Executive is built around this — the -0 encoding for "free" core sets, the positive/negative encoding for active/sleeping jobs, and the diminished absolute value as both a test and a useful output value.

**Data embedded in the instruction stream.** `NO.CORES` (`DEC 7`) is both a constant AND occupies the "+0" skip slot of a `CCS` instruction (page 1106). Similarly, `COREINC` (`DEC 12`) sits in the "+0" slot of a CCS in the JOBWAKE scan (page 1111). This is not accidental — the programmers deliberately placed constants in CCS skip positions that would never be reached, saving precious words of memory.

**`-CCS PRIORITY` as an address label.** The label `-CCSPR` (page 1113) marks the instruction `-CCS PRIORITY` in the middle of the scan loop. This instruction is never executed — its purpose is to provide a reference address for the arithmetic that converts a scan loop position into a core set offset. The instruction's *address* is the data, not its *operation*.

**The three-`DXCH` swap pattern.** Without a hardware stack or temporary registers, swapping two memory locations requires three double-exchange instructions — the memory equivalent of the classic three-variable swap `temp = a; a = b; b = temp`, but using the A,L register pair as the temporary.

**Alarm recovery by design.** The 1202 alarm wasn't a crash — it was a designed-in overload response. When the Executive couldn't find a free core set, it called `BAILOUT1`, which displayed the alarm code on the DSKY but allowed the system to continue running. Lower-priority jobs that couldn't be scheduled were simply dropped. The guidance equations, at higher priority, kept running. This is why the Apollo 11 landing succeeded despite the alarms — the Executive's priority system ensured that the most important work always got done first.

**69 KB for everything.** The entire Executive — job creation, scheduling, context switching, sleep/wake, priority management, idle loop — fits in roughly 600 lines of assembly, occupying perhaps 400 words of fixed memory (~750 bytes). A modern RTOS kernel is typically 10,000–100,000 lines of C. The AGC team achieved this density through relentless optimization: every instruction does double duty, every constant is placed to save a word, every encoding is chosen to minimize the code that interprets it.

---

## Appendix: Key Symbols Quick Reference

| Symbol | Type | Purpose |
|--------|------|---------|
| `NEWJOB` | Erasable | Offset to highest-priority waiting core set (+0 = current, -0 = idle) |
| `NEWPRIO` | Erasable | Priority of job being created |
| `NEWLOC` | Erasable (DP) | 2CADR of job being created |
| `LOCCTR` | Erasable | Current core set offset during scans |
| `EXECTEM1` | Erasable | Saved caller bank during job creation |
| `EXECTEM2` | Erasable | Loop counter during core set scans |
| `EXECBANK` | Fixed | CADR of the Executive's bank (for switching) |
| `FAKEPRET` | Fixed | Offset marking NOVAC jobs (no VAC area) |
| `COREINC` | Fixed | Core set size: 12 words |
| `NO.CORES` | Fixed | Number of core sets: 7 |
| `LOW9` | Fixed | Mask for extracting VAC area pointer from PRIORITY |
| `OVFIND` | Erasable | Interpreter overflow indicator for current job |
| `FIXLOC` | Erasable | Base address of current job's VAC area |
| `PUSHLOC` | Erasable | Interpreter push-down pointer (sign = overflow flag when saved) |
| `BUF`, `BUF+1`, `BUF+2` | Erasable | Temporaries used during priority scan |