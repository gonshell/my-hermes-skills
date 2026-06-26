# Agent Loop Design Review Checklist

Concrete code-level anti-patterns and fixes, derived from reviewing real agent loop implementations.

## 1. LLM Interface Layer

### ❌ Anti-pattern: Text-only LLM interface
```python
def _call_llm(self, system_prompt: str, user_prompt: str):
    """Returns (text, input_tokens, output_tokens)"""
    # Forces JSON-from-text parsing downstream
```

### ✅ Correct: Function calling + structured output
```python
class LLMClient:
    def chat(self, messages, tools=None, response_format=None) -> LLMResponse:
        # Supports function calling (tools param)
        # Supports JSON mode (response_format={"type": "json_object"})
        # Returns structured LLMResponse with tool_calls list
```

**Why**: Function calling is 10x more reliable than regex-extracting JSON from text. Every major provider supports it.

## 2. Executor: Single vs Multi Tool Call

### ❌ Anti-pattern: One action per round
```python
parsed = json.loads(response)  # fragile
round.action = parsed["action"]
result = tools.execute(parsed["action"], parsed["action_input"])
# → Reading a file costs an entire round + verification
```

### ✅ Correct: Loop until LLM stops calling tools
```python
while tool_call_count < max_tool_calls:
    response = llm.chat(messages, tools=tool_schemas)
    if not response.has_tool_calls:
        break  # LLM decided it's done
    for tc in response.tool_calls:
        result = tools.execute(tc.name, tc.arguments)
        messages.append(tool_result_message(tc.id, result))
```

## 3. Verification Strategy

### ❌ Anti-pattern: LLM judge every round
```python
# Every round:
semantic_result = llm.chat(verify_prompt)  # expensive
if semantic_result.confidence < threshold:  # unreliable gate
    continue
```

### ✅ Correct: Hard check every round, semantic only at end
```python
# Every round:
hard_result = run_pytest()  # free, deterministic

# Only when hard_result.passed:
if config.semantic_verify_on_completion:
    semantic_result = llm.chat(verify_prompt)  # once, at the end
```

## 4. Context Management

### ❌ Anti-pattern: Full history every round
```python
context = "\n".join(str(r) for r in state.round_history)
# Round 10 = 10x the context of round 1
```

### ✅ Correct: Three-tier compression
```python
# L0: last 3 rounds — full detail
# L1: earlier rounds — one-line summary per round (no LLM needed)
# L2: global state — goal, verified items, progress (always)
```

L1 summary format (NOT LLM-generated):
```
Round 1: [read_file, write_file, run_command] → 3 tests failed
Round 2: [read_file, write_file, run_command] → 1 test failed
```

## 5. Path Security

### ❌ Anti-pattern: Naive path check
```python
if ".." in filename or filename.startswith("/"):
    return "error"
# Misses: symbolic links, encoded paths, absolute paths after join
```

### ✅ Correct: Normalize then boundary check
```python
filepath = os.path.normpath(os.path.join(work_dir, filename))
if not filepath.startswith(os.path.normpath(work_dir)):
    return "error: path traversal"
```

## 6. Shell Command Whitelist

### ❌ Anti-pattern: First-word check only
```python
cmd_name = command.split()[0]
if cmd_name in allowed_commands: ...
# python -c "os.system('rm -rf /')" passes! (cmd_name = "python")
```

### ✅ Correct: shlex + injection detection
```python
import shlex
tokens = shlex.split(command)  # handles quotes correctly
cmd_name = tokens[0]

# Additional: check for injection via -c flags
if "python" in cmd_name and "-c" in command:
    if any(risk in command for risk in ["os.system", "subprocess", "exec("]):
        return "error: injection risk"
```

## 7. Reflection Rounds

### ❌ Anti-pattern: Reflection without action
```python
def _run_reflection_round(self, state, round_record):
    round_record.llm_thought = "Reflecting..."  # hardcoded placeholder
    round_record.action_taken = "reflect"
    # No actual LLM call, no tool use — wasted round
```

### ✅ Correct: LLM-powered reflection with tool access
```python
def _run_reflection_round(self, state, round_record):
    prompt = self.context.build_reflection_context(state)
    # Same executor, same tools — agent can read files to diagnose
    self.executor.execute_reflection(state, round_record, prompt)
    state.consecutive_stagnant_rounds = 0
```

## 8. Progress Detection

### ❌ Anti-pattern: Confusing index semantics
```python
prev_round = state.round_history[-2]  # comment says "-1 is current"
# But current round was already appended via new_round()!
```

### ✅ Correct: Search for last non-reflection round with hard check
```python
prev_hard = None
for r in reversed(state.round_history[:-1]):
    if r.round_type != "reflect" and r.hard_check_passed is not None:
        prev_hard = r.hard_check_details
        break
```

## 9. Error Handling in Tool Execution

### ❌ Anti-pattern: Bare except swallowing errors
```python
except:
    return {"passed": False, ...}  # hides the real problem
```

### ✅ Correct: Specific exception handling + logging
```python
except subprocess.TimeoutExpired:
    return f"error: command timed out ({timeout}s)"
except FileNotFoundError:
    return f"error: command not found: {cmd_name}"
except Exception as e:
    logger.warning(f"Unexpected tool error: {e}")
    return f"error: {e}"
```

## 10. State Machine Completeness

Ensure every state transition is explicit and every state has an exit:

```
PENDING → RUNNING → VERIFYING → SUCCEEDED ✓
                    ↓         ↘ FAILED ✓
                  RUNNING ✓ (retry)
                    ↓
                REFLECTING → RUNNING ✓ (post-reflection)
                    ↓
                  ERROR ✓ (exception/circuit break)
```

Missing transitions to watch for:
- What if reflection itself fails? → ERROR
- What if LLM returns empty response? → retry or ERROR
- What if tool execution hangs? → timeout → continue or ERROR
