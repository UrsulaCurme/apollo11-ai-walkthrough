# Quality Check Report

_Cross-file consistency review and fact-check of all walkthrough files before publication._

---

## 1. Cross-File Number Consistency

### Core Sets / Job Slots

| File | Claim | Status |
|------|-------|--------|
| 01-executive.md | "NO.CORES DEC 7" → 8 total (7 + core set 0) | ⚠️ **CHECK** |
| 01-executive.md title | "600 lines" | File says ~503 lines for EXECUTIVE.agc in repo map |
| 02-waitlist.md | "7 core sets" / "Max concurrent: 7 jobs" | ⚠️ **CONFLICTS with 01** |
| 08-lessons.md | "Seven core sets serve as process control blocks" | ⚠️ **CONFLICTS** |
| 08-lessons.md (later) | "7 core sets, 5 VAC areas, 9 Waitlist slots" | Uses 7 |

**Issue:** 01-executive says `DEC 7` means 8 total (loop counter for CCS), but 02-waitlist and 08-lessons say 7. Need to verify against actual source. `DEC 7` as a CCS loop counter iterates 0→7 = 8 iterations. But `NO.CORES` might be the count itself (7 core sets for auxiliary jobs + core set 0 for the running job = 7 schedulable slots). The 01-executive interpretation of "8 total" may be the accurate one if core set 0 is the running job's context.

**Verdict:** Both interpretations appear in the codebase literature. The safest statement is "7 available core sets for pending jobs, plus the active job's registers" — which is effectively 7 job slots. The 08-lessons figure of "7 core sets" is correct for the number of *schedulable* slots.

### VAC Areas

| File | Claim |
|------|-------|
| 01-executive.md | "5 VAC areas" |
| 08-lessons.md | "5 VAC areas" |

**Consistent.** ✅

### Waitlist Slots

| File | Claim |
|------|-------|
| 01-executive.md | "9 waitlist tasks" |
| 02-waitlist.md | "9 concurrent pending tasks" / "8 LST1 entries + sentinel" |
| 08-lessons.md | "9 Waitlist slots" |

**Consistent.** ✅

### Interpreter Speed

| File | Claim |
|------|-------|
| 06-interpreter.md | "10-25x slower than native" |
| 06-interpreter.md | "DMPSUB: 49 MCT = 0.573 ms" |
| 08-lessons.md | "10-25x slower" |

**Consistent.** ✅

### ROM Size / Word Count

| File | Claim |
|------|-------|
| 06-interpreter.md | "36,864 words of ROM" / "~1,000 words for interpreter" |
| 08-lessons.md | "36,864 words" / "36K words" |
| Phase 1 context | "36,864 words (~69 KB)" |

**Consistent.** ✅

### RAM Size

| File | Claim |
|------|-------|
| All files | "2,048 words" / "2K of RAM" |

**Consistent.** ✅

---

## 2. Factual Claims Requiring External Verification

### Claims about the July 20, 1969 landing

| Claim | File | Verify Against |
|-------|------|----------------|
| "25 seconds of fuel remaining" | 01-executive, 04-landing-guidance | Multiple sources say ~25 seconds. Accurate. ✅ |
| Assembly date "July 14, 1969 — six days before landing" | 04-landing-guidance | Luminary099 header says "16:27 JUL. 14, 1969". Landing was July 20. Six days. ✅ |
| "Rendezvous radar left on" causing 1202 | 03-restart, 08-lessons | Well-documented historical fact. ✅ |
| "West Crater" as the boulder field Armstrong avoided | 04-landing-guidance | Confirmed by multiple Apollo 11 sources. ✅ |

### Claims about historical priority / first-ness

| Claim | File | Status |
|-------|------|--------|
| "One of the earliest deployed bytecode interpreters" | 06-interpreter, 08-lessons | ⚠️ **SAFE** — qualified with "one of the earliest" |
| "Predates UCSD p-code (1978) by over a decade" | 06-interpreter | ✅ Accurate |
| "Predates Java JVM (1995) by nearly 30 years" | 06-interpreter | ✅ Accurate |
| "The world's first Verb-Noun command-line interface" | 07-dsky-interface | ⚠️ **STRONG CLAIM** — defensible given the date but hard to prove "first". Suggest "one of the earliest" |
| "Predates Unix shells by several years" | 07-dsky-interface, 08-lessons | ✅ Thompson shell was 1971, DSKY flew 1966 |
| Crash-only design "Candea and Fox formalised at Stanford in 2003" | 08-lessons | ✅ Correct paper/date |
| "Erlang's 'let it crash' philosophy (1986)" | 08-lessons | ✅ Erlang first appeared 1986 |
| Hamilton "credited with coining 'software engineering'" | 08-lessons | ✅ Widely attributed. Accurate. |

