"""
Hybrid NL Query Engine - Routes queries to REQL, CADSL, or RAG.

This module implements a smart routing engine that:
1. Uses LLM to classify the NL query type
2. Routes to the appropriate execution path:
   - REQL: Simple structural queries
   - CADSL: Complex queries with graph algorithms, joins, visualizations
   - RAG: Semantic/similarity-based queries

The query-generating LLM has access to tools for fetching grammars and examples.
"""

import re
import json
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..logging_config import nlq_debug_logger as debug_log


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


def _load_classification_prompt() -> str:
    """Load the classification prompt."""
    return _load_resource("HYBRID_CLASSIFICATION.prompt")


# Load classification prompt at module import
CLASSIFICATION_SYSTEM_PROMPT = _load_classification_prompt()


# ============================================================
# QUERY GENERATION TOOLS
# ============================================================

# Tool definitions for the query-generating LLM
QUERY_TOOLS = [
    {
        "name": "get_reql_grammar",
        "description": "Get the complete REQL (RETE Query Language) formal grammar in Lark format. Call this when you need to generate a REQL query and want to ensure correct syntax.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_cadsl_grammar",
        "description": "Get the complete CADSL (Code Analysis DSL) formal grammar in Lark format. Call this when you need to generate a CADSL query with pipelines, graph operations, or diagrams.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_examples",
        "description": "List available CADSL example files organized by category. Use this to find relevant examples before generating a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by category: 'smells', 'diagrams', 'rag', 'testing', 'inspection', 'refactoring', 'patterns', 'exceptions', 'dependencies', 'inheritance'. Leave empty for all."
                }
            },
            "required": []
        }
    },
    {
        "name": "get_example",
        "description": "Get the content of a specific CADSL example file. Use this to see how similar queries are structured.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The example name (e.g., 'god_class', 'call_graph', 'duplicate_code')"
                }
            },
            "required": ["name"]
        }
    }
]


def handle_get_reql_grammar() -> str:
    """Return the REQL grammar."""
    grammar = _load_resource("REQL_GRAMMAR.lark")
    return f"""# REQL Grammar (Lark format)

{grammar}

## Key Points:
- Use `type` predicate for entity types: `?x type oo:Class`
- Use `oo:` prefix ONLY for types (oo:Class, oo:Method, oo:Function)
- Predicates have NO prefix: `name`, `inFile`, `definedIn`, `calls`, `inheritsFrom`
- FILTER requires parentheses: `FILTER(?count > 5)`
- Patterns separated by dots: `?x type oo:Class . ?x name ?n`
"""


def handle_get_cadsl_grammar() -> str:
    """Return the CADSL grammar."""
    grammar = _load_resource("CADSL_GRAMMAR.lark")
    return f"""# CADSL Grammar (Lark format)

{grammar}

## Key Points:
- Tool types: `query`, `detector`, `diagram`
- Sources: `reql {{ ... }}`, `rag {{ search, query: "..." }}`
- Pipeline steps: `| filter {{ }}`, `| select {{ }}`, `| map {{ }}`, `| emit {{ }}`
- Graph ops: `| graph_cycles {{ }}`, `| graph_traverse {{ }}`, `| render_mermaid {{ }}`
- REQL inside uses same syntax as standalone REQL (see get_reql_grammar)
"""


def handle_list_examples(category: Optional[str] = None) -> str:
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

    result += "\nUse get_example(name) to view a specific example."
    return result


