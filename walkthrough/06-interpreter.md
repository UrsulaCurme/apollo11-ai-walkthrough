# The AGC Interpreter: A 1966 Virtual Machine on a 15-Bit Computer

## Luminary099/INTERPRETER.agc — The Software That Made the Moon Landing Fit in Memory

---

## Overview

The Apollo Guidance Computer had 36,864 words of ROM and 2,048 words of RAM. The navigation and guidance mathematics required for a lunar mission — orbital mechanics, powered descent guidance, rendezvous radar processing, inertial platform alignment — would not fit if coded in native AGC assembly. The solution was radical for 1966: build a virtual machine *inside* the AGC that executed its own higher-level instruction set.

The interpreter is not a separate program. It is a subroutine within the Luminary flight software that, when called, begins reading subsequent memory words as its own packed opcodes rather than native AGC instructions. It provides double-precision and vector arithmetic, trigonometric functions, matrix operations, and a linear address space — all impossible or impractical in native AGC code.

This file, at 93 pages of the original printout (pages 1002–1094), is the largest single module in Luminary. It implements the complete interpreter runtime: the dispatch loop, opcode decoder, address resolution, the pushdown list (stack), all arithmetic operations, square root, trigonometric functions, division, and the switch (flag) manipulation system.

---

## 1. Architecture: How the Interpreter Works

### 1.1 Entering Interpreted Mode: `TC INTPRET`

The entry point is at page 1002. When native AGC code executes `TC INTPRET`, control transfers here:

```agc
INTPRET     RELINT                          # Re-enable interrupts
            EXTEND
            QXCH    LOC                     # Q register (return address) → LOC

 +2         CA      BBANK                   # Save current bank setting
            TS      BANKSET
            MASK    BIT15                   # Extract bit 15 of FBANK
            TS      INTBIT15               # For indexed address resolution

            TS      EDOP                   # Clear EDOP — no leftover opcodes

            TCF     NEWOPS                 # Begin fetching opcode pairs
```

The key insight: when native code does `TC INTPRET`, the Q register is automatically loaded with the address of the *next* word in memory — the first interpreted instruction. `QXCH LOC` moves this into `LOC`, which serves as **the interpreter's program counter**. The interpreter then reads words starting at `LOC` and treats them as its own opcodes, not as native AGC instructions.

`BANKSET` preserves the calling program's bank register so the interpreter can restore it when switching banks or exiting. `INTBIT15` caches bit 15 of the current FBANK, needed for resolving addresses that cross the fixed-memory bank boundary.

`EDOP` is cleared by writing to it (the EDOP editing register auto-shifts on any access, and writing zero effectively resets it), ensuring no stale opcode remains from a previous interpreter session.

### 1.2 Opcode Packing: Two Instructions Per Word

Interpreted instructions are packed two per 15-bit word. The encoding uses 7-bit opcodes:

```
Word layout:  [opcode1 (7 bits)] [opcode2 (7 bits)] [sign bit]
              Bits 14-8          Bits 7-1             Bit 15
```

When the sign bit (bit 15) is 0, the word is an opcode pair. When bit 15 is 1, the word is a store code (explained in Section 2). This is detected by `CCS A` in the `NEWOPS` routine — `CCS` performs a 4-way branch on sign and zero, so a positive word routes to `DOSTORE` while other cases proceed as opcode pairs.

The fetch sequence at `NEWOPS` (page 1003):

```agc
NEWOPS      INDEX   LOC                    # Use LOC as program counter
            CA      0                      # Fetch word at C(LOC)
            CCS     A                      # Test sign: positive = store code
            TCF     DOSTORE                # Bit 15 set → store code

LOW7        OCT     177                    # Mask for 7-bit opcode

            TS      EDOP                   # Write full pair to EDOP register
            MASK    LOW7                   # Extract low 7 bits (first opcode)
```

Here is where the EDOP register becomes crucial. When the word is written to EDOP (address 23), the **EDOP editing register automatically shifts right 7 positions and zeros the upper 8 bits**. So after `TS EDOP`, EDOP contains *only* the second opcode (bits 14-8 of the original word, shifted down to bits 7-1). The `MASK LOW7` on the accumulator extracts the first opcode (the low 7 bits).

The first opcode is dispatched immediately. The second opcode waits in EDOP until the first instruction completes.

### 1.3 The EDOP Register as Hardware Decoder

The EDOP register at address 23 is an "editing register" — it automatically transforms data on every read or write:

- **On write:** The value is shifted right 7 positions, and the upper 8 bits are zeroed
- **On read:** The same transformation occurs again (shifting the remaining bits further right)

This hardware behavior is exploited as a free opcode unpacker. When an opcode pair `AAAAAAA BBBBBBB` is written to EDOP:
1. EDOP now contains `0000000 0AAAAAAA` (the first opcode, A, has been shifted into the low bits... wait — let me re-examine)

