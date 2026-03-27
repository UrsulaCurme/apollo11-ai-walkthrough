# Phase 3 — Deep Dive Prompts

_Run these one at a time, in order. Each produces a walkthrough markdown file. After each, note in PROCESS.md what the AI got right, what it got wrong, and what you corrected._

---

## 3A: The Executive (Job Scheduler)

```
Read Luminary099/EXECUTIVE.agc.

The AGC had no operating system. The Executive implements the entire cooperative
multitasking job scheduler from scratch.

Analyze the file and produce a walkthrough covering:

1. **Core Data Structures**
   - How are jobs represented? What is a "core set"? How many exist?
   - What fields does each core set contain? (priority, LOC, MPAC, VAC area)
   - How does the PRIORITY register encode job state? (positive=active, negative=sleeping, -0=free)

2. **Job Creation (FINDVAC / NOVAC)**
   - Trace the FINDVAC routine step by step — how does it find a free core set?
   - What is the difference between FINDVAC and NOVAC?
   - What are VAC areas and how are they allocated?
   - What happens when all core sets are full? (the 1202 alarm path)

3. **Scheduling and Context Switching**
   - How does priority-based scheduling work? Trace the EJSCAN priority scan
   - How does a job voluntarily yield? (CHANG1/CHANG2)
   - How does the context switch work? What registers are saved/restored?
   - What is NEWJOB and how is it used?

4. **Job Lifecycle**
   - How does a job sleep? (JOBSLEEP)
   - How is a sleeping job woken? (JOBWAKE)
   - How does a job terminate? (ENDOFJOB)
   - What is DUMMYJOB and what does the idle loop look like?

5. **Modern parallels**
   - Compare to FreeRTOS task management
   - What would a modern developer find surprising?

Be specific: cite line numbers, trace register contents through key routines,
and show actual instruction sequences for critical paths.

Save as walkthrough/01-executive.md
```

---

## 3A2: The Waitlist (Timer-Driven Task Scheduler)

```
Read Luminary099/WAITLIST.agc.

The Waitlist is the AGC's timer-driven preemptive task scheduler, complementing
the Executive's cooperative job scheduler. Waitlist tasks are short, time-critical
operations triggered by hardware timer interrupts.

Analyze the file and produce a walkthrough covering:

1. **Architecture**
   - What is the difference between an Executive job and a Waitlist task?
   - How are tasks stored? (LST1 delta-time array, LST2 2CADR array)
   - What is the maximum number of concurrent tasks?
   - What is the sentinel task (ENDTASK)?

2. **T3RUPT and Task Dispatch**
   - How does TIME3 overflow trigger T3RUPT?
   - Trace the T3RUPT handler: how is the first task dispatched?
   - How are subsequent tasks' timers updated when the first fires?
   - What happens when a task finishes? (TASKOVER)

3. **Task Insertion**
   - Trace the WAITLIST entry point: how is a new task inserted into the sorted list?
   - How does the XCH rotation chain work for array insertion?
   - What happens if the list is full? (alarm 1203)

4. **FIXDELAY / VARDELAY / LONGCALL**
   - How does a task reschedule itself? (FIXDELAY reads inline delay, VARDELAY from A)
   - What is LONGCALL and when is it needed?
   - What are the timing constraints? (minimum delay, maximum delay)

5. **Timing Analysis**
   - The header contains a hand-written WCET analysis. Explain it.
   - What are the real-time guarantees?
   - How does this compare to modern RTOS timer systems?

Be specific: cite line numbers, trace register contents through key routines,
and show actual instruction sequences for critical paths.

Save as walkthrough/02-waitlist.md
```

---

## 3B: The Alarm Handler That Saved Apollo 11

