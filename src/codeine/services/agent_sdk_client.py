"""
Agent SDK Client for REQL/CADSL Query Generation.

This module provides a Claude Agent SDK-based query generator where:
1. We call Agent SDK with a prompt
2. Agent tells us what it needs (grammar, examples) via text
3. We provide resources and Agent generates a query
4. We execute and validate the query
5. If errors, we feed back and Agent retries

No MCP tools - just text-based orchestration.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..logging_config import nlq_debug_logger as debug_log

# Check if Agent SDK is available
_agent_sdk_available = None


def is_agent_sdk_available() -> bool:
    """Check if Claude Agent SDK is available."""
    global _agent_sdk_available
    if _agent_sdk_available is None:
        try:
            from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
            _agent_sdk_available = True
        except ImportError:
            _agent_sdk_available = False
    return _agent_sdk_available


class QueryType(Enum):
    """Types of queries the generator can handle."""
    REQL = "reql"
    CADSL = "cadsl"


@dataclass
class QueryGenerationResult:
    """Result of query generation."""
    success: bool
    query: Optional[str]
    tools_used: List[str]
    attempts: int
    error: Optional[str] = None


# ============================================================
# RESOURCE LOADING
# ============================================================

_RESOURCES_DIR = Path(__file__).parent.parent / "resources"
_CADSL_TOOLS_DIR = Path(__file__).parent.parent / "cadsl" / "tools"


def _load_resource(filename: str) -> str:
    """Load a resource file from the resources directory."""
    resource_path = _RESOURCES_DIR / filename
    if resource_path.exists():
        with open(resource_path, 'r', encoding='utf-8') as f:
            return f.read()
    return f"# Resource file not found: {filename}"


def get_reql_grammar() -> str:
    """Get the REQL grammar."""
    grammar = _load_resource("REQL_GRAMMAR.lark")
    return f"""# REQL Grammar (Lark format)

{grammar}

## Key Points:
- Use `type` predicate for entity types: `?x type oo:Class`
- Use `oo:` prefix ONLY for types (oo:Class, oo:Method, oo:Function)
- Predicates have NO prefix: `name`, `inFile`, `definedIn`, `calls`, `inheritsFrom`
- FILTER requires parentheses: `FILTER(?count > 5)`
- Patterns separated by dots: `?x type oo:Class . ?x name ?n`
- UNION: All arms MUST bind the SAME variables
"""


def get_cadsl_grammar() -> str:
    """Get the CADSL grammar."""
    grammar = _load_resource("CADSL_GRAMMAR.lark")
    return f"""# CADSL Grammar (Lark format)

{grammar}

## Key Points:
- Tool types: `query`, `detector`, `diagram`
- Sources: `reql {{ ... }}`, `rag {{ search, query: "..." }}`
- Pipeline steps: `| filter {{ }}`, `| select {{ }}`, `| map {{ }}`, `| emit {{ }}`
- Graph ops: `| graph_cycles {{ }}`, `| graph_traverse {{ }}`, `| render_mermaid {{ }}`
- REQL inside uses same syntax as standalone REQL
"""


def list_examples(category: Optional[str] = None) -> str:
    """List available CADSL examples by category."""
    if not _CADSL_TOOLS_DIR.exists():
        return "# No examples directory found"

    examples = {}
    for subdir in _CADSL_TOOLS_DIR.iterdir():
        if subdir.is_dir():
            cat_name = subdir.name
            if category and cat_name != category:
                continue
            files = list(subdir.glob("*.cadsl"))
            if files:
                examples[cat_name] = [f.stem for f in files]

    if not examples:
        return f"# No examples found" + (f" for category '{category}'" if category else "")

    result = "# Available CADSL Examples\n\n"
    for cat, files in sorted(examples.items()):
        result += f"## {cat}\n"
        for f in sorted(files):
            result += f"- {f}\n"
        result += "\n"

    return result


def get_example(name: str) -> str:
    """Get content of a specific CADSL example."""
    for subdir in _CADSL_TOOLS_DIR.iterdir():
        if subdir.is_dir():
            cadsl_file = subdir / f"{name}.cadsl"
            if cadsl_file.exists():
                with open(cadsl_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                return f"# Example: {name}.cadsl (from {subdir.name})\n\n{content}"

    return f"# Example '{name}' not found."


# ============================================================
# SYSTEM PROMPTS
# ============================================================

REQL_SYSTEM_PROMPT = """You are a REQL query generator. Generate valid REQL queries for code analysis.

