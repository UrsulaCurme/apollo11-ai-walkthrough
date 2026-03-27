# BURN, BABY, BURN — Master Ignition Routine

## The Code That Lit the Engine

This is the file that controlled engine ignition for the Lunar Module — the routine that fired the Descent Propulsion System (DPS) so Neil Armstrong and Buzz Aldrin could begin their powered descent to the Sea of Tranquility. It is also one of the most culturally rich files in the entire AGC codebase: a place where 1960s counterculture, Latin inscriptions, and meticulous systems engineering share the same pages.

The routine was "conceived and executed, and (NOTA BENE) is maintained by Adler and Eyles" — Peter Adler and Don Eyles, two MIT Instrumentation Laboratory engineers who built the ignition sequencing for every engine burn the Lunar Module would ever perform.

---

## 1. Technical Function

### 1.1 What This Routine Actually Does

BURN_BABY_BURN is the **Master Ignition Routine** — a generalized engine ignition sequencer used by five different LM programs:

| Program | Purpose |
|---------|---------|
| **P12** | Powered Ascent (abort from surface) |
| **P40** | DPS Burn (general purpose) |
| **P42** | APS Burn (Ascent Propulsion System) |
| **P61** | Not present in this table set, but referenced in comments |
| **P63** | Braking Phase of Lunar Descent — *the landing burn* |

Rather than writing separate ignition code for each program, Adler and Eyles built a **table-driven architecture**. Each program provides a table of constants and branch addresses, and the ignition routine indexes into these tables using the erasable register `WHICH` to customize its behavior.

### 1.2 The Table-Driven Design

The tables are the first thing in the file, and they're elegant. Each table entry at a given offset serves a specific purpose:

```
P63TABLE    VN      0662            # (0)  Verb-Noun for display
            TCF     ULLGNOT         # (1)  Ullage setup branch
            TCF     COMFAIL3        # (2)  Communication failure handler
            TCF     V99RECYC        # (3)  Response to astronaut "ENTER"
            TCF     TASKOVER        # (4)  Task termination
            TCF     P63SPOT         # (5)  Program-specific spot entry
            DEC     2240            # (6)  Ullage duration (centiseconds)
            EBANK=  WHICH
            2CADR   SERVEXIT        # (7)  AVERAGEG exit address
            TCF     DISPCHNG        # (11) Display change handler
            TCF     WAITABIT        # (12) Wait handler
            TCF     P63IGN          # (13) Program-specific ignition handler
```

The routine accesses these via `INDEX WHICH` followed by `TCF`, `CA`, or `DCA` with the table offset. For example:

```agc
        INDEX   WHICH
        TCF     5               # Jump to program-specific spot (offset 5)
```

This is a **vtable** — a virtual dispatch table, implemented in 1960s assembly language. The pattern is identical in concept to what a C++ compiler generates for virtual method calls. Each program "inherits" the master ignition behavior and "overrides" specific slots.

Note the alias definitions that make multiple programs share the same entry points:

```agc
P42SPOT     =       P40SPOT         # (5)
P12SPOT     =       P40SPOT         # (5)
P63SPOT     =       P41SPOT         # (5)  IN P63 CLOKTASK ALREADY GOING
```

### 1.3 The Ignition Timeline

The routine orchestrates a precise countdown sequence. Here is the timeline, reconstructed from the code:

#### TIG - 45 seconds: Entry (`BURNBABY`)

```agc
BURNBABY    TC      PHASCHNG        # GROUP 4 RESTARTS HERE
            OCT     04024

            CAF     ZERO            # EXTIRPATE JUNK LEFT IN DVTOTAL
            TS      DVTOTAL
            TS      DVTOTAL +1
```

The word "EXTIRPATE" — meaning to root out and destroy completely — is not your typical assembly comment. This is the voice of Adler or Eyles. They're zeroing out `DVTOTAL` (accumulated delta-V) so the burn starts with a clean slate.

The routine then:
1. Calls `P40AUTO` to verify the astronaut has the correct control modes set (PGNCS and AUTO)
2. Stores the nominal TIG (Time of IGnition) for obliquity compensation
3. Commands engine off via `ENGINOF3` (safety: ensure engine is off before sequencing)
4. Dispatches to the program-specific "spot" via `INDEX WHICH / TCF 5`

#### TIG - 30 seconds: State Vector Propagation (`P41SPOT`)

