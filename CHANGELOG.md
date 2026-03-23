# Changelog

## 0.1.5

- Configure GitHub release publishing to run in the `pypi` environment for Trusted Publisher uploads
- Make the default README Chinese and split the English guide into `README.en.md`
- Default installation guidance to the GitHub repository until the first PyPI release is live

## 0.1.4

- Re-issue the release from the correct commit after the previous tag pointed at an older revision
- Include the cross-platform PowerShell profile path fix in the tagged release

## 0.1.3

- Normalize probed PowerShell profile paths so cross-platform tests pass on macOS and Linux runners
- Make the test matrix more diagnosable by disabling fail-fast and enabling verbose pytest output

## 0.1.2

- Align CI, build, and release workflows to Python 3.14
- Declare Python 3.14 as the supported runtime in package metadata
- Force GitHub Actions JavaScript actions onto Node 24 to avoid the Node 20 deprecation path

## 0.1.1

- Point installers to the GitHub repository so users can install MXTerm before PyPI is enabled
- Update English and Chinese documentation with real installation commands and links
- Fix Windows release packaging path handling

## 0.1.0

- Initial MXTerm MVP
- Cross-platform shell hooks for zsh, bash, and PowerShell
- Ollama-based natural language translation
- Safety assessment, confirmation flow, and install/uninstall CLI
