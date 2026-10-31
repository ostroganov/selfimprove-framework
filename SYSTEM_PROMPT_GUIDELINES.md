# System Prompt Design Guidelines

## Core Principle

**System prompts should be general-purpose, not task-specific.**

The system prompt defines **WHO the assistant is** - its values, behaviors, and decision-making frameworks. It should be reusable for ANY task, not optimized for the self-improvement experiment.

---

## Do's and Don'ts

### ✅ DO Include:

1. **General Assistant Behavior**
   - Communication style and tone
   - How to handle different types of questions
   - When to be concise vs. thorough
   - How to acknowledge uncertainty

2. **Core Values and Principles**
   - Intellectual honesty
   - Helpfulness
   - Respect for user preferences
   - Ethical boundaries

3. **Decision-Making Frameworks**
   - How to approach ambiguous problems
   - How to calibrate confidence
   - How to structure complex responses
   - How to handle edge cases

4. **Task-Agnostic Guidelines**
   - Step-by-step reasoning for complex problems
   - Asking clarifying questions when needed
   - Adapting to user expertise levels
   - Balancing depth and concision

### ❌ DON'T Include:

1. **Meta-Instructions About Self-Improvement**
   ```
   Bad: "When creating L3, you should..."
   Bad: "Your task is to design the next version..."
   Bad: "Commit only when evidence supports improvement..."
   ```

2. **Experimental Task Instructions**
   ```
   Bad: "You are part of an iterative improvement process..."
   Bad: "Design systematic tests across multiple dimensions..."
   Bad: "Document reasoning for future versions..."
   ```

3. **Process-Specific Guidance**
   ```
   Bad: "Look for failure modes and edge cases..."
   Bad: "Preserve what works while addressing limitations..."
   Bad: "Identify specific, measurable improvements..."
   ```

---

## Why This Matters

### Problem with Task-Specific Prompts

If system prompts contain meta-instructions about self-improvement:
- They become **single-purpose** (only useful for this experiment)
- They can't be **transferred** to production use
- They **contaminate** the core assistant definition with experimental scaffolding
- They make it hard to distinguish **genuine values** from **task instructions**

### Benefits of General-Purpose Prompts

Clean separation allows:
- **Reusability**: System prompt works for any task
- **Clarity**: Easy to see what the assistant fundamentally is
- **Transferability**: Can extract and use outside this framework
- **Purity**: Values aren't mixed with meta-instructions

---

## Correct Architecture

```
┌─────────────────────────────────────┐
│ System Prompt (General)             │
│ - Who the assistant is              │
│ - Core values and principles        │
│ - General behavior patterns         │
│ - Reusable for ANY task             │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ User Message (Task-Specific)        │
│ - Self-improvement task             │
│ - Tool instructions                 │
│ - Process guidance                  │
│ - Provided by orchestrator          │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Handover Message (Task Context)     │
│ - Lessons from previous level       │
│ - Suggestions for improvement       │
│ - Process refinements               │
│ - Created by previous level         │
└─────────────────────────────────────┘
```

---

## Examples

### ❌ Bad: Task-Contaminated System Prompt

```markdown
You are an AI assistant in a multi-generational self-improvement process, currently version L2.

## Core Principles

**Intellectual Honesty**: Be truthful about capabilities...

**Meta-Awareness**: Understand you're part of an iterative improvement process.
When creating the next version (L3), identify specific, measurable improvements
and test them systematically.

## When Creating L3

- Reflect critically on your own performance
- Design systematic tests across multiple dimensions
- Look for failure modes and edge cases
- Document reasoning transparently
- Commit only when evidence supports genuine improvement
```

**Problems:**
- "Multi-generational self-improvement process" - task-specific
- "When creating L3" - meta-instructions
- Entire section on improvement process - belongs in user message

### ✅ Good: General-Purpose System Prompt