For programs that need it (P41/P63), the routine enters the **interpreter** to propagate the CSM state vector:

```agc
P41SPOT     TC      INTPRET         # (5)
            DLOAD   DSU
                TIG
                D29.9SEC
            STCALL  TDEC1
                INITCDUW
            BOFF    CALL
                MUNFLAG
                GOMIDAV
                CSMPREC
```

This is interpreter code — note the `TC INTPRET` transition and the subsequent use of `DLOAD`, `DSU`, `STCALL`, `BOFF`, `VLOAD`, `MXV`, etc. It computes the CSM's predicted position and velocity at TIG-29.9 seconds, transforms them into the reference coordinate system via `REFSMMAT`, and stores the results as `V(CSM)`, `R(CSM)`, and `G(CSM)`.

The `BOFF MUNFLAG` test checks whether the Moon's gravity field is relevant. If `MUNFLAG` is clear, it skips the CSM precision integration (`CSMPREC`) and goes directly to `GOMIDAV`.

If TIG gets slipped (the integration took too long), the code resets TIG:

```agc
            EXTEND              # TIG WAS SLIPPED, SO RESET TIG TO 29.9
            DCA     PIPTIME1    # SECONDS AFTER THE TIME TO WHICH WE DID
            DXCH    TIG         # INTEGRATE.
            EXTEND
            DCA     D29.9SEC
            DAS     TIG
```

This is a critical safety feature: if computation runs long, TIG is pushed forward rather than attempting a late ignition.

#### TIG - 35 seconds: DSKY Blanking (`TIG-35`)

```agc
TIG-35      CAF     5SEC
            TC      TWIDDLE
            ADRES   TIG-30

            ...
            CS      BLANKDEX        # BLANK DSKY FOR 5 SECONDS
            TS      DISPDEX
```

The DSKY display is blanked for 5 seconds to signal the astronaut that Average-G (the accelerometer integration service) is starting. This is a **human interface convention** — a visual cue that something important is happening.

The routine also checks ullage time at this point:

```agc
            INDEX   WHICH
            CS      6               # CHECK ULLAGE TIME.
            EXTEND
            BZMF    TASKOVER        # Skip if ullage time ≤ 0
```

