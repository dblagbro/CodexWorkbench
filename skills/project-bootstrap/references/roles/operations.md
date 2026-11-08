# Systems operations

Discover target host role, existing deployment/service ownership, runtime state, storage/mount semantics, capacity, identities and recovery access. Read the private site policy before selecting execution/ingress hosts. Installed Docker does not grant a server role; preserve workstation testing/utility restrictions. Keep tool setup separate from production runtime.

Prepare versioned configuration, secret references, health/readiness, restart/shutdown behavior, logs/redaction, upgrades, rollback and recovery commands proportional to the service. Use application-consistent backups and verify restoration where consequential. Respect owner-approved local secret storage while excluding secrets from external publication/build contexts.

Verify actual target state before and after authorized changes. Record uncertain side effects before retrying and coordinate shared production mutations. Use networking guidance only if routing, ingress, DNS/TLS or firewall changes are part of the work. Essential maintenance/recovery paths must work without an active AI session.
