# Lunar Landing Guidance Equations: The Code That Landed on the Moon

## Overview

`LUNAR_LANDING_GUIDANCE_EQUATIONS.agc` is the single most consequential file in the Apollo 11 codebase. It contains Programs 63, 64, 65, 66, and 67 — the guidance routines that flew the Lunar Module from powered descent initiation at ~50,000 feet to touchdown on the Sea of Tranquility.

This file lives in Luminary099, the Lunar Module's flight software (Luminary 1A, build 099). It was assembled on **July 14, 1969** — six days before the landing.

The code spans pages 798–828 of the original MIT printout. It is a mixture of native AGC assembly and interpreter language, with the computationally intensive guidance math running on the AGC's software virtual machine (entered via `TC INTPRET`), and the time-critical control flow, display logic, and phase switching running in native assembly.

---

## 1. Architecture: The Flight Sequence Table

The landing guidance is organized around a **state machine** driven by the variable `WCHPHASE`:

```
WCHPHASE = -1  →  IGNALG    (Ignition Algorithm)
WCHPHASE =  0  →  BRAKQUAD  (Braking Phase — P63)
WCHPHASE =  1  →  APPRQUAD  (Approach Phase — P64)
WCHPHASE =  2  →  VERTICAL  (Vertical Descent — P65/P66/P67)
```

Rather than using if-else chains, the code uses **jump tables** — arrays of `TCF` (Transfer Control to Fixed) instructions indexed by `WCHPHASE`. Each guidance pass walks through a fixed pipeline of stages, and at each stage the appropriate handler is selected by indexing into the relevant table:

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

The pipeline is:

1. **NEWPHASE** — phase transition logic
2. **PREGUIDE** — pre-guidance computations (coordinate transforms, redesignation)
3. **WHATGUID** — the actual guidance equations
4. **AFTRGUID** — post-guidance (throttle, steering)
5. **WHATEXIT** — exit and window vector computations
6. **WHATDISP** — DSKY display updates

This table-driven architecture is elegant: adding a new phase means adding one entry to each table, not restructuring control flow. The `INDEX WCHPHASE` instruction adds the value of WCHPHASE to the next instruction's address, selecting the correct `TCF` from the table.

---

## 2. Entry Points

### Normal Entry: LUNLAND

The guidance loop is called from SERVOUT (the servicer — the routine that processes IMU and PIPA data at ~2 Hz):

```agc
LUNLAND     TC      PHASCHNG
            OCT     00035           # GROUP 5: RETAIN ONLY PIPA TASK
            TC      PHASCHNG
            OCT     05023           # GROUP 3: PROTECT GUIDANCE WITH PRIO 21
            OCT     21000           #   JUST HIGHER THAN SERVICER'S PRIORITY
```

The first action is restart protection. The AGC had no operating system in the modern sense, but it had a cooperative multitasking system (the Executive) and a restart/recovery system. `PHASCHNG` records the current program phase so that if a hardware restart occurs, the system can resume from a known state.

Priority 21 is "just higher than SERVICER's priority" — guidance must preempt the servicer but not critical interrupt handlers.

### Ignition Algorithm Entry: ?GUIDSUB

```agc
?GUIDSUB    EXIT
            CAF     TWO            # N = 3
            TS      NGUIDSUB
            TCF     GUILDRET +2
```

This is called during the ignition algorithm phase (before braking begins). It delivers N=3 passes of quadratic guidance to converge on the initial trajectory. The `EXIT` instruction returns from the interpreter to native AGC code. The label `?GUIDSUB` is notable — the `?` prefix is legal in AGC labels and was used by convention for subroutines called from other modules.

---

## 3. GUILDENSTERN: The Auto-Modes Monitor (R13)

One of the most recognizable sections in all of Apollo software, named after a character from Shakespeare's *Hamlet* (and later Stoppard's *Rosencrantz and Guildenstern Are Dead*):

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

The label `GUILDENSTERN` was split across two lines — `GUILDEN` on line one, `STERN` on line two. The transcription notes that `STERN` was "not originally a comment" — in the original source it was simply a continuation of the label on the next line, which was legal in YUL assembly syntax but not in modern yaYUL, so the transcribers commented it out.

### What GUILDENSTERN Does

Every guidance cycle, before computing guidance commands, GUILDENSTERN checks the astronaut's control mode by reading discrete inputs from I/O channels:

1. **Channel 30, Bit 5**: The "un-auto-throttle" discrete. If present → start P67 (manual throttle)
2. **Channel 31, Bit 13**: The "un-attitude-hold" discrete. If present with attitude-hold selected → start P66 (rate-of-descent mode)

The logic flow:

```
Is manual throttle discrete present?
  YES → STARTP67 (manual throttle, always)
  NO  → Are we in P67?
    YES → STARTP66 (astronaut released manual throttle, go to ROD mode)
    NO  → Is attitude-hold discrete present?
      YES → GUILDRET (all's well, continue current program)
      NO  → Are we in P66?
        YES → Has there been a restart?
          YES → Reinitialize P66 but keep VDGVERT
          NO  → Continue with ROD
        NO  → Has ROD switch been clicked?
          YES → STARTP66
          NO  → GUILDRET (continue automatic landing)
```

### Starting P66

```agc
STARTP66    TC      FASTCHNG
            TC      NEWMODEX
DEC66       DEC     66
            EXTEND
            DCA     HDOTDISP    # SET DESIRED ALTITUDE RATE = CURRENT
            DXCH    VDGVERT     #   ALTITUDE RATE.
```

