# Key AI Agent Papers (May 2026 Snapshot)

## Foundational Papers

### MetaGPT (2308.00352)
**Title**: MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework
**Authors**: Sirui Hong et al.
**Published**: 2023-08-01
**Categories**: cs.AI, cs.MA
**Contribution**: SOP-based multi-agent collaboration simulating software company roles (PM, Architect, Engineer, PM). Reduces logic inconsistency through structured inter-agent communication.

### HuggingGPT (2303.17580)
**Title**: Solving AI Tasks with ChatGPT and its Friends in Hugging Face
**Authors**: Yongliang Shen et al.
**Published**: 2023-03-30
**Categories**: cs.CL, cs.AI, cs.CV, cs.LG
**Contribution**: LLM as orchestrator of heterogeneous ML models (detection, generation, etc.) via Hugging Face ecosystem.

### AgentBench (2308.03688)
**Title**: AgentBench: Evaluating LLMs as Agents
**Authors**: Xiao Liu et al.
**Published**: 2023-08-07
**Categories**: cs.AI, cs.CL, cs.LG
**Contribution**: Multi-dimensional benchmark across 8 environments for evaluating LLM-as-agent performance.

### CAMEL (2303.17760)
**Title**: CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society
**Authors**: Guohao Li et al.
**Published**: 2023-03-31
**Categories**: cs.AI, cs.CL, cs.CY, cs.LG, cs.MA
**Contribution**: Role-playing framework with inception prompting for scalable autonomous multi-agent cooperation. Open-sourced: github.com/camel-ai/camel.

**Verified abstract**: "The rapid advancement of chat-based language models has led to remarkable progress in complex task-solving. However, their success heavily relies on human input to guide the conversation, which can be challenging and time-consuming. This paper explores the potential of building scalable techniques to facilitate autonomous cooperation among communicative agents, and provides insight into their 'cognitive' processes. To address the challenges of achieving autonomous cooperation, we propose a novel communicative agent framework named role-playing. Our approach involves using inception prompting to guide chat agents toward task completion while maintaining consistency with human intentions."

---

## 2025-2026 Frontier Papers (Latest)

### RAO - Recursive Agent Optimization (2605.06639)
**Title**: Recursive Agent Optimization
**Authors**: Apurva Gandhi, Satyaki Chakraborty et al. (CMU / Meta)
**Published**: 2026-05-07
**Categories**: cs.LG, cs.AI, cs.CL, cs.MA
**Contribution**: RL approach for training **recursive agents** — agents that can spawn sub-agents to delegate sub-tasks recursively. Implements inference-time scaling via divide-and-conquer.
**Key insight**: Instead of single LLM doing all reasoning, agent learns when/how to delegate. Natural generalization to longer contexts.

### SkillOS (2605.06614)
**Title**: SkillOS: Learning Skill Curation for Self-Evolving Agents
**Authors**: Siru Ouyang et al.
**Published**: 2026-05-07
**Categories**: cs.AI
**Contribution**: Agents learn reusable skills from experience. Key bottleneck: high-quality **skill curation**. Existing approaches: manual or heuristic → quality drift.
**Key insight**: Current agents are "one-off problem solvers" — need experience-driven skill library.

### StraTA (2605.06642)
**Title**: StraTA: Incentivizing Agentic Reinforcement Learning with Strategic Trajectory Abstraction
**Authors**: Xiangyuan Xue et al.
**Published**: 2026-05-07
**Categories**: cs.CL, cs.AI
**Contribution**: Long-horizon RL for LLM agents. Current methods: purely reactive → poor exploration and credit assignment over extended trajectories.
**Key insight**: Explicit trajectory abstraction guides exploration; improves credit assignment.

### Superintelligent Retrieval Agent (2605.06647)
**Title**: Superintelligent Retrieval Agent: The Next Frontier of Information Retrieval
**Authors**: Zeyu Yang et al. (Rice University)
**Published**: 2026-05-07
**Categories**: cs.IR, cs.AI, cs.LG
**Contribution**: RAG agents treat retrieval as black box (exploratory query → inspect snippets → iterate). Experts have **strong priors** and **strategic navigation**.
**Key insight**: Need to move from passive retrieval to active knowledge navigation.

### Cited but Not Verified (2605.06635)
**Title**: Cited but Not Verified: Parsing and Evaluating Source Attribution in LLM Deep Research Agents
**Authors**: Hailey Onweller et al.
**Published**: 2026-05-07
**Categories**: cs.CL
**Contribution**: Deep research agents synthesize from hundreds of sources, but **citations cannot be reliably verified**. Existing methods: trust self-cite (hallucination risk) or RAG without validation.
**Key insight**: Need verifiable citation mechanisms for agent outputs.

### AI Co-Mathematician (2605.06651)
**Title**: AI Co-Mathematician: Accelerating Mathematicians with Agentic AI
**Authors**: Daniel Zheng et al. (DeepMind)
**Published**: 2026-05-07
**Categories**: cs.AI
**Contribution**: Workbench for mathematicians using AI agents for open-ended research: ideation, literature search, computation, theorem proving.
**Key insight**: Asynchronous exploratory workflows require holistic agent support.

### AI CFD Scientist (2605.06607)
**Title**: AI CFD Scientist: Toward Open-Ended Computational Fluid Dynamics Discovery with Physics-Aware AI Agents
**Authors**: Nithin Somasekharan et al.
**Published**: 2026-05-07
**Categories**: cs.AI
**Contribution**: Extends agentic AI loop to high-fidelity physical simulators. Solver completion ≠ physical validity. Many failure modes only in field-level imagery.
**Key insight**: Physical awareness needed for simulation-based scientific discovery.

### BAMI (2605.06664)
**Title**: BAMI: Training-Free Bias Mitigation in GUI Grounding
**Authors**: Borui Zhang et al.
**Published**: 2026-05-07
**Categories**: cs.CV, cs.AI
**Contribution**: Training-free approach to bias in GUI grounding — complex scenarios where agents must click/drag precisely.
**Key insight**: GUI agents struggle with precise operation localization in complex scenarios.

### MASPO (2605.06623)
**Title**: MASPO: Joint Prompt Optimization for LLM-based Multi-Agent Systems
**Authors**: Zhexuan Wang et al.
**Published**: 2026-05-07
**Categories**: cs.CL, cs.AI
**Contribution**: Multi-agent systems use role-specific prompts. **Joint optimization** is hard due to misalignment between local objectives and global system goal.
**Key insight**: Prompt optimization in multi-agent setting requires coordinated optimization across agents.
