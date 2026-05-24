# Scripts

This directory is reserved for lightweight local automation.

Planned contents:

- release manifest helpers
- audit reconstruction helpers
- replay and evidence inspection utilities
- manifest validation helpers with governance reference checks
- release-bundle packaging and attestation linkage helpers

Local support is intentionally light. AWS remains the primary runtime target.

For orchestration development, prefer the Docker-based Airflow path documented
in [docs/local-airflow-development.md](/Users/danny/Documents/UNI/thesis/thesis-proposed-solution/docs/local-airflow-development.md).

Current workflow-linked helpers:

- [build_release_bundle.py](/Users/danny/Documents/UNI/thesis/thesis-proposed-solution/scripts/build_release_bundle.py)
  writes the generated release manifest, change record, and runtime config for
  an attested GitHub Actions release-controls run.
