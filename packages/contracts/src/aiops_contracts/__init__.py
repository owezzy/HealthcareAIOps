"""Cross-process contracts for Healthcare AIOps.

Anything that crosses a process or file boundary (scenario files, API payloads,
LLM structured output, eval datasets) is defined here, once. No I/O beyond
loading YAML, no framework imports beyond Pydantic.
"""
