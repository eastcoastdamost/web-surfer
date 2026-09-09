"""Main window: CSD chrome, tabs, navigation, start page, bookmarks.

Layout (top to bottom):
    HeaderBar — logo, tab chips, new-tab, window controls
    Nav bar — back, forward, reload, URL, star, list, bar toggle
    Optional bookmarks bar (~28px)
    Gtk.Stack of WebViews

Bookmark reorder is press/move/release (Gtk DND was unreliable).
New windows from JS must use WebView.new_with_related_view.
"""

import base64
from pathlib import Path

import gi

from . import config

gi.require_version("Gtk", config.GTK_API)
gi.require_version("WebKit2", config.WEBKIT_API)
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango, WebKit2

from .bookmarks import OTHER_ID, BookmarkStore
from . import favicons
from .utils import normalize_url

_ROOT = Path(__file__).resolve().parent.parent
_ASSETS = _ROOT / "assets"
_LOGO_CANDIDATES = (
    _ASSETS / "logo.png",
    _ASSETS / "logo.jpg",
    _ASSETS / "icons" / "logo.png",
    _ROOT / "web_surfer_logo.jpg",
    Path.home() / "src" / "web-surfer" / "assets" / "logo.png",
)


class BookmarkEditor(Gtk.Dialog):
    def __init__(self, parent, store: BookmarkStore, url: str, title: str, editing=False):
        heading = "Edit bookmark" if editing else "Add bookmark"
        super().__init__(title=heading, transient_for=parent, flags=0)
        self.store = store
        self.url = url
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        if editing:
            self.add_button("Delete", Gtk.ResponseType.REJECT)
        self.add_button("Save", Gtk.ResponseType.OK)
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_modal(True)
        self.set_default_size(420, 200)

        grid = Gtk.Grid(column_spacing=8, row_spacing=8, margin=12)
        self.get_content_area().pack_start(grid, True, True, 0)

        grid.attach(Gtk.Label(label="Name", xalign=0), 0, 0, 1, 1)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_text(title or url)
        self.name_entry.set_hexpand(True)
        grid.attach(self.name_entry, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Folder", xalign=0), 0, 1, 1, 1)
        self.folder_combo = Gtk.ComboBoxText()
        self._refill_folders()
        pair = store.find_with_folder(url)
        current_id = pair[0]["id"] if pair else OTHER_ID
        self.folder_combo.set_active_id(current_id)
        grid.attach(self.folder_combo, 1, 1, 1, 1)

        new_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.new_folder_entry = Gtk.Entry()
        self.new_folder_entry.set_placeholder_text("New folder name")
        new_btn = Gtk.Button(label="Add folder")
        new_btn.connect("clicked", self.on_add_folder)
        new_row.pack_start(self.new_folder_entry, True, True, 0)
        new_row.pack_start(new_btn, False, False, 0)
        grid.attach(new_row, 1, 2, 1, 1)

        self.bar_check = Gtk.CheckButton(label="Show this bookmark on the bookmarks bar")
        current_item = pair[1] if pair else None
        self.bar_check.set_active(bool(current_item and current_item.get("on_bar")))
        grid.attach(self.bar_check, 1, 3, 1, 1)

        self.folder_bar_check = Gtk.CheckButton(label="Show this folder on the bookmarks bar")
        folder = pair[0] if pair else None
        self.folder_bar_check.set_active(bool(folder and folder.get("on_bar")))
        self.folder_combo.connect("changed", self._on_folder_changed)
        self._on_folder_changed(self.folder_combo)
        grid.attach(self.folder_bar_check, 1, 4, 1, 1)
        self.show_all()

    def _refill_folders(self):
        self.folder_combo.remove_all()
        for folder in self.store.folders:
            self.folder_combo.append(folder["id"], folder["name"])

    def on_add_folder(self, _btn):
        name = self.new_folder_entry.get_text().strip()
        if not name:
            return
        folder = self.store.add_folder(name)
        self._refill_folders()
        self.folder_combo.set_active_id(folder["id"])
        self.new_folder_entry.set_text("")

    def _on_folder_changed(self, combo):
        folder_id = combo.get_active_id()
        folder = self.store.folder_by_id(folder_id) if folder_id else None
        can_pin = bool(folder and folder.get("id") != OTHER_ID)
        self.folder_bar_check.set_sensitive(can_pin)
        if folder and can_pin:
            self.folder_bar_check.set_active(bool(folder.get("on_bar")))
        elif not can_pin:
            self.folder_bar_check.set_active(False)

    def values(self):
        folder_id = self.folder_combo.get_active_id() or OTHER_ID
        return (
            self.name_entry.get_text().strip(),
            folder_id,
            self.bar_check.get_active(),
            self.folder_bar_check.get_active(),
        )


class BrowserWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=config.APP_NAME)
        self.set_default_size(config.DEFAULT_WIDTH, config.DEFAULT_HEIGHT)
        self.set_resizable(True)
        self.connect("destroy", Gtk.main_quit)
        self.connect("window-state-event", self.on_window_state)
        self.connect("key-press-event", self.on_key_press)

        self.bookmarks = BookmarkStore()
        self._tabs = []
        self._active = None

        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings is not None:
            gtk_settings.set_property(
                "gtk-decoration-layout", "menu:minimize,maximize,close"
            )

        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_decoration_layout(":minimize,maximize,close")
        header.set_custom_title(Gtk.Label(label=""))
        self._header = header
        self.set_titlebar(header)
        self._set_logo(header)

        self._apply_tab_css()

        self.tab_strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.tab_strip.set_hexpand(False)
        self.tab_strip.set_valign(Gtk.Align.CENTER)
        header.pack_start(self.tab_strip)

        self.new_tab_btn = Gtk.Button.new_from_icon_name("list-add", Gtk.IconSize.MENU)
        self.new_tab_btn.set_tooltip_text("New tab (Ctrl+T)")
        self.new_tab_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.new_tab_btn.set_valign(Gtk.Align.CENTER)
        self.new_tab_btn.connect("clicked", lambda *_: self.add_tab())
        self.tab_strip.pack_end(self.new_tab_btn, False, False, 0)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.pack_start(spacer)

        self.context = WebKit2.WebContext.get_default()
        try:
            self.context.set_favicon_database_directory(str(favicons.favicon_dir()))
        except Exception:
            pass
        self.content_manager = WebKit2.UserContentManager()

        overlay = Gtk.Overlay()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        overlay.add(vbox)
        self._ghost_fixed = Gtk.Fixed()
        overlay.add_overlay(self._ghost_fixed)
        try:
            overlay.set_overlay_pass_through(self._ghost_fixed, True)
        except Exception:
            pass
        self.add(overlay)

        nav_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        nav_bar.set_margin_start(5)
        nav_bar.set_margin_end(5)
        nav_bar.set_margin_top(4)
        nav_bar.set_margin_bottom(4)
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
        self.url_entry.connect("button-press-event", self.on_url_button_press)
        self.url_entry.connect("focus-in-event", self.on_url_focus_in)
        nav_bar.pack_start(self.url_entry, True, True, 0)

        self.bookmark_btn = Gtk.Button.new_from_icon_name("non-starred", Gtk.IconSize.BUTTON)
        self.bookmark_btn.set_tooltip_text("Bookmark this page")
        self.bookmark_btn.connect("clicked", self.on_bookmark_clicked)
        nav_bar.pack_start(self.bookmark_btn, False, False, 0)

        self._bm_drag = None
        self._ghost = None
        self._drop_line = Gtk.Box()
        self._drop_line.set_size_request(2, 20)
        self._drop_line.get_style_context().add_class("ws-drop-line")
        self._list_drop_line = Gtk.Box()
        self._list_drop_line.set_size_request(-1, 2)
        self._list_drop_line.get_style_context().add_class("ws-drop-line")
        self._flyout = None
        self._flyout_row = None
        self._flyout_timeout = None
        self.bookmarks_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        list_scroll = Gtk.ScrolledWindow()
        list_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_scroll.add(self.bookmarks_list)
        list_scroll.set_size_request(360, 420)
        list_scroll.set_min_content_width(360)
        list_scroll.set_min_content_height(420)
        self._list_ghost_fixed = Gtk.Fixed()
        list_overlay = Gtk.Overlay()
        list_overlay.add(list_scroll)
        list_overlay.add_overlay(self._list_ghost_fixed)
        try:
            list_overlay.set_overlay_pass_through(self._list_ghost_fixed, True)
        except Exception:
            pass
        self.bookmarks_popover = Gtk.Popover()
        try:
            self.bookmarks_popover.set_constrain_to(Gtk.PopoverConstraint.NONE)
        except Exception:
            pass
        self.bookmarks_popover.add(list_overlay)
        self.bookmarks_popover.connect("closed", lambda *_: self._hide_flyout())
        list_overlay.show_all()
        self.bookmarks_btn = Gtk.MenuButton()
        self.bookmarks_btn.set_tooltip_text("Bookmarks")
        self.bookmarks_btn.set_popover(self.bookmarks_popover)
        self.bookmarks_btn.set_image(
            Gtk.Image.new_from_icon_name("user-bookmarks", Gtk.IconSize.BUTTON)
        )
        nav_bar.pack_start(self.bookmarks_btn, False, False, 0)

        self.bar_toggle = Gtk.ToggleButton()
        self.bar_toggle.set_image(
            Gtk.Image.new_from_icon_name("view-list", Gtk.IconSize.BUTTON)
        )
        self.bar_toggle.set_tooltip_text("Show bookmarks bar")
        self.bar_toggle.set_active(self.bookmarks.bar_visible)
        self.bar_toggle.connect("toggled", self.on_toggle_bar)
        nav_bar.pack_start(self.bar_toggle, False, False, 0)

        self.bookmarks_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.bookmarks_bar.set_margin_start(8)
        self.bookmarks_bar.set_margin_end(8)
        self.bookmarks_bar.set_margin_top(0)
        self.bookmarks_bar.set_margin_bottom(0)
        self.bookmarks_bar.set_size_request(-1, 28)
        self.bookmarks_bar.set_valign(Gtk.Align.CENTER)
        self.bar_revealer = Gtk.Revealer()
        self.bar_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.bar_revealer.add(self.bookmarks_bar)
        self.bar_revealer.set_reveal_child(self.bookmarks.bar_visible)
        vbox.pack_start(self.bar_revealer, False, False, 0)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        vbox.pack_start(self.stack, True, True, 0)

        self._rebuild_bookmarks_menu()
        self._rebuild_bookmarks_bar()

    @property
    def webview(self):
        return None if self._active is None else self._active["webview"]

    def add_tab(self, url=None, background=False, related=None):
        if related is not None:
            webview = WebKit2.WebView.new_with_related_view(related)
        else:
            webview = WebKit2.WebView.new_with_user_content_manager(self.content_manager)
        settings = webview.get_settings()
        settings.set_enable_developer_extras(True)
        settings.set_enable_javascript(True)
        webview.connect("load-changed", self.on_load_changed)
        webview.connect("notify::uri", self.on_uri_changed)
        webview.connect("notify::title", self.on_title_changed)
        webview.connect("notify::favicon", self.on_favicon)
        webview.connect("decide-policy", self.on_decide_policy)
        webview.connect("create", self.on_create_webview)

        scrolled = Gtk.ScrolledWindow()
        scrolled.add(webview)
        name = f"tab-{id(webview)}"
        self.stack.add_named(scrolled, name)
        scrolled.show_all()

        icon = Gtk.Image.new_from_icon_name("text-html", Gtk.IconSize.MENU)
        icon.set_pixel_size(16)
        label = Gtk.Label(label="New Tab")
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(16)
        label.set_xalign(0)

        close_btn = Gtk.Button.new_from_icon_name("window-close", Gtk.IconSize.MENU)
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.set_tooltip_text("Close tab")
        close_img = close_btn.get_image()
        if close_img is not None:
            close_img.set_pixel_size(12)

        inner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        inner.set_valign(Gtk.Align.CENTER)
        inner.pack_start(icon, False, False, 0)
        inner.pack_start(label, True, True, 0)
        inner.pack_start(close_btn, False, False, 0)
        inner.show_all()

        chrome = Gtk.EventBox()
        chrome.set_visible_window(True)
        chrome.get_style_context().add_class("ws-tab")
        self._bind_hover(chrome)
        chrome.add(inner)
        chrome.set_size_request(140, 28)
        chrome.set_valign(Gtk.Align.CENTER)
        chrome.show_all()
        self.tab_strip.pack_start(chrome, False, False, 0)
        self.tab_strip.reorder_child(self.new_tab_btn, -1)

        tab = {
            "page": scrolled,
            "webview": webview,
            "button": chrome,
            "label": label,
            "icon": icon,
            "name": name,
        }
        self._tabs.append(tab)
        chrome.connect("button-press-event", self._on_tab_press, tab)
        close_btn.connect("button-press-event", self._on_close_press, tab)

        if related is None:
            target = url if url else config.HOMEPAGE
            self._load_in_view(webview, target if url else config.HOMEPAGE)
        if not background:
            self._select_tab(tab)
        return webview

    def _on_tab_press(self, _widget, event, tab):
        if event.button == 1:
            self._select_tab(tab)
            return True
        if event.button == 2:
            self.close_tab(tab)
            return True
        return False

    def _on_close_press(self, _widget, event, tab):
        if event.button == 1:
            self.close_tab(tab)
            return True
        return False

    def _select_tab(self, tab):
        self._active = tab
        self.stack.set_visible_child(tab["page"])
        for other in self._tabs:
            ctx = other["button"].get_style_context()
            if other is tab:
                ctx.add_class("ws-tab-active")
            else:
                ctx.remove_class("ws-tab-active")
        view = tab["webview"]
        uri = self._display_uri(view)
        self.url_entry.set_text(uri)
        self._update_nav_buttons(view)
        self._update_bookmark_button(view.get_uri() or "")
        title = view.get_title() or uri or "New Tab"
        self.set_title(f"{title} — {config.APP_NAME}")

    def close_tab(self, tab):
        if tab not in self._tabs:
            return
        idx = self._tabs.index(tab)
        self._tabs.remove(tab)
        self.tab_strip.remove(tab["button"])
        self.stack.remove(tab["page"])
        if not self._tabs:
            self.destroy()
            return
        next_tab = self._tabs[min(idx, len(self._tabs) - 1)]
        self._select_tab(next_tab)

    def close_current_tab(self):
        if self._active is not None:
            self.close_tab(self._active)

    def load_url(self, url: str):
        view = self.webview
        if view is None:
            self.add_tab(url)
            return
        self._load_in_view(view, url)

    def _is_home(self, url: str) -> bool:
        text = (url or "").strip().lower()
        return text in ("", "about:blank", config.HOMEPAGE, "websurfer:home")

    def _home_html(self) -> str:
        logo = self._find_logo()
        img = ""
        if logo is not None and logo.is_file():
            mime = "image/png" if logo.suffix.lower() == ".png" else "image/jpeg"
            payload = base64.b64encode(logo.read_bytes()).decode("ascii")
            img = f'<img src="data:{mime};base64,{payload}" alt="Web Surfer">'
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>New Tab</title>
<style>
  html, body {{
    height: 100%;
    margin: 0;
    background: #f4f4f4;
  }}
  body {{
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  img {{
    max-width: min(52vw, 560px);
    max-height: 52vh;
    width: auto;
    height: auto;
    filter: grayscale(1);
    opacity: 0.3;
    user-select: none;
    pointer-events: none;
  }}
</style></head>
<body>{img}</body></html>
"""

    def _load_in_view(self, webview, url: str):
        if self._is_home(url):
            webview.load_html(self._home_html(), "about:blank")
            return
        webview.load_uri(normalize_url(url))

    def _display_uri(self, webview) -> str:
        uri = webview.get_uri() or ""
        if self._is_home(uri):
            return ""
        return uri

    def on_url_enter(self, entry):
        self.load_url(entry.get_text())

    def on_url_focus_in(self, entry, _event):
        self._hide_flyout()
        return False

    def _url_index_at_x(self, entry, x):
        layout = entry.get_layout()
        if layout is None:
            return entry.get_text_length()
        lx, _ly = entry.get_layout_offsets()
        index, _trailing = layout.xy_to_index(int((x - lx) * Pango.SCALE), 0)
        text = entry.get_chars(0, -1)
        try:
            return len(text.encode("utf-8")[:index].decode("utf-8"))
        except Exception:
            return min(index, len(text))

    def on_url_button_press(self, entry, event):
        if event.button != 1:
            return False
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            pos = self._url_index_at_x(entry, event.x)
            entry.grab_focus_without_selecting()
            entry.select_region(pos, pos)
            entry.set_position(pos)
            return True
        if event.type == Gdk.EventType.BUTTON_PRESS and not entry.has_focus():
            entry.grab_focus()
            GLib.idle_add(entry.select_region, 0, -1)
            return True
        return False

    def on_back(self, _button):
        view = self.webview
        if view is not None and view.can_go_back():
            view.go_back()

    def on_forward(self, _button):
        view = self.webview
        if view is not None and view.can_go_forward():
            view.go_forward()

    def on_reload(self, _button):
        view = self.webview
        if view is not None:
            view.reload()

    def _tab_for_view(self, webview):
        for tab in self._tabs:
            if tab["webview"] is webview:
                return tab
        return None

    def on_load_changed(self, webview, load_event):
        tab = self._tab_for_view(webview)
        if tab:
            self._sync_tab_chrome(tab)
        if webview is not self.webview:
            return
        if load_event == WebKit2.LoadEvent.FINISHED:
            self.url_entry.set_text(self._display_uri(webview))
            self._update_nav_buttons(webview)
            self._update_bookmark_button(webview.get_uri() or "")

    def on_uri_changed(self, webview, _pspec):
        tab = self._tab_for_view(webview)
        if tab:
            self._sync_tab_chrome(tab)
        if webview is not self.webview:
            return
        self.url_entry.set_text(self._display_uri(webview))
        self._update_nav_buttons(webview)
        self._update_bookmark_button(webview.get_uri() or "")

    def on_title_changed(self, webview, _pspec):
        tab = self._tab_for_view(webview)
        if tab:
            self._sync_tab_chrome(tab)

    def on_favicon(self, webview, _pspec):
        tab = self._tab_for_view(webview)
        if not tab:
            return
        surface = webview.get_favicon()
        uri = webview.get_uri() or ""
        if surface is not None and uri:
            favicons.save_surface(uri, surface)
        self._apply_favicon(tab, uri, surface)
        self._rebuild_bookmarks_menu()
        self._rebuild_bookmarks_bar()

    def _apply_favicon(self, tab, uri, surface=None):
        pixbuf = favicons.pixbuf_from_surface(surface, 16) if surface is not None else None
        if pixbuf is None and uri:
            pixbuf = favicons.load_pixbuf(uri, 16)
        if pixbuf is not None:
            tab["icon"].set_from_pixbuf(pixbuf)
            tab["icon"].set_pixel_size(16)
        else:
            tab["icon"].set_from_icon_name("text-html", Gtk.IconSize.MENU)
            tab["icon"].set_pixel_size(16)

    def _apply_tab_css(self):
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            headerbar { min-height: 36px; padding: 2px 6px; }
            headerbar .ws-tab {
                padding: 0 6px;
                min-height: 28px;
                min-width: 140px;
                border-radius: 4px;
            }
            headerbar .ws-tab-active {
                background-color: alpha(currentColor, 0.12);
            }
            .ws-tab, .ws-bar-chip, .ws-list-row {
                border-radius: 4px;
                background-color: transparent;
            }
            .ws-hover {
                background-color: rgba(127, 127, 127, 0.22);
            }
            .ws-drop-line {
                background-color: #3584e4;
                min-width: 2px;
                min-height: 2px;
            }
            .ws-ghost {
                background-color: alpha(@theme_bg_color, 0.92);
                border: 1px solid alpha(@theme_fg_color, 0.35);
                border-radius: 4px;
                padding: 2px 8px;
            }
            .ws-bar-chip {
                min-height: 28px;
                padding: 0 8px;
            }
            .ws-drop-folder {
                background-color: alpha(#3584e4, 0.22);
                border-radius: 3px;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _sync_tab_chrome(self, tab):
        view = tab["webview"]
        title = (view.get_title() or "").strip()
        uri = view.get_uri() or ""
        if self._is_home(uri):
            title = "New Tab"
        elif not title:
            title = self._pretty_host(uri) or "New Tab"
        tab["label"].set_text(title)
        tab["label"].set_tooltip_text(title)
        if tab is self._active:
            self.set_title(f"{title} — {config.APP_NAME}")
        self._apply_favicon(tab, uri, view.get_favicon())

    def _pretty_host(self, uri: str) -> str:
        if not uri:
            return ""
        text = uri
        for prefix in ("https://", "http://"):
            if text.startswith(prefix):
                text = text[len(prefix):]
                break
        text = text.split("/")[0]
        if text.startswith("www."):
            text = text[4:]
        return text

    def on_create_webview(self, webview, _navigation_action):
        # Must return a related view. A brand-new WebView trips a WebKit
        # WindowFeatures assertion (optional not engaged) and aborts.
        return self.add_tab(related=webview)

    def on_decide_policy(self, _webview, decision, decision_type):
        return False

    def on_bookmark_clicked(self, _button):
        view = self.webview
        if view is None:
            return
        uri = view.get_uri() or ""
        if not uri:
            return
        title = view.get_title() or self._pretty_host(uri) or uri
        editing = self.bookmarks.find(uri) is not None
        dialog = BookmarkEditor(self, self.bookmarks, uri, title, editing=editing)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name, folder_id, on_bar, folder_on_bar = dialog.values()
            self.bookmarks.add(
                uri,
                name,
                folder_id=folder_id,
                on_bar=on_bar,
                folder_on_bar=folder_on_bar,
            )
        elif response == Gtk.ResponseType.REJECT:
            self.bookmarks.remove(uri)
        dialog.destroy()
        self._update_bookmark_button(uri)
        self._rebuild_bookmarks_menu()
        self._rebuild_bookmarks_bar()

    def on_toggle_bar(self, button):
        self.bookmarks.bar_visible = button.get_active()
        self.bookmarks.save()
        self.bar_revealer.set_reveal_child(self.bookmarks.bar_visible)

    def _update_bookmark_button(self, uri: str):
        starred = bool(uri and self.bookmarks.find(uri))
        icon = "starred" if starred else "non-starred"
        self.bookmark_btn.set_image(
            Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        )
        self.bookmark_btn.set_tooltip_text(
            "Edit bookmark" if starred else "Bookmark this page"
        )

    def _favicon_image(self, url: str) -> Gtk.Image:
        pixbuf = favicons.load_pixbuf(url, 16)
        if pixbuf is not None:
            return Gtk.Image.new_from_pixbuf(pixbuf)
        return Gtk.Image.new_from_icon_name("text-html", Gtk.IconSize.MENU)

    def _apply_bookmark_drop(self, src_key: str, dest_key: str, after=False) -> bool:
        if not src_key or not dest_key:
            return False
        if src_key.startswith("bar:") and dest_key.startswith("bar:"):
            return self.bookmarks.reorder_bar(src_key[4:], dest_key[4:], after=after)
        if src_key.startswith("mf:") and dest_key.startswith("mf:"):
            return self.bookmarks.reorder_folders(src_key[3:], dest_key[3:], after=after)
        if src_key.startswith("mi:") and dest_key.startswith("mf:"):
            try:
                src_url = src_key.split(":", 2)[2]
            except IndexError:
                return False
            return self.bookmarks.move(src_url, dest_key[3:])
        if src_key.startswith("mi:") and dest_key.startswith("mi:"):
            try:
                _p, src_folder, src_url = src_key.split(":", 2)
                _p, dest_folder, dest_url = dest_key.split(":", 2)
            except ValueError:
                return False
            if src_folder != dest_folder:
                self.bookmarks.move(src_url, dest_folder)
            return self.bookmarks.reorder_item(
                dest_folder, src_url, dest_url, after=after
            )
        return False

    def _bind_hover(self, widget):
        def _enter(_w, event):
            if event.detail == Gdk.NotifyType.INFERIOR:
                return False
            widget.get_style_context().add_class("ws-hover")
            return False

        def _leave(_w, event):
            if event.detail == Gdk.NotifyType.INFERIOR:
                return False
            widget.get_style_context().remove_class("ws-hover")
            return False

        widget.connect("enter-notify-event", _enter)
        widget.connect("leave-notify-event", _leave)

    def _bind_reorder(self, widget, key, group, on_click=None):
        widget.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON_MOTION_MASK
        )
        self._bind_hover(widget)
        widget.connect("button-press-event", self._on_bm_press, key, group)
        widget.connect("motion-notify-event", self._on_bm_motion, key, group)
        widget.connect("button-release-event", self._on_bm_release, key, group, on_click)

    def _on_bm_press(self, widget, event, key, group):
        if event.button != 1:
            return False
        title = ""
        child = widget.get_child() if hasattr(widget, "get_child") else None
        if child is not None:
            for kid in getattr(child, "get_children", lambda: [])():
                if isinstance(kid, Gtk.Label):
                    title = kid.get_text()
                    break
        self._bm_drag = {
            "key": key,
            "group": group,
            "widget": widget,
            "title": title,
            "x": event.x_root,
            "y": event.y_root,
            "moved": False,
            "dest": None,
            "after": False,
        }
        return False

    def _ghost_layer(self, key=""):
        if key.startswith("mi:") or key.startswith("mf:"):
            return self._list_ghost_fixed
        return self._ghost_fixed

    def _ensure_ghost(self, title, key=""):
        if self._ghost is not None:
            return
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.get_style_context().add_class("ws-ghost")
        box.pack_start(Gtk.Label(label=title or "Bookmark"), False, False, 0)
        box.set_opacity(0.9)
        box.show_all()
        layer = self._ghost_layer(key)
        layer.put(box, 0, 0)
        self._ghost = box
        self._ghost_layer_widget = layer

    def _move_ghost(self, x_root, y_root):
        if self._ghost is None:
            return
        layer = getattr(self, "_ghost_layer_widget", self._ghost_fixed)
        gdkwin = layer.get_window() or self.get_window()
        if gdkwin is not None:
            ox, oy = gdkwin.get_root_coords(0, 0)
            x = int(x_root - ox + 12)
            y = int(y_root - oy + 8)
        else:
            x, y = int(x_root + 12), int(y_root + 8)
        layer.move(self._ghost, max(0, x), max(0, y))

    def _hide_ghost(self):
        if self._ghost is not None:
            layer = getattr(self, "_ghost_layer_widget", self._ghost_fixed)
            layer.remove(self._ghost)
            self._ghost = None
            self._ghost_layer_widget = None
        for line in (self._drop_line, self._list_drop_line):
            if line.get_parent() is not None:
                line.get_parent().remove(line)
        self._clear_folder_drop_style()

    def _clear_folder_drop_style(self):
        for child in list(self.bookmarks_list.get_children()):
            child.get_style_context().remove_class("ws-drop-folder")

    def _place_drop_line(self, index):
        parent = self.bookmarks_bar
        if self._drop_line.get_parent() is parent:
            parent.remove(self._drop_line)
        parent.pack_start(self._drop_line, False, False, 0)
        parent.reorder_child(self._drop_line, max(0, index))
        self._drop_line.show()

    def _place_list_drop_line(self, dest_widget, after):
        parent = dest_widget.get_parent()
        if parent is None:
            return
        if self._list_drop_line.get_parent() is not None:
            self._list_drop_line.get_parent().remove(self._list_drop_line)
        children = [c for c in parent.get_children() if c is not self._list_drop_line]
        try:
            idx = children.index(dest_widget)
        except ValueError:
            return
        if after:
            idx += 1
        parent.pack_start(self._list_drop_line, False, False, 0)
        parent.reorder_child(self._list_drop_line, idx)
        self._list_drop_line.show()

    def _on_bm_motion(self, widget, event, key, group):
        drag = self._bm_drag
        if not drag or drag.get("key") != key:
            return False
        if abs(event.x_root - drag["x"]) + abs(event.y_root - drag["y"]) > 8:
            drag["moved"] = True
            self._ensure_ghost(drag.get("title"), key)
            self._move_ghost(event.x_root, event.y_root)
            vertical = not str(key).startswith("bar:")
            hit = self._hit_reorder_side(
                event.x_root, event.y_root, group, vertical=vertical
            )
            self._clear_folder_drop_style()
            if hit:
                dest, after, idx, dest_widget = hit
                drag["dest"] = dest
                drag["after"] = after
                if str(key).startswith("bar:"):
                    self._place_drop_line(idx + (1 if after else 0))
                elif key.startswith("mi:") and dest.startswith("mf:"):
                    drag["after"] = False
                    dest_widget.get_style_context().add_class("ws-drop-folder")
                    if self._list_drop_line.get_parent() is not None:
                        self._list_drop_line.get_parent().remove(self._list_drop_line)
                else:
                    self._place_list_drop_line(dest_widget, after)
            try:
                widget.get_window().set_cursor(
                    Gdk.Cursor.new_from_name(widget.get_display(), "grabbing")
                )
            except Exception:
                pass
        return bool(drag.get("moved"))

    def _on_bm_release(self, widget, event, key, group, on_click):
        drag = self._bm_drag
        self._bm_drag = None
        self._hide_ghost()
        try:
            widget.get_window().set_cursor(None)
        except Exception:
            pass
        if drag and drag.get("moved"):
            dest = drag.get("dest")
            if dest and self._apply_bookmark_drop(key, dest, after=drag.get("after")):
                self._rebuild_bookmarks_menu()
                self._rebuild_bookmarks_bar()
            return True
        if on_click:
            on_click()
        return False

    def _hit_reorder_side(self, x_root, y_root, group, vertical=False):
        for idx, (key, widget) in enumerate(group):
            win = widget.get_window()
            if win is None:
                continue
            alloc = widget.get_allocation()
            if widget.get_has_window():
                ox, oy = win.get_root_coords(0, 0)
            else:
                ox, oy = win.get_root_coords(alloc.x, alloc.y)
            if ox <= x_root <= ox + alloc.width and oy - 8 <= y_root <= oy + alloc.height + 8:
                if vertical:
                    after = y_root >= oy + alloc.height / 2
                else:
                    after = x_root >= ox + alloc.width / 2
                return key, after, idx, widget
        return None

    def _list_row(self, icon_widget, title, key, group, on_click=None):
        row = Gtk.EventBox()
        row.set_visible_window(True)
        row.get_style_context().add_class("ws-list-row")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.pack_start(icon_widget, False, False, 0)
        lbl = Gtk.Label(label=title, xalign=0)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        box.pack_start(lbl, True, True, 0)
        row.add(box)
        self._bind_reorder(row, key, group, on_click=on_click)
        group.append((key, row))
        return row

    def _pointer_in(self, widget):
        if widget is None:
            return False
        win = widget.get_realized() and widget.get_window()
        if not win:
            return False
        try:
            device = widget.get_display().get_default_seat().get_pointer()
            _w, x, y, _mask = win.get_device_position(device)
        except Exception:
            return False
        alloc = widget.get_allocation()
        if widget.get_has_window():
            return 0 <= x <= alloc.width and 0 <= y <= alloc.height
        return alloc.x <= x <= alloc.x + alloc.width and alloc.y <= y <= alloc.y + alloc.height

    def _hide_flyout(self):
        if self._flyout_timeout:
            try:
                GLib.source_remove(self._flyout_timeout)
            except Exception:
                pass
            self._flyout_timeout = None
        if self._flyout is not None:
            self._flyout.destroy()
            self._flyout = None
        self._flyout_row = None

    def _schedule_hide_flyout(self):
        def _do():
            self._flyout_timeout = None
            if self._pointer_in(getattr(self, "_flyout_box", None)) or self._pointer_in(
                self._flyout_row
            ):
                return False
            self._hide_flyout()
            return False
        if self._flyout_timeout:
            GLib.source_remove(self._flyout_timeout)
        self._flyout_timeout = GLib.timeout_add(180, _do)

    def _is_crossing_child(self, event):
        return event.detail in (
            Gdk.NotifyType.INFERIOR,
            Gdk.NotifyType.VIRTUAL,
            Gdk.NotifyType.ANCESTOR,
        )

    def _show_folder_flyout(self, row, folder):
        if self._bm_drag and self._bm_drag.get("moved"):
            return
        if self._flyout is not None and getattr(self._flyout, "_folder_id", None) == folder.get("id"):
            self._cancel_hide_flyout()
            return
        self._hide_flyout()
        pop = Gtk.Popover()
        pop.set_relative_to(row)
        pop.set_position(Gtk.PositionType.RIGHT)
        pop.set_modal(False)
        pop._folder_id = folder.get("id")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.set_valign(Gtk.Align.START)
        items = folder.get("items") or []
        height = max(28, 28 * max(1, len(items)))
        box.set_size_request(240, height)
        if not items:
            lab = Gtk.Label(label="Empty", xalign=0)
            lab.set_margin_start(8)
            lab.set_margin_top(4)
            lab.set_margin_bottom(4)
            box.pack_start(lab, False, False, 0)
        else:
            group = []
            for item in items:
                url = item.get("url")
                box.pack_start(
                    self._list_row(
                        self._favicon_image(url),
                        item.get("title") or url,
                        f"mi:{folder['id']}:{url}",
                        group,
                        on_click=lambda u=url: self._open_bookmark(u),
                    ),
                    False,
                    False,
                    0,
                )
        pop.add(box)
        pop.connect(
            "enter-notify-event",
            lambda _w, e: (self._cancel_hide_flyout() or self._is_crossing_child(e)) and False,
        )
        pop.connect(
            "leave-notify-event",
            lambda _w, e: False if self._is_crossing_child(e) else self._schedule_hide_flyout() or False,
        )
        pop.show_all()
        self._flyout = pop
        self._flyout_box = box
        self._flyout_row = row
        if not items:
            GLib.timeout_add(50, self._schedule_hide_flyout)

    def _cancel_hide_flyout(self):
        if self._flyout_timeout:
            GLib.source_remove(self._flyout_timeout)
            self._flyout_timeout = None

    def _rebuild_bookmarks_menu(self):
        self._hide_flyout()
        for child in list(self.bookmarks_list.get_children()):
            self.bookmarks_list.remove(child)
        list_group = []
        other = self.bookmarks.folder_by_id(OTHER_ID)
        named = self.bookmarks.user_folders()
        has_anything = False
        for folder in named:
            has_anything = True
            row = Gtk.EventBox()
            row.set_visible_window(True)
            row.get_style_context().add_class("ws-list-row")
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_margin_start(8)
            box.set_margin_end(8)
            box.set_margin_top(6)
            box.set_margin_bottom(6)
            box.pack_start(
                Gtk.Image.new_from_icon_name("folder", Gtk.IconSize.MENU),
                False,
                False,
                0,
            )
            box.pack_start(
                Gtk.Label(label=folder.get("name") or "Folder", xalign=0),
                True,
                True,
                0,
            )
            box.pack_start(
                Gtk.Image.new_from_icon_name("go-next", Gtk.IconSize.MENU),
                False,
                False,
                0,
            )
            row.add(box)
            self._bind_reorder(row, f"mf:{folder['id']}", list_group)
            list_group.append((f"mf:{folder['id']}", row))
            row.connect(
                "enter-notify-event",
                lambda w, e, f=folder: False
                if e.detail == Gdk.NotifyType.INFERIOR
                else self._show_folder_flyout(w, f) or False,
            )
            row.connect(
                "leave-notify-event",
                lambda _w, e, f=folder: False
                if self._is_crossing_child(e)
                else (
                    self._hide_flyout()
                    if not (f.get("items") or [])
                    else self._schedule_hide_flyout()
                )
                or False,
            )
            self.bookmarks_list.pack_start(row, False, False, 0)
        if other and other.get("items"):
            if named:
                self.bookmarks_list.pack_start(Gtk.Separator(), False, False, 4)
            for item in other["items"]:
                has_anything = True
                url = item.get("url")
                self.bookmarks_list.pack_start(
                    self._list_row(
                        self._favicon_image(url),
                        item.get("title") or url,
                        f"mi:{OTHER_ID}:{url}",
                        list_group,
                        on_click=lambda u=url: self._open_bookmark(u),
                    ),
                    False,
                    False,
                    0,
                )
        if not has_anything:
            empty = Gtk.Label(label="No bookmarks yet")
            empty.set_margin_top(8)
            empty.set_margin_bottom(8)
            self.bookmarks_list.pack_start(empty, False, False, 0)
        self.bookmarks_list.show_all()

    def _open_bookmark(self, url):
        self.bookmarks_popover.popdown()
        self.load_url(url)

    def _popup_bar_folder(self, widget, folder):
        menu = Gtk.Menu()
        items = folder.get("items") or []
        if not items:
            empty = Gtk.MenuItem(label="Empty")
            empty.set_sensitive(False)
            menu.append(empty)
        else:
            for item in items:
                url = item.get("url")
                mi = Gtk.MenuItem(label=item.get("title") or url)
                mi.connect("activate", lambda _m, u=url: self.load_url(u))
                menu.append(mi)
        menu.show_all()
        menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)

    def _bar_chip(self, icon, title, key, group, on_click):
        chip = Gtk.EventBox()
        chip.set_visible_window(True)
        chip.get_style_context().add_class("ws-bar-chip")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(0)
        box.set_margin_end(0)
        box.set_margin_top(0)
        box.set_margin_bottom(0)
        box.get_style_context().add_class("ws-bar-chip")
        box.pack_start(icon, False, False, 0)
        lbl = Gtk.Label(label=title)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
        lbl.set_max_width_chars(18)
        box.pack_start(lbl, False, False, 0)
        chip.add(box)
        chip.set_tooltip_text(title)
        self._bind_reorder(chip, key, group, on_click=on_click)
        group.append((key, chip))
        return chip

    def _rebuild_bookmarks_bar(self):
        for child in list(self.bookmarks_bar.get_children()):
            self.bookmarks_bar.remove(child)
        entries = self.bookmarks.bar_entries()
        if not entries:
            hint = Gtk.Label(label="Pin a bookmark or folder to this bar from the star dialog.")
            hint.get_style_context().add_class("dim-label")
            self.bookmarks_bar.pack_start(hint, False, False, 0)
            self.bookmarks_bar.show_all()
            return
        group = []
        for key, kind, payload in entries:
            if kind == "folder":
                folder = payload
                chip = self._bar_chip(
                    Gtk.Image.new_from_icon_name("folder", Gtk.IconSize.MENU),
                    folder.get("name") or "Folder",
                    f"bar:{key}",
                    group,
                    on_click=lambda w=None, f=folder: self._popup_bar_folder(
                        self.bookmarks_bar, f
                    ),
                )
                self.bookmarks_bar.pack_start(chip, False, False, 0)
            else:
                item = payload
                url = item.get("url")
                chip = self._bar_chip(
                    self._favicon_image(url),
                    item.get("title") or url,
                    f"bar:{key}",
                    group,
                    on_click=lambda u=url: self.load_url(u),
                )
                self.bookmarks_bar.pack_start(chip, False, False, 0)
        self.bookmarks_bar.show_all()

    def _update_nav_buttons(self, view=None):
        view = view if view is not None else self.webview
        self.back_btn.set_sensitive(bool(view and view.can_go_back()))
        self.forward_btn.set_sensitive(bool(view and view.can_go_forward()))

    def on_key_press(self, _window, event):
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        if not ctrl:
            return False
        key = event.keyval
        if key in (Gdk.KEY_t, Gdk.KEY_T):
            self.add_tab()
            return True
        if key in (Gdk.KEY_w, Gdk.KEY_W):
            self.close_current_tab()
            return True
        if key in (Gdk.KEY_l, Gdk.KEY_L):
            self.url_entry.grab_focus()
            self.url_entry.select_region(0, -1)
            return True
        if key in (Gdk.KEY_d, Gdk.KEY_D):
            self.on_bookmark_clicked(None)
            return True
        if key in (Gdk.KEY_b, Gdk.KEY_B):
            self.bar_toggle.set_active(not self.bar_toggle.get_active())
            return True
        n = len(self._tabs)
        if n and key in (Gdk.KEY_Tab, Gdk.KEY_ISO_Left_Tab, Gdk.KEY_Page_Down, Gdk.KEY_Page_Up):
            shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK) or key == Gdk.KEY_Page_Up
            cur = self._tabs.index(self._active) if self._active in self._tabs else 0
            nxt = (cur + (-1 if shift else 1)) % n
            self._select_tab(self._tabs[nxt])
            return True
        return False

    def _find_logo(self):
        for path in _LOGO_CANDIDATES:
            if path.is_file():
                return path
        return None

    def _set_logo(self, header):
        logo = self._find_logo()
        if logo is None:
            print("Web Surfer: logo not found under assets/")
            return
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(logo), 28, 28, True)
        except Exception as exc:
            print(f"Web Surfer: could not load logo {logo}: {exc}")
            return
        image = Gtk.Image.new_from_pixbuf(pixbuf)
        image.set_pixel_size(28)
        header.pack_start(image)
        self.set_icon(pixbuf)

    def on_window_state(self, _window, event):
        return False