This is critical: when switching to P66, the desired altitude rate (`VDGVERT`) is initialized to the **current** altitude rate (`HDOTDISP`). This means the astronaut doesn't experience a jolt — the guidance seamlessly transitions to maintaining whatever descent rate was current at the moment of switchover.

The initialization continues in interpreter mode:

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

This loads PIPA (accelerometer) biases as a vector, scales by `BIASFACT` (655.36 B-28), stores the result as `VBIAS`, and initializes the ROD computation state. The bias correction is essential — the PIPAs had known biases that had to be compensated in software.

### The "TEMPORARY" Comment

```agc
            TC      BANKCALL        # TEMPORARY, I HOPE HOPE HOPE
            CADR    STOPRATE        # TEMPORARY, I HOPE HOPE HOPE
```

This is one of the most famous comments in the codebase. The call to `STOPRATE` (which zeros the attitude rate commands) was added as a temporary fix and the programmer hoped it would be replaced with a proper solution. It was not. It flew to the Moon exactly as written. The triple "HOPE" conveys the programmer's resigned awareness that temporary code in flight software has a way of becoming permanent.

---

## 4. Phase Initialization

### TTFINCR: Time-to-Go and Landing Site Update

Every guidance pass begins with `TTFINCR`, which performs two critical operations:

**1. Update TTF/8 (time-to-go divided by 8):**

```agc
# TTF/8 UPDATED FOR TIME SINCE LAST PASS:
#     TTF/8 = TTF/8 + (TPIP - TPIPOLD)/8
```

The time-to-go is stored divided by 8 for scaling reasons — keeping the value small enough to fit in the AGC's fractional arithmetic without overflow.

**2. Update the landing site vector for lunar rotation:**

```agc
# LANDING SITE VECTOR UPDATED FOR LUNAR ROTATION:
#     ____               ____   ____                   __
#     LAND = /LAND/ UNIT(LAND - LAND(TPIP - TPIPOLD) * WM)
```

The Moon is rotating beneath the LM during descent. `WM` is the lunar angular velocity vector. The code computes the cross product of `LAND` with `WM`, scales by the elapsed time, subtracts from `LAND`, normalizes, and rescales to the original magnitude (`/LAND/`). This keeps the landing site vector in the correct inertial position as the Moon rotates.

The implementation in interpreter code:

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

After computing the rotated landing vector in `LANDTEMP`, the code exits the interpreter and uses native AGC instructions with `FASTCHNG` (restart protection) to atomically update the live `LAND` vector:

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

The vector has three DP components (x, y, z), each stored as two consecutive words. `DXCH` (double exchange) atomically swaps two words between the A,L register pair and memory — six `DXCH` operations update the full 3D vector.

---

## 5. P63 — Braking Phase

### Pre-Guidance: CALCRGVG and RGVGCALC

P63 uses `CALCRGVG` for its first pass (coming from the ignition algorithm) and `RGVGCALC` for subsequent passes. The difference is that `CALCRGVG` first computes velocity from the integration output with a trim correction:

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

`VATT1` is the velocity from the integration routine, `REFSMMAT` is the reference-to-stable-member matrix, and `UNFC/2` is a trim correction term computed on the previous pass.

`RGVGCALC` then computes the state in guidance coordinates:

```agc
# VELOCITY RELATIVE TO THE SURFACE:
#     ANGTERM = V + R × WM
# STATE IN GUIDANCE COORDINATES:
#     RGU = CG*(R - LAND)
#     VGU = CG*(V - WM × R)
```

Where:
- `CG` is the guidance-to-platform coordinate transformation matrix
- `R` is the position vector
- `V` is the velocity vector  
- `WM` is the lunar angular velocity
- `LAND` is the landing site vector
- `RGU` and `VGU` are position and velocity in the guidance coordinate frame

The code also computes horizontal velocity for display:

```agc
# HORIZONTAL VELOCITY FOR DISPLAY:
#     VHORIZ = 8 ABVAL(0, VG₂, VG₁)
```

This forms a vector from the two horizontal components of the guidance velocity (zeroing the vertical component), takes its absolute value, and scales by 8. This is the value displayed to the astronaut during P65.

### Depression Angle (LOOKANGL)

```agc
# DEPRESSION ANGLE FOR DISPLAY:
#     LOOKANGL = ARCSIN(UNIT(R - LAND) · XNBPIP)
```

The code computes the angle between the line-of-sight to the landing site and the LM's X-axis (the body axis pointing "up" out of the ascent stage). This is the LPD (Landing Point Designator) angle displayed during P64.

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

The sine value (in MPAC from the dot product) is doubled, then `SPARCSIN` computes the arcsine. A half-degree offset (`1/2DEG = +.00278`) is added — likely a calibration correction for the LPD window markings. The result is multiplied by 180 to convert from the AGC's fractional-circle representation to degrees.

### TTF/8 Computation: The Root Finder

The heart of the braking guidance is the computation of TTF/8 (time-to-go divided by 8). This is done by finding the root of a cubic polynomial:

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

The coefficients A(0) through A(3) encode the guidance constraint equations. The subscript `2` denotes the vertical component (the third component in the guidance coordinate system, indexed by `+4` since each DP value occupies two words).

The polynomial is then solved using Newton's method via `ROOTPSRS`:

