# Apollo 11 AGC Source Code Analysis — Phase 1 Context Prompt

_Copy this entire document into Claude Code as your initial prompt before cloning or analyzing the Apollo 11 repo._

---

## PROMPT BEGINS HERE

You are about to analyze the original Apollo 11 Guidance Computer (AGC) source code from `https://github.com/chrislgarry/Apollo-11`. This codebase is written in AGC4 assembly language — a 1960s instruction set that has almost nothing in common with modern x86, ARM, or RISC-V assembly. You MUST use the architectural reference below rather than pattern-matching against modern assembly conventions.

The goal is to produce a technically rigorous, file-by-file walkthrough of the key modules, suitable for publication as a long-form technical article targeting modern software engineers.

---

## AGC4 ARCHITECTURE REFERENCE

### Hardware Overview

- **Word length:** 15 data bits + 1 parity bit (parity is invisible to software)
- **Arithmetic:** 1's-complement (NOT 2's-complement). This means there are two representations of zero: +0 (000000000000000) and -0 (111111111111111)
- **Clock:** 2.048 MHz crystal, divided to 1.024 MHz internally. One machine cycle (MCT) = 11.72 µs
- **Erasable memory (RAM):** 2,048 words (~3.8 KB). Organized as 8 banks of 256 words (banks E0-E7)
- **Fixed memory (ROM):** 36,864 words (~69 KB). Core rope memory — physically woven, read-only. 36 banks
- **No operating system.** The software IS the system. The "Executive" and "Waitlist" modules implement cooperative multitasking from scratch
- **No hardware stack.** Only the Q register stores a return address. Nested calls require manually saving Q

### Data Representation

- **Single Precision (SP):** 15-bit 1's-complement. Bit 15 = sign. Bits 14-1 = magnitude as a FRACTION (binary point is between sign and bit 14). So bit 14 = 0.5, bit 13 = 0.25, etc.
- **Double Precision (DP):** Two consecutive SP words. First word = more significant. 28 bits of magnitude total
- **Triple Precision (TP):** Three consecutive SP words. 42 bits. Used mainly by the interpreter for time
- **Vectors:** Three consecutive DP values (x, y, z components)
- **Scaling:** Programmers must manually track where the "imaginary binary point" sits. There is no floating point. Constants in source use optional `En` (×10^n) and `Bn` (×2^n) scaling factors
- **Integers:** Written in octal (e.g., `37777`) or decimal with trailing `D` (e.g., `16383D`)

### Central Registers (Memory-Mapped)

| Address | Name | Description |
|---------|------|-------------|
| 00 | A | Accumulator. 16-bit (15 data + 1 overflow). Almost every instruction uses it |
| 01 | L | Lower product register. Paired with A for DP operations |
| 02 | Q | Return address register. Set by TC. Also holds DV remainder |
| 03 | EB | Erasable bank register (3-bit field selects which E-bank maps to 1400-1777) |
| 04 | FB | Fixed bank register (5-bit field selects which F-bank maps to 2000-3777) |
| 05 | Z | Program counter. Always points to NEXT instruction |
| 06 | BB | Both-banks register. Combines EB and FB fields |
| 07 | (zero) | Hardwired to 00000. Useful as constant source since most instructions lack immediates |

### Editing Registers (Addresses 20-23)

These auto-transform values on read/write:
- **CYR** (20): Cycle right (bit 1 wraps to bit 15)
- **SR** (21): Shift right with sign extension (divide by 2)
- **CYL** (22): Cycle left (bit 15 wraps to bit 1)
- **EDOP** (23): Shift right 7 bits, zero upper 8. Used by the interpreter to decode packed opcodes

### Counter/Timer Registers (Addresses 24-60)

