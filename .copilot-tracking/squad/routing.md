---
description: "Squad routing: request patterns mapped to roles, autonomy tiers, and parallel eligibility"
---

# Squad Routing

| Pattern / Keyword | Role(s) | Autonomy Tier | Parallel-Eligible |
|---|---|---|---|
| research, investigate, explore, find out | researcher | auto | yes |
| plan, break down, sequence, design plan | lead | confirm | no |
| implement, build, code, fix | developer | confirm | no |
| review, validate, check quality | tester | auto | yes |
| security, threat, vulnerability, STRIDE | security | confirm | yes |
| design, UX, UI, wireframe, accessibility | designer | confirm | yes |
| architecture, system design, components | architect | auto | yes |
| responsible AI, RAI, fairness, harm | rai | confirm | yes |
| verify finding, confirm claim, fact-check | fact-checker | auto | yes |
| author IaC, write Bicep, write Terraform, convert LLD to infra, infrastructure as code | iac-author | confirm | no |
| deploy, provision, what-if, terraform plan, terraform apply, az deployment | deployer | confirm | no |
| as-built, resource inventory, compliance matrix, operations runbook, DR plan, document deployed infrastructure | asbuilt-author | confirm | no |
| diagnose, troubleshoot, resource health, why is resource failing, investigate deployed, policy check | azure-diagnose | auto | yes |
| validate, cross-check, pre-implementation review, council, design review, go/no-go, implement-and-cost, implement-and-risk | architect, security, cost-manager, rai (optional) | confirm | yes |
| modernize, upgrade framework, migrate, port legacy, .NET upgrade, Java migration, dependency upgrade, containerize | modernizer | confirm | no |
| re-platform, rewrite, port to, rebuild in, cross-stack rewrite, Node to .NET, React to Angular, convert to another language | modernizer | confirm | no |