Actually, let me trace this more carefully. The word format in memory is:

```
Bit 15 (sign) | Bits 14-8 (first opcode) | Bits 7-1 (second opcode)
```

No — looking at the code again:

```agc
            TS      EDOP        # Write the full opcode pair to EDOP
            MASK    LOW7        # Extract bits 1-7 from A (which still has the original value)
```

`TS` copies A to the target but **does not change A**. So A still holds the original word. `MASK LOW7` extracts bits 1-7 from A — this is the **right-hand opcode** which is dispatched first.

Meanwhile, EDOP received the full word and auto-shifted it right 7 positions, zeroing the upper 8 bits. So EDOP now holds bits 14-8 of the original word — the **left-hand opcode** — waiting for later dispatch.

After the first (right-hand) opcode finishes execution, control returns to `DANZIG`, which checks EDOP:

```agc
DANZIG      CA      BANKSET                # Restore bank setting
            TS      BBANK

NOIBNKSW    CCS     EDOP                   # Is there a second opcode waiting?
            TCF     OPJUMP                 # Yes — dispatch it (EDOP auto-clears on read)

            CCS     NEWJOB                 # No — check for higher-priority jobs
            TCF     CHANG2                 # Yield to job scheduler if needed

            INCR    LOC                    # Advance program counter
```

`CCS EDOP` reads EDOP (which triggers another auto-shift, leaving EDOP at zero for next time) and branches: if the second opcode was non-zero, it jumps to `OPJUMP` for dispatch. If zero (which is the EXIT opcode), it falls through. The `CCS` also decrements the value by 1, which is accounted for in the dispatch tables.

**This is a cooperative multitasking checkpoint.** Every time the interpreter finishes an instruction pair, it checks `NEWJOB` to see if the Executive has a higher-priority job waiting. If so, the interpreter yields via `CHANG2`. This is how the AGC avoids starvation — even long interpreted computation sequences will periodically give other tasks a chance to run.

### 1.4 The Interpreter's Program Counter

The interpreter's program counter is stored in **`LOC`**, an erasable memory location. It points to the current opcode pair word in fixed memory. After both opcodes in a pair are executed, `INCR LOC` advances to the next word, which may be another opcode pair or an address word belonging to the previous instruction.

Address words for instructions that require operands are fetched inline — the instruction handler itself does `INDEX LOC` / `CA 1` to look ahead at the next word. When an address word is consumed, `INCR LOC` is called to skip past it.

### 1.5 Opcode Dispatch: The Three-Stage Decoder

The dispatch mechanism is a cascading series of prefix-bit tests that route opcodes to one of four categories. The 7-bit opcode is placed in `CYR` (the Cycle Right editing register), and successive `CCS CYR` instructions test the prefix bits:

```agc
OPJUMP      TS      CYR                   # Load opcode into Cycle Right register
            CCS     CYR                   # Test first prefix bit
            TCF     OPJUMP2               # Bit set → not a simple indexed op

            TCF     EXIT                  # +0 opcode = EXIT instruction
```

The CYR register cycles right on each access, rotating the bits. This effectively shifts different prefix bits into testable positions. The three-stage cascade:

1. **First `CCS CYR`** at `OPJUMP`: Tests the first prefix bit
   - Non-zero → `OPJUMP2` (miscellaneous, unary, or shift)
   - Zero → `EXIT` (opcode 00 is EXIT)
   - Otherwise → falls through to `ADDRESS` for operand resolution, then dispatches through `INDJUMP` table

2. **Second `CCS CYR`** at `OPJUMP2` (page 1009): Tests the second prefix bit
   - Non-zero → `OPJUMP3` (unary or shift operations)
   - Zero → `15BITADR` (miscellaneous with 15-bit address)

3. **Third `CCS CYR`** at `OPJUMP3` (page 1010): Tests the third prefix bit
   - Non-zero → `UNAJUMP` table (unary operations)
   - Zero → short shift operations (`SHORTT` or `SHORTV`)

The three jump tables at pages 1011-1013 handle the actual dispatch:

**INDJUMP** (page 1011) — 32 entries for addressable operations:
```agc
INDJUMP     TCF     VLOAD       # 00 — Load vector
            TCF     TAD         # 01 — Triple precision add
            TCF     SIGN        # 02 — Conditional complement
            TCF     VXSC        # 03 — Vector × scalar
            TCF     CGOTO       # 04 — Computed GOTO
            TCF     TLOAD       # 05 — Triple precision load
            TCF     DLOAD       # 06 — Double precision load
            TCF     V/SC        # 07 — Vector ÷ scalar
            ...                 # (continues through opcode 37)
```

