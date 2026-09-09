#!/usr/bin/env python3
"""Entry point for Web Surfer."""

import sys
import gi

from . import config

gi.require_version("Gtk", config.GTK_API)
gi.require_version("WebKit2", config.WEBKIT_API)

from gi.repository import Gtk  # noqa: E402
from .browser import BrowserWindow  # noqa: E402


def main(argv=None):
    argv = sys.argv if argv is None else argv
    win = BrowserWindow()
    if len(argv) > 1:
        win.load_url(argv[1])
    else:
        win.load_url(config.HOMEPAGE)
    win.show_all()
    Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