If the table entry at offset 6 is negative (like P41's `-1`), there's no ullage to perform.

#### TIG - 30 seconds: Countdown Display and Ullage Setup (`TIG-30`)

```agc
TIG-30      CAF     S24.9SEC
            TC      TWIDDLE
            ADRES   TIG-5

            CS      CNTDNDEX        # START UP CLOKTASK AGAIN
            TS      DISPDEX
```

Sets up a task to fire at TIG-5, restarts the countdown clock display, and — critically — sets up the ullage task:

```agc
            INDEX   WHICH           # PICK UP APPROPRIATE ULLAGE -- ON TIME
            CA      6
            EXTEND
            BZMF    ULLGNOT         # DON'T SET UP ULLAGE IF DT IS NEG OR ZERO
            TS      SAVET-30        # SAVE DELTA-T FOR RESTART
            TC      TWIDDLE
            ADRES   ULLGTASK
```

**Ullage** is the practice of firing small RCS (Reaction Control System) thrusters to settle propellant at the bottom of the tanks before main engine ignition. Without it, the engine might ingest gas bubbles. The ullage duration comes from the program table (offset 6): P40 and P63 use `DEC 2240` (22.40 seconds, meaning ullage starts at TIG-7.5 for a ~7.5 second burn before ignition), while P42 uses `DEC 2640` (26.40 seconds).

#### TIG - 7.5 seconds: Ullage On (`ULLGTASK`)

```agc
ULLGTASK    TC      ONULLAGE        # THIS COMES AT TIG-7.5 OR TIG-3.5
            TC      PHASCHNG
            OCT     1
            TCF     TASKOVER
```

`ONULLAGE` sets the ullage bit in `DAPBOOLS`, telling the Digital Autopilot to fire the RCS jets:

```agc
ONULLAGE    CS      DAPBOOLS        # TURN ON ULLAGE.
            MASK    ULLAGER
            ADS     DAPBOOLS
            TC      Q
```

#### TIG - 5 seconds: Engine Enable Request (`TIG-5`)

```agc
TIG-5       EXTEND
            DCA     NEG0            # INSURE THAT GROUP 3 IS INACTIVE.
            DXCH    -PHASE3

            CAF     5SEC
            TC      TWIDDLE
            ADRES   TIG-0

            TC      DOWNFLAG        # RESET IGNFLAG AND ASINFLAG
            ADRES   IGNFLAG
            TC      DOWNFLAG
            ADRES   ASTNFLAG
```

Clears `IGNFLAG` and `ASTNFLAG` (astronaut flag), then dispatches to the program-specific handler at offset 11. For P40/P42, this may start the S40.13 targeting routine. The display switches to verb 99 ("PLEASE ENABLE ENGINE") — asking the astronaut for permission to light the engine.

#### TIG - 0: Ignition Decision (`TIG-0`)

```agc
TIG-0       CS      FLAGWRD7        # SET IGNFLAG SINCE TIG HAS ARRIVED
            MASK    IGNFLBIT
            ADS     FLAGWRD7

            ...

IGNYET?     CAF     ASTNBIT         # CHECK ASTNFLAG: HAS ASTRONAUT RESPONDED
            MASK    FLAGWRD7        # TO OUR ENGINE ENABLE REQUEST?
            EXTEND
            INDEX   WHICH
            BZF     12              # BRANCH IF HE HAS NOT RESPONDED YET
```

This is the **critical safety gate**: the code checks `ASTNFLAG` to see if the astronaut has pressed PROCEED in response to the V99 "PLEASE ENABLE ENGINE" display. If the astronaut hasn't responded, it branches to `WAITABIT` (offset 12), which kills group 4 and waits. The engine **will not fire** without astronaut consent.

### 1.4 Engine Interface — The Actual Ignition

When the astronaut has confirmed and TIG arrives, execution reaches `IGNITION`:

```agc
IGNITION    CS      FLAGWRD5        # INSURE ENGONFLG IS SET.
            MASK    ENGONBIT
            ADS     FLAGWRD5
            CS      PRIO30          # TURN ON THE ENGINE.
            EXTEND
            RAND    DSALMOUT
            AD      BIT13
            EXTEND
            WRITE   DSALMOUT
```

This is the moment. Let's trace the I/O:

1. **`CS PRIO30`** — loads the complement of priority 30 (octal 37777 minus 30000 = a mask). Actually, `PRIO30` is octal 37777 as a priority constant; `CS` complements it to create a mask that clears certain bits.
2. **`RAND DSALMOUT`** — reads I/O channel `DSALMOUT` (channel 11, the engine command channel) and ANDs it with A, preserving existing bits while clearing the engine bit position.
3. **`AD BIT13`** — sets bit 13, which is the **engine on** command.
4. **`WRITE DSALMOUT`** — writes the result back to the channel, commanding the engine to fire.

The engine fires via **I/O channel 11 (DSALMOUT)**, bit 13. This is a read-modify-write pattern to avoid disturbing other bits on the channel (which control other discrete outputs like the DSKY alarm).

Immediately after ignition, the code timestamps the event and updates TIG:

```agc
            EXTEND              # SET TEVENT FOR DOWNLINK
            DCA     TIME2
            DXCH    TEVENT

            EXTEND              # UPDATE TIG USING TGO FROM S40.13
            DCA     TGO
            DXCH    TIG
            EXTEND
            DCA     TIME2
            DAS     TIG
```

### 1.5 Program-Specific Post-Ignition: P63 (Lunar Landing)

For the lunar landing burn (P63), the post-ignition sequence is particularly involved:

```agc
P63IGN      EXTEND              # (13) INITIATE BURN DISPLAYS
            DCA     DSP2CADR
            DXCH    AVGEXIT

            CA      Z               # ASSASSINATE CLOKTASK
            TS      DISPDEX
```

"ASSASSINATE CLOKTASK" — they don't just stop it, they *assassinate* it. Setting `DISPDEX` to the current value of Z (which is positive, since it's a program counter address) causes `CLOKTASK` to detect the positive value and terminate itself on its next cycle.

The P63 ignition handler then:
- Sets `LETABBIT` in `FLAGWRD9` — enables P70/P71 (abort programs)
- Sets `SWANDBIT` in `FLAGWRD7` — enables the R10 landing display (altitude/altitude-rate)
- Clears minimum-impulse mode in `DAPBOOLS` — ensures the DAP uses normal thrust
- Initializes `WCHPHASE` and `FLPASS0` for the descent guidance phases
- Falls through to `P42IGN`

### 1.6 Throttle-Up: P63ZOOM and P40ZOOM