```
Read Luminary099/FRESH_START_AND_RESTART.agc and Luminary099/ALARM_AND_ABORT.agc.

During the Apollo 11 landing, the AGC triggered 1202 and 1201 program alarms — 
executive overflow, meaning all VAC areas were occupied and the computer could 
not schedule a new job. The rendezvous radar had been left on, flooding the computer 
with interrupts. Margaret Hamilton's restart architecture saved the mission.

Analyze both files and produce a walkthrough covering:

1. **Fresh Start vs. Restart**
   - What is the difference between a fresh start (power-up) and a restart (software reset)?
   - What state is preserved across a restart? What is lost?
   - How does the code decide which type of initialization to perform?

2. **The Restart Logic**
   - Trace the restart entry point step by step
   - How does the AGC detect which phase of which program was running when the restart occurred?
   - What is the "phase table" mechanism? How do programs register restart points?
   - How does the restart logic decide what to kill and what to keep running?

3. **The 1202/1201 Alarm**
   - Where in the code is executive overflow detected?
   - What alarm code is generated?
   - How does the code decide the landing program should survive while lower-priority 
     tasks are shed?
   - Trace the path from alarm detection to resumed execution

4. **The Design Philosophy**
   - Why did Hamilton's team design the system this way?
   - How does this compare to modern approaches to graceful degradation?
   - What would have happened with a simpler error-handling approach?

Cite specific line numbers and instruction sequences. Trace the critical decision 
path that keeps P63/P64 running while shedding radar processing.

Save as walkthrough/03-restart.md
```

---

## 3C: The Landing Guidance Equations

```
Read Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc.

This file contains Programs 63, 64, and 66 — the guidance routines that flew 
the Lunar Module from ~50,000 feet to the surface of the Moon.

Analyze the file and produce a walkthrough covering:

1. **The Three Landing Programs**
   - P63 (Braking Phase): What is the guidance law? What sensor inputs drive it? 
     How is the throttle computed? When does it hand off to P64?
   - P64 (Approach Phase): How does this differ from P63? Where does the landing 
     point designation enter? What is the "LPD angle" displayed to the astronaut?
   - P66 (Manual Control): How does the astronaut take over from automatic guidance? 
     What does the computer still control in P66? What is the ROD (Rate of Descent) mode?

2. **Guidance Math**
   - Identify the key equations (look for the guidance acceleration computations)
   - How is the gravity turn modeled?
   - Where does landing radar data enter the computation?
   - What fixed-point scaling is used? What precision trade-offs were made?
   - Note: much of the math will be in INTERPRETER language (VLOAD, DLOAD, etc.), 
     not native AGC assembly

3. **Control Flow**
   - How does the code transition between P63 → P64 → P66?
   - What triggers each transition?
   - Where are the DSKY displays updated (Noun 63, Noun 64)?

4. **Historical Context**
   - The "crank the silly thing around" comment — what is it about?
   - Any other notable comments or Easter eggs?
   - What temporary code became permanent? (look for the famous "TEMPORARY" comment)

Flag any guidance math you cannot fully verify. This is dense interpreter code 
with implicit scaling — it's okay to say "I can see this is computing a gravity 
compensation vector but I cannot verify the scaling factor."

Save as walkthrough/04-landing-guidance.md
```

---

## 3D: The Master Ignition Routine (BURN_BABY_BURN)

```
Read Luminary099/BURN_BABY_BURN--MASTER_IGNITION_ROUTINE.agc.

This routine controls engine ignition sequencing for the Lunar Module — literally 
the code that throttled the descent engine so Armstrong and Aldrin could land.

Analyze the file and produce a walkthrough covering:

1. **Technical Function**
   - What does this routine actually do? Walk through the ignition sequence
   - How does it interface with the engine (which I/O channels)?
   - What safety checks are performed before ignition?
   - How is thrust timing managed?

2. **Cultural Archaeology**
   - Catalog EVERY comment in this file that isn't strictly technical — jokes, 
     cultural references, programmer personality
   - The header note about Don Eyles and Peter Adler — what's the full story?
   - "BURN_BABY_BURN" — origin in Magnificent Montague and the 1965 LA riots
   - "OFF TO SEE THE WIZARD" — what's happening technically when this comment appears?
   - "HAS THE LITTLE OLD LADY LEFT?" — what does this check?
   - Any other references you can identify

3. **Code Quality**
   - How is this code structured compared to the guidance equations?
   - Is it primarily native AGC or interpreter code?
   - What does the control flow look like?

This file is a cultural artifact as much as a technical one. Give both aspects 
equal weight.

Save as walkthrough/05-burn-baby-burn.md
```

