# Pi Tutor - System Design & Tech Stack

## Quick Tech Stack Summary

| Layer              | Technology                | Why                                                        |
|--------------------|---------------------------|------------------------------------------------------------|
| **Frontend**       | Next.js (React)           | SSR, great DX, LiveKit has official Next.js starter        |
| **AI Agent**       | LiveKit Python Agent      | Most mature SDK, best NLP ecosystem, your existing setup   |
| **Voice Infra**    | LiveKit Cloud / Self-host | WebRTC, rooms, data channels, RPC — all built in           |
| **LLM**           | OpenAI GPT-4.1-mini       | Already configured, fast, cost-effective                   |
| **STT**           | AssemblyAI (streaming)    | Already configured, good accuracy                          |
| **TTS**           | Inworld TTS               | Already configured                                         |
| **Agent-to-UI**   | LiveKit RPC + Data Channels | Real-time commands from agent to frontend                |

---

## Python Agent vs JavaScript Agent — Why Python Wins

| Factor                    | Python Agent                          | JS/TS Agent                          |
|---------------------------|---------------------------------------|--------------------------------------|
| **SDK Maturity**          | Most mature, primary SDK              | Newer, catching up                   |
| **NLP Libraries**         | spaCy, NLTK, etc. (noun detection!)  | Limited NLP ecosystem                |
| **ML/AI Ecosystem**       | PyTorch, transformers, etc.          | Less native support                  |
| **Your Existing Setup**   | Already have `agent.py` working      | Would need rewrite                   |
| **Community & Examples**  | Largest community, most examples     | Fewer resources                      |
| **LiveKit Docs Priority** | Python examples appear first          | Secondary in docs                    |

**Verdict: Stick with Python.** You already have it running, and the NLP ecosystem
(for features like noun/pronoun detection) is vastly superior in Python.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LIVEKIT CLOUD / SERVER                       │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │                     LiveKit Room                              │  │
│   │                                                              │  │
│   │   Handles: WebRTC, Audio Tracks, Data Channels, RPC          │  │
│   │                                                              │  │
│   └─────────────┬───────────────────────────┬────────────────────┘  │
│                 │                           │                       │
└─────────────────┼───────────────────────────┼───────────────────────┘
                  │                           │
        ┌─────────▼─────────┐       ┌────────▼──────────┐
        │                   │       │                    │
        │   PYTHON AGENT    │       │   NEXT.JS FRONTEND │
        │   (Backend)       │       │   (Instructor UI)  │
        │                   │       │                    │
        │ ┌───────────────┐ │       │ ┌────────────────┐ │
        │ │  LiveKit SDK  │ │◄─────►│ │  LiveKit JS SDK│ │
        │ │  (Python)     │ │ Room  │ │  (@livekit/    │ │
        │ └───────────────┘ │       │ │  components)   │ │
        │                   │       │ └────────────────┘ │
        │ ┌───────────────┐ │       │                    │
        │ │  STT          │ │       │ ┌────────────────┐ │
        │ │  (AssemblyAI) │ │       │ │  Live          │ │
        │ └───────────────┘ │       │ │  Transcript    │ │
        │                   │       │ │  Panel         │ │
        │ ┌───────────────┐ │       │ └────────────────┘ │
        │ │  LLM          │ │       │                    │
        │ │  (GPT-4.1)    │ │       │ ┌────────────────┐ │
        │ └───────────────┘ │       │ │  Interactive   │ │
        │                   │       │ │  Content Panel │ │
        │ ┌───────────────┐ │       │ │  (highlights,  │ │
        │ │  TTS          │ │       │ │   annotations) │ │
        │ │  (Inworld)    │ │       │ └────────────────┘ │
        │ └───────────────┘ │       │                    │
        │                   │       │ ┌────────────────┐ │
        │ ┌───────────────┐ │       │ │  Student       │ │
        │ │  NLP Engine   │ │       │ │  Matrix View   │ │
        │ │  (for noun/   │ │       │ │  (seating map) │ │
        │ │   pronoun     │ │       │ └────────────────┘ │
        │ │   detection)  │ │       │                    │
        │ └───────────────┘ │       │ ┌────────────────┐ │
        │                   │       │ │  Projector     │ │
        │                   │       │ │  View (student │ │
        │                   │       │ │  facing screen)│ │
        │                   │       │ └────────────────┘ │
        └───────────────────┘       └────────────────────┘