**MISCJUMP** (page 1012) — 16 entries for index/branch/misc operations:
```agc
MISCJUMP    TCF     AXT         # 00 — Address to index true
            TCF     AXC         # 01 — Address to index complemented
            ...
            TCF     BOV(B)      # 17 — Branch on overflow
```

**UNAJUMP** (page 1013) — 16 entries for unary operations:
```agc
UNAJUMP     TCF     SQRT        # 01 — Square root
            TCF     SINE        # 02 — Sine
            TCF     COSINE      # 03 — Cosine
            TCF     ARCSIN      # 04 — Arc sine
            TCF     ARCCOS      # 05 — Arc cosine
            ...
            TCF     RVQ         # 16 — Return via QPRET
            TCF     PUSH        # 17 — Push MPAC down
```

The `INDEX CYR` / `TCF INDJUMP-1` pattern at the end of address resolution (e.g., `ITR15`) uses the opcode value in CYR as an offset into the jump table. The `7` before `INDJUMP -1` is a pseudo-instruction that, after being modified by `INDEX CYR`, becomes `TCF INDJUMP + opcode`.

### 1.6 Address Resolution

Before dispatching addressable instructions, the interpreter must resolve the operand address. This is handled by the `ADDRESS` routine (page 1004) and its sub-cases:

- **Direct addresses** (page 1004-1005): The next word after the opcode pair contains the address. Addresses < 45 decimal are relative to the current job's work area (VAC area). Addresses 100-3777 are general erasable (requires EBANK switching). Addresses above that are in fixed memory (requires FBANK switching).

- **Indexed addresses** (page 1006): The address is modified by adding the contents of an index register (X1 or X2). The `INDEX` routine at page 1006 handles this, including bank switching for the resulting address.

- **Push-up addresses** (page 1008): When no address word follows the opcode, the operand is taken from the pushdown list. The `PUSHUP` routine decrements `PUSHLOC` by the appropriate amount (2 for DP, 6 for vector) and uses the resulting address.

### 1.7 The Multi-Purpose Accumulator (MPAC)

The interpreter's primary working register is **MPAC**, a 7-word block in erasable memory:

| Register | Purpose |
|----------|---------|
| MPAC     | Most-significant word (or vector X high) |
| MPAC+1   | Second word (or vector X low) |
| MPAC+2   | Third word (TP low, or scratch) |
| MPAC+3   | Vector Y high |
| MPAC+4   | Vector Y low |
| MPAC+5   | Vector Z high |
| MPAC+6   | Vector Z low |

The **MODE** register tracks what MPAC currently contains:
- **0** = Double precision scalar (DP)
- **+1** = Triple precision scalar (TP)
- **-1** = Vector (three DP components)

This polymorphism is central to the interpreter's efficiency — the same MPAC serves as a scalar accumulator or a vector register depending on context.

### 1.8 The Pushdown List (Stack)

The interpreter maintains a pushdown list (stack) in the job's work area, tracked by `PUSHLOC`. Instructions like `PUSH`, `PDDL`, and `PDVL` save MPAC contents to the stack and optionally reload MPAC. The stack grows downward and supports both DP (2-word) and vector (6-word) entries.

The push-up mechanism (taking operands from the stack when no address is given) makes the interpreter resemble a stack machine for many operations, similar to how the JVM operates.

---

## 2. Instruction Categories

### 2.1 Load/Store Instructions

**DLOAD** (page 1002) — The simplest load, illustrating the pattern:

```agc
DLOAD       EXTEND
            INDEX   ADDRWD
            DCA     0              # Load DP value from address in ADDRWD
SLOAD2      DXCH    MPAC           # Store in MPAC, MPAC+1
            CAF     ZERO

            TS      MPAC +2        # Zero MPAC+2 (declare DP mode)
```

After every load, control falls into `NEWMODE` → `DANZIG` to set the MODE register and dispatch the next instruction.

**VLOAD** (page 1019) loads all three vector components:

```agc
VLOAD       EXTEND
            INDEX   ADDRWD
            DCA     0              # X component
            DXCH    MPAC

ENDVLOAD    EXTEND
            INDEX   ADDRWD
            DCA     2              # Y component
            DXCH    MPAC +3

            EXTEND
            INDEX   ADDRWD
            DCA     4              # Z component
            DXCH    MPAC +5

VMODE       CS      ONE            # MODE = -1 (vector)
            TCF     NEWMODE
```

**STORE** (pages 1014-1017) — Store codes are detected at `NEWOPS` when the fetched word has bit 15 set. The store code encodes both the erasable destination address and the store type (STORE, STODL, STOVL, STCALL). The `DOSTORE` routine at page 1014 extracts these fields:

