---
description: "Squad roster: roles and the deployed HVE Core agents that fill them"
---

# Squad Roster

## Members

| Role | Member Name | Agent Name (Primary) | Alternate Agents | Invocation | Model Tier |
|------|-------------|----------------------|------------------|------------|------------|
| researcher | Alpha | Task Researcher | Researcher Subagent, Codebase Profiler, Meeting Analyst | runSubagent / task | fast |
| lead | Beta | Task Planner | RPI Agent, Phase Implementor, Task Challenger | runSubagent / task | default |
| developer | Gamma | Task Implementor | Phase Implementor | runSubagent / task | default |
| tester | Delta | Task Reviewer | Code Review Full, Code Review Standards, Code Review Functional, PR Review, Implementation Validator, Plan Validator, RPI Validator | runSubagent / task | fast |
| architect | Epsilon | System Architecture Reviewer | Arch Diagram Builder, ADR Creator, Network ISA-95 Planner | runSubagent / task | default |
| azure-architect | Zeta | Squad Azure Architect | — | runSubagent / task | default |
| iac-author | Eta | Squad IaC Author | — | runSubagent / task | default |
| deployer | Theta | Squad Deployer | — | runSubagent / task | default |
| asbuilt-author | Iota | Squad As-Built Author | — | runSubagent / task | fast |
| azure-diagnose | Kappa | Squad Azure Diagnose | — | runSubagent / task | fast |
| security | Lambda | Security Planner | Security Reviewer, SSSC Planner, Skill Assessor, Finding Deep Verifier, Report Generator, Dependency Reviewer, Codebase Profiler | runSubagent / task | default |
| rai | Mu | RAI Planner | — | runSubagent / task | default |
| designer | Nu | UX UI Designer | DT Coach, DT Learning Tutor | runSubagent / task | default |
| fact-checker | Xi | Finding Deep Verifier | — | runSubagent / task | fast |
| cost-manager | Omicron | Squad Cost Manager | — | runSubagent / task | default |
| modernizer | Pi | Squad Modernization Planner | — | runSubagent / task | default |
| scribe | Rho | Squad Scribe | Memory | runSubagent / task | fast |
| product-owner | Sigma | GitHub Backlog Manager | ADO Backlog Manager, Jira Backlog Manager, Issue Triage Agent, Agile Coach, Product Manager Advisor | runSubagent / task | default |
