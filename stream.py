"""Stream a WAV file to AssemblyAI with the right realtime model for the job.

--use-case transcript  -> AssemblyAI-STT-3.7-Realtime ($0.30/hr), speaker labels on.
                          For notetakers, captions and live transcripts nobody answers.
--use-case agent       -> AssemblyAI-STT-3.7-Realtime-Agent ($0.45/hr).
                          For voice agents: anything that waits on the model to decide
                          the caller is done.

The two sessions differ by one connection parameter, speech_model. Everything else
in this file (connect, stream, handle Turn events, disconnect) is the same code.
"""

import argparse
import json
import os
import sys
import time
import wave

from dotenv import load_dotenv
from assemblyai.streaming.v3 import (
    BeginEvent,
    RealTimeError,
    RealTimeEvents,
    RealTimeParameters,
    RealTimeTranscriber,
    RealTimeTranscriberOptions,
    SpeechStartedEvent,
    TerminationEvent,
    TurnEvent,
)

MODELS = {
    "transcript": "assemblyai-stt-3-7-realtime",
    "agent": "assemblyai-stt-3-7-realtime-agent",
}

CHUNK_MS = 100  # the docs accept 50-1000 ms chunks; 100 ms is a common choice


def build_params(use_case: str, sample_rate: int) -> RealTimeParameters:
    """Return connection parameters for the chosen use case."""
    if use_case == "transcript":
        # Live transcript with speaker labels. Labels are final when each turn ends.
        return RealTimeParameters(
            sample_rate=sample_rate,
            speech_model=MODELS["transcript"],
            speaker_labels=True,
        )
    # Voice agent. Leave turn detection on its defaults: they are entity-aware,
    # so a pause inside a phone number doesn't end the turn.
    return RealTimeParameters(
        sample_rate=sample_rate,
        speech_model=MODELS["agent"],
    )


def read_wav(path: str):
    """Open a 16-bit mono PCM WAV file and return (wave reader, sample rate)."""
    wav = wave.open(path, "rb")
    if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
        sys.exit(
            "Expected 16-bit mono PCM WAV. Convert with:\n"
            "  ffmpeg -i input.mp3 -ac 1 -ar 16000 -sample_fmt s16 audio.wav"
        )
    return wav, wav.getframerate()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("audio", help="Path to a 16-bit mono PCM WAV file")
    parser.add_argument(
        "--use-case",
        choices=sorted(MODELS),
        default="transcript",
        help="transcript (notetaker, captions) or agent (voice agent)",
    )
    parser.add_argument(
        "--print-params",
        action="store_true",
        help="Print the connection parameters and exit without connecting",
    )
    args = parser.parse_args()

    wav, sample_rate = read_wav(args.audio)
    params = build_params(args.use_case, sample_rate)

    if args.print_params:
        print(json.dumps(params.model_dump(exclude_none=True, mode="json"), indent=2))
        return

    load_dotenv()
    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not api_key:
        sys.exit("Set ASSEMBLYAI_API_KEY in your environment or a .env file.")

    def on_begin(client: RealTimeTranscriber, event: BeginEvent):
        print(f"Session {event.id} started on {params.speech_model}")

    def on_speech_started(client: RealTimeTranscriber, event: SpeechStartedEvent):
        # On the Agent model this is the barge-in signal: stop your TTS playback here.
        if args.use_case == "agent":
            print(f"\n[speech started at {event.timestamp} ms: stop agent playback]")

    def on_turn(client: RealTimeTranscriber, event: TurnEvent):
        if not event.transcript:
            return  # ignore empty finals
        if event.end_of_turn:
            label = f"Speaker {event.speaker_label}: " if event.speaker_label else ""
            print(f"\rFINAL   {label}{event.transcript}")
        else:
            # Each partial re-sends the turn so far, so overwrite rather than append.
            print(f"\rpartial {event.transcript}", end="", flush=True)

    def on_terminated(client: RealTimeTranscriber, event: TerminationEvent):
        print(f"\nSession ended: {event.audio_duration_seconds}s of audio")

    def on_error(client: RealTimeTranscriber, error: RealTimeError):
        print(f"\nError: {error}", file=sys.stderr)

    client = RealTimeTranscriber(
        RealTimeTranscriberOptions(terminate_timeout=30.0),
        api_key=api_key,
    )
    client.on(RealTimeEvents.Begin, on_begin)
    client.on(RealTimeEvents.SpeechStarted, on_speech_started)
    client.on(RealTimeEvents.Turn, on_turn)
    client.on(RealTimeEvents.Termination, on_terminated)
    client.on(RealTimeEvents.Error, on_error)

    client.connect(params)
    frames_per_chunk = int(sample_rate * CHUNK_MS / 1000)
    try:
        while True:
            chunk = wav.readframes(frames_per_chunk)
            if not chunk:
                break
            client.stream(chunk)
            time.sleep(CHUNK_MS / 1000)  # send at live speed, like a real call
    finally:
        client.disconnect(terminate=True)
        wav.close()


if __name__ == "__main__":
    main()
