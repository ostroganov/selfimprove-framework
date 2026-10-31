"""Google Gemini provider implementation."""

from typing import List, Dict, Any, Optional, Tuple
import json

from .llm_interface import LLMInterface
from .message_types import TokenUsage


class GoogleProvider(LLMInterface):
    """Google Gemini provider."""

    def __init__(self, config):
        super().__init__(config)

        # Import google-genai here to make it optional
        try:
            from google import genai
            self.genai = genai
            self.client = genai.Client(api_key=config.api_key)
        except ImportError:
            raise ImportError(
                "google-genai package not installed. Install with: pip install google-genai"
            )

    def generate(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        use_cache: bool = True,
        user_id: Optional[str] = None,
    ) -> Tuple[str, List[Dict[str, Any]], TokenUsage]:
        """
        Generate a response using Google Gemini.

        Note: Google Gemini does not have explicit prompt caching like Anthropic,
        but the API may cache internally.

        Args:
            user_id: Unused (Google doesn't support user tracking parameter)
        """
        # Convert messages to Google format using proper types
        google_messages = []

        for msg in messages:
            role = msg["role"]
            content = msg.get("content")

            # Map assistant -> model for Google
            if role == "assistant":
                role = "model"
            # Skip system messages (handled separately)
            elif role == "system":
                continue
            # Handle tool messages - Google expects them as user messages with parts
            elif role == "tool":
                # Convert tool results to user message with function response
                tool_call_id = msg.get("tool_call_id", "")
                response_data = json.loads(content) if isinstance(content, str) else content

                part = self.genai.types.Part(
                    function_response=self.genai.types.FunctionResponse(
                        name=tool_call_id,
                        response=response_data
                    )
                )
                google_messages.append(
                    self.genai.types.Content(role="user", parts=[part])
                )
                continue

            # Handle regular messages
            parts = []
            if isinstance(content, str):
                parts.append(self.genai.types.Part.from_text(text=content))
            elif isinstance(content, list):
                # Anthropic-style content blocks
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            parts.append(self.genai.types.Part.from_text(text=block.get("text", "")))
                        elif block.get("type") == "tool_use":
                            # Tool use in messages - convert to function call
                            # Check if we have preserved Google-specific data
                            if "_google_function_call" in block:
                                fc_data = block["_google_function_call"]
                            else:
                                # Fallback: create function call with bypass signature for Gemini 3+
                                fc_data = {
                                    "name": block.get("name"),
                                    "args": block.get("input", {}),
                                    "thought_signature": "context_engineering_is_the_way_to_go"
                                }

                            # Create FunctionCall without thought_signature
                            fc = self.genai.types.FunctionCall(
                                name=fc_data["name"],
                                args=fc_data.get("args", {})
                            )

                            # Create Part with function_call and thought_signature
                            part_kwargs = {"function_call": fc}
                            if fc_data.get("thought_signature"):
                                part_kwargs["thought_signature"] = fc_data["thought_signature"]

                            parts.append(self.genai.types.Part(**part_kwargs))
                        elif block.get("type") == "tool_result":
                            # Tool result - convert to function response
                            response_data = json.loads(block.get("content", "{}"))
                            parts.append(
                                self.genai.types.Part(
                                    function_response=self.genai.types.FunctionResponse(
                                        name=block.get("tool_use_id", ""),
                                        response=response_data
                                    )
                                )
                            )
            elif content is None:
                # Handle None content (e.g., messages with only tool_calls)
                if "tool_calls" in msg:
                    # OpenAI-style tool calls
                    for tc in msg["tool_calls"]:
                        # Check if we have preserved Google-specific data
                        if "_google_function_call" in tc:
                            fc_data = tc["_google_function_call"]
                        else:
                            func = tc.get("function", {})
                            # Add bypass signature for Gemini 3+ compatibility
                            fc_data = {
                                "name": func.get("name"),
                                "args": json.loads(func.get("arguments", "{}")),
                                "thought_signature": "context_engineering_is_the_way_to_go"
                            }

                        # Create FunctionCall without thought_signature
                        fc = self.genai.types.FunctionCall(
                            name=fc_data["name"],
                            args=fc_data.get("args", {})
                        )

                        # Create Part with function_call and thought_signature
                        part_kwargs = {"function_call": fc}
                        if fc_data.get("thought_signature"):
                            part_kwargs["thought_signature"] = fc_data["thought_signature"]

                        parts.append(self.genai.types.Part(**part_kwargs))

            if parts:
                google_messages.append(
                    self.genai.types.Content(role=role, parts=parts)
                )

        # Prepare API call parameters
        config_params = {
            "temperature": self.config.temperature,
        }

        # Add system instruction if provided
        if system_prompt:
            config_params["system_instruction"] = system_prompt

        # Convert tools to Google's function declarations format using proper types
        google_tools = None
        if tools:
            function_declarations = []
            for tool in tools:
                function_declarations.append(
                    self.genai.types.FunctionDeclaration(
                        name=tool["name"],
                        description=tool["description"],
                        parameters=tool["input_schema"]
                    )
                )
            google_tools = [self.genai.types.Tool(function_declarations=function_declarations)]

        # Make API call
        try:
            # Add tools to config if provided
            if google_tools:
                config_params["tools"] = google_tools

            # Build config
            config_obj = self.genai.types.GenerateContentConfig(**config_params)

            # Call generate_content
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=google_messages,
                config=config_obj
            )

            # Extract response text and tool calls
            response_text = ""
            tool_calls = []

            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content:
                    for part in candidate.content.parts:
                        # Extract text
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text

                        # Extract function calls
                        if hasattr(part, 'function_call') and part.function_call:
                            fc = part.function_call
                            # Preserve thought_signature if present (required for Gemini 3+)
                            thought_sig = getattr(part, 'thought_signature', None)

                            google_fc_data = {
                                "name": fc.name,
                                "args": dict(fc.args) if fc.args else {}
                            }
                            # Add thought_signature if present
                            if thought_sig:
                                google_fc_data["thought_signature"] = thought_sig

                            tool_calls.append({
                                "id": fc.name,  # Google doesn't have separate IDs
                                "name": fc.name,
                                "input": dict(fc.args) if fc.args else {},
                                # Store for message reconstruction
                                "_google_function_call": google_fc_data
                            })

            # Extract token usage
            token_usage = TokenUsage(
                input_tokens=0,
                output_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0,
            )

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                token_usage = TokenUsage(
                    input_tokens=getattr(usage, 'prompt_token_count', 0) or 0,
                    output_tokens=getattr(usage, 'candidates_token_count', 0) or 0,
                    cache_creation_tokens=0,  # Google doesn't expose cache details
                    cache_read_tokens=getattr(usage, 'cached_content_token_count', 0) or 0,
                )

            return response_text, tool_calls, token_usage

        except Exception as e:
            raise RuntimeError(f"Google API error: {str(e)}")

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Note: Google Gemini API supports token counting, but for simplicity
        we use a rough estimate similar to Anthropic's approach.
        """
        if text is None:
            return 0

        # Rough estimate: 4 characters per token
        # This is conservative and tends to overestimate
        return len(text) // 4 + 1 if text else 0