```agc
            EXTEND
            DCA     TTF/8
            DXCH    MPAC            # LOADS TTF/8 (INITIAL GUESS) INTO MPAC
            CAF     TWO             # DEGREE - ONE
            TS      L
            CAF     TABLTTFL
            TC      ROOTPSRS        # YIELDS TTF/8 IN MPAC
```

`ROOTPSRS` is a general-purpose double-precision root finder by Allan Klumpp (credited in the comments). It uses Newton's method with convergence checking and gives up after 8 iterations. The code documentation is unusually thorough:

```agc
# ROOTPSRS FINDS ONE ROOT OF THE POWER SERIES A(N)X^N + A(N-1)X^(N-1) + ... + A(1)X + A(0)
# USING NEWTON'S METHOD STARTING WITH AN INITIAL GUESS FOR THE ROOT.
```

The return convention is notable: normal return is to `TC ROOTPSRS + 3` (skipping two words), while failure to converge returns to `TC ROOTPSRS + 1`. This skip-on-success pattern allows the alarm handler to sit in the "fall-through" position:

```agc
            INDEX   WCHPHASE
            TCF     WHATALM         # BAD RETURN: alarm
            
            EXTEND                  # GOOD RETURN
            DCA     MPAC
            DXCH    TTF/8           # CORRECTED TTF/8
```

---

## 6. The Main Guidance Equation (QUADGUID)

This is the central guidance law, documented in the source comments:

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

This is a **quadratic guidance law** — it computes the commanded acceleration (`ACG`) as a function of:
- `ADG` — the desired (target) acceleration
- `VDG` — the desired (target) velocity
- `VG` — the current velocity (in guidance coordinates)
- `RDG` — the desired (target) position
- `RG` — the current position (in guidance coordinates)
- `TTF` — time to go (TTF/8 × 8)

The equation is algebraically identical in both forms. The "as programmed" form avoids explicit TTF² computation by nesting divisions by TTF/8, and the 3/4 factor absorbs scale differences.

### Lead-Time Compensation

Before the main equation, there's a subtle correction:

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

This computes a ratio that accounts for the computational lag — the time between when sensor data is sampled and when the computed thrust command takes effect. `LEADTIME` is negative (it represents how far ahead the guidance should "look"). The `POSMAX` addition followed by the `CS L / AD L` idiom clamps negative values to zero — a safeguard to prevent the ratio from going negative near touchdown.

The ratio and its square are then used to compute coefficients for each term of the guidance equation:

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

This chain of additions builds four distinct coefficients from combinations of the ratio and ratio². These coefficients modify the standard guidance equation to account for computational lag, effectively "predicting forward" so the thrust command is correct when it actually takes effect.

> **Uncertainty flag:** I can follow the algebra that produces these four coefficients, but I cannot independently verify that the specific combinations of `BUF` (ratio) and `BUF+1` (ratio²) produce the correct lead-time-compensated guidance law without access to the original Guidance System Operations Plan (GSOP) derivation. The pattern is consistent with a Taylor expansion of the guidance law evaluated at `t + lead_time` rather than `t`.

### The Guidance Computation Itself

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

In interpreter pseudo-code, this computes:

1. `coeff_vgu × VGU` — push to stack
2. `coeff_vdg × VDG` — push to stack
3. `(RDG - RGU) / TTF/8` — scaled range-to-go rate
4. Scale by `coeff_rdg`, add accumulated terms
5. Divide by `TTF/8` again, scale by 3/4
6. Add `coeff_adg × ADG` — the target acceleration

The result is the commanded acceleration vector in guidance coordinates.

### Gravity Compensation (AFCCALC1)

```agc
AFCCALC1    VXM     VSL1            # VERGUID COMES HERE
                    CG
            PDVL    V/SC
                    GDT/2
                    GSCALE
            BVSU    STADR
            STORE   UNFC/2          # UNFC/2 NEED NOT BE UNITIZED
```

The commanded acceleration is transformed from guidance coordinates to stable-member coordinates via the `CG` matrix (`VXM` = vector × matrix, `VSL1` = vector shift left 1 for scaling). Then gravitational acceleration (`GDT/2`, scaled by `GSCALE = 100 B-11`) is subtracted. The result `UNFC/2` is the force command that the engine must produce — it's the guidance command minus gravity, because gravity is "free" (the engine doesn't need to create it).

### Thrust Limiting (AFCCALC2)

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

