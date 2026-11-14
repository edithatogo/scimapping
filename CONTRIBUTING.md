# Contributing to scimapping

scimapping develops Python connectors and analyses for bibliographic data. Read the [README](README.md), [AGENTS.md](AGENTS.md), and [protocol](PROTOCOL.md) before changing source adapters or analysis interfaces.

## Before you start

Search existing issues and pull requests before starting, and discuss substantial changes or new dependencies in an issue. Use an issue template when one is offered. For a bug, include the affected commit or version, environment, a minimal reproduction, and expected versus observed behavior; remove sensitive information from logs and screenshots.

## Development and validation

Follow the README's installation guidance and [pyproject.toml](pyproject.toml) for the package and optional development dependencies. Keep dependency changes consistent with [requirements.txt](requirements.txt). The existing agent instructions require PEP 8, type hints, documented interfaces, and tests for new functionality.

Extend the tests in [tests](tests) for affected connectors or analyses. Prefer deterministic fixtures or mocked responses for API behavior, including pagination, empty results, malformed records, and failures. Record any test that requires unavailable credentials or external access separately from completed checks.

Keep source-specific parsing separate from the common data representation. Preserve identifiers and provenance, document inference uncertainty, and respect data-source usage and redistribution conditions. Do not present a placeholder dependency or license declaration as settled policy.

## Pull requests

Work on a focused branch from the current default branch. Open a pull request explaining the problem, the resulting behavior, and any compatibility or data-format changes. Link the relevant issue and complete any existing PR template.

Add focused regression coverage for changed behavior and update affected examples or documentation. Describe the checks actually run, their results, and any checks you could not run. For documentation-only changes, verify links, examples, and rendered formatting. Use the repository's existing checks and review/merge process; preserve required checks and resolve actionable feedback without weakening the checks.

## Security and sensitive information

Follow the [account security policy](https://github.com/edithatogo/.github/blob/main/SECURITY.md). Report vulnerabilities privately through the repository's **Report a vulnerability** option if available; otherwise request a private reporting contact without posting exploit details. Never include credentials, personal information, restricted datasets, or confidential records in issues, commits, fixtures, or diagnostic output.

## Licensing and conduct

Be respectful and constructive, and follow the [account code of conduct](https://github.com/edithatogo/.github/blob/main/CODE_OF_CONDUCT.md). Preserve attribution and third-party notices. Contribute only material you are entitled to share; resolve unclear permissions before adding third-party content. This guide does not change licensing terms or introduce a CLA or DCO requirement.

## References

- [GitHub contribution guideline conventions](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/setting-guidelines-for-repository-contributors)
- [OpenSSF contribution and quality criteria](https://www.bestpractices.dev/en/criteria)
