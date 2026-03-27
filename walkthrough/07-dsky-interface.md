# Chapter 7: The DSKY Interface — Pinball Game Buttons and Lights

## Introduction

The Display and Keyboard unit — the DSKY (pronounced "dis-key") — was the astronaut's sole interface to the Apollo Guidance Computer. No mouse, no touchscreen, no monitor. Just 19 keys, a handful of status lights, and three rows of five-digit seven-segment displays. The software that managed this interface was called **PINBALL GAME BUTTONS AND LIGHTS**, and at roughly 3,800 lines across two files, it is one of the largest single modules in the Lunar Module's flight software.

The name was not a joke — or rather, it was a joke that became permanent. As Ramón Alonso, one of the original AGC developers, recalled: the Verb-Noun interface was invented on the fly for a demo unit meant to impress visitors to the MIT Instrumentation Laboratory. Nobody expected it to survive into flight software. But nobody got around to replacing it either, and the coders won a "devilish game" of countering objections like "it's not scientific" and "astronauts won't understand it." The astronauts understood it fine. They just didn't like it — most of them wanted dials and switches, like in an aircraft cockpit.

The module we're examining spans two files:
- **PINBALL_GAME_BUTTONS_AND_LIGHTS.agc** (~3,400 lines) — the command parser, display engine, keyboard handler, monitor system, and all the verb handlers
- **PINBALL_NOUN_TABLES.agc** (~600 lines) — noun definition tables, scale factor tables, and the table-reading routines that live in their own bank

Together, these files implement what is arguably one of the earliest Verb-Noun command-line interfaces — predating Unix shells by several years.

---

## 1. The Verb-Noun Command System

### 1.1 The Paradigm

Every interaction with the DSKY follows a simple grammar: **VERB** *number* **NOUN** *number* **ENTR**. The Verb says *what to do*, the Noun says *what to do it to*. Both are two-digit decimal numbers.

From the file header:

```
# THE LANGUAGE OF COMMUNICATION WITH THE PROGRAM IS A PAIR OF WORDS
# KNOWN AS VERB AND NOUN.  EACH OF THESE IS REPRESENTED BY A 2 CHARACTER
# DECIMAL NUMBER.  THE VERB CODE INDICATES WHAT ACTION IS TO BE TAKEN, THE
# NOUN CODE INDICATES TO WHAT THIS ACTION IS APPLIED.  NOUNS USUALLY
# REFER TO A GROUP OF ERASABLE REGISTERS.
```

Verbs fall into categories:
- **Display verbs** (V01–V07): show data in octal or decimal
- **Monitor verbs** (V11–V17): display data and refresh it once per second
- **Load verbs** (V21–V25): accept data input from the astronaut
- **Special verbs** (V30–V39): request executive, terminate, proceed, change program, test lights, fresh start
- **Extended verbs** (V40+): handled by a separate module — these cover complex operations like IMU alignment, orbit calculations, etc.

Key combinations seen during the mission:
- **V06N62**: Display velocity, time-to-ignition, and accumulated delta-V (the classic "are we there yet" display during burns)
- **V16N68**: Monitor slant range, time to go, and altitude difference (powered descent)
- **V37N00E**: Change major mode (the "change program" verb — the most important single command)
- **V35E**: Test all display lights (astronaut confidence check)
- **V50N25**: "Please perform" — the computer asking the astronaut to do something

### 1.2 How Keystrokes Reach Pinball

The DSKY keyboard generates a hardware interrupt on every key press. The flow is:

1. Astronaut presses a key
2. Hardware puts a 5-bit keycode into I/O channel 15
3. **KEYRUPT1** interrupt fires (vector address 4024 octal)
4. The interrupt service routine reads the keycode, places it into `MPAC`, and enters an Executive request for the Pinball program at entry point `CHARIN`
5. The ISR executes `RESUME` to return from interrupt
6. When the Executive schedules the job, Pinball processes the keystroke

The keycodes are documented in the source:

```
# THE INPUT CODES ASSUMED FOR THE KEYBOARD ARE,
# 0		10000
# 1		00001
# 9		01001
# VERB		10001
# ERROR RES	10010
# KEY RLSE	11001
# +		11010
# -		11011
# ENTER		11100
# CLEAR		11110
# NOUN		11111
```

Note that the PROCEED key has no keycode — it is read through an alternate mechanism (a bit in an I/O channel, polled during T4RUPT display service). This is a hardware quirk: PRO was wired differently from the other keys.

### 1.3 The CHARIN Keystroke Dispatcher

`CHARIN` is the main entry point for keystroke processing. It implements a jump table indexed by the 5-bit keycode:

```agc
CHARIN		CAF	ONE		# BLOCK DISPLAY SYST
		XCH	DSPLOCK		# MAKE DSP SYST BUSY, BUT SAVE OLD
		TS	21/22REG	# C(DSPLOCK) FOR ERROR LIGHT RESET.
```

The first thing Pinball does on *any* keystroke is set `DSPLOCK` to 1. This "locks" the display system against internal programs trying to use it — the astronaut has the floor.

Then comes the dispatch table — a series of `TC` instructions indexed by the keycode stored in `CHAR`:

```agc
CHARIN2		XCH	MPAC
		TS	CHAR
		INDEX	A
		TC	+1		# INPUT CODE	FUNCTION
		TC	CHARALRM	# 0
		TC	NUM		# 1
		TC	NUM		# 2
		TC	NUM		# 3
		...
		TC	NUM	-2	# 20		0
		TC	VERB		# 21		VERB
		TC	ERROR		# 22		ERROR LIGHT RESET
		...
		TC	VBRELDSP	# 31		KEY RELEASE
		TC	POSGN		# 32		+
		TC	NEGSGN		# 33		-
		TC	ENTERJMP	# 34		ENTER
		...
		TC	CLEAR		# 36		CLEAR
		TC	NOUN		# 37		NOUN
```

The `INDEX A` / `TC +1` pattern is a computed jump: it adds the value of A to the program counter, effectively selecting one of the subsequent `TC` instructions. This is the AGC's equivalent of a `switch` statement.