def handle_get_example(name: str) -> str:
    """Get content of a specific CADSL example."""
    # Search in all subdirectories
    for subdir in _CADSL_TOOLS_DIR.iterdir():
        if subdir.is_dir():
            cadsl_file = subdir / f"{name}.cadsl"
            if cadsl_file.exists():
                with open(cadsl_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                return f"# Example: {name}.cadsl (from {subdir.name})\n\n{content}"

    return f"# Example '{name}' not found. Use list_examples() to see available examples."


def handle_tool_call(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Handle a tool call and return the result."""
    if tool_name == "get_reql_grammar":
        return handle_get_reql_grammar()
    elif tool_name == "get_cadsl_grammar":
        return handle_get_cadsl_grammar()
    elif tool_name == "list_examples":
        return handle_list_examples(tool_input.get("category"))
    elif tool_name == "get_example":
        return handle_get_example(tool_input.get("name", ""))
    else:
        return f"Unknown tool: {tool_name}"


# ============================================================
# QUERY TYPE CLASSIFICATION
# ============================================================

class QueryType(Enum):
    """Types of queries the hybrid engine can handle."""
    REQL = "reql"           # Simple structural queries
    CADSL = "cadsl"         # Complex pipelines, graph algorithms
    RAG = "rag"             # Semantic/similarity search


@dataclass
class QueryClassification:
    """Result of classifying a natural language query."""
    query_type: QueryType
    confidence: float
    reasoning: str
    suggested_cadsl_tool: Optional[str] = None


async def classify_query_with_llm(question: str, ctx) -> QueryClassification:
    """
    Use LLM to classify a natural language query.

    Args:
        question: The natural language question
        ctx: MCP context for LLM sampling

    Returns:
        QueryClassification with type and reasoning
    """
    try:
        prompt = f"Classify this code analysis question:\n\n{question}"

        response = await ctx.sample(prompt, system_prompt=CLASSIFICATION_SYSTEM_PROMPT)
        response_text = response.text if hasattr(response, 'text') else str(response)

        debug_log.debug(f"CLASSIFICATION RESPONSE: {response_text}")

        # Parse JSON response
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(response_text)

        query_type = QueryType(result.get("type", "reql"))

        return QueryClassification(
            query_type=query_type,
            confidence=float(result.get("confidence", 0.8)),
            reasoning=result.get("reasoning", "LLM classification"),
            suggested_cadsl_tool=result.get("suggested_tool")
        )

    except Exception as e:
        debug_log.debug(f"LLM classification failed: {e}, falling back to REQL")
        return QueryClassification(
            query_type=QueryType.REQL,
            confidence=0.5,
            reasoning=f"Fallback to REQL (classification error: {e})"
        )


# ============================================================
# TOOL-AUGMENTED QUERY GENERATION
# ============================================================

REQL_GENERATION_PROMPT = """You are a REQL query generator. Generate valid REQL queries for code analysis.

You have tools available to help you:
- get_reql_grammar: Get the formal REQL grammar
- list_examples: See available query examples
- get_example: View a specific example

CRITICAL SYNTAX RULES:
1. Type patterns MUST use `type` predicate: `?x type oo:Class` NOT `?x oo:Class`
2. Use `oo:` prefix ONLY for types after `type`: oo:Class, oo:Method, oo:Function, oo:Module
3. Predicates have NO prefix: `name`, `inFile`, `definedIn`, `calls`, `inheritsFrom`, `atLine`
4. FILTER needs parentheses: `FILTER(?count > 5)`
5. Separate patterns with dots: `?x type oo:Class . ?x name ?n`

COMMON MISTAKE - NEVER do this:
  WRONG: `?x oo:Class .`           <- missing `type` predicate!
  RIGHT: `?x type oo:Class .`      <- always include `type`

When ready, return ONLY the REQL query (no explanation).
"""

CADSL_GENERATION_PROMPT = """You are a CADSL query generator. Generate valid CADSL pipelines for complex code analysis.

You have tools available to help you:
- get_cadsl_grammar: Get the formal CADSL grammar
- get_reql_grammar: Get the REQL grammar (for embedded reql blocks)
- list_examples: See available CADSL tool examples by category
- get_example: View a specific example to understand patterns

CRITICAL RULES:
1. CADSL uses `query`, `detector`, or `diagram` as tool types
2. Inside reql {} blocks, use `type` predicate: `?x type {Class}` or `?x type oo:Class`
3. In CADSL, use curly braces for cross-language types: `{Class}`, `{Method}`, `{Module}`
4. Predicates have NO prefix: `name`, `inFile`, `definedIn`, `calls`, `imports`
5. Pipeline steps use `|` operator: `| filter { }`, `| emit { }`

COMMON MISTAKE - NEVER do this in REQL blocks:
  WRONG: `?m1 oo:Module .`           <- missing `type` predicate!
  RIGHT: `?m1 type {Module} .`       <- always include `type`

RECOMMENDED: Call get_example() to see the EXACT syntax used in working examples.

When ready, return ONLY the CADSL query (no explanation).
"""


async def generate_query_with_tools(
    question: str,
    query_type: QueryType,
    ctx,
    max_iterations: int = 5
) -> str:
    """
    Generate a query using tool-augmented LLM.

    The LLM can call tools to fetch grammars and examples before generating.

    Args:
        question: Natural language question
        query_type: REQL or CADSL
        ctx: MCP context for sampling
        max_iterations: Maximum tool-use iterations

    Returns:
        Generated query string
    """
    system_prompt = REQL_GENERATION_PROMPT if query_type == QueryType.REQL else CADSL_GENERATION_PROMPT

    messages = [
        {"role": "user", "content": f"Generate a query for: {question}"}
    ]

    for iteration in range(max_iterations):
        debug_log.debug(f"Query generation iteration {iteration + 1}")

        # Call LLM with tools
        response = await ctx.sample(
            messages[-1]["content"] if iteration == 0 else None,
            system_prompt=system_prompt,
            tools=QUERY_TOOLS,
            messages=messages if iteration > 0 else None
        )

        response_text = response.text if hasattr(response, 'text') else str(response)
        debug_log.debug(f"LLM response: {response_text[:500]}...")

        # Check if response contains tool calls
        tool_calls = getattr(response, 'tool_calls', None) or []

        # Also check for tool_use in content blocks (Claude format)
        if hasattr(response, 'content'):
            for block in response.content:
                if hasattr(block, 'type') and block.type == 'tool_use':
                    tool_calls.append({
                        'name': block.name,
                        'input': block.input,
                        'id': getattr(block, 'id', f'tool_{iteration}')
                    })

        if not tool_calls:
            # No tool calls - LLM returned the final query
            return extract_query_from_response(response_text, query_type)

        # Handle tool calls
        for tool_call in tool_calls:
            tool_name = tool_call.get('name') or getattr(tool_call, 'name', '')
            tool_input = tool_call.get('input') or getattr(tool_call, 'input', {})
            tool_id = tool_call.get('id') or getattr(tool_call, 'id', f'tool_{iteration}')

            debug_log.debug(f"Tool call: {tool_name}({tool_input})")

            # Execute tool
            tool_result = handle_tool_call(tool_name, tool_input)

            # Add to conversation
            messages.append({
                "role": "assistant",
                "content": response_text,
                "tool_calls": [{"id": tool_id, "name": tool_name, "input": tool_input}]
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": tool_result
            })

    # Max iterations reached
    debug_log.warning("Max iterations reached in query generation")
    return extract_query_from_response(response_text, query_type)


def extract_query_from_response(response_text: str, query_type: QueryType) -> str:
    """Extract query from LLM response."""
    lang = "cadsl" if query_type == QueryType.CADSL else "reql|sparql|sql"

    # Try to find query in code blocks
    code_block_match = re.search(
        rf'```(?:{lang})?\s*\n?(.*?)\n?```',
        response_text,
        re.DOTALL | re.IGNORECASE
    )
    if code_block_match:
        query = code_block_match.group(1).strip()
    else:
        # Assume entire response is the query
        query = response_text.strip()

    # Remove any markdown artifacts
    query = re.sub(r'^```\w*\s*', '', query)
    query = re.sub(r'\s*```$', '', query)

    return query


# ============================================================
# LEGACY HELPERS (kept for compatibility)
# ============================================================

def extract_cadsl_from_response(response_text: str) -> str:
    """Extract CADSL query from LLM response."""
    return extract_query_from_response(response_text, QueryType.CADSL)


def build_cadsl_prompt(
    question: str,
    schema_info: str,
    attempt: int = 1,
    generated_query: Optional[str] = None,
    last_error: Optional[str] = None
) -> str:
    """Build the prompt for CADSL generation (legacy)."""
    if attempt == 1:
        return f"{schema_info}\nQuestion: {question}\n\nGenerate a CADSL query:"
    else:
        return f"""Question: {question}

Previous CADSL query attempt:
```cadsl
{generated_query}
```

Error received:
{last_error}

Please fix the CADSL query to correct the error. Return ONLY the corrected query:"""


# ============================================================
# RAG QUERY BUILDER
# ============================================================

def build_rag_query_params(question: str) -> Dict[str, Any]:
    """Extract RAG query parameters from natural language question."""
    params = {
        "top_k": 20,
        "search_scope": "code",
        "include_content": False,
    }

    question_lower = question.lower()
    entity_types = []

    if "class" in question_lower and "method" not in question_lower:
        entity_types.append("class")
    if "method" in question_lower or "function" in question_lower:
        entity_types.extend(["method", "function"])
    if "document" in question_lower or "docs" in question_lower:
        params["search_scope"] = "docs"
        entity_types.append("document")

    if entity_types:
        params["entity_types"] = entity_types

    query = question
    for word in ["find", "search", "look for", "show", "get", "list"]:
        query = re.sub(rf'\b{word}\b', '', query, flags=re.IGNORECASE)
    query = query.strip()

    params["query"] = query if query else question

    return params


# ============================================================
# HYBRID QUERY EXECUTION
# ============================================================

@dataclass
class HybridQueryResult:
    """Result of executing a hybrid query."""
    success: bool
    results: List[Dict[str, Any]]
    count: int
    query_type: QueryType
    generated_query: Optional[str] = None
    rag_params: Optional[Dict[str, Any]] = None
    classification: Optional[QueryClassification] = None
    execution_time_ms: float = 0
    error: Optional[str] = None
    tools_used: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "results": self.results,
            "count": self.count,
            "query_type": self.query_type.value,
            "generated_query": self.generated_query,
            "rag_params": self.rag_params,
            "classification": {
                "type": self.classification.query_type.value,
                "confidence": self.classification.confidence,
                "reasoning": self.classification.reasoning,
            } if self.classification else None,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "tools_used": self.tools_used,
        }