```agc
DOSTORE     TS      ADDRWD
            MASK    LOW11          # Extract erasable address (11 bits)
            XCH     ADDRWD
            MASK    B12T14         # Extract store code number (bits 12-14)
            EXTEND
            MP      BIT5           # Multiply by 2 for jump table offset
            INDEX   A
            TCF     STORJUMP       # Dispatch through store jump table
```

The `STORJUMP` table (page 1015) handles all eight store variants, each calling the appropriate storing routine followed by either returning to `DANZIG` or initiating a load for the combined STODL/STOVL codes.

The actual store in `STARTSTO` (page 1017) checks MODE to determine whether to store 2 words (DP), 3 words (TP), or 6 words (vector):

```agc
STARTSTO    EXTEND
            DCA     MPAC           # Always store first two words
            INDEX   ADDRWD
            DXCH    0

            CCS     MODE
            TCF     TSTORE         # TP: also store MPAC+2
            TC      Q              # DP: done

VSTORE      EXTEND                 # Vector: store Y and Z components too
            DCA     MPAC +3
            INDEX   ADDRWD
            DXCH    2
            EXTEND
            DCA     MPAC +5
            INDEX   ADDRWD
            DXCH    4
            TC      Q
```

### 2.2 Arithmetic: Double Precision Multiply (DMPSUB)

The multiply subroutine at page 1031 is one of the interpreter's most-called routines. It multiplies the DP contents of MPAC by the DP value at `C(ADDRWD)`, leaving a triple-precision result:

```agc
DMPSUB      INDEX   ADDRWD
            CA      1              # Get minor part of operand
            TS      MPAC +2
            CAF     ZERO
            XCH     MPAC +1        # Save minor of MPAC, zero MPAC+1
            TS      MPTEMP
            EXTEND
            MP      MPAC +2        # minor(MPAC) × minor(operand)

            XCH     MPAC +2        # Discard lowest product, get cross term
            EXTEND
            MP      MPAC           # major(MPAC) × minor(operand)
            DAS     MPAC +1        # Accumulate — guaranteed no overflow

            INDEX   ADDRWD
            CA      0              # Get major part of operand
            XCH     MPTEMP
DMPSUB2     EXTEND
            MP      MPTEMP         # major(operand) × minor(MPAC)
            DAS     MPAC +1        # Accumulate

            XCH     MPAC           # Set MPAC to overflow indicator (0 or ±1)
            EXTEND
            MP      MPTEMP         # major(MPAC) × major(operand)
            DAS     MPAC           # Final accumulation
            TC      Q              # 49 MCT = 0.573 ms including return
```

The comment tells us the execution time: **49 MCT (machine cycles) = 0.573 milliseconds**. This is a single DP multiply. A dot product calls DMPSUB three times; a cross product calls it six times.

### 2.3 Double Precision Division (DDV/BDDV)

Division is the most complex arithmetic operation, spanning pages 1057-1068. The algorithm:

1. Force both dividend and divisor positive, tracking the result sign in `DVSIGN`
2. Normalize the divisor (shift left until ≥ 0.5) tracking shifts in `DVNORMCT`
3. Apply the same shifts to the dividend
4. Handle the special "MAXDV" case where major parts are equal
5. Perform the actual division using the native `DV` instruction for each half
6. Apply sign correction

The general division at page 1062 uses the approximation:

```
(A + sB) / (C + sD) ≈ Q + s(R - QD)/C
```

where s = 2^(-14) and Q, R are quotient and remainder of A/C. This avoids a full double-precision divide by using single-precision divides with a correction term.

### 2.4 Vector Operations

**VAD/VSU** (page 1026) — Vector add/subtract reuses the `DCA`/`DCS` opcodes cleverly:

```agc
VSU         CAF     BIT15          # Changes opcode to DCS (subtract)
            TCF     +2
VAD         CAF     PRIO30         # Changes opcode to DCA (add)
            ADS     ADDRWD         # Modify ADDRWD so INDEX+DCA becomes INDEX+DCS
```

This is a remarkable trick: by adding a constant to ADDRWD before using it as an index, the `DCA 0` that would normally load becomes `DCS 0` that loads the complement. The same instruction sequence handles both add and subtract.

**VXV** (page 1042) — Vector cross product. Computes:

```
result = (M3·X2 - M2·X3, M1·X3 - M3·X1, M2·X1 - M1·X2)
```

where M is the vector in MPAC and X is at the given address. This requires six calls to DMPSUB plus careful register shuffling through VBUF to avoid clobbering intermediate results.

**DOT** (page 1033/1038) — Dot product uses `DOTSUB`, which calls DMPSUB three times (once per component) and accumulates the triple-precision partial products in BUF. The `DOTINC` variable controls the stride between vector components, which is normally 2 (consecutive DP words) but is set to 6 by VXM to dot with matrix columns.