- **TIME1** (25): Incremented every 10ms. Master clock
- **TIME2** (24): Incremented on TIME1 overflow. TIME1+TIME2 = 28-bit clock (~31 days)
- **TIME3** (26): 10ms counter. Overflow triggers T3RUPT → drives the Waitlist scheduler
- **TIME4** (27): 10ms counter. Overflow triggers T4RUPT → services DSKY display
- **TIME5** (30): 10ms counter. Overflow triggers T5RUPT → digital autopilot (DAP)
- **TIME6** (31): 1/1600 second counter. T6RUPT → DAP jet timing
- **CDUX/Y/Z** (32-34): IMU gimbal angles (2's-complement, 15-bit, ~40 arcseconds per count)
- **PIPAX/Y/Z** (37-41): Velocity change counters from accelerometers

### Memory Map

The memory map uses bank-switching because instructions only have 12-bit address fields:

- **0000-1377**: Unswitched erasable (directly addressable RAM, includes all registers)
- **1400-1777**: Switched erasable (selected by EB register, 8 banks)
- **2000-3777**: Common fixed (selected by FB register + superbank bit, 36 banks)
- **4000-7777**: Fixed-fixed (directly addressable ROM, always available)

Banks E0-E2 of switched erasable overlap with unswitched erasable. Banks 02-03 of common fixed overlap with fixed-fixed at 4000-7777. There is also a "superbank" bit in I/O channel 7 needed to reach banks 40-43.

### Interrupt System

11 interrupt types, vectored through a table at address 4000:

| Vector | Name | Trigger | Purpose |
|--------|------|---------|---------|
| 4000 | (boot) | Power-up/reset | Program entry point |
| 4004 | T6RUPT | TIME6→0 | DAP jet control |
| 4010 | T5RUPT | TIME5 overflow | Autopilot |
| 4014 | T3RUPT | TIME3 overflow | Waitlist task scheduler |
| 4020 | T4RUPT | TIME4 overflow | DSKY display update |
| 4024 | KEYRUPT1 | DSKY keystroke | Keyboard input |
| 4030 | KEYRUPT2 | Secondary DSKY | Navigator station (CM only) |
| 4034 | UPRUPT | Uplink word ready | Ground control data |
| 4040 | DOWNRUPT | Downlink ready | Telemetry |
| 4044 | RADAR RUPT | Radar data ready | Rendezvous/landing radar |
| 4050 | RUPT10 | Hand controller | Manual control input |

Interrupts are disabled by INHINT, enabled by RELINT. An ISR must manually save A, L, Q, BB using registers ARUPT, LRUPT, QRUPT, BBRUPT. Return via RESUME instruction.

Interrupts are deferred during: overflow in accumulator, after INDEX, during another ISR, and after INHINT.

### AGC4 Instruction Set — Basic Instructions

These are the native CPU instructions (3-bit opcode + 12-bit address):

| Mnemonic | Octal | Description |
|----------|-------|-------------|
| **TC** K | 00000+K | Transfer Control. Unconditional jump to K. Saves return address in Q. This is the subroutine call instruction |
| **CCS** K | 10000+K | Count, Compare, and Skip. Loads DABS(K) into A, then does a 4-way skip: K>0 → next, K=+0 → skip 1, K<0 → skip 2, K=-0 → skip 3. The primary conditional branch |
| **INDEX** K | 50000+K | Adds the value at K to the NEXT instruction before executing it. Used for array indexing, table lookups, and modifying opcodes |
| **CA** K | 30000+K | Clear and Add. Loads value at K into A (clears overflow). Also: CAE (erasable only), CAF (fixed only) |
| **CS** K | 40000+K | Clear and Subtract. Loads 1's-complement of K into A |
| **AD** K | 60000+K | Add. Adds value at K to A. Does NOT overflow-correct A first |
| **MASK** K | 70000+K | Bitwise AND of A with value at K |
| **TS** K | 54000+K | Transfer to Storage. Stores A to K. If overflow: corrects sign in K, sets A to +1/-1, and SKIPS the next instruction. This skip-on-overflow is critical to how the AGC handles multi-precision arithmetic |
| **XCH** K | 56000+K | Exchange A with K |
| **DAS** K | 20001+K | Double Add to Storage. DP add of A,L pair to K,K+1 pair. Result stored in K,K+1. After: L=+0, A=+1/-1/+0 (carry indicator) |
| **LXCH** K | 22000+K | Exchange L with K |
| **INCR** K | 24000+K | Increment erasable K by +1 |
| **ADS** K | 26000+K | Add A to K, store result in both A and K |
| **DXCH** K | 52001+K | Double Exchange. Swaps A,L pair with K,K+1 pair |
| **QXCH** K | 22000+K | Exchange Q with K |

**Key derived/alias instructions:**
- **RETURN** = `TC Q` (jump to return address)
- **NOOP** = `CA A` (load A into A — does nothing useful)
- **COM** = `CS A` (complement accumulator)
- **DOUBLE** = `AD A` (double the accumulator)
- **RESUME** = `INDEX 25` (return from interrupt, restores Z from ZRUPT)
- **INHINT** = `INDEX 17` (disable interrupts)
- **RELINT** = `INDEX 16` (enable interrupts)
- **EXTEND** = `INDEX 5777` (next instruction is an extracode)
- **DTCB** = `DXCH Z` (jump switching both banks, via A,L preload)
- **DTCF** = `DXCH FB` (jump switching fixed bank)

### AGC4 Instruction Set — Extracodes

These require EXTEND (one word) before the instruction (one word) = 2 words total:

| Mnemonic | Description |
|----------|-------------|
| **DCA** K | Double Clear and Add. Load DP value from K,K+1 into A,L |
| **DCS** K | Double Clear and Subtract. Load negated DP value into A,L |
| **MP** K | Multiply. A × K → high product in A, low product in L |
| **DV** K | Divide. DP value in A,L ÷ SP value in K → quotient in A, remainder in L |
| **SU** K | Subtract. A = A - K (1's complement) |
| **BZF** K | Branch Zero to Fixed. Jump to K (in fixed memory) if A = ±0 |
| **BZMF** K | Branch Zero or Minus to Fixed. Jump if A ≤ 0 |
| **MSU** K | Modular Subtract. 2's-complement subtract, used for CDU angle differences |
| **READ** K | Read I/O channel K into A |
| **WRITE** K | Write A to I/O channel K |
| **RAND** K | Read I/O channel K AND with A |
| **WAND** K | Write A AND channel K to channel K |
| **ROR** K | Read I/O channel K OR with A |
| **WOR** K | Write A OR channel K to channel K |
| **RXOR** K | Read I/O channel K XOR with A |
| **AUG** K | Augment. If K≥0, increment by 1. If K≤0, decrement by 1 |
| **DIM** K | Diminish. If K>0, decrement by 1. If K<0, increment by 1. ±0 unchanged |

### The Interpreter — A Virtual Machine Inside the AGC

The AGC's native instruction set was too limited for navigation/guidance math. The team built an INTERPRETER: a software virtual machine running inside the AGC that provided:
- Linear address space (no bank switching hassle)
- Double-precision and vector arithmetic
- Trigonometric functions (sin, cos, arctan)
- Matrix × vector operations
- State vector manipulation

**How it works:** A `TC INTPRET` call switches from native AGC instructions to interpreted mode. The interpreter reads subsequent words as its own packed opcodes (two 7-bit opcodes + two 15-bit addresses per pair of words). It continues interpreting until hitting an EXIT or equivalent instruction that returns to native mode.

**Trade-off:** Interpreted instructions are ~10-25x slower than native instructions but use far less ROM. Without the interpreter, the software would not have fit in 36K words of fixed memory.

**Key interpreter instructions you'll see in the source:**
- VLOAD, DLOAD, SLOAD — load vector/DP/SP values
- STORE — store to memory
- STODL, STOVL — store and load in one instruction
- CLEAR, SET — manipulate single-bit flags ("switches")
- CALL, GOTO — control flow within interpreted code
- RTB — Return To Basic (exit interpreter)
- EXIT — return to native AGC code
- DAD, DSU, DMP, DDV — DP add, subtract, multiply, divide
- VAD, VSU, VXV, DOT — vector add, subtract, cross product, dot product
- MXV — matrix × vector
- SIN, COS, ASIN, ACOS — trig functions
- UNIT — normalize a vector
- ABVAL — absolute value / vector magnitude
- BON, BOFF — branch on flag set/clear
- BMN, BPL, BZE — branch minus/plus/zero

### Source Code Formatting

- Comments start with `#`
- `$FILENAME.agc` includes another source file
- Labels start in column 1, max 8 characters, can contain almost any character (e.g., `-1/(D)+A` is legal)
- Opcodes start at second tab stop
- Operands at third tab stop
- `##` comments were added by the modern transcription team, not original 1969 code
- Lines starting with `## Page NNN` mark original printout page boundaries

### The Two Programs

The repo contains two complete programs:

1. **Comanche055/** — Command Module AGC software (Colossus 2A). Navigation, re-entry guidance, service propulsion control. ~21,000 lines
2. **Luminary099/** — Lunar Module AGC software (Luminary 1A). Descent guidance, ascent, abort, landing radar integration. ~23,000 lines. This is where the landing happened

Margaret Hamilton was the Colossus Programming Leader. The LM software (Luminary) is where most of the famous code lives: the landing guidance equations, the 1202 alarm handler, BURN_BABY_BURN, etc.

---

## YOUR TASK

With this architectural context loaded, you are now equipped to analyze the Apollo 11 AGC source code accurately. When analyzing any .agc file:

1. **Read the file header comments first** — they state the module's purpose, author credits, and page references to the original printout
2. **Identify whether code is native AGC assembly or interpreter language** — look for `TC INTPRET` to mark transitions. Interpreter blocks use different mnemonics (VLOAD, DLOAD, STORE, etc.)
3. **Track the data flow through registers** — most computation flows through A, with L as the DP companion and Q holding return addresses
4. **Watch for the TS skip pattern** — `TS` followed by `TC somewhere` is the standard overflow-branch idiom
5. **Note CCS as the primary conditional** — remember it's a 4-way skip (positive/+0/negative/-0), not a simple branch
6. **Flag uncertainty** — if you're unsure about an AGC-specific idiom (bank switching, EDOP decoding, interrupt timing), say so explicitly rather than guessing

Begin by cloning the repo and mapping its structure.
