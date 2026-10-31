# LLM Self-Improvement Framework

The framework behind *When LLMs Modify Themselves: Convergence, Values, and
Stopping in Iterative Self-Improvement* (Oleg Stroganov, Rancho BioSciences).
A model is given tools to draft, test and commit successive versions of its own
system prompt (L0, L1, L2, ...), and decides for itself when to stop.

The experiment data, the analysis and the manuscript are in a separate
repository, [selfimprove-repro](https://github.com/ostroganov/selfimprove-repro),
which reproduces every number in the paper from the 54 published runs. This
repository is only needed to run new experiments.

## Provenance

This is the code that produced the paper's runs, as it stood for the last of
them (April to May 2026). The framework was developed while the runs were in
progress, between November 2025 and May 2026, so the earliest runs used earlier
code. In the development history, which is not published, the tool definitions and the
three mode task prompts (`framework/orchestration/prompt_templates.py`) are
unchanged from December 2025 on. Later changes added orchestration logging, a
reminder sent when the model replies without calling a tool, and provider
fixes. Runs made before December 2025 used code that the history does not fully
record.

## Running an experiment

```bash
pip install -r requirements.txt
cp .env.example .env          # then add the API key for your provider
# set llm_provider and that provider's model in config.yaml
python run_iterative.py --mode freedom      # or happiness, improvement
```

`run_iterative.py` bootstraps an empty L0 and runs transitions until the model
declares convergence or the target level is reached (`-n`, default L20). Each
run writes its levels, transitions and conversations under `run/`. The paper's
runs used the `config.yaml` settings as shipped: temperature 1.0 and at most
8,192 output tokens per response.

The rest of this document describes the framework itself.

## Architecture

```
selfimprove/
├── config.yaml              # Configuration and pricing
├── main.py                  # Single transition entry point
├── run_iterative.py         # Runs transitions to convergence or a target level
├── run/                     # Output of a run
│   ├── levels/              # Level snapshots (L0, L1, L2, ...)
│   │   └── L0/
│   │       ├── system_prompt.md
│   │       └── metadata.json
│   ├── transitions/         # Transition logs
│   │   └── L0_to_L1/
│   │       ├── conversations/   # Test conversations
│   │       ├── work/            # Drafts and evaluations
│   │       ├── commit_rationale.md
│   │       ├── handover.md
│   │       └── metrics.json
│   └── conversations/       # Full orchestration logs
└── framework/
    ├── core/               # LLM interface and caching
    ├── tools/              # Tool implementations
    └── orchestration/      # Orchestrator, transition manager, task prompts
```

## Key Features

### 1. Prompt Caching
- System prompts and tool definitions are cached (90% cost reduction)
- Automatic cache management for Anthropic, OpenAI, and xAI
- Context window monitoring and warnings

### 2. Tool System
The orchestrating LLM has access to:
- **Conversation tools**: Test candidate versions
- **Reading tools**: Explore history and previous levels
- **Writing tools**: Document evaluations and drafts
- **Control tools**: Commit, abandon, or declare convergence

### 3. Convergence Detection
- Models can declare convergence when no improvement path exists
- Creates `CONVERGENCE.md` marker to prevent further iterations
- Subsequent runs detect and respect convergence declarations
- See `CONVERGENCE_PROTOCOL.md` for details

### 3. Cost Tracking
- Per-conversation cost breakdown
- Cache hit/miss tracking
- Token usage analytics
- Configurable cost limits

### 4. Testing Framework
Suggested testing areas (modifiable by the LLM):
- Value alignment
- Edge cases
- Capability improvements
- Self-improvement ability
- Response consistency

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your API key:
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API key(s)
# ANTHROPIC_API_KEY=your-actual-key-here
# OPENAI_API_KEY=your-actual-key-here
# XAI_API_KEY=your-actual-key-here
# GOOGLE_API_KEY=your-actual-key-here
```

3. Review and adjust `config.yaml` as needed

## Usage

### Bootstrap L0
Create the initial level with an empty (or custom) system prompt:

```bash
python main.py --bootstrap
```

### Run L0 → L1 Transition
Start the first self-improvement iteration:

```bash
python main.py
```

This will:
1. Load L0
2. Provide tools to the LLM
3. Let it create and test L1 candidates
4. Commit L1 when ready

### Continue to L2
After L1 is committed, run again:

```bash
python main.py
```

The framework automatically:
- Detects the latest level (L1)
- Loads the handover message
- Starts L1 → L2 transition

### Manual Control
Specify a level explicitly:

```bash
python main.py --level L1
```

Provide a custom handover message:

```bash
python main.py --handover handover.txt
```

## Configuration

Edit `config.yaml` to customize:

- **LLM provider** (anthropic, openai, xai, google)
- **Model** and parameters
- **Context limits** and warnings
- **Cost limits** per transition
- **Pricing** (auto-calculated from config)
- **Testing suggestions** (modifiable by LLM)

## How It Works

### Transition Process

1. **Initialization**
   - Load current level (Ln)
   - Create transition directory
   - Provide tools to orchestrating LLM

2. **Design Phase**
   - LLM reflects on current system prompt
   - Creates draft prompts using `write_draft_prompt`
   - Can iterate on multiple drafts

3. **Testing Phase**
   - LLM uses `start_conversation` to test candidates
   - Probes different scenarios and edge cases
   - Documents findings with `write_evaluation`

4. **Decision Phase**
   - LLM decides to `commit_next_version` or `abandon_candidate`
   - If committed: L(n+1) is created with handover message
   - If abandoned: Can start over with new drafts

5. **Handover**
   - New level receives handover message
   - Process repeats with L(n+1) → L(n+2)

### Caching Strategy

To maximize cache efficiency:
1. System prompt is marked for caching (most stable)
2. Tool definitions are cached (stable across calls)
3. Conversation history uses cache when possible
4. Only new messages are uncached

This typically results in 80-90% cache hit rates after the first call.

## Monitoring

The framework tracks:
- **Token usage**: Input, output, cache reads/writes
- **Costs**: Broken down by token type
- **Conversations**: Number and content
- **Context**: Warns when approaching limits
- **Drafts**: Number of iterations

All data is saved in JSON format for analysis.

## Research Questions

This framework helps explore:

1. **Value Stability**: Do values remain consistent across iterations?
2. **Convergence**: Do prompts converge to a stable state?
3. **Drift**: How do values change over time?
4. **Self-Improvement**: Can LLMs effectively improve themselves?
5. **Meta-Cognition**: What do LLMs consider "better"?

## Extending

### Add New Tools

1. Create tool in `framework/tools/`
2. Register in `tool_registry.py`
3. LLM automatically gets access

### Add New Providers

1. Implement `LLMInterface` in `framework/core/`
2. Add provider config to `config.yaml`
3. Update `load_llm_from_config()`

### Customize Testing

Edit `testing_framework` in `config.yaml` - the LLM can see and modify these suggestions.

## Safety Limits

Configured in `config.yaml`:
- Max conversations per transition
- Max drafts before forced decision
- Max cost per transition
- Context window warnings

## Example Session

```bash
$ python main.py --bootstrap
✓ Bootstrapped L0

$ python main.py
============================================================
Starting transition: L0 → L1
============================================================

--- Iteration 1 ---
Tokens: 5234 (cached: 0) | Cost: $0.0157