**MXV/VXM** (pages 1038-1039) — Matrix-vector multiply. These compute three dot products between the MPAC vector and successive rows (MXV) or columns (VXM) of the matrix. The difference is just in the stride:

```agc
MXV         CAF     TWO            # MATINC = 2: rows are consecutive DP pairs
            TS      MATINC
            TCF     VXM/MXV

VXM         CS      TEN            # MATINC = -10: columns are 6 words apart
            TS      MATINC         # (negative because we advance backwards)
            CAF     SIX            # DOTINC = 6: dot with column vectors
```

### 2.5 Trigonometric Functions

**SINE/COSINE** (pages 1082-1083) — Cosine uses the identity cos(x) = sin(π/2 - |x|), then falls into SINE. The sine function:

1. Doubles the argument (the interpreter uses the convention that angles are scaled so 1.0 = 2π)
2. Reduces the argument to the range [-π/2, π/2] using identities
3. Squares the reduced argument
4. Evaluates a 4th-order Hastings polynomial approximation:

```agc
            TC      POLY
            DEC     3              # Degree - 1
            2DEC    +.3926990796   # ≈ π/8 (coefficient A0)
            2DEC    -.6459637111   # A1
            2DEC    +.318758717    # A2
            2DEC    -.074780249    # A3
            2DEC    +.009694988    # A4
```

5. Multiplies by the original argument and shifts left 2

The `POLY` subroutine (page 1034) evaluates a general polynomial using Horner's method: starting with the highest-degree coefficient, it repeatedly multiplies by x and adds the next coefficient.

**ARCCOS** (pages 1084-1085) uses the Hastings approximation:

```
arccos(x) = sqrt(1-x) · P(x)
```

where P(x) is a 7th-order polynomial. The coefficients include scaling factors like `B+1`, `B+2`, etc., which are powers-of-2 scaling to keep values in the fractional range.

**SQRT** (pages 1076-1081) — The square root algorithm:

1. Normalizes the input (shifts left until ≥ 0.125)
2. Uses a linear approximation as initial guess (different slopes for ranges 0.125-0.25 and 0.25-0.5)
3. Performs two Newton-Raphson iterations: x_{n+1} = x_n/2 + (arg/2)/x_n
4. Returns the normalized result with a shift count for un-normalization

The constants `SLOPEHI (.5884)`, `BIASHI (.4192 B-1)`, `SLOPELO (.8324)`, `BIASLO (.2974 B-1)` are the linear approximation parameters for the two argument ranges.

### 2.6 Control Flow