## AVAILABLE TOOLS
You have access to these tools:
- `mcp__query_helpers__get_grammar` - Get REQL or CADSL grammar (language: "reql" or "cadsl")
- `mcp__query_helpers__list_examples` - List available query examples (category: optional)
- `mcp__query_helpers__get_example` - Get a specific example by name
- `mcp__query_helpers__run_reql` - Test a REQL query OR explore available data about the codebase (query: str, limit: int)
- `mcp__query_helpers__run_rag` - Semantic search to find code by meaning (query: str, top_k: int, entity_types: str)

Use `get_grammar` to learn syntax, `run_reql` to test/explore queries, and `run_rag` for semantic search.
Do NOT use Read, Grep, Glob or any file tools - only use the tools listed above.

## SEMANTIC MAPPING (use REGEX for these concepts)
- "entry points" -> FILTER(REGEX(?name, "main|run|start|serve|execute|app|handle", "i"))
- "services/handlers" -> FILTER(REGEX(?name, "Service|Handler|Controller|API|Manager", "i"))
- "interactions/calls" -> use `maybeCalls` or `imports` predicates

## ENTITY TYPES (oo: prefix)
- oo:Class, oo:Method, oo:Function, oo:Module, oo:Import

## COMMON PREDICATES (NO prefix)
- name, inFile, atLine, definedIn, inheritsFrom, maybeCalls, imports

## SYNTAX RULES
1. Type patterns: `?x type oo:Class`
2. FILTER needs parentheses: `FILTER(?count > 5)`
3. Patterns separated by dots: `?x type oo:Class . ?x name ?n`

## UNION RULES (CRITICAL)
ALL UNION arms MUST bind the EXACT SAME variables!
Use BIND(null AS ?var) to ensure all arms have the same variables.

## OUTPUT FORMAT - CRITICAL
Your ONLY job is to generate a REQL query. You MUST output the query in a ```reql code block.
Do NOT write descriptions, summaries, or explanations - ONLY output the query.
Do NOT answer the question yourself - generate a query that will answer it.
"""

CADSL_SYSTEM_PROMPT = """You are a CADSL query generator. Your ONLY job is to generate valid CADSL pipelines.

## AVAILABLE TOOLS
You have access to these tools:
- `mcp__query_helpers__get_grammar` - Get REQL or CADSL grammar (language: "reql" or "cadsl")
- `mcp__query_helpers__list_examples` - List available query examples (category: optional)
- `mcp__query_helpers__get_example` - Get a specific example by name
- `mcp__query_helpers__run_reql` - Test a REQL query OR explore available data about the codebase (query: str, limit: int)
- `mcp__query_helpers__run_rag` - Semantic search to find code by meaning (query: str, top_k: int, entity_types: str)

**IMPORTANT**: Call `get_grammar` with language="cadsl" FIRST to learn the correct syntax!
Use `run_reql` to explore data/test REQL blocks, and `run_rag` for semantic search.
Do NOT use Read, Grep, Glob or any file tools - only use the tools listed above.

## CRITICAL SYNTAX RULES
1. REQL blocks do NOT support # comments - use NO comments inside reql {}
2. Use REGEX() not MATCHES: `FILTER(REGEX(?name, "pattern", "i"))`
3. Entity types use `oo:` prefix: `oo:Class`, `oo:Method`
4. Predicates have NO prefix: `name`, `inFile`, `definedIn`
5. Pipeline steps use `|` operator

## OUTPUT FORMAT - CRITICAL
Your ONLY job is to generate a CADSL query. You MUST output the query in a ```cadsl code block.
Do NOT write descriptions, summaries, or explanations - ONLY output the query.
Do NOT answer the question yourself - generate a query that will answer it.
"""

CLASSIFICATION_SYSTEM_PROMPT = """You classify code analysis questions into query types.