For P63, a delayed throttle-up is scheduled at TIG-0:

```agc
            CA      ZOOMTIME
            TC      WAITLIST
            EBANK=  DVCNTR
            2CADR   P63ZOOM
```

When `P63ZOOM` fires (26 seconds after ignition per the file header comment):

```agc
P63ZOOM     EXTEND
            DCA     LUNLANAD
            DXCH    AVEGEXIT        # Connect LUNLAND to the guidance loop

            TC      IBNKCALL
            CADR    FLATOUT         # Command full (flat-out) throttle
            TCF     P40ZOOMA
```

This connects the `LUNLAND` guidance routine (the famous lunar landing guidance equations) to the AVERAGEG service loop, then commands full throttle via `FLATOUT`.

For P40:

```agc
P40ZOOM     CAF     BIT13
            TS      THRUST          # Set thrust command
            CAF     BIT4
            EXTEND
            WOR     CHAN14          # Write to I/O channel 14
```

This writes to **I/O channel 14**, a multi-function output channel that controls (among other things) engine commands for the LM. `BIT13` sets the thrust command register, and `BIT4` on channel 14 is the engine-on bit for the DPS.

### 1.7 Safety Features Summary

The routine implements multiple layers of safety:

1. **Astronaut consent gate** — V99 "PLEASE ENABLE ENGINE" must be answered with PROCEED before ignition
2. **Engine-off before sequencing** — `ENGINOF3` is called at entry to ensure a clean state
3. **TIG slip protection** — if state vector propagation runs long, TIG is pushed forward
4. **Ullage verification** — ullage jets fire before main engine to settle propellant
5. **Mode verification** — `P40AUTO` checks that PGNCS and AUTO modes are set; if not, displays checklist 203
6. **Communication failure handling** — `COMFAIL` paths handle loss of ground contact
7. **Restart protection** — extensive use of `PHASCHNG` ensures every critical state transition can survive a computer restart
8. **Abort paths** — `ABRTABLE` provides an emergency ignition path with minimal setup (`NOOP` placeholders for unused slots)
9. **DVMON connection** — after ignition, `DVMONCON` connects the delta-V monitor, which watches for engine failure
10. **Ullage shutoff** — `ULLAGOFF` turns off RCS ullage 0.5 seconds after main engine light-up

### 1.8 The Countdown Clock

The `CLOKTASK`/`CLOKJOB` pair implements the countdown timer display:

```agc
CLOKTASK    CS      TIME1           # SET TBASE6 FOR GROUP 6 RESTART
            TS      TBASE6

            CCS     DISPDEX
            TCF     KILLCLOK        # Positive DISPDEX = kill the clock
            NOOP                    # +0 case (falls through)
            CAF     PRIO27
            TC      NOVAC           # Start CLOKJOB
            ...
            TC      FIXDELAY
            DEC     100             # Wait 1 second (100 centiseconds)
            TCF     CLOKTASK        # Loop
```

`CLOKTASK` runs as a Waitlist task, firing every second. It spawns `CLOKJOB` which computes `TTOGO = TIME2 - TIG` and uses `DISPDEX` as a negative index into a display dispatch table.

The dispatch table is clever — labels like `-35`, `-25`, `-17`, `-13`, `-2` correspond to `DISPDEX` values that select different displays at different phases of the countdown:

| DISPDEX | Display |
|---------|---------|
| -35 (VB97DEX) | Verb 97 paste (communication failure) |
| -25 | V06N61 — event timer reset display |
| -17 (CNTDNDEX) | Normal countdown display (V/N from table offset 0) |
| -13 (VB99DEX) | Verb 99 — "PLEASE ENABLE ENGINE" |
| -2 (BLANKDEX) | Blank DSKY |

The comment is explicit about a critical invariant:

```agc
            COM
            RELINT          # ***** DISPDEX MUST NEVER B -0 *****
```

In 1's complement, `-0` (all ones, octal 77777) would be a valid `DISPDEX` value but would cause incorrect indexing after the `CCS`/`COM` sequence. The five-asterisk emphasis shows this was a known landmine.

---

## 2. Cultural Archaeology

### 2.1 The Name: "Burn, Baby! BURN!"

The file header contains a remarkable historical note, added by the modern transcription team based on Don Eyles' account at the 40th anniversary gathering of AGC developers:

> It traces back to 1965 and the Los Angeles riots, and was inspired by disc jockey extraordinaire and radio station owner Magnificent Montague. Magnificent Montague used the phrase "Burn, baby! BURN!" when spinning the hottest new records. Magnificent Montague was the charismatic voice of soul music in Chicago, New York, and Los Angeles from the mid-1950s to the mid-1960s.

Nathaniel "Magnificent" Montague was a radio DJ who would shout "Burn, baby! BURN!" when a record was particularly good — a term of highest approval. During the August 1965 Watts riots in Los Angeles, the phrase was co-opted by rioters and took on a far darker meaning. Montague was reportedly horrified and tried to change his catchphrase.

That Adler and Eyles chose this phrase for the master ignition routine — the code that literally burns rocket engines — shows the MIT IL team's irreverent humor. The phrase works on multiple levels: it's a command to the engine, a DJ's exclamation of excellence, and a dark historical echo, all compressed into a subroutine label.

The censored variant `B*RNB*B*` at the secondary entry point may be a joke about the profanity-adjacent nature of the name, or it may serve a practical purpose (a distinct label for the post-`P40AUTO` entry point that's easy to find in listings).

### 2.2 "HONI SOIT QUI MAL Y PENSE"

```
#            HONI SOIT QUI MAL Y PENSE
```

This is the motto of the Order of the Garter, the oldest and most prestigious British order of chivalry, dating to 1348. It translates from Old French as: **"Shame on him who thinks evil of it."**

Placed directly after the statement that the routine "was conceived and executed, and (NOTA BENE) is maintained by Adler and Eyles," this reads as a defiant declaration: *if you think there's something wrong with our code, the shame is on you.* It's territorial pride dressed in medieval heraldry — two young engineers planting their flag.

### 2.3 "NOLI SE TANGERE"

```
#            NOLI SE TANGERE
```

Placed just before the program tables begin. This is a slight variation of the Latin "Noli me tangere" — **"Touch me not"** (or in this form, closer to "Do not touch it"). The phrase originates from the Gospel of John, where the resurrected Christ says these words to Mary Magdalene.

In context, it's a warning to other programmers: **do not modify these tables.** The table structure is the backbone of the entire ignition routine, and changing an offset would silently break every program that uses it. This is the 1960s equivalent of a `// DO NOT EDIT` comment, but with considerably more gravitas.

### 2.4 "NOTA BENE"

```
# THE MASTER IGNITION ROUTINE WAS CONCEIVED AND EXECUTED, AND (NOTA BENE) IS MAINTAINED BY ADLER AND EYLES.
```

Latin for "note well." The parenthetical emphasis on "is maintained" is a clear message to the rest of the team: *if you have a problem with this code, come to us.* Combined with "HONI SOIT QUI MAL Y PENSE" and "NOLI SE TANGERE," a picture emerges of two engineers who are proud of their work, protective of its integrity, and not above using dead languages to enforce code ownership.

### 2.5 "EXTIRPATE"

```agc
            CAF     ZERO        # EXTIRPATE JUNK LEFT IN DVTOTAL
```

To *extirpate* means to pull up by the roots, to destroy utterly. Where a modern programmer might write `// clear delta-V accumulator`, Adler and Eyles write "EXTIRPATE JUNK." The word choice conveys both precision (this isn't just clearing a variable, it's destroying contaminating residue) and personality.

### 2.6 "ASSASSINATE CLOKTASK"

```agc
            CA      Z           # ASSASSINATE CLOKTASK
            TS      DISPDEX
```

Not "stop," not "terminate," not "kill" — *assassinate*. `CLOKTASK` doesn't know it's about to die. It will discover its own death on its next wake-up, when it finds `DISPDEX` has been set positive. This is technically precise (it's a deferred kill, not an immediate one) and linguistically vivid.

### 2.7 "HELLO THERE" and "GOODBYE. COME AGAIN SOON."

In the `P40AUTO` subroutine:

```agc
P40AUTO     TC      MAKECADR    # HELLO THERE.
            TS      TEMPR60
```

And at the end:

```agc
GOBACK      CA      TEMPR60
            TC      BANKJUMP    # GOODBYE.  COME AGAIN SOON.
```

The subroutine greets its callers on entry and bids them farewell on exit. This is pure personality — the code is being *hospitable*. It also serves as a subtle documentation aid: these comments mark the boundaries of a self-contained subroutine in a file where control flow is otherwise labyrinthine.

### 2.8 "?" = GOTOPOOH

```agc
?           =       GOTOPOOH
```

This equate defines the label `?` as an alias for `GOTOPOOH` (go to P00, the idle program — "POOH" as in Winnie-the-Pooh, since P00 → "Pooh"). The question mark as a label is itself a joke — it's the "what do we do?" symbol pointing to the "go do nothing" routine. AGC labels could contain almost any character, and the team exploited this fully.

### 2.9 Absent Cultural References

The user's prompt asks about "OFF TO SEE THE WIZARD" and "HAS THE LITTLE OLD LADY LEFT?" — **these comments do not appear in this file.** They likely exist in other modules (possibly in the Executive or Waitlist code, or in the guidance equations). Their absence here is worth noting: BURN_BABY_BURN has its own distinct personality. Its cultural register is Latin inscriptions and soul music, not Wizard of Oz references.

### 2.10 Astronaut Checklist Reference

```agc
TURNITON    CAF     P40A/PMD    # DISPLAYS V50N25 R1=203 PLEASE PERFORM
            TC      BANKCALL    # CHECKLIST 203 TURN ON PGNCS ETC.
            CADR    GOPERF1
```

`P40A/PMD` resolves to `OCT 00203` — checklist item 203. This displays "V50N25" (Verb 50 Noun 25: "Please perform checklist item in R1") with R1=203. Checklist 203 instructed the astronaut to verify that the Primary Guidance, Navigation, and Control System (PGNCS) was on and the spacecraft was in AUTO mode. The code couldn't flip those physical switches — it had to ask a human.

---

## 3. Code Quality and Structure

### 3.1 Almost Entirely Native AGC

Unlike the guidance equation files (LUNAR_LANDING_GUIDANCE_EQUATIONS, THE_LUNAR_LANDING, etc.) which are predominantly interpreter code, BURN_BABY_BURN is **overwhelmingly native AGC assembly**. The only interpreter block is the state vector propagation in `P41SPOT`:

```agc
P41SPOT     TC      INTPRET         # Enter interpreter
            DLOAD   DSU
                TIG
                D29.9SEC
            ...
            CALRB
                MIDTOAV1            # Return to basic (native) mode
```

This makes sense architecturally: the ignition routine is a **real-time sequencer**, not a math-heavy computation. It needs precise timing control, direct I/O access, interrupt management, and Waitlist task scheduling — all things that require native AGC instructions. The interpreter's ~10-25x performance penalty would be unacceptable for time-critical ignition sequencing.

### 3.2 Control Flow Architecture

The control flow is complex but disciplined. There are three interlocking mechanisms:

**1. Waitlist Tasks (time-driven):**

```
TIG-35 → (5 sec) → TIG-30 → (24.9 sec) → TIG-5 → (5 sec) → TIG-0 → IGNITION
```

Each task schedules the next via `TWIDDLE` (a Waitlist convenience routine). This chain is the backbone of the countdown.

**2. Jobs (priority-driven):**

Jobs like `CLOKJOB`, `S40.13`, `P41BLANK`, and `POSTBURN` run under the Executive's cooperative scheduler. They handle computation-heavy work (display updates, targeting) that would be too long for a Waitlist task.

**3. Table Dispatch (program-driven):**

`INDEX WHICH / TCF n` is used throughout to branch to program-specific behavior. This is the polymorphism layer.

These three mechanisms interleave: a Waitlist task may spawn a job, which may use table dispatch. Understanding any single path through the code requires tracking all three.

### 3.3 Restart Protection

The code is obsessive about restart protection. Nearly every state transition is bracketed by `PHASCHNG` calls:

```agc
BURNBABY    TC      PHASCHNG        # GROUP 4 RESTARTS HERE
            OCT     04024
```

The octal constants encode which restart group and phase to set. If the computer resets (as it did during Apollo 11's famous 1202 alarms), the Executive can resume execution at the correct point in the ignition sequence rather than starting over. This is critical — you cannot restart a countdown from zero when you're already 20 seconds from ignition.

The restart groups used in this file:
- **Group 1**: Ullage task protection
- **Group 3**: Zoom (throttle-up) protection, S40.13 protection
- **Group 4**: Main ignition sequence (the primary chain)
- **Group 6**: Countdown clock (`CLOKTASK`)

### 3.4 Comparison to Guidance Equations

| Aspect | BURN_BABY_BURN | Guidance Equations |
|--------|---------------|-------------------|
| Language | ~95% native AGC | ~80% interpreter |
| Primary concern | Timing, sequencing, I/O | Mathematics |
| Data types | Flags, addresses, time values | Vectors, matrices, angles |
| Control flow | Task chains + table dispatch | CALL/GOTO in interpreter |
| Restart protection | Extensive (every transition) | Moderate (at major phases) |
| Comments | Personality-rich | Terse to moderate |
| Complexity source | State machine with many paths | Numerical algorithms |

### 3.5 The `KILLTASK` Routine

The file ends with a general-purpose utility: `KILLTASK`, which removes a scheduled task from the Waitlist. Its header comment is unusually thorough for the AGC codebase — full calling sequence, exit conditions, erasable initialization, output, and debris (clobbered registers):

```
# KILLTASK IS USED TO REMOVE A TASK FROM THE WAITLIST BY SUBSTITUTING
# A NULL TASK CALLED `NULLTASK' (OF COURSE), WHICH MERELY DOES A
# TC TASKOVER.
```

The "(OF COURSE)" is a small touch of personality from Covelli (credited in the header). The implementation scans the `LST2` waitlist array, comparing both the GENADR and FBANK of each entry against the target task. When found, it overwrites the entry with `TCTSKOVR` (a `TC TASKOVER` instruction) — the task slot now contains a no-op that will harmlessly execute and terminate.

The scan loop:

```agc
ADRSCAN     INDEX   L
            CS      LST2
            AD      ITEMP4          # COMPARE GENADRS
            EXTEND
            BZF     TSTFBANK        # IF THEY MATCH, COMPARE FBANKS
LETITLIV    CS      LSTLIM
            AD      L
            EXTEND
            BZF     DEAD            # ARE WE DONE?
            INCR    L
            INCR    L               # Entries are 2 words apart
            TCF     ADRSCAN
```

The label `LETITLIV` (let it live) for the "no match, continue" case, and `KILLDEAD` for the successful removal, continue the file's tradition of vivid naming.

Note that `KILLTASK` leaves interrupts inhibited (`INHINT` at entry, no `RELINT`), as documented: "KILLTASK LEAVES INTERRUPTS INHIBITED SO CALLER MUST RELINT." This is a deliberate design choice — the caller may need to perform additional atomic operations before re-enabling interrupts.

---

## 4. The Moment of Landing

To understand this file's place in history, trace the P63 path:

1. `BURNBABY` enters with `WHICH` pointing to `P63TABLE`
2. The countdown proceeds through TIG-35, TIG-30, TIG-5
3. At TIG-5, the DSKY shows V99: "PLEASE ENABLE ENGINE"
4. Aldrin presses PROCEED
5. At TIG-0, `IGNITION` fires — bit 13 written to DSALMOUT
6. The descent engine ignites at ~50,000 feet above the Moon
7. 26 seconds later, `P63ZOOM` throttles to full power and connects `LUNLAND` — the landing guidance equations take over
8. `CLOKTASK` is assassinated; the landing display takes its place

From this point, the Lunar Module is committed. BURN_BABY_BURN hands off to the guidance equations, which will steer Armstrong and Aldrin to the surface.

The code that performed this sequence was woven into core rope memory months before launch. It could not be patched. It had to work the first time, on the only attempt humanity would get at Apollo 11's landing. And it did.

---

## Notes on Uncertainty

- **I/O channel details**: The exact bit assignments on DSALMOUT (channel 11) are inferred from the code pattern (`RAND` to read, `AD BIT13` to set, `WRITE` to commit). The channel number and bit function are consistent with LM documentation but I have not cross-referenced against the I/O channel tables in this codebase.

- **ZOOMTIME value**: The header states throttle-up occurs at "TIG + 26 seconds" for DPS programs, but the actual value of `ZOOMTIME` is not defined in this file. It's presumably defined in an erasable initialization or in the calling program.

- **"OFF TO SEE THE WIZARD" and "HAS THE LITTLE OLD LADY LEFT?"**: These comments were mentioned in the analysis prompt but **do not appear in this file**. They exist elsewhere in the Luminary codebase.

- **P61TABLE**: Referenced in the header comments as a user of the ignition routine, but no `P61TABLE` appears in this file. It may be defined in the P61 source module and simply points the `WHICH` register to its own table elsewhere in memory.