---

## 3E: The Interpreter (Virtual Machine)

```
Read Luminary099/INTERPRETER.agc (and any associated files like 
INTER-BANK_COMMUNICATION.agc if relevant).

The AGC team built an interpreted language layer on top of native assembly to 
fit more functionality into 36K words of ROM. This is a software virtual machine 
running on a 15-bit computer in 1966.

Analyze the file and produce a walkthrough covering:

1. **Architecture**
   - How does a `TC INTPRET` call switch from native AGC to interpreted mode?
   - How are interpreted opcodes packed? (two 7-bit opcodes per word, with address fields)
   - How does the EDOP register decode the packed opcodes?
   - Where is the interpreter's "program counter" stored?
   - How does the interpreter dispatch to handler routines for each opcode?

2. **Instruction Categories**
   - Load/Store: VLOAD, DLOAD, SLOAD, STORE, STODL, STOVL
   - Arithmetic: DAD, DSU, DMP, DDV, DMPR, BDDV
   - Vector: VAD, VSU, VXV, DOT, VPROJ, VXSC, V/SC
   - Matrix: MXV, VXM
   - Trig: SIN, COS, ASIN, ACOS
   - Control: CALL, GOTO, RTB, EXIT, BON, BOFF, BMN, BPL, BZE
   - How many total interpreted instructions exist?

3. **The Engineering Trade-off**
   - Why was a subroutine library rejected in favor of an interpreter? 
     (reference the AGC4 Basic Training Manual rationale)
   - What is the typical execution time of an interpreted instruction vs. native?
   - How much ROM did the interpreter save?
   - Where is the performance penalty visible in the flight software?

4. **Computer Science Significance**
   - This is one of the earliest deployed p-code / bytecode interpreters
   - How does it compare to the Java JVM or Python bytecode interpreter conceptually?
   - What design choices were driven by the 15-bit word size?

This is dense code. Focus on the dispatch loop and opcode decoding mechanism 
rather than trying to trace every single instruction handler.

Save as walkthrough/06-interpreter.md
```

---

## 3F: Pinball Game — DSKY Keyboard and Display System

