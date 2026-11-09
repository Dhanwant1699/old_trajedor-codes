# Implementation Plan: Bullion AI Alexa-Style Voice Companion & Emotional Trader Agent

Create a dedicated, real-time **Interactive Voice Companion & Emotional Trader Agent (`BullionVoiceCompanionAgent`)** for Bullion AI that acts like an institutional trading Alexa / Jarvis. It understands user feelings (stress, FOMO, panic, curiosity, excitement), maintains conversational memory, supports wake-word listening, and interacts fluently in natural conversational Hinglish.

---

## 🏗️ How the Real-Time Alexa Pipeline is Mapped to Bullion AI

```
 🎙️ User Speaks ("Hey Bullion, market kyu gir raha hai? Tension ho rahi hai")
       │
       ▼ [1. Wake Word & Continuous ASR (<100ms)]
  Web Speech API (hi-IN / en-IN streaming chunks with "Hey Bullion" / "Bullion" trigger)
       │
       ▼ [2. Emotional State & Intent Extraction - NLU (<150ms)]
  VoiceCompanionAgent decodes:
    • Intent: Market_Query + Position_Status
    • Emotion: FEAR / ANXIETY (Drawdown fear)
    • Context: 1 open BUY position (#58513584508 @ 4364.05)
       │
       ▼ [3. Context-Aware Empathetic Reasoning & Dialogue (<300ms)]
  Unified LLM Client with Conversational Memory (last 6 turns) + Live MT5 & Strategy Council Telemetry:
    • Calming trader psychology response
    • Exact institutional data: Stop Loss $4353.56 safe, EMA 21 holding, Risk only 1.5%
       │
       ▼ [4. Neural Audio Voice Synthesis (<150ms)]
  Edge / Google Natural Indian Neural TTS (hi-IN / en-IN) with dynamic pitch, cadence, and human warmth
       │
       ▼
 🔊 Real-Time Voice Playback + Alexa-Style Glowing Orb Animation (<800ms total loop)
```

---

## Proposed Changes

### 1. New Dedicated Agent: `agents/voice_companion_agent.py` [NEW]
- **Emotional State Classifier**: Analyzes user tone and messages for emotional triggers:
  - `FEAR_PANIC`: Small pullback or floating red -> Provides calm reassurance, highlights SL safety and risk parameters.
  - `GREED_FOMO`: Urge to over-leverage or chase tops -> Enforces discipline, CRO rules, and patience for the zone.
  - `FRUSTRATION_WAITING`: Impatience during range-bound "HOLD" -> Explains institutional liquidity accumulation.
  - `HAPPINESS_PROFIT`: Target reached / profit locked -> Celebrates with disciplined risk management praise.
  - `CURIOSITY_LEARNING`: Asking about SMC, Orderblocks, VWAP -> Explains complex concepts in simple Hinglish analogies.
- **Short-Term Conversational Memory**: Stores recent dialogue turns to support natural follow-up queries (e.g. *"Abhi kitna profit chal raha hai?"*, *"Uski SL kahan thi?"*).
- **Council & MT5 Telemetry Link**: Seamlessly bridges live MT5 positions, account balance, 10 Strategy Agents' real-time opinions, and ForexFactory calendar into the conversation.

---

### 2. Backend Server Endpoint in `core/dashboard_server.py` [MODIFY]
- Add `/api/voice-companion` handler:
  - Accepts `query`, `conversation_history`, `user_language`, `audio_metadata`.
  - Routes requests through `BullionVoiceCompanionAgent`.
  - Returns structured response with `reply_text`, `speak_text`, `detected_emotion`, `trader_sentiment_badge`, and `audio_ssml_parameters` (rate, pitch).

---

### 3. Dashboard UI & Voice Cockpit in `docs/dashboard.html` [MODIFY]
- **Alexa-Style Glowing Voice Orb & Waveform Visualizer**:
  - Interactive pulsing Orb displaying 4 distinct states:
    - 🔵 **Idle**: Gentle breathing blue aura.
    - 🟢 **Listening ("Hey Bullion" / Mic Active)**: Vibrant reactive green pulse.
    - 🟡 **Thinking (Agent Council Deliberation)**: Golden rotating shimmer.
    - 🟣 **Speaking (Neural TTS Streaming)**: Neon purple rhythmic waveform audio waves.
- **Continuous Wake-Word Detection**:
  - Built-in continuous listener for `"Hey Bullion"`, `"Bullion AI"`, or `"Alexa"` to activate voice dialog without touching the keyboard.
- **Emotional Badge & Empathy HUD**:
  - Displays dynamic badges: `😌 Calm Trader HUD`, `🧘 Zen Discipline Mode`, `🛡️ CRO Risk Shield`, `🚀 Target Reached`.
- **Top-Tier Neural Voice Synthesizer**:
  - Automatically loads and selects the most natural available neural voices (`Microsoft Swara Online (Natural) - Hindi`, `Microsoft Neerja Online (Natural) - English (India)`, `Google हिन्दी`, `Google UK/US Natural`).
  - Implements pitch and rate modulation to match the conversation emotion (e.g., slower and reassuring when calming stress, energetic when celebrating profit).

---

## Verification Plan

### Automated & Manual Tests
1. **Agent Unit Test (`tests/test_voice_companion.py`)**:
   - Test emotional classification across scenarios (Fear, Greed, Frustration, Excitement, Analysis).
   - Test conversational memory retention across multi-turn dialogs.
   - Test voice trade intent requiring security code `198311`.
2. **Interactive Browser Verification**:
   - Open `http://localhost:8888` on Chrome/Edge.
   - Test Wake Word trigger: Say *"Hey Bullion, market kaisa lag raha hai?"*.
   - Test Emotional Response: Ask *"Bhai trade thoda loss me ja raha hai, darr lag raha hai"* -> Verify empathetic, reassuring trader psychology reply.
   - Verify Neural TTS voice quality and audio waveform visualizer.
