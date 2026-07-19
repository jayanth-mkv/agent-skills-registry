# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub’s private vulnerability reporting or Security Advisory feature for this repository and include:

- the affected skill, script, or workflow;
- reproduction steps;
- expected and observed behavior;
- likely impact;
- a safe remediation idea, if known.

Do not include live secrets or private customer data. Maintainers will acknowledge the report, investigate it, and coordinate disclosure when appropriate.

## Skill security expectations

Skills are instructions that can influence tools and file access. Contributions must avoid hidden network access, unsafe command construction, destructive defaults, credential collection, and untrusted instruction execution. Any required network behavior, external dependency, or state-changing operation must be explicit in the skill and pull request.