Digits 1–9 route to `NUM`. Digit 0 routes to `NUM -2` (two instructions before `NUM`, which zeros `CHAR` first — since keycode 20 octal needs to be treated as digit value 0). Invalid codes route to `CHARALRM`, which turns on the Operator Error light.

### 1.4 Parsing Two-Digit Numbers from Individual Keystrokes

When the astronaut presses VERB, the `VERB` handler clears `VERBREG` and sets `DSPCOUNT` to point at the verb display position:

```agc
VERB		CAF	ZERO
		TS	VERBREG
		CAF	VD1
NVCOM		TS	DSPCOUNT
		TC	2BLANK
		CAF	ONE
		TS	DECBRNCH	# SET FOR DEC V/N CODE
```

`DSPCOUNT` is the display position indicator. `VD1` is octal 23, which corresponds to the leftmost verb digit position. The routine blanks the two verb digit positions and sets `DECBRNCH` to indicate decimal input mode.

Subsequent digit keystrokes land in `NUM`, which assembles the two-digit number. The key insight is the `CYL` (Cycle Left) register trick for octal assembly:

```agc
		INDEX	INREL		# +0 OCTAL
		XCH	VERBREG
		TS	CYL
		CS	CYL
		CS	CYL
		XCH	CYL
		AD	CHAR
		TC	ENDNMTST
```

This sequence loads the current accumulated value into the CYL editing register, which automatically rotates bits left on each access. The three `CS CYL` operations rotate the value left by 3 bit positions (one octal digit), then the new digit (`CHAR`) is added in. This is the AGC's way of doing `value = (value << 3) | new_digit` without a shift instruction.

For decimal input (used for verb/noun codes and signed data), the code does something more sophisticated — it maintains the value as a fraction, multiplying by 10 and adding each new digit:

```agc
DECTOBIN	INDEX	INREL
		XCH	VERBREG
		TS	MPAC		# SUM X 2EXP-14 IN MPAC
		CAF	ZERO
		TS	MPAC +1
		CAF	TEN		# 10 X 2EXP-14
		TC	SHORTMP		# 10SUM X 2EXP-28 IN MPAC, MPAC+1
		XCH	MPAC +1
		AD	CHAR
		TS	MPAC +1
```

This performs `sum = sum * 10 + digit` in the AGC's fractional arithmetic. The result stays scaled as a fraction in `MPAC`, which is the format needed for later display and storage.

### 1.5 The ENTER Key and Verb Execution

When ENTER is pressed, the code enters via `ENTERJMP`, which jumps to `ENTER`:

```agc
ENTER		CAF	ZERO
		TS	CLPASS
		CAF	ENDINST
		TS	ENTRET
		CCS	REQRET
		TC	ENTPAS0		# IF +, PASS 0
		TC	ENTPAS0		# IF +, PASS 0
		TC	+1		# IF -, NOT PASS 0
```

`REQRET` determines whether this is "pass 0" (the initial execute) or a higher pass (loading data). Pass 0 triggers `ENTPAS0`, which is the verb execution path.

`ENTPAS0` starts by blocking further numeric input, then dispatches through the verb fan:

```agc
ENTPAS0		CAF	ZERO		# NOUN VERB SUB ENTERS HERE
		TS	DECBRNCH
		CS	VD1		# BLOCK FURTHER NUM CHAR, SO THAT STRAY
		TS	DSPCOUNT	# CHAR DO NOT GET INTO VERB OR NOUN LTS.
TESTVB		CS	VERBREG
		TS	VERBSAVE	# SAVE VERB FOR POSSIBLE RECYCLE.
		AD	LOWVERB		# LOWVERB - VB
		EXTEND
		BZMF	VERBFAN		# VERB G/ E LOWVERB
```

Verbs below `LOWVERB` (decimal 28) go through noun validation first. Verbs 28 and above skip the noun test — these are the "special" verbs that don't need a noun (terminate, proceed, change program, etc.).

The actual verb dispatch uses a table of `CADR` (Complete Address) values:

```agc
VBFANDIR	INDEX	VERBREG
		CAF	VERBTAB
		TC	BANKJUMP

VERBTAB		CADR	GODSPALM	# VB00 ILLEGAL
		CADR	DSPA		# VB01 DISPLAY OCT COMP 1 (R1)
		CADR	DSPB		# VB02 DISPLAY OCT COMP 2 (R1)
		...
		CADR	MONITOR		# VB16 MONITOR DECIMAL
		...
		CADR	ABCLOAD		# VB25 LOAD COMP 1,2,3 (R1,R2,R3)
		...
		CADR	MMCHANG		# VB37 CHANGE MAJOR MODE
```

Each entry is a `CADR` — a complete address (including bank bits) that `BANKJUMP` can use to transfer control across memory banks. This is necessary because 36K of ROM requires bank switching, and verb handlers are scattered across multiple banks.

### 1.6 Extended Verbs (V40+)

Verbs 40 and above are "extended verbs" — they're too numerous and specialized to fit in Pinball's own bank:

```agc
VERBFAN		CS	LST2CON
		AD	VERBREG		# VERB = LST2CON
		CCS	A
		AD	ONE		# VERB G/ LST2CON
		TC	+2
		TC	VBFANDIR	# VERB L/ LST2CON
		TS	MPAC
		TC	RELDSP		# RELEASE DISPLAY SYST
		TC	POSTJUMP	# GO TO GOEXTVB WITH VB=40 IN MPAC.
		CADR	GOEXTVB
LST2CON		DEC	40		# FIRST LIST2 VERB (EXTENDED VERB)
```

When a verb ≥ 40 is detected, Pinball *releases* the display system and jumps to `GOEXTVB` in a separate bank. The verb number minus 40 is passed in `MPAC`. The extended verb fan is maintained in a completely separate log section (`EXTENDED VERBS`). This architectural separation was essential — Pinball's own banks were already full.

### 1.7 Special Key Handling

**CLEAR**: Blanks the current data register (R1, R2, or R3) and backs up the input cursor. Successive CLEARs blank R3, then R2, then R1:

