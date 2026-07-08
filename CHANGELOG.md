# Changelog

Notable changes to asqav-langflow. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

First release.

### Added
- Asqav Sign Action Langflow custom component: signs an agent action through the
  Asqav SDK and returns the receipt as a Langflow `Data` object.
- Optional `langflow` extra to pull in the Langflow host alongside the component.
- Tag-gated PyPI publish workflow using OIDC trusted publishing.
- Pull-request build dry run that runs `python -m build` and `twine check`.

### Changed
- Pinned the `asqav` SDK dependency to the 0.8 line (`asqav>=0.8.0,<0.9.0`).
