"""System tray icon for OpenJarvis on macOS.

Provides a ``rumps``-backed menu bar app so users can toggle the wake-word,
switch the active language, and open the local dashboard without ever
touching a terminal. The module is intentionally tolerant: when ``rumps``
is not installed (Linux dev hosts, headless CI), it exposes a no-op
``main()`` that prints a single hint line instead of crashing.
"""

from __future__ import annotations

from typing import Any, List, Protocol, Tuple


class _MenuItemLike(Protocol):
    """Minimal duck-typed view of the rumps ``MenuItem`` callbacks need.

    ``rumps`` calls our handlers with a sender that exposes ``.title``;
    declaring it here keeps the static type-checker happy without forcing
    a runtime import of ``rumps`` on hosts where the library is missing.
    """

    title: str


try:
    import rumps  # type: ignore[import-not-found]

    class JarvisTray(rumps.App):  # type: ignore[misc, valid-type]
        """macOS menu bar app for OpenJarvis.

        The tray surfaces the three controls the user changes most often:
        wake-word toggle, language cycle, and a link to the local web
        dashboard running on ``http://localhost:3000``.
        """

        def __init__(self) -> None:
            """Build the menu with the default Spanish-language labels."""
            super().__init__("Jarvis", icon="🤖")
            self.menu: List[Any] = [
                rumps.MenuItem("Jarvis", callback=self.dashboard),
                None,
                rumps.MenuItem("Wake word: ON", callback=self.toggle_wake),
                rumps.MenuItem("Idioma: Español", callback=self.toggle_lang),
                None,
                rumps.MenuItem("Salir", callback=rumps.quit_application),
            ]
            self.wake_enabled: bool = True

        def dashboard(self, _sender: Any) -> None:
            """Open the local OpenJarvis web dashboard in the default browser."""
            rumps.open_url("http://localhost:3000")

        def toggle_wake(self, sender: _MenuItemLike) -> None:
            """Flip the wake-word on/off and refresh the menu label."""
            self.wake_enabled = not self.wake_enabled
            sender.title = f"Wake word: {'ON' if self.wake_enabled else 'OFF'}"

        def toggle_lang(self, sender: _MenuItemLike) -> None:
            """Cycle to the next supported language in the menu label."""
            langs = ["Español", "English", "Português"]
            current = sender.title.split(": ")[1]
            idx = langs.index(current)
            next_lang = langs[(idx + 1) % len(langs)]
            sender.title = f"Idioma: {next_lang}"

        def notify(self, title: str, subtitle: str, message: str) -> None:
            """Forward to rumps so subclasses/tests can fire a notification."""
            rumps.notification(title, subtitle, message)

    def main() -> None:
        """Launch the tray icon (blocking call)."""
        JarvisTray().run()


except ImportError:
    def main() -> None:
        """Fallback entry point used when ``rumps`` is unavailable.

        Prints a one-line hint so an operator on a non-macOS box still
        understands why the tray did not start.
        """
        print("rumps no instalado. Para habilitar tray: pip install rumps")
        print("Tray deshabilitado. Jarvis seguirá corriendo en background.")


__all__: Tuple[str, ...] = ("main",)


if __name__ == "__main__":
    main()