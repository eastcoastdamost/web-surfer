# Contributing to Web Surfer

Thank you for helping keep this browser free and open.

## License of contributions

By opening a pull request you agree that your contribution is licensed under
the **GNU GPL v3 or later**, the same license as the rest of the project.

## How to work on the code

1. Fork the repository on GitHub.
2. Clone your fork.
3. Create a branch: `git checkout -b feature/short-name`
4. Install system packages listed in the README (`python3-gi`, WebKitGTK).
5. Run: `python3 web_surfer.py`
6. Unit tests that do not need a display: `python3 -m pytest tests -q`

## Pull requests

- Keep the first version of the browser small: URL bar, back, forward, reload, WebView.
- Do not vendor Chromium or Chrome.
- Do not copy SmartTube source. Ideas are fine; that code is not.
- SearxNG, if bundled later, must keep its own AGPL notices.

## Code of conduct (short)

Be kind. No harassment. Argue about the code, not the person.