```

---

## Who Talks to What — Communication Flow

```
┌──────────────┐                                        ┌──────────────┐
│              │  1. Teacher speaks into mic             │              │
│   TEACHER    │ ──────────────────────────────────────► │  LIVEKIT     │
│  (Faizan)    │         (Audio Track)                   │  ROOM        │
│              │                                        │              │
└──────────────┘                                        └──────┬───────┘
                                                               │
                                                               │ 2. Audio
                                                               │    forwarded
                                                               ▼
                                                        ┌──────────────┐
                                                        │              │
                                                        │  PYTHON      │
                                                        │  AGENT       │
                                                        │              │
                                                        └──────┬───────┘
                                                               │
                    ┌──────────────────────────────────────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │   AGENT PROCESSING PIPELINE   │
    │                               │
    │   Audio ──► STT ──► Text      │
    │                     │         │
    │                     ▼         │
    │               LLM Processes   │
    │               (understands    │
    │                intent)        │
    │                     │         │
    │          ┌──────────┼──────────────────────────┐
    │          │          │                          │
    │          ▼          ▼                          ▼
    │     Voice Reply   RPC Command           Data Message
    │     (TTS audio)   to Frontend           to Frontend
    │          │          │                          │
    └──────────┼──────────┼──────────────────────────┘
               │          │                          │
               ▼          │                          │
    ┌──────────────┐      │                          │
    │   LIVEKIT    │      │                          │
    │   ROOM       │      │                          │
    └──────┬───────┘      │                          │
           │              │                          │
           ▼              ▼                          ▼
    ┌──────────────────────────────────────────────────┐
    │                NEXT.JS FRONTEND                   │
    │                                                   │
    │  3. Audio plays     4. UI updates     5. Transcript│
    │     through            (highlight       updates    │
    │     speakers           nouns, etc.)     live       │
    └──────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │   PROJECTOR  │  ◄── Students see this on the big screen
    │   / SCREEN   │
    └──────────────┘
```

---

## The Interactive Feature — "Mark Nouns in Red"

This is where it gets exciting. Here's exactly how the noun/pronoun highlighting works:

### Flow Diagram

```
Teacher says: "Hey AI, mark all nouns in red and pronouns in green"
                │
                ▼
┌─────────────────────────────────┐
│  1. STT converts speech → text  │
│     "mark all nouns in red and  │
│      pronouns in green"         │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  2. LLM understands intent:     │
│     Action: HIGHLIGHT_TEXT      │
│     Rules:                      │
│       - nouns → red             │
│       - pronouns → green        │
│                                 │
│  3. Agent uses NLP (or LLM) to  │
│     analyze the paragraph on    │
│     screen and tag each word    │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  4. Agent sends RPC to frontend │
│                                 │
│  room.local_participant         │
│    .perform_rpc(                │
│      destination = "frontend",  │
│      method = "highlight_text", │
│      payload = JSON:            │
│      {                          │
│        "action": "highlight",   │
│        "rules": [               │
│          {                      │
│            "type": "noun",      │
│            "color": "#FF0000",  │
│            "style": "highlight" │
│          },                     │
│          {                      │
│            "type": "pronoun",   │
│            "color": "#00FF00",  │
│            "style": "underline" │
│          }                      │
│        ],                       │
│        "words": [               │
│          {"word":"cat",         │
│           "type":"noun",        │
│           "positions":[3,15]},  │
│          {"word":"he",          │
│           "type":"pronoun",     │
│           "positions":[20]}     │
│        ]                        │
│      }                          │
│    )                            │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│  5. Next.js frontend receives   │
│     the RPC call, parses JSON,  │
│     and applies CSS classes     │
│     to the paragraph text       │
│                                 │
│  "The cat sat on the mat.       │
│   He was happy."                │
│        │            │           │
│        ▼            ▼           │
│   "The [cat] sat on the [mat].  │
│    [He] was happy."             │
│     ^^^red^^^         ^^^green  │
└─────────────────────────────────┘
```

### The LiveKit RPC Mechanism (The Key Feature)

**On the Python Agent side:**
```python
# Agent sends a UI command to the frontend
await ctx.room.local_participant.perform_rpc(
    destination_identity="frontend-participant-id",
    method="highlight_text",
    payload=json.dumps({
        "action": "highlight",
        "rules": [
            {"type": "noun", "color": "#FF0000", "style": "highlight"},
            {"type": "pronoun", "color": "#00FF00", "style": "underline"}
        ],
        "words": [
            {"word": "cat", "type": "noun", "positions": [3, 15]},
            {"word": "he", "type": "pronoun", "positions": [20]}
        ]
    })
)
```

**On the Next.js Frontend side:**
```typescript
// Frontend registers RPC handlers when joining the room
room.registerRpcMethod("highlight_text", async (data) => {
    const payload = JSON.parse(data.payload);
    // Apply highlighting to the content panel
    applyHighlights(payload.words, payload.rules);
    return JSON.stringify({ success: true });
});