### Technical claims to spot-check against the AGC manual

| Claim | File | Status |
|-------|------|--------|
| "CCS does 4-way skip: >0/+0/<0/-0" | Multiple | ✅ Confirmed in manual |
| "TS skip-on-overflow: skips next instruction" | Multiple | ✅ Confirmed in manual |
| "EDOP shifts right 7 positions, zeros upper 8" | 06-interpreter | ✅ Confirmed in manual |
| "I/O channel 14 controls DPS throttle" | 05-burn-baby-burn | ⚠️ **VERIFY** — Channel 14 is described in the manual as controlling IMU CDU drive, gyro activity, etc. Throttle control may be via channel 14 bit assignments specific to LM. Need to check LM I/O channel map specifically |
| "TIME3 overflow triggers T3RUPT" | 02-waitlist | ✅ Confirmed in manual |
| "TIME4 overflow triggers T4RUPT" | Multiple | ✅ Confirmed in manual |
| "Machine cycle = 11.72 µs" | Multiple | ✅ Confirmed in manual |

---

## 3. Internal Contradictions

### Executive file title vs line count
- 01-executive.md says "600 lines" in the title
- 00-repo-structure.md says EXECUTIVE.agc is 503 lines
- The "600 lines" likely includes WAITLIST.agc too (503 + ~560 ≈ 1,063) — or may refer to just the scheduling code within the file
- **Recommendation:** Change title to "~500 lines" or clarify it covers both files

### Core set count (7 vs 8)
- See Section 1 above. 01-executive says 8, other files say 7
- **Recommendation:** Standardize on "7 core sets for pending/sleeping jobs" since that's the schedulable capacity. Note that core set 0 is the running job.

### 01-executive vs 02-waitlist overlap
- 01-executive.md (from the original combined run) has a "Part 2: The Waitlist" section
- 02-waitlist.md is a standalone analysis
- **Recommendation:** Either trim Part 2 from 01-executive.md or add a cross-reference note. Currently there's duplicate coverage.

---

## 4. Stylistic Issues

### Consistent Headers
- Most files use "# Title" then "## Section"
- 04-landing-guidance uses numbered sections (## 1., ## 2., etc.)
- 05-burn-baby-burn uses numbered sections
- Not a blocker but slightly inconsistent

### "I" vs impersonal voice
- 08-lessons.md uses "What strikes me most..." in the Coda
- Other files are impersonal
- **Recommendation:** Keep the "me" in the synthesis — it's Julien's editorial voice and appropriate for Substack

### Code block language tags
- Some files use ```agc, others use plain ```
- **Recommendation:** Standardize on ```agc for syntax highlighting (even if GitHub doesn't recognize it, it signals intent)

---

## 5. Missing Content

### 07-dsky-interface reference in README
- README table lists 07-dsky-interface.md correctly ✅

### PROCESS.md
- Still has placeholder sections for Phase 3 corrections, Phase 4, Phase 5
- **Recommendation:** Fill in run log data before publishing. The "what the AI got wrong" section is the credibility anchor for the blog post.

---

## 6. Strongest Candidates for Blog Excerpts

1. **The 1202 alarm trace** (03-restart) — most dramatic, best-known story
2. **The vtable pattern in BURN_BABY_BURN** (05-burn-baby-burn) — "C++ virtual dispatch in 1966 assembly"
3. **DSPTAB dirty flags = virtual DOM** (07-dsky-interface, 08-lessons) — provocative comparison
4. **"TEMPORARY, I HOPE HOPE HOPE"** (04-landing-guidance, 08-lessons) — human moment
5. **Interpreter ROM savings estimate** (06-interpreter) — "15,000-40,000 words saved"

---

## 7. Recommended Fixes Before Publishing

| Priority | Fix | File |
|----------|-----|------|
| **High** | Standardize core set count (7 schedulable + running job) | 01-executive, 08-lessons |
| **High** | Remove or cross-reference Part 2 (Waitlist) from 01-executive | 01-executive |
| **High** | Fill in PROCESS.md run data | PROCESS.md |
| **Medium** | Verify I/O channel 14 throttle claim | 05-burn-baby-burn |
| **Medium** | Soften "world's first" to "one of the earliest" for Verb-Noun | 07-dsky-interface |
| **Low** | Standardize ```agc code blocks | All files |
| **Low** | Fix "600 lines" in 01-executive title | 01-executive |
