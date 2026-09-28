# Security policy

## Supported versions

Security fixes target the latest release in the `0.1.x` series. Upgrade to the latest patch release before reproducing a report.

## Report a vulnerability

Use [GitHub's private vulnerability reporting](https://github.com/Buktal/ReAct-M/security/advisories/new). Include the affected version, a minimal reproduction, the potential impact and any proposed mitigation. Keep exploit details and credentials out of public issues.

## Execution model

ReAct-M runs registered async Python tools in the host process. Tool handlers are trusted code and receive the permissions of that process. Register only tools appropriate for the application and supply model credentials through environment variables.

Timeouts rely on cooperative cancellation. An uncertain external effect must be reconciled by the host before execution resumes with a new Engine. The runtime does not provide process isolation or roll back external changes.

Model responses and tool outputs are recorded in run traces. Review these traces before sharing them; `results/local/` is excluded from Git by default.
