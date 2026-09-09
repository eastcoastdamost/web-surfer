#!/usr/bin/env python3
"""Gtk application entry: construct the window and run the main loop."""

import sys
import gi

from . import config

# Bindings must request API versions before importing the repositories.
gi.require_version("Gtk", config.GTK_API)
gi.require_version("WebKit2", config.WEBKIT_API)

from gi.repository import Gtk  # noqa: E402
from .browser import BrowserWindow  # noqa: E402


def main(argv=None):
    """Create the browser, open the first tab, and block in Gtk.main()."""
    argv = sys.argv if argv is None else argv
    win = BrowserWindow()
    # Optional URL on the command line; otherwise the local start page.
    initial = argv[1] if len(argv) > 1 else config.HOMEPAGE
    win.add_tab(initial)
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
