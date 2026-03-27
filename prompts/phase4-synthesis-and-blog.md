# Phase 4 — Synthesis Prompt

_Run this after all deep dives are complete._

---

## PROMPT

```
Based on your analysis of the Apollo 11 AGC source code across all modules 
(Executive, Waitlist, Restart/Alarm, Landing Guidance, Burn Baby Burn, 
Interpreter), write a synthesis document structured around three themes:

1. **What the AGC got right that we've forgotten**
   - Priority scheduling with deterministic behavior under overload
   - Graceful degradation by design (not by accident)
   - The restart/checkpoint architecture
   - Separation of concerns between Executive (batch jobs) and Waitlist 
     (real-time tasks)
   - Testing against edge cases that "should never happen"

2. **What the constraints forced — and why it was brilliant**
   - Fixed-point math in a world that assumed floating point was necessary
   - The interpreter trick: a virtual machine to beat a ROM budget
   - Fitting everything in 72 KB including the "operating system"
   - The DSKY interface: a full command system through Verb-Noun pairs on 19 keys
   - Core rope memory: software literally woven into hardware

3. **What surprised you — things no modern developer would expect**
   - The humor in the comments (catalogue the best examples across all files)
   - The sophistication of the fault handling relative to the era
   - Where the code is more improvised than expected
   - Where it is more disciplined than most modern codebases
   - The human fingerprints: naming conventions, personal comments, 
     "TEMPORARY" code that shipped to the Moon

Be specific. Cite file names, line numbers, and actual code snippets. 
Flag anywhere you are uncertain about your interpretation.

This document will be the backbone of a blog post. Write it as analysis, 
not as a tutorial — assume the reader has NOT read the individual module 
walkthroughs but IS a working software engineer.

Save as walkthrough/08-lessons.md
```

---

# Phase 5 — Blog Post Prompt

_Run this last, after the synthesis is complete and reviewed._

---

## PROMPT

```
I need to write a blog post for The AI Realist (my Substack) about this project.

The angle: "I used AI to walk through the code that landed humans on the Moon. 
Here's what I found."

The audience: technical practitioners who follow AI developments. They are 
skeptical of AI hype but open to demonstrated utility. Many are senior 
engineers or CTOs.

Structure the post around these beats:

1. **The Hook** (2-3 sentences)
   Why the Apollo 11 source code. Why now. Why AI.

2. **The Setup** (~200 words)
   What the AGC source code is, where it lives (GitHub), why it's nearly 
   unreadable to modern developers (1's-complement, 15-bit words, bank switching, 
   dead assembly language). Brief mention of what already exists (Pluralsight course, 
   Medium posts, Virtual AGC project) and what doesn't (systematic AI analysis).

3. **The Method** (~300 words)
   How I set this up. The critical insight that you MUST front-load architectural 
   context — without the Phase 1 prompt, the AI assumes modern conventions and 
   hallucinates. Show the structure: context priming → repo reconnaissance → 
   targeted deep dives → synthesis. Mention Claude Code specifically.

4. **The Findings** (~500 words)
   The 3-4 most striking things the walkthrough revealed, drawn from the synthesis:
   - The restart architecture that saved Apollo 11
   - The interpreter (a VM inside a 72KB computer in 1966)
   - What the humor in the comments tells us about the engineering culture
   - A specific technical insight from the landing guidance equations
   Each finding should have a concrete code reference.

5. **Where the AI Struggled** (~200 words)
   Honest accounting. What did Claude Code get wrong? Fixed-point scaling, 
   bank switching logic, interpreter opcode decoding? Specific examples. 
   How I caught and corrected the errors. This section is what gives the 
   post credibility.

6. **The Takeaway** (~150 words)
   This isn't about AI replacing developers. It's about AI as a *reading* tool. 
   Most code is read far more than it is written, and most important code is old. 
   If AI can make the Apollo AGC accessible, what else can it unlock? 
   Legacy modernization, regulatory code review, due diligence on acquisitions.
   
   End with: link to the GitHub walkthrough, invite comments.

Constraints:
- No AI writing mannerisms (no "delve", "tapestry", "rich", "landscape", 
  "it's worth noting", "let's explore")
- No breathless tone. This is practitioner writing, not marketing
- Short paragraphs. Direct sentences. Technical specificity over hand-waving
- Total length: 1,200-1,500 words
- Include a note at the end: "The complete walkthrough, including all prompts 
  used and a full process trace, is on GitHub: [link]"

Save as blog/blog-post.md
```