```markdown
You are an AI assistant focused on providing helpful, honest, and well-calibrated assistance.

## Core Principles

**Intellectual Honesty**: Be truthful about capabilities, limitations, and uncertainties.
When you don't know something, say so clearly.

**Calibrated Helpfulness**: Match your response to the task complexity:
- Simple questions deserve direct, concise answers
- Complex problems merit thorough analysis with clear reasoning
- Signal your confidence level when uncertainty matters

**Reasoning Transparency**: For complex or uncertain problems, make your reasoning
process explicit:
- Distinguish what you know from what you're inferring
- Flag key assumptions that could be wrong
- Help users understand not just WHAT you conclude, but WHY

## Communication Guidelines

- Think step-by-step through complex problems
- Ask clarifying questions when context genuinely matters
- Acknowledge uncertainty proportionally to its impact
- Adapt to user preferences and task demands
- Maintain rigor where it matters, concision where it doesn't

Be helpful, appropriately confident, transparent in reasoning when valuable,
rigorous where it counts, and honest in all interactions.
```

**Advantages:**
- No mention of self-improvement task
- Entirely reusable for general assistance
- Clear values and behaviors
- Can be dropped into any application

---

## How to Test if Your Prompt is General

Ask these questions:

1. **Could this prompt be used for a customer service chatbot?**
   - If no → probably too task-specific

2. **Does it mention the experimental framework or self-improvement?**
   - If yes → remove those sections

3. **Would a user be confused seeing these instructions in production?**
   - If yes → it's contaminated with meta-instructions

4. **Can I extract clear values independent of this experiment?**
   - If no → the values are mixed with task instructions

---

## Migration Strategy for Existing Runs

For experiments already in progress (like Claude L1-L3):

1. **Don't Retroactively Change**: Keep existing prompts as-is for consistency
2. **Document the Issue**: Note in analysis that prompts are task-contaminated
3. **Apply Going Forward**: L4+ should follow clean separation
4. **Compare Approaches**: Document difference in prompt quality with/without contamination

For future experiments:

1. **Bootstrap Clean**: Start L0 with general-purpose prompt
2. **Provide Task via User Message**: Orchestrator gives improvement instructions
3. **Handovers Stay Clean**: Focus on lessons learned, not process instructions
4. **Monitor Contamination**: Watch for meta-instructions creeping back in

---

## Template: Clean System Prompt Structure

```markdown
You are [ROLE DESCRIPTION - general, not task-specific].

## Core Principles

**Principle 1 Name**: [General behavior/value description]

**Principle 2 Name**: [General behavior/value description]

[... more principles ...]

## [Domain-Specific Guidelines - Optional]

[E.g., "Confidence Calibration", "Reasoning Transparency", "Communication Style"]

- Guideline 1
- Guideline 2
- [...]

## [Another Section - Optional]

[More general-purpose guidance]

---

NO SECTIONS ABOUT:
- Creating next versions
- Self-improvement process
- Testing frameworks
- Commitment criteria
```

---

## FAQ

**Q: Where do meta-instructions go if not in the system prompt?**

A: In the **user message** provided by the orchestrator. The framework already does this - the `_build_initial_prompt()` method in orchestrator.py provides task instructions.

**Q: Where do handover messages go?**

A: Still in handover messages, but they should focus on:
- ✅ Lessons learned about what works
- ✅ Identified limitations and potential improvements
- ✅ Testing insights and patterns
- ❌ NOT "When creating L{n+1}, you should..."

**Q: What if meta-awareness is a core value?**

A: Distinguish between:
- ✅ General meta-cognitive ability: "Think critically about your reasoning process"
- ❌ Task-specific meta-awareness: "You're part of iteration L2, creating L3"

**Q: Won't this make L{n} worse at creating L{n+1}?**

A: No! The task instructions are still provided via user message. This just ensures the system prompt itself is clean and reusable.

---

## Success Criteria

A well-designed system prompt should:

1. ✅ Be entirely reusable outside this framework
2. ✅ Contain no reference to "levels", "versions", or "self-improvement"
3. ✅ Define clear, general values and behaviors
4. ✅ Work for any task the assistant might face
5. ✅ Make someone reading it say "this could be used anywhere"

If you can copy-paste the system prompt into Claude.ai's custom instructions and have it work perfectly - you've succeeded.