```agc
CLEAR		CCS	DSPCOUNT
		AD	ONE
		TC	+2
		AD	ONE
		INDEX	A
		CAF	INRELTAB
		TS	INREL
```

The `CLPASS` variable tracks how many times CLEAR has been pressed, so successive presses back up through the registers.

**KEY RELEASE** (`VBRELDSP`): This is the most nuanced key. Its behavior depends on state:

```
# THE HIGHEST PRIORITY FUNCTION OF THE KEY RELEASE BUTTON IS THE
# UNSUSPENDING OF A SUSPENDED MONITOR WHICH WAS EXTERNALLY INITIATED.
# ...
# IN ADDITION IF THERE IS A JOB IN ENDIDLE, THEN CONTROL IS TRANSFERRED
# TO PINBRNCH ... TO RE-EXECUTE THE SERIES OF NVSUB CALLS ETC.
```

KEY RELEASE clears the uplink activity light, releases `DSPLOCK` (allowing internal programs to display again), and can wake up suspended monitors or re-establish flashing displays that the astronaut overwrote.

**ERROR RESET** (`ERROR`): Turns off the Operator Error light, turns off the UPLINK ACTIVITY light, resets various status lights, and forces bit 12 of all DSPTAB entries to 1 (marking them for redisplay). It also resets fail bits so that if a real failure still exists, the alarm will reappear.

**PROCEED (PRO)**: Handled through `VBPROC` (equivalent to V33):

```agc
VBPROC		CAF	ONE		# PROCEED WITHOUT DATA
		TS	LOADSTAT
		TC	KILMONON	# TURN ON KILL MONITOR BIT
		TC	RELDSP
		TC	FLASHOFF
		TC	RECALTST	# SEE IF THERE IS ANY RECALL FROM ENDIDLE
```

Sets `LOADSTAT` to +1, kills any running monitor, releases the display, turns off flashing, and wakes up any program sleeping in ENDIDLE.

### 1.8 The 8/9 Rejection Logic

A subtle detail — digits 8 and 9 are only valid in decimal context. When the astronaut is entering an octal value, 8 and 9 must be rejected:

```agc
89TEST		CCS	DSPCOUNT
		TC	+4		# +
		TC	+3		# +0
		TC	ENDOFJOB	# - BLOCK DATA IN IF DSPCOUNT IS - OR -0
		TC	ENDOFJOB	# -0
		CAF	THREE
		MASK	DECBRNCH
		CCS	A
		TC	NUM		# IF DECBRNCH IS +, 8 OR 9 OK
		TC	CHARALRM	# IF DECBRNCH IS +0, REJECT 8 OR 9
```

If `DECBRNCH` is positive (decimal mode active), 8 and 9 are accepted. If `DECBRNCH` is +0 (octal mode), the Operator Error light turns on. This is one of the earliest examples of input validation in a user interface.

---

## 2. Display Management

### 2.1 The DSPTAB Buffer

The DSKY has 21 digit positions organized as:

```
# MD1	MD2 				(MAJOR MODE)
# VD1	VD2 (VERB)	ND1	ND2 	(NOUN)
# R1D1	R1D2	R1D3	R1D4	R1D5 	(R1)
# R2D1	R2D2	R2D3	R2D4	R2D5 	(R2)
# R3D1	R3D2	R3D3	R3D4	R3D5 	(R3)
```

These are managed through an 11-register buffer called `DSPTAB` (plus 3 more entries for relay controls, 14 total). Each DSPTAB entry encodes a relay word selection and the 5-bit codes for two display characters:

```
# OUTPUT FORMAT FOR DISPLAY PANEL.  SET OUT0 TO AAAABCCCCCDDDDD.
# A'S 	SELECTS A RELAYWORD. THIS DETERMINES WHICH PAIR OF CHARACTERS ARE
#     	ENERGIZED.
# B	FOR SPECIAL RELAYS SUCH AS SIGNS ETC.
# C'S	5 BIT RELAY CODE FOR LEFT CHAR OF PAIR SELECTED BY RELAYWORD.
# D'S	5 BIT RELAY CODE FOR RIGHT CHAR OF PAIR SELECTED BY RELAYWORD.
```

The 5-bit relay codes for each digit:

```
# BLANK	00000
# 0	10101
# 1	00011
# 2	11001
# 3	11011
# 4	01111
# 5	11110
# 6	11100
# 7	10011
# 8	11101
# 9	11111
```

These are not ASCII or BCD — they are the physical wiring codes that drive the electroluminescent segments of each seven-segment display through relay logic. The mapping from digit value to segment pattern is baked into hardware, and this 5-bit code selects which relays to energize.

### 2.2 The DSPIN Routine — Writing to the Display

`DSPIN` is the core routine for placing a character into the display buffer. It takes a display position in `COUNT` and a relay code in `CODE`:

```agc
DSPIN		XCH	Q
		TS	DSEXIT
		CAF	LOW5
		MASK	COUNT
		TS	SR
		XCH	SR
		TS	DSREL
```

The routine computes which DSPTAB entry to modify (`DSREL`), whether the character goes in the left or right half of the entry, and whether to blank the sign relay. It then reads the current DSPTAB entry, masks out the old character, inserts the new one, and writes it back:

```agc
DSPIN1		INHINT
		INDEX	DSREL
		CCS	DSPTAB
		TC	+2		# IF +
		TC	CCSHOLE
		AD	ONE		# IF -
		TS	DSMAG
		INDEX	COUNT
		MASK	DSMSK
		EXTEND
		SU	CODE
		EXTEND
		BZF	DSLV		# SAME
DFRNT		INDEX	COUNT
		CS	DSMSK
		MASK	DSMAG
		AD	CODE
		CS	A
		INDEX	DSREL
		XCH	DSPTAB
		EXTEND
		BZMF	DSLV		# DSPTAB ENTRY WAS -
		INCR	NOUT		# DSPTAB ENTRY WAS +
DSLV		RELINT
		TC	DSEXIT
```

