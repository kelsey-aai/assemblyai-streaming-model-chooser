# AssemblyAI streaming model chooser: Realtime or Realtime-Agent

Companion code for the AssemblyAI blog post [Realtime or Realtime-Agent? How to choose a streaming model](https://www.assemblyai.com/blog/realtime-vs-realtime-agent-streaming-model).

AssemblyAI has two streaming speech-to-text models, and you pick one with a single connection parameter:

| If your audio is | Use | `speech_model` | Price |
|---|---|---|---|
| A live stream that ends in a transcript (notetakers, captions, meetings) | AssemblyAI-STT-3.7-Realtime | `assemblyai-stt-3-7-realtime` | $0.30/hr |
| A live stream your voice agent answers | AssemblyAI-STT-3.7-Realtime-Agent | `assemblyai-stt-3-7-realtime-agent` | $0.45/hr |

The test: if anything in your code waits for the model to decide the speaker is done, use Realtime-Agent.

`stream.py` streams a WAV file at live speed with either model and prints partial and final turns. In `transcript` mode it turns on speaker labels. In `agent` mode it prints the `SpeechStarted` event, which is where a voice agent stops its own playback.

## Quick start

```bash
git clone https://github.com/kelsey-aai/assemblyai-streaming-model-chooser.git
cd assemblyai-streaming-model-chooser
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then paste your API key into .env
```

Get an API key at [assemblyai.com/dashboard/signup](https://www.assemblyai.com/dashboard/signup). New accounts get free credits for the speech APIs.

## Run it

The script expects 16-bit mono PCM WAV. Convert anything else with ffmpeg:

```bash
ffmpeg -i input.mp3 -ac 1 -ar 16000 -sample_fmt s16 audio.wav
```

Live transcript with speaker labels (AssemblyAI-STT-3.7-Realtime):

```bash
python stream.py audio.wav --use-case transcript
```

Voice-agent input (AssemblyAI-STT-3.7-Realtime-Agent):

```bash
python stream.py audio.wav --use-case agent
```

See exactly what each mode sends, without connecting or using an API key:

```bash
python stream.py audio.wav --use-case agent --print-params
```

## What changes between the two modes

Only `build_params()` differs. Connecting, streaming, handling `Turn` events and disconnecting are the same code for both models, so moving between them (or migrating from Universal-Streaming or Universal-3.6 Pro Realtime) is a change to `speech_model` plus the options that only one model supports:

- Speaker labels: supported on both; AssemblyAI recommends Realtime for diarization.
- Voice Focus and `mode="manual"` (bring your own turn detector with `ForceEndpoint`): Realtime-Agent only.

Read the [model selection](https://www.assemblyai.com/docs/streaming/select-the-speech-model) and [turn detection](https://www.assemblyai.com/docs/streaming/turn-detection) docs for every parameter.

## Requirements

- Python 3.9+
- `assemblyai` Python SDK 1.10.11 or later (has both 3.7 model IDs)
