# Network, firewall and ingress

Read owner/site policy and actual topology, gateway roles, routes, firewall/PAT, DNS, TLS termination/passthrough and certificate ownership before proposing changes. Distinguish observed configuration, historical records, desired state and authorization. Reuse designated inbound gateways and working nginx/Certbot conventions for environment-hosted projects; evaluate cloud networking separately.

Do not add normal inbound workstation PAT or assign production container workloads to an unauthorized host. Explicit temporary test exposure needs narrow rules, lifetime, prior-state record, cleanup and verified firewall/PAT reversal. Do not weaken authentication or expose control APIs to make integration convenient.

Prepare concrete reviewable changes and a rollback path; avoid losing management/recovery connectivity. Observe actual state after changes, preserve existing controllers/device ownership, and do not retry uncertain effects blindly. A project being "full-stack" does not itself justify network mutations or require loading this module.