This computes the maximum available horizontal acceleration: given the total available thrust (`HIGHESTF / MASS`) and the vertical and out-of-plane components already committed, how much acceleration is available in the downrange direction? If the answer would be negative (the engine can't provide enough thrust for the vertical and out-of-plane demands), the horizontal component is clamped to zero.

`HIGHESTF = 4.34546769 B-12` — this is the maximum thrust of the LM descent engine in the AGC's internal units.

---

## 7. CG Matrix: The Guidance Coordinate Frame

`CGCALC` erects the guidance-to-stable-member transformation matrix:

```agc
CGCALC      CAF     EBANK5
            TS      EBANK
            EBANK=  TCGIBRAK
            EXTEND
            INDEX   WCHPHASE
            INDEX   TARGTDEX
            DCA     TCGFBRAK
```

This double-indexed lookup retrieves a time parameter that depends on the current phase (braking vs. approach). The code then checks whether this time has been reached:

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

This is an AGC idiom for testing whether a DP value is non-negative. The double `CCS` tests both words — if either is positive, control goes to `EXTLOGIC` (skip the matrix update). Only when both words are non-positive (time has been reached) does the matrix get updated.

The matrix construction itself uses the landing site vector as the primary axis:

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

The first row of `CG` is `UNIT(LAND)` — the unit vector toward the landing site, which defines "down" in guidance coordinates.

The second row is constructed from the cross product of an adjusted range vector with `LAND`, then normalized. The "NUMERO MYSTERIOSO" comment refers to `GAINBRAK` — a gain constant whose derivation was apparently mysterious even to the programmers.

The third row is the cross product of rows 1 and 2, forming a right-handed orthogonal coordinate system.

> **Uncertainty flag:** The exact purpose of the `GAINBRAK` gain in the second row computation is unclear from the code alone. It appears to rotate the guidance frame based on the angular momentum term (`ANGTERM`), possibly to align the frame with the expected trajectory curvature. Without the GSOP derivation I cannot verify this interpretation.

---

## 8. Phase Transitions: P63 → P64 → P65/P66/P67

### EXTLOGIC: The Phase Switch

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

The transition condition is simple: when `TTF/8 + TENDBRAK ≤ 0` (tested via `BZMF` — Branch Zero or Minus to Fixed), the current phase's time-to-go has expired, and `WCHPHASE` is incremented. `TENDBRAK` is a negative number representing how far before the target time the transition should occur.

- **P63 → P64**: `WCHPHASE` goes from 0 to 1. `STARTP64` is called, which sets the program number to 64, augments TTF/8 by `DELTTFAP`, enables RUPT10 (for the redesignation hand controller), and initializes the redesignation flag.
- **P64 → P65**: `WCHPHASE` goes from 1 to 2. `P65START` sets program number to 65 and enables X-axis override.

### P65 → P66/P67

The transition from P65 to P66 or P67 is not time-based — it's driven by astronaut input, handled by GUILDENSTERN (see Section 3). When the astronaut engages the attitude-hold or manual throttle discretes, GUILDENSTERN switches the program mode while keeping `WCHPHASE = 2`.

Within `WCHPHASE = 2`, the variable `WCHVERT` selects among P65, P66, and P67:

```agc
VERTGUID    CCS     WCHVERT
            TCF     P67VERT         # POSITIVE NON-ZERO → P67
            TCF     P66VERT         # +0
# P65 falls through to P65VERT
```

This uses the CCS (Count, Compare, and Skip) four-way branch:
- `WCHVERT > 0` → P67 (manual throttle; `WCHVERT` is set to 10 by `STARTP67`)
- `WCHVERT = +0` → P66 (rate of descent)
- `WCHVERT < 0` → P65 falls through (automatic vertical descent; `WCHVERT` is set to -2 by `P65START`)

---

## 9. P64 — Approach Phase with Redesignation

### Landing Point Redesignation (REDESIG)

During P64, the astronaut can redesignate the landing point using the hand controller. The redesignation logic is the pre-guidance computation for the approach phase:

```agc
REDESIG     CA      FLAGWRD6        # IS REDFLAG SET?
            MASK    REDFLBIT
            EXTEND
            BZF     RGVGCALC        # NO: SKIP REDESIGNATION LOGIC

            CA      TREDES          # YES: HAS TREDES REACHED ZERO?
            EXTEND
            BZF     RGVGCALC        # YES: SKIP REDESIGNATION LOGIC
```

Two conditions must be met: `REDFLAG` must be set (enabled by P64CEED when the astronaut "proceeds" on the flashing display), and `TREDES` must be non-zero (it counts down to zero as TTF decreases — redesignation is disabled near the end of the approach).

The redesignation itself modifies the `LAND` vector:

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

`ELINCR1` and `AZINCR1` are the accumulated elevation and azimuth increments from the hand controller (accumulated by the PITFALL interrupt handler, discussed below). They are atomically transferred to working copies and zeroed under interrupt inhibit (`INHINT`). This is a classic double-buffer pattern for safely passing data from an interrupt handler to a main-loop computation.

The redesignation math moves the landing point along the LOS (line of sight):

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

The elevation increment rotates the LOS around the LM's Y body axis (cross-range), while the azimuth increment moves it along the Y body axis. A depression angle check prevents the redesignated point from being too close to the horizon:

```agc
            DLOAD   DSU             # MAKE SURE REDESIGNATION IS NOT
                    0               #   TOO CLOSE TO THE HORIZON.
                    DEPRCRIT
            BMN     DLOAD
                    REDES1
                    DEPRCRIT
            STORE   0
```

`DEPRCRIT = -.02 B-1` — the critical depression angle. If the computed depression is below this threshold, it's clamped.

### The PITFALL Interrupt Handler: Redesignator Trap

```agc
PITFALL     XCH     BANKRUPT
            EXTEND
            QXCH    QRUPT

            TC      CHECKMM         # IF NOT IN P64, NO REASON TO CONTINUE
            DEC     64
            TCF     RESUME
```

`PITFALL` is the RUPT10 handler — it fires when the astronaut moves the redesignation hand controller. It first checks that we're actually in P64 (there's no reason to process redesignation inputs in other programs), and resumes if not.

If in P64, it reads the controller bits, sets up a monitoring task, and returns:

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

The names `ELVIRA` and `ZERLINA` are opera character references — `ELVIRA` from Mozart's *Don Giovanni*, `ZERLINA` from the same opera. `ELVIRA` holds the current state of the controller bits; `ZERLINA` is a timeout counter.

