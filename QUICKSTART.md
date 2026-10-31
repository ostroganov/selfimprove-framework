# Quick Start Guide

## Setup (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Key
Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` and add your API key:
```
ANTHROPIC_API_KEY=your-actual-api-key-here
```

### 3. Verify Setup
```bash
python test_setup.py
```

All tests should pass. If not, fix any reported issues.

## Running Your First Experiment

### Step 1: Bootstrap L0
Create the initial level with an empty system prompt:

```bash
python main.py --bootstrap
```

This creates `levels/L0/` with an empty system prompt.

### Step 2: Run L0 → L1 Transition
Start the self-improvement process:

```bash
python main.py
```

**What happens:**
1. The orchestrating LLM (running as L0) receives tools
2. It creates draft system prompts for L1
3. It tests L1 candidates by having conversations with them
4. It evaluates the results
5. It commits L1 when satisfied

**Watch for:**
- Tool calls (start_conversation, write_draft_prompt, etc.)
- Cost tracking (cached vs uncached tokens)
- Iteration progress

The process continues until the LLM calls `commit_next_version`.

### Step 3: Inspect Results

After L1 is committed, check:

```bash
# View the committed system prompt
cat levels/L1/system_prompt.md

# View the commit rationale
cat transitions/L0_to_L1/commit_rationale.md

# View the handover message
cat transitions/L0_to_L1/handover.md

# View test conversations
ls transitions/L0_to_L1/conversations/

# View metrics
cat transitions/L0_to_L1/metrics.json
```

### Step 4: Continue to L2
Simply run again:

```bash
python main.py
```

The framework automatically:
- Detects L1 as the latest level
- Loads the handover message from L0
- Starts L1 → L2 transition

## Understanding the Output

### During Execution
```
--- Iteration 1 ---
Tokens: 5234 (cached: 4012) | Cost: $0.0157