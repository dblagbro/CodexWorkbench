# Architecture

Resolve high-cost boundaries before dependent work: component responsibilities, data ownership/lifecycle, interfaces, permission/trust boundaries, concurrency, deployment topology and failure/rollback paths. Use maintained components where they fit; read the research/adoption module when a substantial custom design may duplicate existing work.

Design an early working vertical slice and explicit contracts; use a focused experiment for the riskiest unknown. Document relevant alternatives, decision reasons and reversibility. Consider idempotency, timeouts, interrupted effects, upgrade/migration and export/exit. Avoid speculative microservices, extension layers or a new platform without a concrete requirement.

Revisit when evidence changes, not to chase architecture fashion. Preserve the current project's constraints and recommend consequential redesign before moving shared resources or changing compatibility. Handoff needs implementation-ready decisions and evidence, not hidden reasoning.