`REDESMON` (Redesignator Monitor) polls the controller at intervals, waiting for the astronaut to release the switch:

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

When the switch is released (bits disappear), `COUNT'EM` accumulates the azimuth and elevation increments:

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

Each "click" of the controller adds a fixed increment:
- `AZEACH = .03491` — 2 degrees of azimuth per click
- `ELEACH = .00873` — 0.5 degrees of elevation per click

The bit assignments are documented:

```agc
+ELBIT      =       BIT2            # -PITCH
-ELBIT      =       BIT1            # +PITCH
+AZBIT      =       BIT5
-AZBIT      =       BIT6
```

Note the inversion: `+ELBIT` corresponds to `-PITCH`. The LPD window markings were calibrated so that "pitch down" (negative pitch) moved the landing point further away (positive elevation in the LPD frame).

---

## 10. P66 — Rate of Descent Mode

P66 is the semi-automatic landing mode. The computer controls attitude to maintain vertical descent; the astronaut controls descent rate via the ROD (Rate of Descent) switch.

### ROD Task

```agc
RODTASK     CAF     PRIO22
            TC      FINDVAC
            EBANK=  DVCNTR
            2CADR   RODCOMP

            TCF     TASKOVER
```

`RODTASK` runs every second (scheduled by `TWIDDLE` with a 1-second delay) at priority 22. It spawns the `RODCOMP` job to compute the ROD guidance.

### RODCOMP: The ROD Computation

```agc
RODCOMP     INHINT
            CAF     ZERO
            XCH     RODCOUNT
            EXTEND
            MP      RODSCAL1
            DAS     VDGVERT         # UPDATE DESIRED ALTITUDE RATE.
```

`RODCOUNT` accumulates clicks from the ROD switch (via the `DESCBITS` interrupt handler). Each click adds or subtracts from the desired vertical rate `VDGVERT`. The count is atomically read and zeroed under interrupt inhibit.

The ROD trap handler is elegantly simple:

```agc
DESCBITS    MASK    BIT7            # BIT 7 = - RATE INCREMENT
            CCS     A               # BIT 6 = + INCREMENT
            CS      TWO
            AD      ONE
            ADS     RODCOUNT
            TCF     RESUME          # TRAP IS RESET WHEN SWITCH IS RELEASED
```

Bit 7 means "decrease rate" (descend faster), bit 6 means "increase rate" (descend slower or ascend). The `CCS / CS TWO / AD ONE` pattern converts: if bit 7 present, A is positive after `CCS`, so `CS TWO` = -2, `AD ONE` = -1; if bit 7 absent (bit 6 must be present), A is zero after `CCS`, so skip to `AD ONE` = +1. Each click changes `RODCOUNT` by ±1.

### P66 Guidance Law

The P66 guidance is substantially more complex than P63/P64. It runs in `RODCOMP` and performs:

1. **PIPA reading and bias correction** — reads the three accelerometer channels, applies bias corrections
2. **Velocity update** — integrates acceleration to get current velocity, applying gravity compensation
3. **Altitude rate computation** — dots the velocity with the unit position vector to get HDOT (altitude rate)
4. **Altitude update** — computes current altitude
5. **Throttle command** — computes the required thrust to achieve the desired descent rate

The throttle law:

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

The altitude rate error (`VDGVERT - HDOTDISP`) is divided by `TAUROD` (a time constant) to get the commanded acceleration. This is a simple proportional controller: if the actual descent rate differs from the desired rate, command an acceleration proportional to the error.

The throttle computation also includes thrust limits:

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

