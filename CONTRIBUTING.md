# Contributing to GL.iNet Community Scripts

Community-maintained scripts, helpers, and automations for GL.iNet routers. ❤️

## What We're Looking For

- **Scripts & utilities** that enhance GL.iNet router functionality
- **Documentation** improvements and tutorials
- **Bug fixes** and minor feature additions to existing tools
- **CI/CD workflows** and testing infrastructure

## How to Get Started

1. **Browse existing repos** — check the [organization page](https://github.com/GLiNet-Community-Scripts) for projects
2. **Open an issue** — report bugs, request features, or propose new scripts
3. **Fork & PR** — fork the relevant repo, make your changes, and open a PR

## Contribution Guidelines

### Before Opening an Issue
- Search existing issues first
- Use clear, descriptive titles
- Include: GL.iNet model, firmware version, expected vs actual behavior, logs

### Before Submitting a PR
- Test your changes on actual hardware (or specify if untested)
- Follow ShellCheck / Pyflakes for shell/Python code
- Add documentation in the README if you add new features
- Keep commits focused — one feature/fix per PR

### Code Standards
- **Shell scripts**: Use `#!/bin/sh` or `#!/bin/bash`, follow [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
- **Python**: Use Python 3, type hints, keep PEP 8 compliant
- **Lua**: OpenWrt LuCI apps, keep functions minimal

### Forking Guidelines
New repos are typically forks from individual contributors' upstream repos. Issues and PRs should target the fork in the organization, not the upstream.

## New Repository Requests

Want to contribute a new script? Open an issue with:
- Script name and purpose
- Target GL.iNet models
- Dependencies and installation steps

## Code of Conduct

Be respectful and constructive. Harassment or discrimination will not be tolerated.

## License

All contributions are licensed under MIT unless otherwise specified in the repository.
