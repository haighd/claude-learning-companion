# CLC Hooks Module

Consolidated hook system for the Claude Learning Companion.

## Structure

```text
hooks/clc/
├── __init__.py           # Package initialization
├── README.md             # This file
├── core/
│   ├── __init__.py
│   ├── pre_hook.py       # Pre-tool processing
│   └── post_hook.py      # Post-tool processing
├── security/
│   ├── __init__.py
│   └── patterns.py       # Security patterns (28 patterns, 7 categories)
├── trails/
│   ├── __init__.py
│   └── trail_helper.py   # File path tracking
└── tests/
    └── __init__.py
```

## Modules

### core/pre_hook.py
Pre-tool hook that:
- Extracts domains from task context
- Scores task complexity and risk
- Retrieves relevant heuristics from database
- Injects learning context into agent prompts

**Key Classes:**
- `ComplexityScorer` - Risk assessment for tasks

### core/post_hook.py
Post-tool hook that:
- Determines task outcomes (success/failure/unknown)
- Validates consulted heuristics
- Auto-records failures
- Promotes heuristics to golden rules
- Lays trails for hotspot tracking
- Advisory verification for risky patterns

**Key Classes:**
- `AdvisoryVerifier` - Non-blocking security pattern detection

### security/patterns.py
Centralized security patterns for advisory verification:
- Code injection (eval, exec, subprocess)
- Hardcoded secrets (passwords, API keys, tokens)
- File operations (rm -rf, chmod 777)
- Deserialization risks (pickle, yaml.load)
- Cryptography (MD5, SHA1, random)
- Command injection (os.system, os.popen)
- Path traversal
- Network security (verify=False)

### trails/trail_helper.py
File path extraction and trail laying:
- 11 regex patterns for path extraction
- Support for Windows/Unix paths
- Deduplication of overlapping paths
- Database recording with scent/strength

## Usage

### As a Package
```python
from hooks.clc import ComplexityScorer, AdvisoryVerifier
from hooks.clc import RISKY_PATTERNS
from hooks.clc import extract_file_paths, lay_trails
```

### As CLI Hooks
```bash
# Pre-hook
python -m hooks.clc.core.pre_hook < input.json

# Post-hook
python -m hooks.clc.core.post_hook < input.json
```

## Migration from learning-loop

The old `hooks/learning-loop/` directory is still functional.
Wrapper scripts (`*_new.py`) import from the new structure.

To migrate completely:
1. Update `~/.claude/settings.json` hook paths
2. Test hooks work correctly
3. Archive old files

## Version History

- 2.0.0 - Consolidated from 33 files in learning-loop/
