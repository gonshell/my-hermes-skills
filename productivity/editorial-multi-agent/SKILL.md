---
name: editorial-multi-agent
description: "Multi-agent editorial pipeline for long-form content creation (blog posts, articles, reports). Orchestrates: Orchestrator (editor-in-chief) → Lead Writer → Tech Reviewer + Editor → Final Review → Merged Output. Use when user wants structured content written via multiple specialized agents."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [writing, content, editorial, multi-agent, delegation, delegate_task]
    related_skills: [subagent-driven-development, writing-plans, tech-research-doc]
---

# Editorial Multi-Agent Pipeline

## Overview

Execute long-form content creation via specialized agent roles: Orchestrator (editor-in-chief), Lead Writer, Tech Reviewer, Editor, and Final Review. Each role has distinct responsibilities. The pipeline enforces two-track review (technical accuracy + editorial quality) before final output.

**Trigger:** User asks to write a blog post/article/report using multiple agents; user wants structured content with roles like "主编/主笔/评审".

## When to Use

Use when:
- Content is 3,000+ words requiring multiple sections
- Target audience is mixed (technical + non-technical)
- Content requires factual accuracy on technical details
- Writing quality, tone consistency, and structure matter
- Task benefits from role specialization

**vs. single-agent writing:**
- Fresh context per role (orchestrator doesn't write, reviewer doesn't draft)
- Parallel execution of independent sections
- Two-track quality gates (tech + editorial)
- Systematic corrections applied to consolidated output

## The Process

### Phase 1: Orchestrator (Editor-in-Chief)

**Role:** Design the article structure, writing plan, quality standards, and style guide.

**Tasks:**
1. Read and analyze source material (transcripts, documents, research)
2. Design article outline with:
   - Title (main + subtitle)
   - Section structure (2 levels)
   - Word count allocation per section
   - Technical density gradient design
   - Quality standards (accuracy, emotional resonance, readability, unique perspective)
   - Writing style guide (tone, sentence structure, terminology usage)
3. Write outline to `~/workspace/blog-outline-<slug>.md`
4. Dispatch writer subagents

**Orchestrator's output format:**
```markdown
# Article Outline

## Title
主标题 + 副标题

## Structure
| Section | Word Count | Tech Density | Purpose |

## Writing Plan
### Section 1
- Core content points
- Writing focus
- Style notes

## Quality Standards
| Dimension | Requirements |

## Style Guide
- Tone:
- Sentence:
- Terminology:
```

### Phase 2: Lead Writers (Parallel)

**Role:** Draft content per assigned sections, following the orchestrator's plan.

**Constraints:**
- Strictly follow outline structure and word counts
- Follow technical density gradient
- Maintain tone consistency
- Each section → separate file: `~/workspace/blog-draft-part{N}.md`

**Writer subagent dispatch pattern:**
```python
# If max_concurrent_children limits you, batch into waves
# Batch 1: Wave 1 (max concurrent)
delegate_task(goal="Write Part 1 + 2", tasks=[...])
# Batch 2: Wave 2
delegate_task(goal="Write Part 3 + 4", tasks=[...])
```

**Key principle:** Don't make subagents read the outline file — embed the full outline text in the context.

### Phase 3: Two-Track Review (Parallel)

After all drafts are written, run **two reviewers in parallel**:

#### Track A: Tech Reviewer

**Focus:** Technical accuracy — data, facts, terminology, context.

**Review criteria:**
- All numerical data matches source material
- Terminology used correctly (codec vs container, etc.)
- Context and timeline correct
- No facts fabricated or exaggerated
- Source claims marked with appropriate qualifiers ("据报道", "有说法称")

**Output format:**
```markdown
## Technical Review Report

### Issues Found
| Location | Issue | Severity | Suggested Fix |

### Verdict: [PASS / NEEDS_REVISION]
```

#### Track B: Editorial Reviewer

**Focus:** Writing quality — readability, structure, tone consistency, rhythm.

**Review criteria:**
- Paragraph length ≤ 150 chars (mobile-friendly)
- Memory points every ~500 words (quote/data/conflict)
- Technical density gradient followed
- Opening/closing hooks effective
- Tone consistent and restrained (not melodramatic)
- Section headers have informational value

**Output format:**
```markdown
## Editorial Review Report

### Issues Found
| Location | Issue | Suggested Fix |

### Verdict: [PASS / NEEDS_REVISION]
```

### Phase 4: Final Review + Corrections

**Role:** Synthesize both reviews, apply corrections to produce final output.

**Process:**
1. Read both review reports
2. Identify all correction points
3. Apply corrections to consolidated draft
4. Save final version: `~/workspace/blog-<slug>-final.md`

**Correction tracking:**
```python
fixes = []
for issue in tech_review + editorial_review:
    apply_fix(issue)
    fixes.append(f"✓ {issue.description}")

print(f"Applied {len(fixes)} corrections")
```

