
        let chatWindowMaximized = false;

        function toggleBullionChatWindow() {
            const win = document.getElementById('bullionChatWindow');
            if (!win) return;
            if (win.style.display === 'flex') {
                win.style.display = 'none';
            } else {
                win.style.display = 'flex';
                const input = document.getElementById('floatingChatInput');
                if (input) setTimeout(() => input.focus(), 100);
            }
        }

        function maximizeBullionChatWindow() {
            const win = document.getElementById('bullionChatWindow');
            if (!win) return;
            chatWindowMaximized = !chatWindowMaximized;
            if (chatWindowMaximized) {
                win.classList.add('maximized');
            } else {
                win.classList.remove('maximized');
            }
        }

        function syncChatLang(val) {
            document.getElementById('userLangSelect').value = val;
            document.getElementById('floatingLangSelect').value = val;
        }

        function discussAgent(agentKey, agentName) {
            const lang = document.getElementById('floatingLangSelect').value;
            let prompt = "";
            if (agentKey === 'CRO') {
                prompt = lang === 'hi' ? 'Chief Risk Officer (CRO) ne risk aur lot size ke baare me kya decision diya?' :
                         lang === 'mr' ? 'Chief Risk Officer (CRO) ने रिस्क आणि लॉट साइजबाबत काय निर्णय दिला?' :
                         'Why did the Chief Risk Officer (CRO) approve/veto the setup and what lot size was calculated?';
            } else if (agentKey === 'Council_Debate') {
                prompt = lang === 'hi' ? '10 Strategy Agents ki aapas me kya debate hui aur Lead Arbitrator ne kya ruling di?' :
                         lang === 'mr' ? '10 स्ट्रॅटेजी एजंट्समध्ये काय चर्चा झाली आणि मुख्य लवादाने काय निर्णय दिला?' :
                         'Summarize the council debate between all 10 strategy agents and the Lead Arbitrator ruling.';
            } else {
                prompt = lang === 'hi' ? `${agentName} ne kya feedback diya aur uska reason kya hai?` :
                         lang === 'mr' ? `${agentName} ने काय मत दिले आणि त्यामागील कारण काय आहे?` :
                         `What is ${agentName}'s opinion, vote, and exact technical reasoning?`;
            }

            // Open window if closed
            const win = document.getElementById('bullionChatWindow');
            if (win.style.display !== 'flex') win.style.display = 'flex';

            document.getElementById('floatingChatInput').value = prompt;
            sendFloatingChatMessage(prompt);
        }

        function sendFloatingQuickPrompt(promptText) {
            document.getElementById('floatingChatInput').value = promptText;
            sendFloatingChatMessage(promptText);
        }

        async function sendFloatingChatMessage(customQuery = null) {
            const input = document.getElementById('floatingChatInput');
            const query = (customQuery || input.value || '').trim();
            if (!query) return;

            if (!customQuery) input.value = '';
            const userLang = document.getElementById('floatingLangSelect').value;

            // 1. Append user message bubble to floating window
            appendMessageBubble('user', query, userLang);

            // Also stream to main HUD stream
            streamJarvisThought(`👤 User: "${query}"`);

            // Show typing indicator
            const typing = document.getElementById('floatingTypingIndicator');
            if (typing) typing.style.display = 'block';

            try {
                const res = await fetch('/api/voice-companion', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query, language: userLang })
                });

                if (typing) typing.style.display = 'none';

                if (res.ok) {
                    const data = await res.json();
                    appendMessageBubble('ai', data.reply, data.detected_language || userLang);
                    streamJarvisThought(`🤖 Bullion AI: ${data.reply}`);

                    // Voice output with companion emotion cadence
                    speakBullionVoice(data.speak_text || data.reply, data.detected_language || userLang, data.pitch || 1.0, data.rate || 1.02);

                    // If trade confirmation is required
                    if (data.action_intent && data.action_intent.require_code) {
                        pendingTradeIntent = data.action_intent;
                        const secBox = document.getElementById('floatingSecurityBox');
                        if (secBox) {
                            secBox.style.display = 'block';
                            document.getElementById('floatingSecCodeInput').focus();
                        }
                    }
                }
            } catch (e) {
                if (typing) typing.style.display = 'none';
                appendMessageBubble('ai', `❌ Error contacting Bullion AI: ${e.message}`, 'en');
            }
        }

        function appendMessageBubble(sender, text, lang) {
            const container = document.getElementById('floatingChatMessages');
            if (!container) return;

            const bubble = document.createElement('div');
            bubble.className = `msg-bubble ${sender === 'user' ? 'msg-user' : 'msg-ai'}`;

            const now = new Date();
            const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;

            if (sender === 'user') {
                bubble.innerHTML = `
                    <div>${text}</div>
                    <div class="msg-meta">
                        <span>You</span>
                        <span>${timeStr}</span>
                    </div>
                `;
            } else {
                const cleanText = text.replace(/'/g, "\\'");
                bubble.innerHTML = `
                    <div>🤖 <strong>Bullion AI:</strong> ${text}</div>
                    <div class="msg-meta">
                        <span>${lang === 'hi' ? '🇮🇳 हिन्दी' : lang === 'mr' ? '🚩 मराठी' : '🇬🇧 English'}</span>
                        <button class="msg-speak-btn" onclick="speakBullionVoice('${cleanText}', '${lang}')" title="Listen to response">🔊 Listen</button>
                    </div>
                `;
            }

            container.appendChild(bubble);
            container.scrollTop = container.scrollHeight;
        }

        async function confirmFloatingTradeWithCode() {
            const secCode = (document.getElementById('floatingSecCodeInput').value || '').trim();
            document.getElementById('secCodeInput').value = secCode;
            await confirmAndExecuteTradeWithCode();
            document.getElementById('floatingSecurityBox').style.display = 'none';
        }

        let isFloatingListening = false;
        let floatingSpeechRec = null;

        function toggleFloatingMic() {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SpeechRec) {
                alert("Speech recognition is not supported in this browser. Please use Chrome, Edge, or Brave.");
                return;
            }

            const micIcon = document.getElementById('floatingMicIcon');
            const micBtn = document.getElementById('floatingMicBtn');
            const userLang = document.getElementById('floatingLangSelect')?.value || 'auto';

            if (isFloatingListening) {
                stopAndSubmitSpeech('floating');
                return;
            }

            if (window.speechSynthesis) {
                try { window.speechSynthesis.cancel(); } catch(e) {}
            }

            accumulatedSpeechText = "";
            floatingSpeechRec = new SpeechRec();
            floatingSpeechRec.continuous = true;
            floatingSpeechRec.interimResults = true;

            if (userLang === 'mr') floatingSpeechRec.lang = 'mr-IN';
            else if (userLang === 'en') floatingSpeechRec.lang = 'en-IN';
            else floatingSpeechRec.lang = 'hi-IN';

            floatingSpeechRec.onstart = () => {
                isFloatingListening = true;
                if (micIcon) micIcon.innerText = '⏹️';
                if (micBtn) micBtn.style.background = 'rgba(239, 68, 68, 0.3)';
            };

            floatingSpeechRec.onresult = (event) => {
                let interim = "";
                let final = "";

                for (let i = 0; i < event.results.length; ++i) {
                    if (event.results[i].isFinal) {
                        final += event.results[i][0].transcript + " ";
                    } else {
                        interim += event.results[i][0].transcript;
                    }
                }

                const currentText = (final + interim).trim();
                accumulatedSpeechText = currentText;

                const input = document.getElementById('floatingChatInput');
                if (input) input.value = currentText;

                // Smart Silence Debounce (1.8s)
                if (speechSilenceTimer) clearTimeout(speechSilenceTimer);
                if (currentText.length > 2) {
                    speechSilenceTimer = setTimeout(() => {
                        if (isFloatingListening) {
                            stopAndSubmitSpeech('floating');
                        }
                    }, 1800);
                }
            };

            floatingSpeechRec.onerror = (e) => {
                console.warn("Floating mic error:", e.error);
                if (e.error !== 'no-speech') {
                    isFloatingListening = false;
                    if (micIcon) micIcon.innerText = '🎤';
                    if (micBtn) micBtn.style.background = 'rgba(239,68,68,0.15)';
                }
            };

            floatingSpeechRec.onend = () => {
                if (isFloatingListening) {
                    stopAndSubmitSpeech('floating');
                } else {
                    if (micIcon) micIcon.innerText = '🎤';
                    if (micBtn) micBtn.style.background = 'rgba(239,68,68,0.15)';
                }
            };

            try {
                floatingSpeechRec.start();
            } catch (err) {
                console.error("Floating mic start error:", err);
            }
        }

        function scrollToRadar() {
            switchAsset('XAUUSD');
            setTimeout(() => {
                const el = document.getElementById('pattern-radar-header');
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    el.style.transition = 'all 0.5s';
                    el.style.padding = '8px 12px';
                    el.style.borderRadius = '8px';
                    el.style.background = 'rgba(96, 165, 250, 0.2)';
                    setTimeout(() => { el.style.background = 'transparent'; }, 2000);
                }
            }, 100);
        }

        function discussTimeframe(tfKey, tfName) {
            const prompt = `${tfName} (${tfKey}) timeframe pe Gold ka kya candlestick pattern, market structure aur target projection ban raha hai? Hinglish me explain karo.`;
            const win = document.getElementById('bullionChatWindow');
            if (win && win.style.display !== 'flex') win.style.display = 'flex';
            const input = document.getElementById('floatingChatInput');
            if (input) input.value = prompt;
            sendFloatingChatMessage(prompt);
        }

        function scrollToAgents() {
            switchAsset('XAUUSD');
            setTimeout(() => {
                const el = document.getElementById('matrix-header');
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    el.style.transition = 'all 0.5s';
                    el.style.padding = '8px 12px';
                    el.style.borderRadius = '8px';
                    el.style.background = 'rgba(245, 158, 11, 0.2)';
                    setTimeout(() => { el.style.background = 'transparent'; }, 2000);
                }
            }, 100);
        }

        function scrollToVoiceCompanion() {
            switchAsset('XAUUSD');
            setTimeout(() => {
                const el = document.querySelector('.alexa-companion-card');
                if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    el.style.transition = 'all 0.5s';
                    el.style.boxShadow = '0 0 40px rgba(0, 240, 255, 0.6)';
                    setTimeout(() => { el.style.boxShadow = ''; }, 2000);
                }
            }, 100);
        }

        // Initialize immediately on load and poll every 3 seconds
        initJarvisGlobe();
        loadAdminConfig();
        fetchLiveStatus();
        setInterval(fetchLiveStatus, 3000);
    