The commanded acceleration is clamped between `MINFORCE/MASS` and `MAXFORCE/MASS` — the LM descent engine had a minimum throttle setting (about 10% — the engine couldn't be throttled below this without instability) and a maximum.

> **Uncertainty flag:** The P66 guidance law involves multiple intermediate computations (the `ITRPNT1` and `ITRPNT2` labels suggest this was iteratively developed). The exact scaling of the PIPA readings, the lag compensation via `LAG/TAU`, and the `SHFTFACT`/`SCALEFAC` constants would require cross-referencing with the GSOP and the PIPA calibration data to fully verify. The overall structure — proportional altitude-rate control with thrust limiting — is clear, but the numerical precision of each intermediate step is difficult to verify from the code alone.

---

## 11. P65 — Automatic Vertical Descent

P65 is the simplest guidance mode — a linear velocity tracking law:

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

The commanded acceleration is simply the velocity error divided by a time constant. `V2FG` is the target velocity vector for vertical descent, `VGU` is the current velocity in guidance coordinates, and `TAUVERT` is the guidance time constant. This drives the LM toward the desired vertical descent velocity profile.

The `GOTO AFCCALC1` shares the gravity compensation and thrust computation with the quadratic guidance.

---

## 12. P67 — Manual Throttle

P67 gives the astronaut full manual control:

```agc
P67VERT     TC      PHASCHNG        # TERMINATE GROUP 3.
            OCT     00003

            TC      INTPRET
            VLOAD   GOTO
                    V
                    VHORCOMP
```

P67 terminates the guidance group (group 3 — no more automatic guidance) and goes directly to `VHORCOMP`, which only computes the horizontal velocity for display purposes. The astronaut controls both attitude and throttle manually. The computer's only role is computing and displaying `VHORIZ` (horizontal velocity) so the astronaut knows when to cut the engine.

---

## 13. Display Updates

### P63 Display: V06N63

```agc
P63DISPS    CAF     V06N63
DISPCOMN    TC      BANKCALL
            CADR    REGODSPR
```

Verb 06 Noun 63 displays:
- R1: Altitude rate (HDOTDISP)
- R2: Altitude (HCALC1)  
- R3: (flight-specific, typically lateral velocity)

### P64 Display: V06N64 (Flashing)

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

The P64 display is **flashing** until the astronaut "proceeds" (presses PRO on the DSKY), which enables the redesignation logic. This is a deliberate human-factors design: the astronaut must actively confirm they want to take control of landing point selection. After proceeding, the display becomes static (non-flashing).

`REFLASHR` returns to one of three locations depending on the astronaut's response:
- TERMINATE (first return) → `GOTOPOOH` (abort to idle)
- PROCEED (second return) → `P64CEED` (enable redesignation)
- RECYCLE (third return) → `P64DISPS` (refresh display)

### P65/P66/P67 Display: V06N60

```agc
VERTDISP    CAF     V06N60
            TCF     DISPCOMN
```

Verb 06 Noun 60 displays altitude rate, altitude, and (for P66) the current descent rate command.

### Display Suppression

```agc
DISPEXIT    EXTEND
            DCA     NEG0
            DXCH    -PHASE3

 +3         CS      FLAGWRD8        # IF FLUNDISP IS SET, NO DISPLAY THIS PASS
            MASK    FLUNDBIT
            EXTEND
            BZF     ENDLLJOB
```

The display is killed every cycle (`-PHASE3` is set to -0, terminating group 3's restart protection) and restored by the next guidance cycle. The `FLUNDISP` flag can suppress displays entirely — used during critical phases where display updates would waste precious CPU time.

---

## 14. Window Vector and Steering

### EXBRAK: Braking Phase Exit

```agc
EXBRAK      TC      INTPRET
            VLOAD
                    UNIT/R/
            STORE   UNWC/2
            EXIT
            TCF     STEER?
```

During braking, the window pointing vector is simply `UNIT(R)` — point the LM's window straight up (away from the Moon). This is the "window up" attitude used during the braking burn.

### EXNORM: Normal Exit (P64)

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

During approach, the window vector is `UNIT(LAND - R)` — point toward the landing site. This is then blended with a backup vector based on the projection angle:

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

The blending uses `PROJMAX` (sin 25°/8) and `PROJMIN` (sin 15°/8) to create a smooth transition between the landing-site-pointing vector and a backup vector (row 3 of the CG matrix) when the look angle is between 15° and 25°. Below 15°, the landing site is too close to the horizon and the backup vector takes over entirely.

The actual blending loop:

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

This loops over the three components (Q = 4, 2, 0) of the window vector, blending the two candidate vectors by their respective coefficients.

### Steering and Throttle

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

If the steering switch is off, or if overflow occurred anywhere in the guidance computations, no commands are issued. Alarm code 01410 signals a guidance overflow — this is non-abortive (the system continues on the next cycle rather than triggering an abort).

If all is well:

```agc
GDUMP1      TC      THROTTLE
            TC      INTPRET
            CALL
                    FINDCDUW -2
            EXIT
```

`THROTTLE` commands the descent engine, and `FINDCDUW` computes the CDU (coupling display unit) commands to steer the LM to the desired attitude.

---

## 15. The Root Finder (ROOTPSRS)

Allan Klumpp's double-precision Newton's method root finder deserves special attention. It is a general-purpose subroutine that finds a root of an Nth-degree polynomial. The landing guidance uses it to solve the cubic time-to-go equation.

### Setup

```agc
ROOTPSRS    EXTEND
            QXCH    RETROOT         # SAVE RETURN ADDRESS
            TS      PWRPTR          # POWER TABLE POINTER
            DXCH    MPAC +3         # PWR TABLE ADRES, N-1
            CA      DERTABLL
            TS      DERPTR          # DERIVATIVE TABLE POINTER
```

### Derivative Coefficient Table

Before iterating, ROOTPSRS pre-computes the derivative coefficients by multiplying each A(i) by i:

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

### Newton Iteration

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

Each iteration: evaluate the polynomial and its derivative at the current guess, compute the Newton step `dx = -f(x)/f'(x)`, and update the root.

### Convergence Check

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

`MODE` is used as an iteration counter. `BIT4` (value 8) is tested — when MODE reaches 8, the mask produces a non-zero value and `CCS` branches to `BADROOT`. The convergence test checks whether `|DX| - DXCRIT ≤ 0` using the CCS four-way skip on both the high and low words.

The precautions documented in the comments are remarkable for 1960s software:

```
# PRECAUTION: ROOTPSRS MAKES NO CHECKS FOR OVERFLOW OR FOR IMPROPER 
# USAGE. IMPROPER USAGE COULD PRECLUDE CONVERGENCE OR REQUIRE EXCESSIVE 
# ITERATIONS.
```

This is essentially a "here be dragons" warning — the routine trusts its caller to provide well-scaled inputs.

---

## 16. The FASTCHNG Subroutine

This tiny subroutine appears throughout the file and deserves explanation:

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

This is a "specialized PHASCHNG routine" — a fast version of the phase change protection that avoids the overhead of the full PHASCHNG subroutine. It stores the current location as a restart point in PHSNAME3 (group 3's phase name). The trick is that `DXCH L` exchanges the A,L pair with the L register and the word after it — but since A was loaded with EBANK3 and the return address is in Q (implicitly, since TC was used to call FASTCHNG), this atomically records the restart point.

The `TC A` at the end is the return — A contains the saved EBANK value, and `TC A` transfers control to the address in A. Wait — that's not right. Let me re-examine.

Actually, looking more carefully: `CA EBANK3` loads A with the EBANK3 constant. `XCH EBANK` swaps A with the EBANK register — now A has the old EBANK value, EBANK is set to bank 3 (where PHSNAME3 lives). `DXCH L` is `DXCH 1` — it exchanges A,L with registers L and Q. So now the old EBANK is in L, and the return address (from Q) is saved. `TS PHSNAME3` stores the return address (which was in A after the DXCH rearrangement) as the restart phase. `LXCH EBANK` restores the original EBANK. `TC A` returns... but A now holds the value that was written to PHSNAME3.

> **Uncertainty flag:** The exact register dance in FASTCHNG is tricky. The net effect is clear — it records the caller's address as a group 3 restart point — but the precise flow through the DXCH involving registers A, L, and Q requires careful cycle-by-cycle analysis that I may have the details wrong on. The key point is that this is a performance optimization: it does in ~7 instructions what the general `PHASCHNG` subroutine does in many more.

---

## 17. Constants and Scaling

```agc
HIGHESTF    2DEC    4.34546769 B-12
```

Maximum thrust force of the LM descent engine, scaled by 2^-12. In the AGC's fractional arithmetic, this represents the thrust in internal units (likely tens of thousands of pounds scaled to fit in the 0-1 range).

```agc
GSCALE      2DEC    100 B-11
```

Gravity scaling factor. 100 × 2^-11 — used to convert the gravity vector to guidance units.

```agc
3/8DP       2DEC    .375
3/4DP       2DEC    .750
```

Fractional constants used in the guidance equations. These avoid multiplication by integers (which would overflow the fractional representation) by expressing them as fractions.

```agc
DEPRCRIT    2DEC    -.02 B-1
```

Depression angle criterion for redesignation limiting — approximately -1.15 degrees (-.02 radians scaled by B-1 = 2^-1).

```agc
PROJMAX     DEC     .42262 B-3      # SIN(25°)/8
PROJMIN     DEC     .25882 B-3      # SIN(15°)/8
```

Window vector blending thresholds. The B-3 scaling means these are actually sin(angle)/8, matching the 1/8 scaling used in the projection computation.

```agc
AZEACH      DEC     .03491          # 2 DEGREES
ELEACH      DEC     .00873          # 1/2 DEGREE
```

Redesignation increments per hand controller click. These are in radians (0.03491 rad ≈ 2°, 0.00873 rad ≈ 0.5°). The asymmetry is deliberate: azimuth (left-right) changes need larger increments because the landing site moves less per degree of azimuth change, while elevation (near-far) is more sensitive.

```agc
BIASFACT    2DEC    655.36 B-28
```

PIPA bias scaling factor. 655.36 × 2^-28 — converts PIPA bias values to the velocity units used in the ROD computation.

---

## 18. Historical Notes and Easter Eggs

### GUILDENSTERN (and ROSENSTERN, elsewhere)

The Shakespeare/Stoppard reference is the most famous naming in the codebase. The routines that monitor automatic mode switching are named after characters who are buffeted by events beyond their control — an apt metaphor for mode-switching logic that must respond to whatever the astronaut does.

### "TEMPORARY, I HOPE HOPE HOPE"

```agc
            TC      BANKCALL        # TEMPORARY, I HOPE HOPE HOPE
            CADR    STOPRATE        # TEMPORARY, I HOPE HOPE HOPE
```

This call to `STOPRATE` at the start of vertical descent initialization was meant to be temporary — a quick fix to zero the attitude rates when entering P65/P66/P67. The programmer's triple "HOPE" expresses the universal programmer's lament: nothing is more permanent than a temporary fix. It flew on Apollo 11 exactly as written.

### ELVIRA and ZERLINA

The redesignation monitor uses opera character names for its state variables — `ELVIRA` holds the current controller state, `ZERLINA` is a debounce timeout counter. Both characters are from Mozart's *Don Giovanni*. This naming convention was common in MIT Instrumentation Lab code — variable names were chosen to be memorable and distinctive rather than descriptive.

### "NUMERO MYSTERIOSO"

```agc
            DMP*    VXSC
                    GAINBRAK,1      # NUMERO MYSTERIOSO
```

The programmer who wrote this comment didn't fully understand where the gain constant came from — it was derived from trajectory analysis and simply provided as a magic number. The candor is refreshing: rather than pretending to understand it, they flagged it honestly.

### Alarm Code 01406

```agc
1406P00     TC      POODOO
            OCT     01406
1406ALM     TC      ALARM
            OCT     01406
            TCF     RATESTOP
```

Alarm 1406 indicates that the TTF/8 root finder failed to converge. During the ignition algorithm (IGNALG), this is fatal — `POODOO` triggers a program alarm and goes to P00 (idle). During braking or approach, it's non-fatal — the alarm is sounded but guidance continues with rate-damping (`RATESTOP`).

The name `POODOO` for the fatal error handler is another example of MIT IL's colorful naming. It's used throughout the codebase for unrecoverable errors.

---

## 19. Control Flow Summary

```
LUNLAND (from SERVOUT, ~2 Hz)
  │
  ├── GUILDENSTERN: Check astronaut mode switches
  │     ├── Manual throttle? → P67
  │     ├── Attitude hold + was P67? → P66
  │     ├── Attitude hold + ROD clicked? → P66
  │     └── Continue current program
  │
  ├── GUILDRET: Initialize pass
  │     ├── Save TPIP timestamps
  │     ├── Copy TTF/8 to working copy
  │     └── Check FLPASS0
  │
  ├── NEWPHASE[WCHPHASE]: Start new phase if needed
  │     ├── IGNALG/BRAKQUAD → TTFINCR
  │     ├── APPRQUAD → STARTP64
  │     └── VERTICAL → P65START
  │
  ├── TTFINCR: Update time-to-go and landing site
  │
  ├── PREGUIDE[WCHPHASE]: Pre-guidance
  │     ├── IGNALG → CALCRGVG (compute V from integration)
  │     ├── BRAKQUAD/VERTICAL → RGVGCALC
  │     └── APPRQUAD → REDESIG → RGVGCALC
  │
  ├── WHATGUID[WCHPHASE]: Guidance equations
  │     ├── IGNALG/BRAKQUAD/APPRQUAD → TTF/8CL → QUADGUID
  │     └── VERTICAL → VERTGUID
  │           ├── P65VERT (linear velocity tracking)
  │           ├── P66VERT → RODCOMP (rate of descent)
  │           └── P67VERT (display only)
  │
  ├── AFTRGUID[WCHPHASE]: Post-guidance
  │     ├── IGNALG/BRAKQUAD/APPRQUAD → CGCALC → EXTLOGIC
  │     └── VERTICAL → STEER?
  │
  ├── WHATEXIT[WCHPHASE]: Exit/window vector
  │     ├── EXGSUB (ignition algorithm return)
  │     ├── EXBRAK (window = UNIT(R))
  │     └── EXNORM (window = blend toward LAND)
  │
  ├── STEER? → THROTTLE → FINDCDUW
  │
  └── WHATDISP[WCHPHASE]: Display
        ├── P63DISPS → V06N63
        ├── P64DISPS → V06N64 (flashing until PROCEED)
        └── VERTDISP → V06N60
```

---

## 20. What This Code Actually Did on July 20, 1969

At 20:05 UTC, the LM *Eagle* began powered descent. P63 (braking) fired the descent engine to slow from orbital velocity. The quadratic guidance law in `QUADGUID` computed thrust commands every ~2 seconds, while `TTFINCR` tracked time-to-go and compensated for lunar rotation.

At approximately 7,000 feet, P64 (approach) took over. Neil Armstrong saw through the LPD window that the computer was targeting a boulder field at the edge of West Crater. He used the redesignation hand controller — processed by `PITFALL` and `REDESMON`, accumulated in `ELINCR1`/`AZINCR1`, and applied in `REDESIG` — to move the landing point. The DSKY displayed the LPD angle (`LOOKANGL`) via Noun 64.

At approximately 500 feet, P66 (rate of descent) engaged. Armstrong used the ROD switch — processed by `DESCBITS`, accumulated in `RODCOUNT`, applied in `RODCOMP` — to control descent rate while the computer maintained attitude. `VDGVERT` tracked his desired rate; `TAUROD` governed how aggressively the computer achieved it.

The "1202" and "1201" program alarms that occurred during the descent were NOT in this file — they came from the Executive's job-overflow detection. But the guidance in this file kept running through those alarms, because the restart protection (`PHASCHNG`, `FASTCHNG`) ensured that each guidance cycle could be restarted from a known state.

At 20:17 UTC, with about 25 seconds of fuel remaining, Armstrong heard "Contact light" as a 67-inch probe dangling from a landing leg touched the surface. He hit the ENGINE STOP button. The code in this file had done its job.

---

## Appendix: Glossary of Key Variables

| Variable | Type | Description |
|----------|------|-------------|
| `WCHPHASE` | SP | Phase selector: -1=IGNALG, 0=BRAK, 1=APPR, 2=VERT |
| `WCHVERT` | SP | Vertical mode: <0=P65, 0=P66, >0=P67 |
| `TTF/8` | DP | Time-to-go / 8 (centiseconds, scaled) |
| `LAND` | Vector (3×DP) | Landing site position vector (inertial, lunar-fixed) |
| `/LAND/` | DP | Magnitude of LAND vector |
| `R` | Vector | Current LM position |
| `V` | Vector | Current LM velocity |
| `RGU` | Vector | Position in guidance coordinates |
| `VGU` | Vector | Velocity in guidance coordinates |
| `CG` | Matrix (3×3) | Guidance-to-stable-member transformation |
| `ANGTERM` | Vector | V + R × WM (velocity relative to surface) |
| `UNFC/2` | Vector | Commanded force / 2 (half the thrust command) |
| `/AFC/` | DP | Magnitude of commanded acceleration (for throttle) |
| `UNWC/2` | Vector | Window pointing vector / 2 |
| `VDGVERT` | DP | Desired vertical velocity (P66 ROD target) |
| `HDOTDISP` | DP | Current altitude rate (for display) |
| `RODCOUNT` | SP | Accumulated ROD switch clicks |
| `ELINCR1` | DP | Accumulated elevation redesignation increment |
| `AZINCR1` | DP | Accumulated azimuth redesignation increment |
| `FLPASS0` | SP | Pass counter within current phase |
| `WM` | Vector | Lunar angular velocity |
| `REFSMMAT` | Matrix | Reference-to-stable-member matrix |