room.registerRpcMethod("update_content", async (data) => {
    const payload = JSON.parse(data.payload);
    // Update the content shown on the interactive panel
    setContentText(payload.text);
    return JSON.stringify({ success: true });
});

room.registerRpcMethod("show_student_focus", async (data) => {
    const payload = JSON.parse(data.payload);
    // Highlight a specific student in the seating matrix
    highlightStudent(payload.studentName, payload.seatNumber);
    return JSON.stringify({ success: true });
});
```

---

## Available RPC Commands (Extensible)

Here are the RPC methods the frontend should register, which the agent can invoke:

| RPC Method            | Purpose                                       | Example Trigger                              |
|-----------------------|-----------------------------------------------|----------------------------------------------|
| `highlight_text`      | Mark words with colors (nouns, pronouns, etc.)| "Mark nouns in red"                          |
| `update_content`      | Display new text/paragraph on screen          | "Show this paragraph on screen"              |
| `clear_highlights`    | Remove all highlights                         | "Clear the markings"                         |
| `show_student_focus`  | Highlight a student on the seating map        | "That back-right student"                    |
| `show_diagram`        | Display a Science diagram or image            | "Show the atom structure diagram"            |
| `update_transcript`   | Send real-time transcript updates             | Automatic during conversation                |
| `show_quiz`           | Display a quick quiz on screen                | "Pop quiz time!"                             |
<!-- | `timer_start`         | Start a visible countdown                     | "You have 30 seconds to answer"              | -->

---

## Next.js Frontend — UI Layout Concept

```
┌─────────────────────────────────────────────────────────┐
│  Pi Tutor                              [⚙️] [🎤 Mute]   │
├──────────────────────────┬──────────────────────────────┤
│                          │                              │
│   INTERACTIVE CONTENT    │     LIVE TRANSCRIPT          │
│   PANEL                  │                              │
│                          │  Faizan: "Can you mark       │
│   "The quick brown fox   │   the nouns in this          │
│    jumped over the       │   paragraph?"                │
│    lazy dog. He was      │                              │
│    very fast."           │  Pi: "Sure thing! Marking    │
│                          │   all nouns in red. Check    │
│   [nouns in RED]         │   the screen, boss!"        │
│   [pronouns in GREEN]   │                              │
│                          │  Faizan: "Now mark the      │
│                          │   pronouns in green"         │
│                          │                              │
│                          │  Pi: "Done! He and it are   │
│                          │   now green. Sakkath!"       │
├──────────────────────────┼──────────────────────────────┤
│                          │                              │
│   SEATING MATRIX         │    CLASS INFO                │
│                          │                              │
│   [7-Karan] [8-Meera]   │    Subject: Science          │
│   [9-Zaid ]             │    Time: 45:00 remaining     │
│   [4-Aarav] [5-Siddharth│    Topic: Parts of Speech    │
│   [6-Priya]             │    Students: 9               │
│   [1-Nikhil][2-Sneha]   │                              │
│   [3-Ananya]            │    [🔴 Recording]            │
│                          │                              │
└──────────────────────────┴──────────────────────────────┘
```

When the teacher says "that back-right student is not focusing", **Zaid's seat** in the matrix
would glow/pulse, and Pi would say his name. The students watching the projector see this
happen in real time — it feels magical!

---

## Project Structure (Recommended)

```
pi-tutor/
├── livekit-voice-agent/          ◄── EXISTING (Python Agent)
│   ├── agent.py                     Main agent code
│   ├── agent-instructions.md        System prompt
│   ├── tools/                       Custom agent tools (future)
│   │   ├── nlp_highlighter.py       Noun/pronoun detection
│   │   └── classroom_tools.py       Classroom management tools
│   ├── pyproject.toml
│   └── .env.local
│
├── pi-tutor-frontend/            ◄── NEW (Next.js Frontend)
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             Landing / Room join
│   │   │   ├── classroom/
│   │   │   │   └── page.tsx         Main classroom UI
│   │   │   └── projector/
│   │   │       └── page.tsx         Student-facing view
│   │   ├── components/
│   │   │   ├── TranscriptPanel.tsx
│   │   │   ├── ContentPanel.tsx     Interactive text (highlights)
│   │   │   ├── SeatingMatrix.tsx    Student grid with positions
│   │   │   ├── AudioVisualizer.tsx
│   │   │   └── ClassTimer.tsx
│   │   ├── hooks/
│   │   │   ├── useRpcHandler.ts     Register/handle RPC from agent
│   │   │   └── useLiveKit.ts        LiveKit room connection
│   │   └── lib/
│   │       └── rpc-handlers.ts      All RPC method handlers
│   ├── package.json
│   └── .env.local
│
└── README.md
```

---

## Deployment Architecture

```
┌─────────────────────────┐     ┌──────────────────────────┐
│   Python Agent          │     │   Next.js Frontend       │
│                         │     │                          │
│   Deploy on:            │     │   Deploy on:             │
│   - Fly.io              │     │   - Vercel               │
│   - Render              │     │   - Cloudflare Pages     │
│   - Hetzner VPS         │     │   - Self-host            │
│   - Railway             │     │                          │
│                         │     │   (Cannot deploy agent   │
│   (Needs long-running   │     │    on Vercel — needs     │
│    process support)     │     │    persistent process)   │
└────────────┬────────────┘     └────────────┬─────────────┘
             │                               │
             └───────────┬───────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  LiveKit Cloud   │
              │  (or self-host)  │
              │                  │
              │  Manages rooms,  │
              │  WebRTC, data    │
              │  channels, etc.  │
              └──────────────────┘
```

**Important**: The Python agent **cannot** run on Vercel (serverless). It needs a platform
that supports long-running processes. Vercel is perfect for the Next.js frontend though.

---

## Getting Started — Next Steps

1. **Keep the Python Agent** — You already have it working. It stays as-is
2. **Create the Next.js Frontend** — Using LiveKit's official Next.js starter
3. **Add RPC handlers** — Register methods on frontend, invoke from agent
4. **Build the NLP tool** — Python `spacy` or LLM-based noun/pronoun detection
5. **Connect to same LiveKit room** — Both agent and frontend join the same room
6. **Build the Interactive Content Panel** — React component that reacts to RPC commands

### Quick Start Commands

```bash
# 1. Create Next.js frontend (from pi-tutor root)
npx -y create-next-app@latest pi-tutor-frontend

# 2. Install LiveKit dependencies
cd pi-tutor-frontend
npm install @livekit/components-react livekit-client

# 3. Add NLP to Python agent (in the agent directory)
cd ../livekit-voice-agent
uv add spacy
python -m spacy download en_core_web_sm
```
