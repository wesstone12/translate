# main.py

import signal
import sys
import time
import sounddevice as sd
from load import SpeechClient, print_default_mic
from rich.live import Live
from rich.panel import Panel
from rich.console import Console
from rich.layout import Layout
from rich.text import Text


def main():
    console = Console()
    print_default_mic()

    client = SpeechClient()
    script = []  # store final translations

    # Callback to feed mic PCM into Azure push stream
    def mic_callback(indata, frames, time_info, status):
        client.push_stream.write(indata.tobytes())

    mic_stream = sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype='int16',
        callback=mic_callback,
    )
    mic_stream.start()

    # Create layout with two panels: live translation and history
    layout = Layout()
    layout.split_column(
        Layout(name="live", size=5),    # fixed height for live updates
        Layout(name="history", ratio=1)  # remaining space for history
    )

    with Live(layout, console=console, refresh_per_second=4):
        # Handler for partial (in-flight) translations
        def on_recognizing(evt):
            partial = evt.result.translations.get(client.target_lang, "…")
            txt = Text(partial, overflow="fold", no_wrap=False)
            layout["live"].update(
                Panel(txt, title="Translating…", style="yellow", expand=True)
            )

        # Handler for finalized translations
        def on_final(evt):
            final = evt.result.translations.get(client.target_lang, "")
            script.append(final)

            # Update live panel to show final
            txt = Text(final, overflow="fold", no_wrap=False)
            layout["live"].update(
                Panel(txt, title="Translation", style="green", expand=True)
            )

            # Build history text and update history panel
            history_text = "\n".join(f"{i+1}. {line}" for i, line in enumerate(script))
            layout["history"].update(
                Panel(Text(history_text, overflow="fold"), title="Transcript History", style="cyan", expand=True)
            )

        # Connect event handlers
        client.recognizer.recognizing.connect(on_recognizing)
        client.recognizer.recognized.connect(on_final)
        client.recognizer.canceled.connect(
            lambda e: console.print(f"[red]⚠️ Recognition canceled: {e.reason} ({e.error_details})[/]")
        )

        # Graceful shutdown on Ctrl+C
        def shutdown(signum, frame):
            mic_stream.stop()
            mic_stream.close()
            client.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown)

        console.print("🎤 Listening... Press Ctrl+C to stop")
        client.start()

        # Keep the app running
        while True:
            time.sleep(0.1)

if __name__ == "__main__":
    main()