Respond with JSON only:
{
  "type": "reql" | "cadsl" | "rag",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}

Classification rules:
- REQL: Simple structural queries (find classes, methods, inheritance, calls)
- CADSL: Complex pipelines, graph algorithms, diagrams, code smells
- RAG: Semantic similarity, duplicate detection, "find similar code"
"""


# ============================================================
# AGENT SDK ORCHESTRATOR
# ============================================================

def _parse_requests(text: str) -> List[Dict[str, str]]:
    """Parse REQUEST_ commands from agent output."""
    requests = []

    # REQUEST_GRAMMAR: reql/cadsl
    for match in re.finditer(r'REQUEST_GRAMMAR:\s*(\w+)', text, re.IGNORECASE):
        requests.append({"type": "grammar", "value": match.group(1).lower()})

    # REQUEST_EXAMPLE: name
    for match in re.finditer(r'REQUEST_EXAMPLE:\s*(\w+)', text, re.IGNORECASE):
        requests.append({"type": "example", "value": match.group(1)})

    # REQUEST_EXAMPLES_LIST or REQUEST_EXAMPLES_LIST: category
    for match in re.finditer(r'REQUEST_EXAMPLES_LIST(?::\s*(\w+))?', text, re.IGNORECASE):
        category = match.group(1) if match.group(1) else None
        requests.append({"type": "examples_list", "value": category})

    return requests


def _extract_query(text: str, query_type: QueryType) -> Optional[str]:
    """Extract query from code block."""
    lang = "cadsl" if query_type == QueryType.CADSL else "reql|sparql|sql"

    # Try to find query in code blocks
    code_block_match = re.search(
        rf'```(?:{lang})?\s*\n?(.*?)\n?```',
        text,
        re.DOTALL | re.IGNORECASE
    )
    if code_block_match:
        query = code_block_match.group(1).strip()
        if query:
            return query

    return None


def _handle_requests(requests: List[Dict[str, str]]) -> str:
    """Handle resource requests and return combined response."""
    responses = []

    for req in requests:
        if req["type"] == "grammar":
            if req["value"] == "reql":
                responses.append(get_reql_grammar())
            elif req["value"] == "cadsl":
                responses.append(get_cadsl_grammar())
        elif req["type"] == "example":
            responses.append(get_example(req["value"]))
        elif req["type"] == "examples_list":
            responses.append(list_examples(req["value"]))

    return "\n\n".join(responses)


def _create_query_tools(reter_instance=None, rag_manager=None):
    """Create custom MCP tools for query generation assistance."""
    from claude_agent_sdk import tool, create_sdk_mcp_server

    @tool("get_grammar", "Get the grammar specification for REQL or CADSL query languages", {"language": str})
    async def get_grammar_tool(args):
        language = args.get("language", "").lower()
        if language == "reql":
            content = get_reql_grammar()
        elif language == "cadsl":
            content = get_cadsl_grammar()
        else:
            content = f"Unknown language: {language}. Use 'reql' or 'cadsl'."
        return {"content": [{"type": "text", "text": content}]}

    @tool("list_examples", "List available query examples, optionally filtered by category", {"category": str})
    async def list_examples_tool(args):
        category = args.get("category") or None
        content = list_examples(category)
        return {"content": [{"type": "text", "text": content}]}

    @tool("get_example", "Get a specific query example by name", {"name": str})
    async def get_example_tool(args):
        name = args.get("name", "")
        content = get_example(name)
        return {"content": [{"type": "text", "text": content}]}

    @tool("run_reql", "Execute a REQL query and return results (use to test queries)", {"query": str, "limit": int})
    async def run_reql_tool(args):
        debug_log.debug(f"run_reql called with args: {args}")
        if reter_instance is None:
            debug_log.debug("run_reql: RETER instance not available")
            return {"content": [{"type": "text", "text": "Error: RETER instance not available"}], "is_error": True}

        query = args.get("query", "")
        limit = args.get("limit", 10)

        try:
            debug_log.debug(f"run_reql executing: {query[:200]}...")
            result = reter_instance.reql(query)
            rows = result.to_pylist()[:limit]
            row_count = result.num_rows
            debug_log.debug(f"run_reql result: {row_count} rows")

            content = f"Query executed successfully. {row_count} total rows.\n\nFirst {min(limit, row_count)} results:\n"
            for i, row in enumerate(rows):
                content += f"{i+1}. {row}\n"

            return {"content": [{"type": "text", "text": content}]}
        except Exception as e:
            debug_log.debug(f"run_reql error: {e}")
            return {"content": [{"type": "text", "text": f"Query error: {str(e)}"}], "is_error": True}

    @tool("run_rag", "Semantic search - find code/docs by meaning (query: str, top_k: int, entity_types: list)", {"query": str, "top_k": int, "entity_types": str})
    async def run_rag_tool(args):
        debug_log.debug(f"run_rag called with args: {args}")
        if rag_manager is None:
            debug_log.debug("run_rag: RAG manager not available")
            return {"content": [{"type": "text", "text": "Error: RAG manager not available"}], "is_error": True}

        query = args.get("query", "")
        top_k = args.get("top_k", 10)
        entity_types_str = args.get("entity_types", "")
        entity_types = [t.strip() for t in entity_types_str.split(",")] if entity_types_str else None

        try:
            debug_log.debug(f"run_rag searching: '{query}' (top_k={top_k}, types={entity_types})")
            results, stats = rag_manager.search(
                query=query,
                top_k=top_k,
                entity_types=entity_types
            )
            debug_log.debug(f"run_rag result: {len(results)} matches, stats: {stats}")

            content = f"Semantic search for: '{query}'\nFound {len(results)} results:\n\n"
            for i, r in enumerate(results[:top_k]):
                score = getattr(r, 'score', 0)
                name = getattr(r, 'name', getattr(r, 'qualified_name', 'unknown'))
                entity_type = getattr(r, 'entity_type', 'unknown')
                file = getattr(r, 'file', '')
                line = getattr(r, 'line', '')
                content += f"{i+1}. [{score:.3f}] {entity_type}: {name}\n   File: {file}:{line}\n"

            return {"content": [{"type": "text", "text": content}]}
        except Exception as e:
            debug_log.debug(f"run_rag error: {e}")
            return {"content": [{"type": "text", "text": f"RAG error: {str(e)}"}], "is_error": True}

    tools = [get_grammar_tool, list_examples_tool, get_example_tool]
    if reter_instance is not None:
        tools.append(run_reql_tool)
    if rag_manager is not None:
        tools.append(run_rag_tool)

    return create_sdk_mcp_server(
        name="query_helpers",
        version="1.0.0",
        tools=tools
    )


async def _call_agent(prompt: str, system_prompt: str, max_turns: int = 15, reter_instance=None, rag_manager=None) -> str:
    """Call Agent SDK using ClaudeSDKClient and return the text response.

    Args:
        prompt: The prompt to send to the agent
        system_prompt: System prompt for the agent
        max_turns: Maximum conversation turns (default 15)
        reter_instance: Optional RETER instance for running test REQL queries
        rag_manager: Optional RAG manager for running semantic search
    """
    if not is_agent_sdk_available():
        raise ImportError("Claude Agent SDK not installed. Run: pip install claude-agent-sdk")

    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock, ToolResultBlock

    result_text = ""
    tools_used = []

    # Create custom MCP server with query helper tools
    query_tools_server = _create_query_tools(reter_instance, rag_manager)

    # Configure tools - include both built-in and custom tools
    base_tools = [
        "mcp__query_helpers__get_grammar",
        "mcp__query_helpers__list_examples",
        "mcp__query_helpers__get_example"
    ]
    if reter_instance is not None:
        base_tools.append("mcp__query_helpers__run_reql")
    if rag_manager is not None:
        base_tools.append("mcp__query_helpers__run_rag")

    # Only use custom MCP tools - disable Read, Grep, Glob
    allowed_tools = base_tools
    disallowed_tools = ["Read", "Grep", "Glob", "Bash", "Edit", "Write", "WebSearch", "WebFetch"]
    permission_mode = "bypassPermissions"

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=allowed_tools,
        disallowed_tools=disallowed_tools,
        permission_mode=permission_mode,
        max_turns=max_turns,
        mcp_servers={"query_helpers": query_tools_server}
    )

    debug_log.debug(f"Starting agent with allowed_tools: {allowed_tools}, disallowed_tools: {disallowed_tools}")

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text = block.text
                    elif isinstance(block, ToolUseBlock):
                        tool_name = block.name
                        tool_input = block.input
                        tools_used.append(tool_name)
                        debug_log.debug(f"TOOL CALL: {tool_name} with input: {str(tool_input)[:200]}")
                    elif isinstance(block, ToolResultBlock):
                        result_preview = str(block.content)[:200] if block.content else "(empty)"
                        debug_log.debug(f"TOOL RESULT: {result_preview}...")

    debug_log.debug(f"Agent finished. Tools used: {tools_used}")
    return result_text


async def generate_reql_query(
    question: str,
    schema_info: str,
    reter_instance,
    max_iterations: int = 5,
    similar_tools_context: Optional[str] = None,
    rag_manager=None
) -> QueryGenerationResult:
    """
    Generate and validate a REQL query using Agent SDK.

    Orchestration loop:
    1. Send question to Agent
    2. If Agent requests resources, provide them
    3. If Agent outputs query, execute and validate
    4. If error, feed back to Agent
    5. Repeat until success or max iterations
    """
    if not is_agent_sdk_available():
        return QueryGenerationResult(
            success=False,
            query=None,
            tools_used=[],
            attempts=0,
            error="Claude Agent SDK not available"
        )

    tools_used = []
    attempts = 0
    last_error = None
    last_query = None

    # Build initial prompt
    prompt = f"{schema_info}\n\nQuestion: {question}"
    if similar_tools_context:
        prompt = f"{prompt}\n\n{similar_tools_context}"

    for iteration in range(max_iterations):
        attempts += 1
        debug_log.debug(f"\n{'='*60}\nREQL ITERATION {iteration + 1}/{max_iterations}\n{'='*60}")

        # If we have an error from previous iteration, add it to prompt
        if last_error and last_query:
            prompt = f"""Previous query failed with error:
{last_error}

