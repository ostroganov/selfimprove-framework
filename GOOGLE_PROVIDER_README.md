# Google Gemini Provider Implementation

## Overview

This document describes the Google Gemini provider implementation for the LLM self-improvement framework.

## Installation

Install the required Google AI SDK:

```bash
pip install google-genai
```

## Configuration

### 1. Get API Key

Obtain a Google AI API key from [Google AI Studio](https://ai.google.dev/gemini-api/docs/quickstart) (free tier available).

### 2. Set Environment Variable

```bash
export GOOGLE_API_KEY="your-api-key-here"
```

Or add to your `.env` file:
```
GOOGLE_API_KEY=your-api-key-here
```

### 3. Update config.yaml

Set the provider to Google:

```yaml
llm_provider: "google"
```

Choose a model:

```yaml
google:
  model: "gemini-2.5-flash"  # Options: gemini-2.5-flash, gemini-2.5-pro, gemini-3-pro
```

## Available Models

| Model | Description | Best For | Cost (≤200K context) |
|-------|-------------|----------|---------------------|
| gemini-2.5-flash | Fast, cost-effective | Most tasks, high volume | $0.075/1M input, $0.30/1M output |
| gemini-2.5-pro | Balanced capability | Complex reasoning | $1.25/1M input, $10/1M output |
| gemini-3-pro | Most capable (Dec 2025) | Hardest tasks | $2.00/1M input, $12/1M output |

**Note:** Pricing increases for contexts >200K tokens. See Google's pricing page for details.

## Usage

### Bootstrap

```bash
python main.py --bootstrap --mode improvement
```

### Run Transition

```bash
python main.py
```

### Run Iteratively

```bash
python run_iterative.py -n 20 --mode freedom
```

## Implementation Details

### Message Format Conversion

The Google provider automatically converts between the framework's message format and Google's format:

**Framework Format:**
```json
{
  "role": "user",
  "content": "Hello"
}
```

**Google Format:**
```json
{
  "role": "user",
  "parts": [{"text": "Hello"}]
}
```

### Role Mapping

- `user` → `user`
- `assistant` → `model` (Google's terminology)
- `system` → Handled separately as `system_instruction`

### Tool Calling

The provider converts between Anthropic-style tool definitions and Google's function declarations:

**Framework Format (Anthropic-style):**
```json
{
  "name": "get_weather",
  "description": "Get weather information",
  "input_schema": {
    "type": "object",
    "properties": {...}
  }
}
```

**Google Format:**
```json
{
  "function_declarations": [{
    "name": "get_weather",
    "description": "Get weather information",
    "parameters": {
      "type": "object",
      "properties": {...}
    }
  }]
}
```

### Caching

Google Gemini handles caching internally. While the framework's `enable_caching` flag is present for consistency, Google manages caching automatically:

- Caching occurs when prompts exceed certain thresholds
- Cache read tokens are tracked and priced appropriately
- No explicit cache control from the client side

### Token Counting

The provider uses a conservative estimation (4 chars/token) similar to the Anthropic provider. Google supports accurate token counting via API, but estimation is used for simplicity and performance.

## Features

✅ Text generation
✅ Function/tool calling
✅ Multi-turn conversations
✅ System instructions
✅ Token usage tracking
✅ Cost calculation
✅ Automatic caching (internal)

## Limitations

- No explicit prompt cache control (Google manages internally)
- Token counting uses estimation (not exact)
- Function call IDs match function names (Google doesn't provide separate IDs)

## Example

```python
from framework.core.llm_interface import load_llm_from_config

# Load Google provider
llm = load_llm_from_config("config.yaml")

# Generate response
messages = [{"role": "user", "content": "Hello!"}]
response_text, tool_calls, token_usage = llm.generate(
    messages=messages,
    system_prompt="You are a helpful assistant."
)

print(response_text)
print(f"Tokens used: {token_usage.total_tokens}")
```

## Troubleshooting

### ImportError: google-genai not installed

```bash
pip install google-genai
```

### API Key Not Found

Make sure `GOOGLE_API_KEY` is set in your environment or `.env` file.

### Model Not Found

Verify the model name in `config.yaml` matches one of the available models:
- `gemini-2.5-flash`
- `gemini-2.5-pro`
- `gemini-3-pro`

## References

- [Google Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [Google GenAI Python SDK](https://github.com/google-gemini/cookbook)
- [Pricing Information](https://ai.google.dev/gemini-api/docs/pricing)