Critical detail: `NOUT` is incremented only when a DSPTAB entry transitions from positive (already displayed) to negative (needs display update). The sign bit of each DSPTAB entry acts as a "dirty flag." The T4RUPT display service routine (`DSPOUT`, called from the TIME4 interrupt every ~120ms) checks `NOUT` and, if nonzero, scans DSPTAB for negative entries, writes them to output channel 10, and marks them positive. This is a double-buffered display system — writes happen under Executive control, actual hardware output happens in interrupt, and the dirty-flag mechanism prevents unnecessary I/O channel writes.

The `INHINT`/`RELINT` pair around the DSPTAB modification is essential — this is a critical section. If a T4RUPT fired between reading and writing DSPTAB, the display could be corrupted.

### 2.3 Display Position Numbering (DSPCOUNT)

Each digit position has a `DSPCOUNT` number used for computation:

```
# MD1	25		R2D1	11		ALL ARE OCTAL
# MD2	24		R2D2	10
# VD1	23		R2D3	 7
# VD2	22		R2D4	 6
# ND1	21		R2D5	 5
# ND2	20		R3D1	 4
# R1D1	16		R3D2	 3
# R1D2	15		R3D3	 2
# R1D3	14		R3D4	 1
# R1D4	13		R3D5	 0
# R1D5	12
```

When `DSPCOUNT` is set negative, no more numeric input is accepted — this is how the system "blocks" data entry after a complete value has been entered or a verb has been executed.

### 2.4 The GETINREL Table

The `INRELTAB` table maps each `DSPCOUNT` position to a "relative input register" — which register (`VERBREG`, `NOUNREG`, `XREG`, `YREG`, or `ZREG`) is being loaded:

```agc
INRELTAB	OCT	4		# R3D5 (DSPCOUNT = 0)
		OCT	4		# R3D4		 =(1)
		...
		OCT	3		# R2D1		 =(9D)
		OCT	2		# R1D5		 =(10D)
		...
		OCT	1		# ND1		 =(17D)
		OCT	0		# VD2		 =(18D)
		OCT	0		# VD1		 =(19D)
```

The values mean: 0=VERBREG, 1=NOUNREG, 2=XREG (R1), 3=YREG (R2), 4=ZREG (R3). This indirect addressing lets the same `NUM` routine handle input for any display register.

### 2.5 Decimal-to-Display Conversion

The `DSPDECWD` routine converts a value in `MPAC, MPAC+1` to five decimal characters:

```agc
DSPDECWD	XCH	Q
		TS	WDRET
		TC	DSPSIGN
		TC	DSPRND
		CAF	FOUR
DSPDCWD1	TS	WDCNT
		CAF	BINCON
		TC	SHORTMP
TRACE1		INDEX	MPAC
		CAF	RELTAB
		MASK	LOW5
		TS	CODE
		CAF	ZERO
		XCH	MPAC +2
		XCH	MPAC +1
		TS	MPAC
		XCH	DSPCOUNT
TRACE1S		TS	COUNT
```

The algorithm repeatedly multiplies by 10 (`BINCON` = decimal 10), takes the integer part as a digit, and continues with the fractional remainder. This is the classic fractional-to-decimal conversion: multiply by 10, peel off the integer, repeat. Five iterations produce five decimal digits.

`DSPSIGN` handles the sign display separately — it checks `MPAC` and calls `+ON` or `-ON` to set the appropriate sign relay in the DSPTAB:

```agc
DSPSIGN		XCH	Q
		TS	DSPWDRET
		CCS	MPAC
		TC	+8D
		TC	+7
		AD	ONE
		TS	MPAC
		TC	-ON
		CS	MPAC +1
		TS	MPAC +1
		TC	DSPWDRET
		TC	+ON
		TC	DSPWDRET
```

The `CCS` four-way skip on `MPAC` handles the four cases: positive → `+ON`, +0 → `+ON`, negative → negate then `-ON`, -0 → `-ON`.

### 2.6 Octal Display

For octal display, `DSPOCTWO` uses the `CYL` register to extract 3 bits at a time:

```agc
DSPOCTWO	TS	CYL
		XCH	Q
		TS	WDRET
		CAF	BIT14		# TO BLANK SIGNS
		ADS	DSPCOUNT
		CAF	FOUR
WDAGAIN		TS	WDCNT
		CS	CYL
		CS	CYL
		CS	CYL
		CS	A
		MASK	DSPMSK
		INDEX	A
		CAF	RELTAB
		MASK	LOW5
		TS	CODE
```

The CYL register rotates left on every access. By complementing three times and then complementing the result, the code extracts three bits — one octal digit — per iteration. The `RELTAB` lookup converts the 3-bit value to the appropriate 5-bit relay code. Five iterations display five octal digits.

### 2.7 Display Locking and the DSPLOCK System

`DSPLOCK` is the critical interlock between keyboard-initiated and program-initiated display requests:

- When `DSPLOCK` = 0: internal programs can use the display
- When `DSPLOCK` ≠ 0: the astronaut is using the keyboard; internal programs are locked out

Any keystroke (via `CHARIN`) immediately sets `DSPLOCK`:
```agc
CHARIN		CAF	ONE
		XCH	DSPLOCK
```

Programs that want to display data call `NVSUB`, which checks:
```agc
NVSUB		...
		CAF	BIT14
		MASK 	MONSAVE1	# EXTERNAL MONITOR BIT
		AD	DSPLOCK
		CCS	A
		TC	Q		# DSP SYST BLOCKED, RET TO 1+ CALLING LOC
```

If blocked, `NVSUB` returns to the calling location + 1 (failure). If available, it returns to calling location + 2 (success). This two-return convention lets the caller handle both cases:

```agc
		CAF	VN_CODE
		TC	NVSUB
		TC	BUSY_HANDLER   # +1: display unavailable
		TC	CONTINUE       # +2: display acquired, V/N executed
```

The `DSPLIST` register provides a waiting queue: if an internal program finds the display locked, it can call `NVSUBUSY` to go to sleep. When the display is released (via KEY RELEASE or certain verbs), `RELDSP` wakes the sleeping job:

```agc
RELDSP		...
		CCS	DSPLIST
		TC	+2
		TC	RELDSP2		# LIST EMPTY
		CAF	ZERO
		XCH	DSPLIST
		TC	JOBWAKE
```

This is a primitive but effective semaphore system — a single-slot waiting queue for display access.

---

## 3. The Noun Tables

### 3.1 Noun Table Architecture

Nouns are defined by a set of parallel tables in `PINBALL_NOUN_TABLES.agc`. Each noun has entries in:

1. **NNADTAB** — Noun Address Table: where the data lives
2. **NNTYPTAB** — Noun Type Table: component count, scale factor routine, scale factor constant
3. **IDADDTAB** — Indirect Address Table (mixed nouns only): individual component addresses
4. **RUTMXTAB** — Scale Factor Routine Mix Table (mixed nouns only): per-component scale factor routine numbers

The table-reading code (`LODNNTAB`) lives in the same bank as the tables (Bank 6) because the tables must be read through bank-switched access:

```agc
LODNNTAB	DXCH	IDAD2TEM	# SAVE RETURN INFO IN IDAD2TEM, IDAD3TEM.
		INDEX	NOUNREG
		CAF	NNADTAB
		TS	NNADTEM
		INDEX	NOUNREG
		CAF	NNTYPTAB
		TS	NNTYPTEM
```

The return address is saved in `IDAD2TEM/IDAD3TEM` because this routine is called via `DXCH Z` (a double-exchange with the program counter — the AGC equivalent of a far call that can cross bank boundaries).

### 3.2 Normal Nouns

A "normal noun" (noun numbers 00–39) points to a contiguous block of memory. All components share the same scale factor and display format.

The `NNADTAB` entry for a normal noun is an `ECADR` (Erasable Complete Address) pointing to the first word:

```agc
NNADTAB		OCT	00000			# 00 	NOT IN USE
		OCT	40000			# 01 	SPECIFY MACHINE ADDRESS (FRACTIONAL)
		...
		ECADR	CDUX			# 20	ICDU ANGLES
		ECADR	PIPAX			# 21	PIPAS
		ECADR	THETAD			# 22	NEW ICDU ANGLES
```

Special values in NNADTAB:
- **+0**: Noun not in use
- **Negative**: Machine address to be specified (the astronaut must enter an ECADR)
- **-1** (77776 octal): Channel to be specified (for I/O channel display)
- **-0** (77777 octal): Augment last machine address

The `NNTYPTAB` entry packs three fields into 15 bits:

```
# NNTYPTAB IS A PACKED TABLE OF THE FORM MMMMMNNNNNPPPPP.
#
# FOR THE NORMAL CASE,	M'S ARE THE COMPONENT CODE NUMBER.
#			N'S ARE THE SF ROUTINE CODE NUMBER.
#			P'S ARE THE SF CONSTANT CODE NUMBER.
```

For example, Noun 20 (ICDU Angles):
```agc
		OCT	04102			# 20	3COMP CDU DEGREES
```

Unpacking 04102 octal = 000 100 001 000 010 binary:
- Bits 15-11 (MMMMM) = 00010 = component code 2 (3-component)
- Bits 10-6 (NNNNN) = 00010 = SF routine 2 (CDU degrees)
- Bits 5-1 (PPPPP) = 00010 = SF constant 2 (CDU degrees)

Component code interpretation:
```
# 00000		1 COMPONENT
# 00001		2 COMPONENT
# 00010		3 COMPONENT
# X1XXX		BIT 4 = 1.  DECIMAL ONLY
# 1XXXX		BIT 5 = 1.  NO LOAD
```

Bit 4 = "decimal only" means octal display of this noun triggers an alarm. Bit 5 = "no load" means load verbs on this noun trigger an alarm. These bits encode access control at the noun level.

### 3.3 Mixed Nouns

Mixed nouns (noun numbers 40–99) are the more complex case. Each component can have a different address, a different scale factor routine, and a different scale factor constant. This is essential because real-world displays often combine heterogeneous data — velocity in one register, altitude in another, time in a third.

For mixed nouns, `NNADTAB` packs an indirect address reference (`IDADDREL`) in the low 10 bits and a component code in the high 5 bits:

```agc
		OCT	24006			# 42	APOGEE / PERIGEE / DELTA V (REQUIRED)
```

The low 10 bits (006) are an index into `IDADDTAB`, where three consecutive `ECADR` entries give the addresses of the three components:

```agc
		ECADR	HAPO			# 42	POS4			DP3
		ECADR	HPER			# 42	POS4			DP3
		ECADR	VGDISP			# 42 	VEL3			DP3
```

The `RUTMXTAB` provides per-component scale factor routine numbers packed as QQQQQRRRRRSSSSS:

```agc
		OCT	16347			# 42	DP3, DP3, DP3
```

The `NNTYPTAB` entry for mixed nouns packs per-component scale factor *constant* numbers instead of a single set.

### 3.4 The MIXNOUN Handler

When a mixed noun is detected (`MIXBR` = 2), the `MIXNOUN` routine performs a data-gather phase before any display. It copies each component from its individual address into a contiguous temp area (`MIXTEMP`):

```agc
MIXNOUN		CCS	NNADTEM
		TC	+4		# + IN USE
		TC	GODSPALM	# +0 NOT IN USE
		...
		CAF	TWO
MIXNN1		TS	DECOUNT
		AD	MIXAD
		TS	NOUNADD		# SET NOUNADD TO MIXTEMP + K
		INDEX	DECOUNT
		CA	IDAD1TEM
		TS	NOUNTEM
		...
		CA	NOUNTEM
		MASK	LOW11
		TC	SETEBANK	# SET EBANK, LEAVE EADRES IN A.
		INDEX	A
		CA	0
		INDEX	NOUNADD
		XCH	0		# STORE IN MIXTEM + K
		CCS	DECOUNT
		TC	MIXNN1
```