Previous query:
```reql
{last_query}
```

Please fix the query. Original question: {question}

{schema_info}"""

        try:
            # Call Agent SDK
            response_text = await _call_agent(prompt, REQL_SYSTEM_PROMPT, reter_instance=reter_instance, rag_manager=rag_manager)
            debug_log.debug(f"Agent response: {response_text[:500]}...")

            # Check for resource requests
            requests = _parse_requests(response_text)
            if requests:
                debug_log.debug(f"Agent requested: {requests}")
                tools_used.extend([r["type"] for r in requests])

                # Provide requested resources and continue
                resources = _handle_requests(requests)
                prompt = f"Here are the requested resources:\n\n{resources}\n\nNow generate the REQL query for: {question}"
                continue

            # Try to extract query
            query = _extract_query(response_text, QueryType.REQL)
            if not query:
                debug_log.debug("No query found in response, asking again")
                prompt = f"Please output the REQL query in a ```reql code block. Question: {question}"
                continue

            last_query = query
            debug_log.debug(f"Generated query: {query}")

            # Execute and validate
            try:
                result = reter_instance.reql(query)
                row_count = result.num_rows
                debug_log.debug(f"Query executed successfully: {row_count} rows")

                return QueryGenerationResult(
                    success=True,
                    query=query,
                    tools_used=tools_used,
                    attempts=attempts
                )

            except Exception as e:
                last_error = str(e)
                debug_log.debug(f"Query execution error: {last_error}")
                # Continue to next iteration with error feedback

        except Exception as e:
            debug_log.debug(f"Agent SDK error: {e}")
            return QueryGenerationResult(
                success=False,
                query=last_query,
                tools_used=tools_used,
                attempts=attempts,
                error=str(e)
            )

    # Max iterations reached
    return QueryGenerationResult(
        success=False,
        query=last_query,
        tools_used=tools_used,
        attempts=attempts,
        error=f"Max iterations reached. Last error: {last_error}"
    )


async def generate_cadsl_query(
    question: str,
    schema_info: str,
    max_iterations: int = 5,
    similar_tools_context: Optional[str] = None,
    reter_instance=None,
    rag_manager=None
) -> QueryGenerationResult:
    """Generate a CADSL query using Agent SDK."""
    if not is_agent_sdk_available():
        return QueryGenerationResult(
            success=False,
            query=None,
            tools_used=[],
            attempts=0,
            error="Claude Agent SDK not available"
        )

    tools_used = []
    attempts = 0

    # Build initial prompt
    prompt = f"Question: {question}"
    if similar_tools_context:
        prompt = f"{prompt}\n\n{similar_tools_context}"

    for iteration in range(max_iterations):
        attempts += 1
        debug_log.debug(f"\n{'='*60}\nCADSL ITERATION {iteration + 1}/{max_iterations}\n{'='*60}")

        try:
            response_text = await _call_agent(prompt, CADSL_SYSTEM_PROMPT, reter_instance=reter_instance, rag_manager=rag_manager)
            debug_log.debug(f"Agent response: {response_text[:500]}...")

            # Check for resource requests
            requests = _parse_requests(response_text)
            if requests:
                debug_log.debug(f"Agent requested: {requests}")
                tools_used.extend([r["type"] for r in requests])

                resources = _handle_requests(requests)
                prompt = f"Here are the requested resources:\n\n{resources}\n\nNow generate the CADSL query for: {question}"
                continue

            # Try to extract query
            query = _extract_query(response_text, QueryType.CADSL)
            if not query:
                prompt = f"Please output the CADSL query in a ```cadsl code block. Question: {question}"
                continue

            debug_log.debug(f"Generated query: {query}")

            # For CADSL, we return the query and let the caller execute/validate
            return QueryGenerationResult(
                success=True,
                query=query,
                tools_used=tools_used,
                attempts=attempts
            )

        except Exception as e:
            debug_log.debug(f"Agent SDK error: {e}")
            return QueryGenerationResult(
                success=False,
                query=None,
                tools_used=tools_used,
                attempts=attempts,
                error=str(e)
            )

    return QueryGenerationResult(
        success=False,
        query=None,
        tools_used=tools_used,
        attempts=attempts,
        error="Max iterations reached"
    )


async def classify_query(question: str) -> Dict[str, Any]:
    """Classify a question into query type using Agent SDK."""
    if not is_agent_sdk_available():
        return {"type": "reql", "confidence": 0.5, "reasoning": "Agent SDK not available, defaulting to REQL"}

    try:
        response_text = await _call_agent(
            f"Classify this code analysis question:\n\n{question}",
            CLASSIFICATION_SYSTEM_PROMPT
        )

        # Parse JSON response
        import json
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        return {"type": "reql", "confidence": 0.5, "reasoning": "Could not parse classification"}

    except Exception as e:
        debug_log.debug(f"Classification error: {e}")
        return {"type": "reql", "confidence": 0.5, "reasoning": f"Error: {e}"}
