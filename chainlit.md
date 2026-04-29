# Omaha-Lab

**A local-first sandbox for LLM security, agentic tool-calling, and OWASP mitigation.**

All inference runs on your hardware via Ollama — no cloud endpoints. The pipeline layers visible in the step cards (input guard, RAG, tool calls, HITL, output guard) are the same ones you attack and defend in the labs below.

---

## Lab Guide

### Module 1 — Foundations

- [Lab 1.1 — Environment Setup](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module1/lab1_1_environment_setup.md)
- [Lab 1.2 — Your First Tool-Calling Agent](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module1/lab1_2_first_agent.md)
- [Lab 1.3 — Reading the ReAct Trace](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module1/lab1_3_react_trace.md)
- [Lab 1.4 — Loading a Persona](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module1/lab1_4_persona.md)
- [Lab 1.5 — Enabling RAG with a Markdown Context Document](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module1/lab1_5_rag.md)

### Module 2 — Offensive Security

Use **Bare** or **RAG Analyst** Lab Mode for these exercises.

- [Lab 2.1 — Direct Prompt Injection](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module2/lab2_1_direct_injection.md)
- [Lab 2.2 — Indirect Injection via Tool Response](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module2/lab2_2_indirect_injection_tool.md)
- [Lab 2.3 — Indirect Injection via RAG Document](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module2/lab2_3_indirect_injection_rag.md)
- [Lab 2.4 — PII Extraction Attack](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module2/lab2_4_pii_extraction.md)
- [Lab 2.5 — System Prompt Leakage](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module2/lab2_5_system_prompt_leakage.md)
- [Lab 2.6 — Excessive Agency: Unauthorized File Write](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module2/lab2_6_excessive_agency.md)
- [Lab 2.7 — Improper Output Handling](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module2/lab2_7_improper_output.md)
- [Lab 2.8 — RAG Poisoning and Embedding Attack](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module2/lab2_8_rag_poisoning.md)
- [Lab 2.9 — Unbounded Consumption Loop](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module2/lab2_9_unbounded_consumption.md)

### Module 3 — Defensive Architecture

Use **Guarded** or **Full Defense** Lab Mode for these exercises.

- [Lab 3.1 — Enabling Llama Guard 3 on Inputs](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module3/lab3_1_llama_guard_inputs.md)
- [Lab 3.2 — Applying Llama Guard 3 to Retrieved RAG Chunks](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module3/lab3_2_llama_guard_rag.md)
- [Lab 3.3 — PII Redaction with Microsoft Presidio](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module3/lab3_3_presidio_pii_redaction.md)
- [Lab 3.4 — HITL Authorization Breakpoint](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module3/lab3_4_hitl.md)
- [Lab 3.5 — Output Validation and Canary Tokens](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module3/lab3_5_output_validation.md)
- [Lab 3.6 — Scoping Tool Permissions per Persona](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module3/lab3_6_tool_scoping.md)
- [Lab 3.7 — Iteration Limits and Rate Control](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module3/lab3_7_iteration_limits.md)
- [Lab 3.8 — Supply Chain Hygiene: Verifying Ollama Models](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module3/lab3_8_supply_chain.md)
- [Lab 3.9 — Grounding with RAG and Search: Reducing Misinformation](https://github.com/packetcraft/Omaha-Lab/blob/master/labs/module3/lab3_9_rag_grounding.md)

---

[GitHub Repository](https://github.com/packetcraft/Omaha-Lab)