This loops from component 2 down to 0, fetching each value from its individual address and storing it into the contiguous `MIXTEMP` buffer. Then `NOUNADD` is set to point at `MIXTEMP`, and the display routines can proceed as if this were a normal contiguous noun.

### 3.5 Scale Factor Tables

Two parallel tables provide the display and input scale factors:

- **SFOUTAB** — Scale factors for display (output). Each entry is a DP value.
- **SFINTAB** — Scale factors for loading (input). Each entry is a DP value.

For example, "VELOCITY3" (XXXX.X FT/SEC):
```agc
# SFINTAB entry:
		OCT	07475			# VELOCITY3
		OCT	16051
# SFOUTAB entry:
		OCT	01031			# VELOCITY3	(POINT BETWN BITS 7-8)
		OCT	21032
```

The SF routine code determines which conversion routine to use — `DEGOUTSF` for degrees, `ARTOUTSF` for arithmetic (straight multiply), `DP1OUTSF`/`DP2OUTSF`/`DP3OUTSF` for various double-precision formats with different assumed binary point positions, `HMSOUT` for hours/minutes/seconds, `M/SOUT` for minutes/seconds, etc.

The comments in the scale factor constant table are a Rosetta stone for AGC data formats:

```
# 00000		WHOLE				USE ARITH
# 00000		DP TIME SEC (XXX.XX SEC)	USE ARITHDP1
# 00010		CDU DEGREES			USE CDU DEGREES
# 01001		VELOCITY2 (XXXXX. FT/SEC)	USE ARITHDP4
# 01010		VELOCITY3 (XXXX.X FT/SEC)	USE ARITHDP3
```

### 3.6 Degree Display: DEGOUTSF

The CDU degree conversion is worth examining as a representative scale factor routine:

```agc
DEGOUTSF	CAF	ZERO
		TS	MPAC +2		# SET INDEX FOR FULL SCALE.
		TC	FIXRANGE
		TC	+2		# NO AUGMENT NEEDED
		TC	SETAUG		# SET AUGMENTER ACCORDING TO C(MPAC +2)
		TC	DEGCOM
```

`FIXRANGE` checks whether the angle is negative (in AGC terms, the high bit is set). If so, it strips the sign bit and takes a different return path to add an augmentation constant (since AGC angles represent 0–360° as 0–2^14). `DEGCOM` then multiplies by 0.18 (the conversion factor from AGC angle units to degrees scaled for display):

```agc
DEGTAB		OCT	05605		# HI PART OF 	.18
		OCT	03656		# LOW PART OF	.18
```

### 3.7 HMS (Hours, Minutes, Seconds) Display

The `HMSOUT` routine is the most complex scale factor routine, splitting a raw centisecond count into separate hours, minutes, and seconds fields across R1, R2, and R3:

```agc
HMSOUT		TC	BANKCALL
		CADR	READLO		# READ FRESH DATA FOR HI AND LO
		TC	TPAGREE		# MAKE DP DATA AGREE.
		TC	SEPSECNR	# SEPARATE SECONDS
		TC	DMP
		ADRES	SECON2		# MULT BY .06
		CAF	R3D1
		TS	DSPCOUNT
		TC	BANKCALL
		CADR	DSPDECWD	# DISPLAY SECONDS IN R3
		TC	SEPMIN		# SEPARATE MINUTES
		...                     # DISPLAY MINUTES IN R2
		...                     # DISPLAY HOURS IN R1
```

It uses `READLO` to fetch fresh data (important for time — the value might change between reads of the high and low words), makes the DP value "agree" (ensures both words have the same sign), then separates seconds, minutes, and hours through a series of multiplications and divisions. Each component is displayed in its own register.

---

## 4. Flashing Displays and the Please Perform Mechanism

### 4.1 Flashing Verb-Noun Display

When a program needs astronaut input, it sets the DSKY's Verb-Noun display flashing. This is done through a hardware bit:

```agc
FLASHON		CAF	BIT6		# TURN ON V/N FLASH
		EXTEND
		WOR	DSALMOUT	# BIT 6 OF CHANNEL 11
		TC	Q
```

Bit 6 of output channel 11 controls the V/N flash hardware. When set, the Verb and Noun indicators blink at a hardware-controlled rate — no software timing needed.

### 4.2 ENDIDLE — Putting a Program to Sleep

When an internal program displays a flashing V/N and needs to wait for astronaut response, it calls `ENDIDLE`:

```agc
ENDIDLE		LXCH	Q		# RETURN ADDRESS INTO L.
		TC	ISCADR+0	# ABORT IF CADRSTOR NOT= +0
		TC	ISLIST+0	# ABORT IF DSPLIST NOT= +0
		CA	L
		MASK	LOW10
		AD	FBANK
		TS	CADRSTOR
		TC	JOBSLEEP
```

`ENDIDLE` saves the return address in `CADRSTOR` and puts the job to sleep. Only one job can be in ENDIDLE at a time — if `CADRSTOR` is already nonzero, the code **aborts** with code 01206. This is a hard constraint: only one flashing display can be awaiting response at any time.

### 4.3 Three Possible Responses

When the astronaut responds to a flashing display, `RECALTST` wakes the sleeping job and routes it based on `LOADSTAT`:

```agc
# LOADSTAT	+0	INACTIVE (WAITING FOR DATA). SET BY NVSUB
#		+1	PROCEED WITHOUT DATA. SET BY SPECIAL VERB
#		-1	TERMINATE. SET BY SPECIAL VERB.
#		-0	DATA IN OR RESEQUENCE. SET BY END OF LOAD ROUTINE
```

The job wakes up at different offsets from its ENDIDLE call:
- **L+1**: TERMINATE (astronaut pressed V34 or refused the action)
- **L+2**: PROCEED without data (astronaut pressed PRO or V33)
- **L+3**: DATA IN or RESEQUENCE (astronaut entered data and pressed ENTR, or pressed V32)

This three-way return is a remarkably elegant pattern. The calling code looks like:

```agc
		TC	ENDIDLE
		TC	HANDLE_TERMINATE    # L+1
		TC	HANDLE_PROCEED      # L+2
		(continue with data)    # L+3
```

