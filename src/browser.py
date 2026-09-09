"""Main browser window: URL bar, back/forward/reload, WebKit view."""

import gi

from . import config

gi.require_version("Gtk", config.GTK_API)
gi.require_version("WebKit2", config.WEBKIT_API)
from gi.repository import Gtk, WebKit2

from .utils import normalize_url


class BrowserWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=config.APP_NAME)
        self.set_default_size(config.DEFAULT_WIDTH, config.DEFAULT_HEIGHT)
        self.connect("destroy", Gtk.main_quit)

        # Shared WebContext so later features (content filters, proxy,
        # cookie policy, Pi-hole-oriented networking) can be attached once.
        self.context = WebKit2.WebContext.get_default()
        self.content_manager = WebKit2.UserContentManager()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        nav_bar.set_margin_start(5)
        nav_bar.set_margin_end(5)
        nav_bar.set_margin_top(5)
        nav_bar.set_margin_bottom(5)
        vbox.pack_start(nav_bar, False, False, 0)

        self.back_btn = Gtk.Button.new_from_icon_name("go-previous", Gtk.IconSize.BUTTON)
        self.back_btn.set_tooltip_text("Back")
        self.back_btn.set_sensitive(False)
        self.back_btn.connect("clicked", self.on_back)
        nav_bar.pack_start(self.back_btn, False, False, 0)

        self.forward_btn = Gtk.Button.new_from_icon_name("go-next", Gtk.IconSize.BUTTON)
        self.forward_btn.set_tooltip_text("Forward")
        self.forward_btn.set_sensitive(False)
        self.forward_btn.connect("clicked", self.on_forward)
        nav_bar.pack_start(self.forward_btn, False, False, 0)

        self.refresh_btn = Gtk.Button.new_from_icon_name("view-refresh", Gtk.IconSize.BUTTON)
        self.refresh_btn.set_tooltip_text("Reload")
        self.refresh_btn.connect("clicked", self.on_reload)
        nav_bar.pack_start(self.refresh_btn, False, False, 0)

        self.url_entry = Gtk.Entry()
        self.url_entry.set_hexpand(True)
        self.url_entry.set_placeholder_text("Enter address or search")
        self.url_entry.connect("activate", self.on_url_enter)
        nav_bar.pack_start(self.url_entry, True, True, 0)

        self.webview = WebKit2.WebView.new_with_user_content_manager(self.content_manager)
        self.webview.connect("load-changed", self.on_load_changed)
        self.webview.connect("notify::uri", self.on_uri_changed)
        self.webview.connect("decide-policy", self.on_decide_policy)

        scrolled = Gtk.ScrolledWindow()
        scrolled.add(self.webview)
        vbox.pack_start(scrolled, True, True, 0)

        self._install_future_hooks()

    def _install_future_hooks(self):
        """Placeholders for Pi-hole filters and YouTube JS injection.

        Next steps:
        - Add WebKit2.UserContentFilterStore and load an EasyList-derived filter.
        - Optionally set a network proxy that points at a local filtering proxy.
        - On youtube.com navigations, run_javascript() or inject a UserScript
          inspired by SmartTube-style playback hooks.
        """
        settings = self.webview.get_settings()
        settings.set_enable_developer_extras(True)
        settings.set_enable_javascript(True)

    def load_url(self, url: str):
        self.webview.load_uri(normalize_url(url))

    def on_url_enter(self, entry):
        self.load_url(entry.get_text())

    def on_back(self, _button):
        if self.webview.can_go_back():
            self.webview.go_back()

    def on_forward(self, _button):
        if self.webview.can_go_forward():
            self.webview.go_forward()

    def on_reload(self, _button):
        self.webview.reload()

    def on_load_changed(self, webview, load_event):
        if load_event == WebKit2.LoadEvent.STARTED:
            self.refresh_btn.set_sensitive(True)
        if load_event == WebKit2.LoadEvent.FINISHED:
            uri = webview.get_uri() or ""
            if uri:
                self.url_entry.set_text(uri)
            self._update_nav_buttons()

    def on_uri_changed(self, webview, _pspec):
        uri = webview.get_uri()
        if uri:
            self.url_entry.set_text(uri)
        self._update_nav_buttons()

    def on_decide_policy(self, _webview, decision, decision_type):
        """Hook point for navigation-based YouTube / ad-blocking logic."""
        # Future: inspect decision.get_request().get_uri() and inject scripts
        # when the target is youtube.com / youtube-nocookie.com.
        return False

    def _update_nav_buttons(self):
        self.back_btn.set_sensitive(self.webview.can_go_back())
        self.forward_btn.set_sensitive(self.webview.can_go_forward())