```
Read Luminary099/PINBALL_GAME_BUTTONS_AND_LIGHTS.agc and 
Luminary099/PINBALL_NOUN_TABLES.agc.

The DSKY (Display and Keyboard) was the astronaut's only interface to the AGC.
Commands were entered as two-digit Verb-Noun pairs. The code that managed this
interface was called "Pinball Game" — and at ~3,800 lines it is one of the
largest single modules in Luminary.

Analyze both files and produce a walkthrough covering:

1. **The Verb-Noun Command System**
   - How does the Verb-Noun paradigm work? What are some key Verb/Noun combinations?
   - How are keystrokes received? (KEYRUPT1 interrupt → how does it reach Pinball?)
   - How does the code parse a two-digit Verb and a two-digit Noun from individual keystrokes?
   - What happens when the astronaut presses ENTR, CLR, KEY REL, RSET, PRO?
   - How are "extended verbs" (V40+) handled differently from regular verbs?

2. **Display Management**
   - How are the three 5-digit display registers (R1, R2, R3) managed?
   - What is DSPTAB and how does it map to the physical DSKY electroluminescent displays?
   - How does the code handle multiple programs competing to use the DSKY?
   - What is the "priority display" vs "normal display" vs "operator request" system?
   - How are numeric values converted to the 5-digit signed decimal format shown on the DSKY?

3. **The Noun Tables (PINBALL_NOUN_TABLES.agc)**
   - How is a Noun defined? What data does the noun table contain per noun?
   - How does the code know where to find the data for a given Noun?
   - What are "normal nouns" vs "mixed nouns"?
   - How does the scaling/formatting work for display? (octal, decimal, degrees, etc.)

4. **Flashing Displays and the Please Perform Mechanism**
   - How does a flashing Verb-Noun display work? (requesting astronaut action)
   - What are the three possible astronaut responses (PROCEED, TERMINATE, RECYCLE)?
   - How does V50N25 ("Please perform checklist item") work?
   - How does V06N61 ("Display time") work?

5. **Cultural Notes**
   - Why is this module called "Pinball Game"?
   - The file header credits — who wrote this?
   - Any notable comments, humor, or personality in the code?
   - GOTOPOOH (P00 = Pooh) — how does the idle state work?

6. **Design Significance**
   - This is one of the earliest implementations of a Verb-Noun command language
   - How does it compare to modern CLI systems or REPL interfaces?
   - What UI/UX constraints did 19 keys and 7-segment displays impose?
   - How much of the DSKY's behavior is hardware vs software?

The PINBALL module is large. Focus on the command parsing state machine,
the display management architecture, and the noun table structure rather
than tracing every individual verb handler.

Save as walkthrough/07-dsky-interface.md
```

---

## SYNTHESIS: Lessons for 2026

```
You have just read seven detailed walkthroughs of the Apollo 11 AGC flight software.
Each one analyses a different subsystem — scheduling, timers, restart protection,
guidance equations, engine ignition, the interpreter virtual machine, and the
astronaut interface.

Now step back and synthesise what these 1960s engineers got right, what modern
developers can learn, and what resonates with how we build software today.

Write a final chapter covering:

1. **Architectural Patterns Ahead of Their Time**
   - Priority-based cooperative multitasking (Executive) vs modern green threads / coroutines
   - The restart / checkpoint system vs modern crash-only design and idempotency
   - The Interpreter as an early bytecode VM — how does the trade-off compare to JVM / WASM?
   - Verb-Noun as a command language — parallels to CLI, REPL, and chatbot UIs

2. **Constraints as a Design Force**
   - 36 K words of ROM, 2 K words of RAM, 15-bit words, ~80 µs cycle time
   - How did these constraints shape the architecture in ways that produced
     *better* designs than unconstrained modern systems sometimes do?
   - What happens when you CAN'T add another microservice — or another dependency?

3. **Reliability Engineering**
   - The 1202 alarm story: why the software survived and what it teaches about
     graceful degradation, priority shedding, and the value of restart tolerance
   - How does AGC restart protection compare to Erlang's "let it crash" philosophy?
   - What modern systems would benefit from AGC-style checkpoint/restart?

4. **The Human Element**
   - The comments, jokes, and cultural references scattered through the code
   - What do they tell us about the team, the era, and the craft of programming?
   - Margaret Hamilton's "priority displays" insight and software engineering as a discipline

5. **What Would a 2026 Engineer Do Differently?**
   - Which AGC design decisions are genuinely timeless?
   - Which are artefacts of the hardware era and would be done differently today?
   - If you were building a safety-critical embedded system today with modern
     constraints (cybersecurity, OTA updates, ML models), which AGC lessons apply?

Be opinionated. This is an essay, not a summary. Draw specific connections between
AGC code you've seen in the walkthroughs and modern software practice.

Save as walkthrough/08-lessons.md
```

---

## After All Deep Dives: Update PROCESS.md

After completing each deep dive, add to PROCESS.md:
1. The exact prompt used (as executed, not as planned — note any modifications)
2. How long the analysis took
3. What the AI got right on the first pass
4. What it got wrong (with specific examples)
5. What corrections you made and how you verified them
6. Any additional context you had to inject mid-analysis
