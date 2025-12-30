# Default Instance Sync Refactoring Design

## Current Problems

1. **Full MD5 computation on every sync**: Reads ALL file contents to compute MD5 hashes
2. **Redundant RETER query**: Calls `reter.get_all_sources()` when we already know what we loaded
3. **Duplicate tracking**: RAG has its own `.default.rag_files.json` tracking the same files
4. **Lazy gitignore loading**: GitignoreParser re-parses nested `.gitignore` files during scan

## Proposed Solution: Single Source-of-Truth JSON

### New File: `.default.sources.json`

```json
{
  "version": "2.0",
  "updated_at": "2024-01-15T10:30:00Z",
  "gitignore_patterns_hash": "abc123...",
  "files": {
    "src/foo.py": {
      "md5": "abc123def...",
      "mtime": 1705312200.0,
      "size": 1234,
      "in_reter": true,
      "in_rag": true,
      "reter_source_id": "abc123def...|src/foo.py"
    },
    "docs/readme.md": {
      "md5": "xyz789...",
      "mtime": 1705311000.0,
      "size": 5678,
      "in_reter": false,
      "in_rag": true,
      "reter_source_id": null
    }
  },
  "gitignore_files": {
    ".gitignore": "hash1...",
    "src/.gitignore": "hash2..."
  }
}
```

### Optimizations

#### 1. Use mtime-first, MD5-when-needed

```python
def _quick_file_check(self, file_path: Path, cached: dict) -> str:
    """Quick check if file changed. Returns 'unchanged', 'modified', or 'new'."""
    stat = file_path.stat()

    # If mtime unchanged and size unchanged, skip MD5
    if cached and cached["mtime"] == stat.st_mtime and cached["size"] == stat.st_size:
        return "unchanged"

    # Only compute MD5 if mtime/size changed
    md5 = self._compute_md5(file_path)
    if cached and cached["md5"] == md5:
        return "unchanged"  # Content same despite mtime change

    return "modified" if cached else "new"
```

**Benefit**: Avoids reading file contents for unchanged files (typical case).

#### 2. Pre-cache gitignore patterns

```python
def _load_all_gitignores(self) -> Tuple[List[GitignorePattern], str]:
    """Load all gitignore files once, return patterns and combined hash."""
    patterns = []
    gitignore_files = {}

    # Find all .gitignore files
    for gitignore in self._project_root.rglob(".gitignore"):
        content = gitignore.read_text()
        gitignore_files[str(gitignore.relative_to(self._project_root))] = hashlib.md5(content.encode()).hexdigest()
        patterns.extend(self._parse_gitignore(gitignore, content))

    # Combined hash for invalidation
    combined = json.dumps(gitignore_files, sort_keys=True)
    patterns_hash = hashlib.md5(combined.encode()).hexdigest()

    return patterns, patterns_hash, gitignore_files
```

**Benefit**: Single pass to load all gitignore patterns. Patterns hash used to detect when gitignores change.

#### 3. Single source of truth (no RETER query)

```python
def _sync_from_json(self, reter: ReterWrapper) -> SyncResult:
    """Sync using JSON as source of truth, not RETER query."""
    # Load our state
    state = self._load_state_json()

    # Quick scan filesystem
    current_files = self._quick_scan_filesystem()

    # Determine changes WITHOUT querying RETER
    to_add = []
    to_modify = []
    to_delete = []

    for rel_path, file_info in current_files.items():
        cached = state["files"].get(rel_path)
        if cached is None:
            to_add.append((rel_path, file_info))
        elif file_info["md5"] != cached["md5"]:
            to_modify.append((rel_path, file_info, cached))

    for rel_path, cached in state["files"].items():
        if rel_path not in current_files:
            to_delete.append((rel_path, cached))

    return SyncResult(to_add, to_modify, to_delete)
```

**Benefit**: No need to query RETER for what we already loaded. JSON is authoritative.

#### 4. Unified RETER + RAG sync

```python
def _apply_sync(self, reter, rag_manager, changes: SyncResult):
    """Apply changes to both RETER and RAG in one pass."""
    state = self._state

    # Delete phase
    for rel_path, cached in changes.to_delete:
        if cached.get("in_reter"):
            reter.forget_source(cached["reter_source_id"])
        if cached.get("in_rag") and rag_manager:
            rag_manager.remove_source(cached["reter_source_id"])
        del state["files"][rel_path]

    # Add/Modify phase
    for rel_path, file_info in changes.to_add + changes.to_modify:
        # Load into RETER
        source_id = self._load_file(reter, rel_path, file_info)

        # Update state
        state["files"][rel_path] = {
            "md5": file_info["md5"],
            "mtime": file_info["mtime"],
            "size": file_info["size"],
            "in_reter": True,
            "in_rag": False,  # Updated after RAG sync
            "reter_source_id": source_id
        }

    # RAG sync (if enabled)
    if rag_manager and rag_manager.is_enabled:
        self._sync_rag(rag_manager, state, changes)

    # Save state
    self._save_state_json(state)
```

**Benefit**: Single coordinated sync for RETER and RAG.

### Migration Path

1. On first run (no `.default.sources.json`):
   - Fall back to current `get_all_sources()` query
   - Build initial JSON state from RETER + filesystem
   - Save JSON

2. On subsequent runs:
   - Load JSON
   - Use mtime-first quick scan
   - Apply incremental changes
   - Save JSON

### File Changes Required

1. **`default_instance_manager.py`**:
   - Add `_load_state_json()`, `_save_state_json()`
   - Replace `_scan_project_files()` with `_quick_scan_filesystem()`
   - Replace `_get_existing_sources()` with JSON lookup
   - Add `_quick_file_check()` for mtime-first check

2. **`rag_index_manager.py`**:
   - Remove separate `.default.rag_files.json`
   - Use state from `DefaultInstanceManager`
   - Add `remove_source()` method for coordinated deletion

3. **`gitignore_parser.py`**:
   - Add batch loading method
   - Add patterns hash computation
   - Cache patterns for reuse

### Performance Comparison

| Operation | Current | Proposed |
|-----------|---------|----------|
| Unchanged file | Read content + MD5 | stat() only |
| Modified file | Read content + MD5 | stat() + Read + MD5 |
| New file | Read content + MD5 | stat() + Read + MD5 |
| Deleted file | Query RETER | JSON lookup |
| Gitignore check | Lazy parse each | Pre-cached patterns |

**Expected improvement**: 10-100x faster for typical "no changes" sync.
