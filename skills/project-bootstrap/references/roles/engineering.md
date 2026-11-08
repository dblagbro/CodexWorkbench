# Engineering and full-stack implementation

Read relevant existing contracts and code before changing behavior. Implement a complete narrow workflow with clear ownership, boundary validation, explicit errors, bounded retries and testable state transitions. Avoid provider-specific flags leaking into shared logic. Use project-scoped environments and appropriate dependency pinning; developer tools must not become accidental runtime requirements.

Watch for duplicated adapter behavior, repeated bugs, coupling and brittle/manual operations. Apply a bounded justified refactor early with behavior/regression evidence; do not rewrite stable code for aesthetics. Use the quality loop for reproduction, remediation, affected-workflow verification and documentation/help updates.

For full-stack work, add only the roles that actually apply: architecture for contracts/data boundaries, UI for a browser surface, operations for deployment, networking for actual network changes. Output reviewable changes, tests and remaining limits. Do not use test passes as proof of live deployment success.
