# textual_app.py

import signal
import sys
import sounddevice as sd
from load import SpeechClient, print_default_mic
from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Static


def _wrap_lines(text: str, width: int) -> str:
    # helper to wrap history lines to given width
    import textwrap
    return "\n".join(textwrap.wrap(text, width))

class TranslatorApp(App):
    """
    A Textual TUI for live speech translation with scrollable history.
    """
    CSS = """
Screen {
  layout: vertical;
}
#live_container {
  height: 7.5;
  border: round blue;
}
#history_container {
  border: round white;
}
"""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            # Scrollable live translation box
            ScrollableContainer(
                Static("", id="live"),
                id="live_container",
            ),
            # Scrollable history box
            ScrollableContainer(
                Static("", id="history"),
                id="history_container",
            ),
            id="body"
        )
        yield Footer()

    def on_mount(self):
        # Print mic info above the TUI
        print_default_mic()

        # Initialize speech translation client
        self.theme = "tokyo-night"
        self.client = SpeechClient()
        self.script = []

        # Start microphone streaming callback
        def mic_cb(indata, frames, time_info, status):
            self.client.push_stream.write(indata.tobytes())
        self.mic_stream = sd.InputStream(
            samplerate=16000,
            channels=1,
            dtype='int16',
            callback=mic_cb
        )
        self.mic_stream.start()

        # Connect SDK events
        self.client.recognizer.recognizing.connect(self.show_partial)
        self.client.recognizer.recognized.connect(self.show_final)
        self.client.recognizer.canceled.connect(self.handle_canceled)

        # Start translation
        self.client.start()

        # Handle Ctrl+C
        signal.signal(signal.SIGINT, self.shutdown)

    def show_partial(self, evt):
        partial = evt.result.translations.get(self.client.target_lang, "")
        live = self.query_one("#live", Static)
        live.update(partial)

    def show_final(self, evt):
        final = evt.result.translations.get(self.client.target_lang, "")
        self.script.append(final)
        live = self.query_one("#live", Static)
        live.update(final)

        # Update history widget
        history_widget = self.query_one("#history", Static)
        # wrap each line to container width
        width = self.size.width - 4  # some padding
        wrapped = [_wrap_lines(line, width) for line in self.script]
        history_widget.update("\n\n".join(f"{i+1}. {wrapped[i]}" for i in range(len(wrapped))))

    def handle_canceled(self, evt):
        reason = evt.cancellation_details.reason
        err = evt.cancellation_details.error_details
        live = self.query_one("#live", Static)
        live.update(f"⚠ Recognition canceled: {reason} ({err})")

    def shutdown(self, *args):
        self.mic_stream.stop()
        self.mic_stream.close()
        self.client.stop()
        sys.exit(0)

if __name__ == "__main__":
    TranslatorApp().run()