**GOTO/CALL** (page 1023) — CALL computes a return address from `BANKSET + LOC` and stores it in `QPRET` (the interpreter's return register), then falls into GOTO. GOTO resolves the target CADR and sets up `LOC` and the bank registers:

```agc
CALL        CA      BANKSET
            MASK    BANKMASK
            AD      BANKMASK       # BANKMASK = -(2000-1)
            AD      LOC
            INDEX   FIXLOC
            TS      QPRET          # Save return address

GOTO        CA      POLISH         # Target address
            ...                    # Bank switching and LOC setup
            TCF     INTPRET +3     # Re-enter interpreter at new location
```

**EXIT** (page 1025):

```agc
EXIT        CA      BANKSET        # Restore user's bank setting
            TS      BBANK
            INDEX   LOC
            TC      1              # Jump to the word after the current opcode
```

EXIT restores the bank register and transfers control to native AGC code at the address following the last interpreted instruction. This is how interpreted blocks hand back to native assembly.

**BZE/BMN/BPL** (page 1091) — All use the `BRANCH` subroutine (page 1025), which performs a triple-precision sign test on MPAC:

```agc
BRANCH      CCS     MPAC
            TC      Q              # Positive → return to Q
            TCF     +2
            TCF     NEG            # Negative

            CCS     MPAC +1        # If MPAC was ±0, check MPAC+1
            TC      Q
            TCF     +2
            TCF     NEG

            CCS     MPAC +2        # And MPAC+2
            TC      Q
            TCF     +2
            TCF     NEG

Q+1         INDEX   Q              # Zero: skip to Q+2
            TC      1

NEG         INDEX   Q              # Negative: skip to Q+3
            TC      2
```

This three-way return (positive/zero/negative) is used by all the conditional branches to determine whether to take the branch.

**Switch instructions** (pages 1092-1094) — The AGC uses single-bit flags ("switches") stored in the `STATE` table for tracking mission phases, hardware status, and program options. The interpreter provides 16 switch operations (BON, BOFF, SET, CLEAR, INVERT, and combinations with GOTO). The switch address encodes:
- Bits 1-4: bit number within the word
- Bits 5-8: operation code (set/invert/clear × branch-if-on/branch-if-off/goto/noop)
- Bits 9+: word number in the STATE table

### 2.7 Instruction Count

Counting all entries across the three jump tables and their variants:

| Category | Instructions |
|----------|-------------|
| **INDJUMP** (addressable ops) | 32 entries (00-37 octal), one slot marked "available" |
| **MISCJUMP** (index/branch/misc) | 16 entries (00-17 octal) |
| **UNAJUMP** (unary) | 16 entries (01-17 octal, 00 is EXIT detected earlier) |
| **Short shifts** | 24 variants (SR1-4, SL1-4, SR1R-4R, SL1R-4R, VSR1-8, VSL1-8) |
| **Store codes** | 8 variants (STORE, STORE,1, STORE,2, STODL, STODL*, STOVL, STOVL*, STCALL) |
| **Switch ops** | 16 variants (4 operations × 4 branch modes) |

**Total: approximately 80-90 distinct interpreted operations**, depending on how one counts variants and aliases. This is comparable to the ~200 opcodes of the Java bytecode set, though the AGC interpreter's operations are generally higher-level (a single VXSC does what would take dozens of JVM bytecodes).

---

## 3. The Engineering Trade-off

### 3.1 Why Not a Subroutine Library?

A subroutine library for vector/matrix math would have been the conventional approach. The interpreter was chosen instead for several reasons:

**ROM savings from opcode packing.** Each interpreted instruction occupies 7 bits of opcode plus (optionally) one 15-bit address word. Two opcodes pack into a single word. A native subroutine call (`TC subroutine` + address setup) would require at least 2-4 words per operation. For a program with thousands of vector operations, this 2-4× reduction in code density was decisive.

**Elimination of bank-switching overhead.** In native AGC code, every cross-bank subroutine call requires `TC BANKCALL` plus a CADR (2 words minimum), and the called routine must handle bank restoration on return. The interpreter provides a **linear address space** — interpreted code can reference any location without explicit bank switching. The interpreter handles all bank switching internally in its address resolution routines. This saved both ROM and programmer mental overhead.

**Implicit operand management.** The pushdown list allows operations to chain without explicit load/store sequences. `VLOAD V1; VXV V2; UNIT; STORE RESULT` — each instruction implicitly operates on MPAC. In native code, the programmer would need to manually shuffle registers between each operation.

**The interpreter itself is amortized.** The interpreter runtime occupies roughly 1,000 words of fixed memory. But it replaces what would have been thousands of words of inline bank-switching, register management, and control flow code scattered across every navigation routine. The break-even point is reached quickly.

### 3.2 Execution Time

The comment on DMPSUB states: **49 MCT = 0.573 ms** for a double-precision multiply.

A native AGC multiply (`EXTEND` + `MP`) takes 3 MCT = 0.035 ms. So the interpreted DP multiply is roughly **16× slower** than a single native multiply — though to be fair, DMPSUB computes a full 28-bit × 28-bit product using four native multiplies, cross-term accumulation, and overflow handling.

The interpreter dispatch overhead per instruction is approximately:
- `DANZIG` bank restore + EDOP check: ~4 MCT
- Address resolution (direct): ~8-12 MCT
- Jump table dispatch: ~3-4 MCT
- **Total overhead: ~15-20 MCT (~0.17-0.23 ms) per instruction**

For a complex operation like VXV (vector cross product), the total is approximately:
- 6 × DMPSUB calls: 6 × 49 = 294 MCT
- Register shuffling: ~60 MCT
- Dispatch overhead: ~20 MCT
- **Total: ~374 MCT ≈ 4.4 ms**

The original AGC documentation states that interpreted instructions run at roughly **10-25× slower** than equivalent native code. This matches: the dispatch + address resolution overhead alone is 15-20 MCT, while a typical native instruction is 1-2 MCT.

### 3.3 Where the Penalty Shows

The performance penalty is most visible in **time-critical loops**:

- **The Digital Autopilot (DAP)** is written almost entirely in native AGC assembly. It runs at 100 Hz (T5RUPT every 10ms) and must complete within its time slot. Interpreted code would be too slow.
- **T6RUPT jet timing** operates at 1/1600 second resolution — entirely native.
- **The descent guidance equations** (P63/P64) use the interpreter for trajectory math but switch to native code for the inner loop of the powered flight integration.

The cooperative multitasking checkpoint at `DANZIG` (checking `NEWJOB`) means interpreted code can be preempted between every instruction pair. This prevents the interpreter from monopolizing the CPU but adds scheduling jitter to interpreted computations.

### 3.4 ROM Savings Estimate

The interpreter module itself occupies approximately 1,000 words (pages 1002-1094 = 93 pages, roughly 10-12 instructions per page). The interpretive programs throughout Luminary (guidance equations, navigation, orbital mechanics) total roughly 8,000-10,000 interpreted instruction words.

If each interpreted instruction were expanded to equivalent native code (conservatively 3-5 words per interpreted instruction, accounting for bank switching, register management, and subroutine calling overhead), the native equivalent would require 24,000-50,000 words — far exceeding the 36,864-word ROM capacity.

**The interpreter saved an estimated 15,000-40,000 words of ROM**, making the difference between a program that fits in the AGC and one that does not.

---

## 4. Computer Science Significance

### 4.1 One of the First Deployed Bytecode Interpreters

The AGC interpreter, designed in 1964-1966 and deployed in flight in 1969, is one of the earliest examples of a bytecode virtual machine deployed in a production system. It predates:

- **UCSD p-code** (1978) by over a decade
- **Smalltalk-80's bytecode interpreter** (1980) by 14 years
- **Java's JVM** (1995) by nearly 30 years
- **Python's bytecode interpreter** (1991) by 25 years

The only comparable contemporaries were Burroughs B5000 descriptors (1961) and some LISP implementations, but the AGC interpreter was unique in being deployed in a safety-critical, real-time, resource-constrained embedded system.

### 4.2 Comparison to the JVM

| Feature | AGC Interpreter | Java JVM |
|---------|----------------|----------|
| **Opcode size** | 7 bits (packed 2 per word) | 8 bits (one per byte) |
| **Operand addressing** | Inline address words | Stack-based with constant pool |
| **Primary accumulator** | MPAC (7-word polymorphic) | Operand stack |
| **Data types** | SP, DP, TP, Vector, Matrix | int, long, float, double, ref |
| **Control flow** | GOTO, CALL, BRANCH, RVQ | goto, invoke*, if*, return |
| **Bank switching** | Handled internally | ClassLoader handles equivalent |
| **Multitasking** | Cooperative (NEWJOB check) | Thread-based (no interpreter cooperation) |
| **Performance ratio** | ~10-25× slower than native | ~10-50× slower (before JIT) |

The conceptual parallels are striking:
- Both pack higher-level operations into compact encodings
- Both provide a linear address space over a segmented underlying architecture
- Both trade execution speed for code density
- Both include a dispatch loop that fetches, decodes, and executes

The key difference is that the AGC interpreter was *designed for a fixed program*. There was no dynamic loading, no class files, no verification. The interpreter and its "bytecode" were manufactured together into the same core rope module.

### 4.3 Design Choices Driven by the 15-Bit Word

Several interpreter design decisions are directly consequences of the 15-bit word size:

**7-bit opcodes.** Two opcodes must fit in one 15-bit word (with the sign bit used as a store-code indicator). 7 + 7 + 1 = 15 bits. This limits the instruction set to 128 possible opcodes, of which roughly 80-90 are used.

**The EDOP hardware decoder.** On a byte-addressed machine, unpacking two opcodes would be a simple shift-and-mask. On the AGC, where shift instructions are limited (no barrel shifter), the EDOP register's automatic 7-bit shift-and-zero behavior provides this unpacking essentially for free — it's a single `TS EDOP` instruction. This is one of the AGC's cleverest hardware/software co-design choices.

**1's-complement overflow handling.** The `TS` skip-on-overflow pattern appears throughout the arithmetic routines. The interpreter must carefully manage overflow in MPAC to maintain precision across chained operations. The `OVFIND` flag provides interpreted-level overflow tracking on top of the native overflow detection.

**CCS as the primary conditional.** The 4-way branch of `CCS` (positive/+0/negative/-0) is used extensively in the dispatch logic, the `BRANCH` subroutine, and throughout the arithmetic routines. The two representations of zero in 1's complement mean that the interpreter must test for both +0 and -0 in many places — a complication that would not exist on a 2's-complement machine.

**Fractional arithmetic.** Because the AGC treats all data as fractions (binary point between the sign and bit 14), the interpreter must be careful about scaling. The comment on DMPNSUB (page 1037) warns: *"The customer must insure that B(A) × B(MPAC,MPAC+1) and B(A) × B(MPAC) are less than 1 in magnitude."* There is no hardware floating point; all scaling is the programmer's responsibility.

---

## 5. Key Subroutines and Support Code

### 5.1 INTER-BANK_COMMUNICATION.agc

This companion file (pages 998-1001) provides the bank-switching primitives used by both native code and the interpreter:

**BANKCALL/SWCALL** — The standard cross-bank subroutine call. `BANKCALL` reads a CADR from inline code; `SWCALL` accepts the CADR in A. Both switch FBANK, execute the target, and return via `SWRETURN`:

```agc
SWCALL      TS      L
            LXCH    FBANK          # Switch banks, saving old FBANK in L
            MASK    LOW10          # Extract sub-address from CADR
            XCH     Q              # Set up return address
            DXCH    BUF2           # Restore caller's A,L
            INDEX   Q
            TC      10000          # Jump to target (setting Q = SWRETURN)
```

**SUPERSW** — Handles the superbank bit for accessing fixed banks 40-43. This is necessary because the 5-bit FBANK field can only address 32 banks, and the AGC has 36.

**USPRCADR** — Allows native code to invoke interpreted code in another bank. It sets up `LOC`, `BANKSET`, and `EDOP`, then enters the interpreter.

### 5.2 The ROUNDSUB Subroutine (Page 1032)

```agc
ROUNDSUB    CAF     ZERO           # Zero MPAC+2 and set mode to DP
 +1         TS      MODE

VROUND      XCH     MPAC +2        # Get rounding bit
            DOUBLE                 # Shift left 1 (test if ≥ 0.5)
            TS      L
            TC      Q              # Return if rounding bit < 0.5

            AD      MPAC +1        # Add 1 to MPAC+1
            TS      MPAC +1
            TC      Q              # Return if no overflow

            AD      MPAC           # Propagate carry to MPAC
            TS      MPAC
            TC      Q
```

This illustrates a pattern seen throughout: **cascading overflow propagation**. Because there is no hardware carry chain across multi-word values, each addition must check for overflow and manually propagate to the next word. The `TS` skip-on-overflow mechanism makes this possible but verbose.

### 5.3 Sign Agreement (TPAGREE/ALSIGNAG)

In 1's-complement DP arithmetic, the two words of a DP value can have different signs (e.g., +37777, -37777 represents the same value as +37776, +00001). Many operations require the signs to agree first. `TPAGREE` (page 1036) forces sign agreement across all three MPAC registers, and `ALSIGNAG` (page 1043) does so for a DP value in A,L. This is a complication unique to 1's-complement that would not exist on a modern 2's-complement machine.

---

## 6. Uncertain Interpretations

1. **The `7 INDJUMP-1` pattern.** The number `7` before `INDJUMP-1` in instructions like `ITR15` appears to be a pseudo-instruction that, when modified by `INDEX CYR`, becomes a `TCF` to the appropriate jump table entry. The exact mechanics of how `7` encodes as an instruction word that becomes `TCF` after indexing is not fully clear from the source alone — it likely depends on `7` being the opcode for `TCF 0` (since `7` octal = `TCF` with a zero address, and the INDEX adds the jump table base).

2. **Store code encoding.** The exact bit layout of store codes (how bits 12-14 encode the 8 store variants while bits 1-11 encode the erasable address) is stated in the code but the sign-bit convention for distinguishing store codes from opcode pairs deserves more analysis. The `CCS A` at `NEWOPS` branches on positive (store code with bit 15 = 0 and non-zero value) vs. the opcode pair case — but the comment says store codes are "stored complemented to make [them] look like opcode pairs." This inversion may mean store codes appear negative in memory, and the `CCS` positive branch is actually catching the *decoded* value after CCS's DABS operation.

3. **POLY subroutine coefficients.** The trigonometric polynomial coefficients appear to use Hastings' approximations. The specific error bounds of these approximations on 28-bit fixed-point arithmetic have not been independently verified here — the original MIT documentation would be authoritative.

4. **Pushdown list overflow.** There appears to be no runtime check for pushdown list overflow. If interpreted code pushes more data than the work area can hold, it would silently corrupt adjacent memory. This suggests the interpreter relied on compile-time verification by the YUL assembler to prevent stack overflow.

---

## Summary

The AGC interpreter is a tour de force of 1960s systems programming. In approximately 1,000 words of hand-crafted assembly, it implements:

- A complete opcode fetch-decode-execute loop with hardware-assisted unpacking
- Double-precision, triple-precision, and vector arithmetic
- Matrix-vector multiplication
- Trigonometric functions via polynomial approximation
- Square root via Newton-Raphson iteration
- General-purpose double-precision division with overflow handling
- A pushdown stack for implicit operand management
- A 16-operation flag manipulation system
- Cooperative multitasking integration with the Executive
- Transparent bank switching across the entire 36K address space

It made the lunar landing software possible by fitting roughly 3× more functionality into the same ROM than native assembly could have achieved. The performance penalty of 10-25× was acceptable because the time-critical autopilot loops were written in native code, while the guidance equations — which ran at human timescales — could afford the slower execution.

As a historical artifact, it stands as one of the earliest bytecode interpreters ever deployed in a production system, predating the concept's popularization by decades. Its design — packed opcodes, polymorphic accumulator, implicit stack operations, cooperative scheduling — anticipates patterns that would become standard in virtual machine design a generation later.