### Phase 5: Delivery

**Final output includes:**
- Final article: `~/workspace/blog-<slug>-final.md`
- Outline: `~/workspace/blog-outline-<slug>.md`
- Review reports (for transparency)

## Reader Feedback Collection (Post-Delivery)

After delivering the final article, collect reader feedback from diverse audience segments to inform a second revision cycle.

### Reader Role Selection

Select **5 roles** spanning the target audience dimensions:

| Role | What They Care About |
|------|---------------------|
| Senior Engineer | Technical precision, numeric accuracy, depth |
| OSS Community Insider | Community dynamics, license, governance |
| General Reader | Accessibility, hook effectiveness, pacing |
| Technical Writer | Prose quality, structure, transitions |
| Entrepreneur/Business | Practical implications, scale, adoption |

**Dispatch pattern:** Run all 5 in parallel (`max_concurrent_children` permitting), each producing `~/workspace/feedback-<role>.md`.

### Feedback Synthesis → Optimization Plan

After collecting all reader reports, produce an **Optimization Plan** (`blog-optimization-plan.md`) as a Chief Editor + Lead Writer joint document:

```markdown
# Optimization Plan

## Feedback Summary
| Source | Verdict | Key Points |

## High Priority Changes (Must-Do)
| # | Location | Change | Rationale | Est. Impact |

## Medium Priority Changes (Recommended)
| # | Location | Change | Rationale | Est. Impact |

## Rejected Feedback
| Feedback | Reason for Rejection |

## Final Design Principles Confirmed
- Core structure unchanged / changed because...
```

**Key principle:** The optimization plan is a **filter**, not a laundry list. Reject feedback that would compromise core design. Document rejections with explicit rationale.

## Optimization Execution

Execute the approved optimization plan via targeted patches (each patch = one item, no new content creation):

1. Read final article
2. Apply each approved change via patch
3. Verify after each patch

**Estimated output size increase:** ~200 chars per high-priority item, ~150 chars per medium-priority item.

---

## Session Example (Extended)

```
[Orchestrator] Read transcript → Design outline → Write blog-outline-ffmpeg.md
[Lead Writers] Part 1 (Hook + Ch1) + Part 2 (Ch2) [parallel, batch 1]
[Lead Writers] Part 3 (Ch3) + Part 4 (Ch4-5 + Conclusion) [parallel, batch 2]
[Merged] blog-draft-full.md

[Tech Reviewer] → blog-review-tech.md (10 corrections)
[Editorial Reviewer] → blog-review-editor.md (structural improvements)

[Final] Applied 10 corrections → blog-ffmpeg-final.md ✓

[Reader Roles ×5] → feedback-*.md (parallel)
[Chief Editor + Lead Writer] → blog-optimization-plan.md

[Execute] blog-optimization-plan.md → blog-ffmpeg-final-v2.md ✓
```

## Key Pitfalls

### Orchestrator Pitfalls
- **Outline too vague:** Writers can't follow vague instructions. Every section needs concrete content points.
- **Ignoring tech density gradient:** Placing two high-density technical sections consecutively causes reader fatigue.

### Writer Pitfalls
- **Exceeding word count:** Stay within allocated word count per section.
- **Inconsistent tone:** Keep emotional expression restrained.
- **Making up technical details:** Stick to verified source material.

### Reviewer Pitfalls
- **Reviewing before all drafts complete:** Wait for full content before reviewing.
- **Focusing on style over accuracy:** Tech review prioritizes factual correctness first.

### General Pitfalls
- **Skipping review phase:** Two-track review catches different issue types.
- **Not batching subagents:** Respect `max_concurrent_children` limits (usually 3).

## Role Definitions Summary

| Role | Goal | Output |
|------|------|--------|
| **Orchestrator** | Design structure + plan + standards | Outline file |
| **Lead Writer** | Draft sections per outline | Part drafts |
| **Tech Reviewer** | Verify factual accuracy | Review report |
| **Editorial Reviewer** | Verify writing quality | Review report |
| **Final Review** | Apply corrections | Final article |

## Session Example

```
[Orchestrator] Read transcript → Design outline → Write blog-outline-ffmpeg.md
[Lead Writers] Part 1 (Hook + Ch1) + Part 2 (Ch2) [parallel, batch 1]
[Lead Writers] Part 3 (Ch3) + Part 4 (Ch4-5 + Conclusion) [parallel, batch 2]
[Merged] blog-draft-full.md

[Tech Reviewer] → blog-review-tech.md (10 corrections)
[Editorial Reviewer] → blog-review-editor.md (structural improvements)

[Final] Applied 10 corrections → blog-ffmpeg-final.md ✓
```

## Remember

```
Orchestrator plans
Writers draft
Reviewers check (two tracks)
Final synthesizes
Corrections applied
Final delivered
```

**Quality is systematic, not accidental.**