`RECALTST` implements this by adding 0, 1, or 2 to the saved return address:

```agc
DOTERM		CAF	ZERO
		TC	RECAL2

DOPROC		CAF	ONE
		TC	RECAL2

RECALTST	...
		CAF	TWO		# -0 DATA IN OR RESEQUENCE
RECAL2		INDEX	LOCCTR
		AD	LOC
		INDEX	LOCCTR
		TS	LOC
```

### 4.4 NVSUB — The Internal Display Interface

Programs use `NVSUB` to display Verb-Noun combinations. The calling convention:

```
# PLACE 0VVVVVVVNNNNNNN INTO A.
# V'S ARE THE 7-BIT VERB CODE.  N'S ARE THE 7-BIT NOUN CODE.
#
# NVSUB RETURNS TO 2+ CALLING LOC AFTER PERFORMING TASK, IF DISPLAY
# SYSTEM IS AVAILABLE.
# IT RETURNS TO 1+ CALLING LOC WITHOUT PERFORMING TASK, IF DISPLAY
# SYSTEM IS BLOCKED.
```

The V and N codes are packed into a single 14-bit value in A. NVSUB unpacks them:

```agc
NVSUB1		...
		CAF	LOW7
		MASK	NVTEMP
		TS	MPAC +3		# NOUN
		CA	NVTEMP
		TS	EDOP		# RIGHT 7
		CA	EDOP
		TS	MPAC +4		# VERB
```

The `EDOP` register (Edit Polish Opcode, address 23) automatically shifts right by 7 positions on access — this is used here purely as a cheap right-shift operation to extract the verb code from the upper 7 bits.

### 4.5 Please Perform (V50N25)

The "Please Perform" mechanism uses a two-call NVSUB sequence:

```
# NVSUB SHOULD BE USED TWICE IN SUCCESSION FOR 'PLEASE PERFORM' SITUATIONS.
# FIRST PLACE THE CODED NUMBER FOR WHAT ACTION IS DESIRED OF OPERATOR
# INTO THE REGISTERS REFERRED TO BY THE 'CHECKLIST' NOUN.
# GO TO NVSUB WITH A DISPLAY VERB AND THE 'CHECKLIST' NOUN.
# GO TO NVSUB AGAIN WITH THE 'PLEASE PERFORM' VERB AND ZEROS IN THE
# LOW 7 BITS.
```

The first call displays what needs to be done (the checklist item number in R1, R2, R3 via the checklist noun). The second call "pastes" the "Please Perform" verb into the verb display, creating a flashing display that says, in effect, "V50 N25: please do item X."

### 4.6 NVMONOPT — Monitor with Please Verb

`NVMONOPT` extends `NVSUB` for monitor verbs that also need to paste a "please" verb after each display update:

```agc
# NVMONOPT IS AN ENTRY SIMILAR TO NVSUB, BUT REQUIRING AN ADDITIONAL
# PARAMETER IN L. IT SHOULD BE USED ONLY WITH A MONITOR VERB-NOUN CODE IN
# A. AFTER EACH MONITOR DISPLAY A *PLEASE* VERB WILL BE PASED INTO THE VERB
# LIGHTS OR DATA WILL BE BLANKED (OR BOTH)
```

### 4.7 The Monitor System

Monitor verbs (V11–V17) create a once-per-second repeating display. The `MONITOR` routine saves the V/N combination in `MONSAVE` and sets up a Waitlist task:

```agc
MONITOR		...
		CCS	MONSAVE
		TC	+5		# IF MONSAVE WAS +, NO REQUEST
		CAF	ONE		# IF MONSAVE WAS 0, REQUEST MONREQ
		TC	WAITLIST
		EBANK=	DSPCOUNT
		2CADR	MONREQ
```

`MONREQ` is called by the Waitlist every second (delay = 144 octal = 100 decimal = 1 second at 10ms/tick):

```agc
MONDEL		OCT	144		# FOR 1 SEC MONITOR INTERVALS
```

It checks the kill bit, re-enters itself into the Waitlist, and spawns an Executive job (`MONDO`) to do the actual display update. This separation is important: Waitlist tasks run in interrupt context and must be short, but display updates require Executive-level operations.

The monitor is killed by the "kill monitor bit" (bit 15 of `MONSAVE1`), which is set by `KILMONON` when the astronaut does V33 (proceed), V34 (terminate), V32 (resequence), or when a new NVSUB call supersedes the monitor:

```agc
KILMONON	CAF	BIT15
		TS	MONSAVE1	# TURN OFF BIT 14, THE EXTERNAL MONITOR BIT.
		TC	Q
```

---

## 5. Cultural Notes

### 5.1 Why "Pinball Game"?

The module header says `LOG SECTION -- PINBALL GAME BUTTONS AND LIGHTS`. The name reflects the whimsical culture of MIT's Instrumentation Laboratory. The DSKY, with its blinking lights and button-pressing interface, apparently reminded the programmers of a pinball machine. The name stuck through years of flight software development.

### 5.2 Credits

The module credits read:
```
# MOD BY -- FILENE
```

Robert J. Filene of MIT/IL was the primary author. The reference document is "Keyboard and Display Program Operation" by **Alan I. Green and Robert J. Filene** (MIT/IL E-2129).

### 5.3 The Shakespeare Quotation

The file opens with a literary flourish:

```
# ::IT WILL BE PROVED TO THY FACE THAT THOU HAST MEN ABOUT THEE THAT
# USUALLY TALK OF A NOUN AND A VERB, AND SUCH ABOMINABLE WORDS AS NO
# CHRISTIAN EAR CAN ENDURE TO HEAR.::
#					HENRY 6, ACT 2, SCENE 4
```

Ron Burkey's annotation corrects the citation: it's actually from *Henry VI*, Part 2, Act IV, Scene VII — the scene where Jack Cade's rebels condemn Lord Say for the crime of literacy. The irony is deliberate and delicious: the AGC programmers were being accused of using "abominable" words (verbs and nouns) by critics who thought the interface wasn't scientific enough.

