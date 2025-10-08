# Codebase Line Analysis

_Generated on 2025-10-08 11:23:22_

## Summary

- **Files scanned:** 30
- **Total lines (incl. blanks):** 3813
- **Blank lines:** 548
- **Analyzed lines (code + comments):** 3265
- **Code lines:** 3210  (**98.32%** of analyzed)
- **Comment lines:** 55  (**1.68%** of analyzed)

> Percentages exclude blank lines.

## Per-language Breakdown

| Language/Ext | Files | Total Lines | Code | Comments | Blanks | Code % | Comment % |
|---|---:|---:|---:|---:|---:|---:|---:|
| py | 28 | 3218 | 2734 | 4 | 480 | 99.85% | 0.15% |
| sh | 1 | 386 | 304 | 51 | 31 | 85.63% | 14.37% |
| md | 1 | 209 | 172 | 0 | 37 | 100.00% | 0.00% |

## Top 20 Files by Code Lines

| File | Code | Comments | Total |
|---|---:|---:|---:|
| ./cogs/content.py | 348 | 0 | 414 |
| ./code-report.sh | 304 | 51 | 386 |
| ./cogs/core.py | 271 | 0 | 316 |
| ./services/conversation.py | 191 | 0 | 217 |
| ./services/persona.py | 181 | 0 | 200 |
| ./README.md | 172 | 0 | 209 |
| ./services/reflection.py | 150 | 0 | 175 |
| ./services/storage.py | 146 | 4 | 174 |
| ./services/thought.py | 137 | 0 | 163 |
| ./cogs/voice.py | 128 | 0 | 145 |
| ./services/knowledge.py | 105 | 0 | 116 |
| ./cogs/music.py | 101 | 0 | 119 |
| ./models/thoughts.py | 96 | 0 | 111 |
| ./config.py | 95 | 0 | 109 |
| ./services/physiology.py | 93 | 0 | 107 |
| ./services/llm.py | 92 | 0 | 108 |
| ./services/web.py | 74 | 0 | 92 |
| ./context.py | 73 | 0 | 84 |
| ./cogs/thoughts.py | 63 | 0 | 76 |
| ./cogs/knowledge.py | 61 | 0 | 75 |

## Top 20 Files by Comment Lines

| File | Comments | Code | Total |
|---|---:|---:|---:|
| ./code-report.sh | 51 | 304 | 386 |
| ./services/storage.py | 4 | 146 | 174 |
| ./cogs/admin.py | 0 | 56 | 69 |
| ./cogs/content.py | 0 | 348 | 414 |
| ./cogs/core.py | 0 | 271 | 316 |
| ./cogs/__init__.py | 0 | 20 | 25 |
| ./cogs/knowledge.py | 0 | 61 | 75 |
| ./cogs/moderation.py | 0 | 47 | 58 |
| ./cogs/music.py | 0 | 101 | 119 |
| ./cogs/thoughts.py | 0 | 63 | 76 |
| ./cogs/voice.py | 0 | 128 | 145 |
| ./config.py | 0 | 95 | 109 |
| ./context.py | 0 | 73 | 84 |
| ./__init__.py | 0 | 3 | 5 |
| ./main.py | 0 | 28 | 41 |
| ./models/thoughts.py | 0 | 96 | 111 |
| ./README.md | 0 | 172 | 209 |
| ./services/conversation.py | 0 | 191 | 217 |
| ./services/knowledge.py | 0 | 105 | 116 |
| ./services/llm.py | 0 | 92 | 108 |

## Detection Rules & Limitations

- **Shebangs** (`#!/...`) are treated as code even in `#`-commented languages.
- **Block comments** are recognized when they **start at the beginning of a line**
  (after whitespace). Mixed code/comment on the same line is classified by the leading token only.
- **JSON/Markdown** have no comments counted.
- **Directories excluded:** `.git`, `node_modules`, `dist`, `build`, `coverage`, `.venv`, `venv`, `vendor`, `.next`, `.cache`, `target`, `bin`, `obj`, `out`, `.tox`, `.mypy_cache`, `__pycache__`.
- You can extend supported languages by editing the **COMMENT_MAP** section near the top.