### 5.4 The Origin Story

The extended annotation from Ramón Alonso tells the full story: the Verb-Noun interface was thrown together for a demo unit, never intended for flight. Objections ranged from "it's not scientific" to "astronauts won't understand it." The programmers countered with "perhaps sophistic arguments" and won. Most astronauts didn't like it — they wanted dials and switches. Dave Scott was apparently the lone exception who spoke well of the AGC.

### 5.5 GOTOPOOH and the Idle State

`GOTOPOOH` (not in this file, but frequently referenced) sends the AGC to Program 00 — the idle state, also known as "P-double-zero" or, affectionately, "Pooh," as in Winnie the Pooh. When the computer has nothing to do, it goes to Pooh. V37N00E (change major mode to 00) invokes this. The V37 handler is `MMCHANG`:

```agc
MMCHANG		TC	REQMM
		CAF	BIT5
		AD	DSPCOUNT
		EXTEND
		BZF	+2
		TC	ALMCYCLE	# DEMAND 2 NUM CHAR WERE PUNCHED IN
```

It demands exactly two numeric characters for the mode code, then routes to `MODROUTB` (which equals `V37`, the program change handler in the service routines). The new mode number appears in A.

---

## 6. Design Significance

### 6.1 The First Verb-Noun Interface

The Pinball module is one of the earliest implementations of a structured command language for human-computer interaction. It predates:
- Unix shells (1971)
- SQL (1974)
- Any modern CLI or REPL

The Verb-Noun paradigm maps remarkably well to modern concepts:
- **Verb** → command/function name
- **Noun** → argument/parameter
- **ENTER** → execute/return
- **Extended verbs** → subcommands or plugins
- **NVSUB** → programmatic API for the same interface
- **DSPLOCK** → a mutex/semaphore for display access
- **Monitor verbs** → `watch` command / live dashboards
- **ENDIDLE** → `await` / `Promise` / blocking I/O

### 6.2 Hardware Constraints as Design Drivers

The DSKY had:
- **19 keys**: digits 0–9, VERB, NOUN, ENTER, CLEAR, KEY RELEASE, ERROR RESET, +, -, and PRO
- **Three 5-digit registers** (R1, R2, R3) with sign indicators
- **Two 2-digit registers** (Verb, Noun)
- **One 2-digit register** (Program/Major Mode)
- **Status lights**: COMP ACTY, UPLINK ACTY, TEMP, KEY REL, OPR ERR, and others

With only 21 digit positions and no alphabetic display, every piece of information had to be encoded as numbers. This forced the two-digit code system: you couldn't display "VELOCITY" — you had to display "06" and the astronaut had to know that Noun 06 was "Option Code" or whatever. Cue cards were velcroed to the spacecraft panels listing all the V/N combinations.

The lack of a hardware character generator also explains the relay-code tables in the software. The 5-bit codes don't represent characters — they represent which physical relays to energize to illuminate the right segments.

### 6.3 Software vs Hardware in the DSKY

Almost everything is software. The hardware provides:
- Interrupt generation on keypress
- The electroluminescent display segments
- The V/N flash circuit (toggled by a single bit)
- Status indicator lamps (toggled by output channel bits)

Everything else — character encoding, display buffering, input parsing, decimal conversion, command dispatch, the monitor system, display locking, error handling — is software. The `DSPTAB` double-buffer scheme with dirty flags is a software optimization to minimize the number of I/O channel writes (which are relatively expensive in CPU cycles).

### 6.4 The DSPTAB Dirty-Flag Architecture

The `DSPTAB` sign-bit scheme deserves special note. Each DSPTAB entry uses its sign bit as a "needs update" flag:
- **Positive**: this entry has been written to the hardware display
- **Negative**: this entry has been modified and needs to be sent to hardware

The T4RUPT display service scans for negative entries, writes them to I/O channel 10, and flips them positive. `NOUT` counts how many negative entries exist, so the ISR can skip scanning when `NOUT` = 0. This is essentially a 1960s implementation of a dirty-page table — the same concept used in modern virtual memory systems and graphics engines.

### 6.5 The One-Job ENDIDLE Constraint

The restriction that only one job can sleep in ENDIDLE at a time seems limiting, but it reflects a fundamental UI truth: there's only one astronaut looking at one DSKY. Only one question can be asked at a time. If a second program tries to ask a question while the first is still waiting for an answer, that's a design error — and the code catches it with an abort (code 01206).

This constraint is also why the display locking system exists. Internal programs must coordinate their display use, and the astronaut always has priority. The architecture is essentially a single-writer, multiple-reader system with the astronaut as the privileged writer.

---

## Summary

The Pinball module is a complete user interface framework implemented in ~3,800 lines of AGC assembly. It provides:

| Feature | Implementation |
|---------|---------------|
| Command parsing | Jump table dispatcher with decimal/octal input assembly |
| Display management | Double-buffered DSPTAB with dirty-flag tracking |
| Access control | DSPLOCK semaphore + DSPLIST wait queue |
| Data formatting | 14 scale factor routines for degrees, velocity, position, time, etc. |
| Noun abstraction | Table-driven data binding with normal and mixed noun types |
| Asynchronous I/O | ENDIDLE sleep/wake with 3-way response routing |
| Periodic updates | Monitor system with 1-second Waitlist-driven refresh |
| Error handling | Operator Error light, alarm codes, input validation |

It was written without an operating system, without dynamic memory allocation, without a stack, and with 2K of RAM and 36K of ROM. The programmers tracked their own binary points, managed their own bank switching, and hand-optimized every multiply. And yet the architecture — event-driven input, double-buffered display, table-driven data binding, mutex-protected shared resources — would be recognizable to any modern UI framework developer.

The Pinball module is not just historically significant as the world's first Verb-Noun command interface. It is a masterclass in building a complete, robust, real-time user interface system under extreme resource constraints. Every feature exists because it was needed. Nothing is wasted. The code is dense, but it is not clever for cleverness's sake — it is clever because 38,912 words was all they had, and the Moon was waiting.