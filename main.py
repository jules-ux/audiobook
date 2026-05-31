import streamlit as st
import json
import re
import time
import os

# 1. Pagina configuratie
st.set_page_config(
    layout="wide", 
    page_title="AI Audioboek Bioscoop",
    page_icon="📚",
    initial_sidebar_state="collapsed"
)

# VASTE BESTANDSNAAM INSTELLEN (Pas "film.srt" aan naar jouw bestandsnaam)
VAST_SRT_BESTAND = "transscriptie_film.srt" 

if 'fase' not in st.session_state:
    st.session_state['fase'] = 'setup'
if 'raw_srt_data' not in st.session_state:
    st.session_state['raw_srt_data'] = None
if 'active_video_id' not in st.session_state:
    st.session_state['active_video_id'] = ""

def get_youtube_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return match.group(1) if match else None

def srt_tijd_naar_seconden(tijd_str):
    tijd_str = tijd_str.strip().replace(',', '.')
    delen = tijd_str.split(':')
    return (int(delen[0]) * 3600) + (int(delen[1]) * 60) + float(delen[2])

def parse_srt_raw(srt_tekst):
    blokken = re.split(r'\n\s*\n', srt_tekst.strip())
    data = []
    idx = 0
    for blok in blokken:
        regels = [r.strip() for r in blok.split('\n') if r.strip()]
        if len(regels) >= 2:
            tijd_regel = next((r for r in regels if "-->" in r), None)
            if tijd_regel:
                tekst_start_index = regels.index(tijd_regel) + 1
                tijd_delen = tijd_regel.split('-->')
                data.append({
                    "id": idx,
                    "start": srt_tijd_naar_seconden(tijd_delen[0]),
                    "end": srt_tijd_naar_seconden(tijd_delen[1]),
                    "text_orig": " ".join(regels[tekst_start_index:])
                })
                idx += 1
    return data

# --- FASE 1: SETUP (NU MET VASTE FILE-INLADING) ---
if st.session_state['fase'] == 'setup':
    st.title("📚 AI Audioboek Bioscoop")
    
    # Visuele melding over het gekoppelde vaste bestand
    if os.path.exists(VAST_SRT_BESTAND):
        st.success(f"🔗 Vaste transcriptie gekoppeld: `{VAST_SRT_BESTAND}`")
    else:
        st.error(f"❌ Bestand `{VAST_SRT_BESTAND}` niet gevonden! Plaats het bestand in dezelfde map als dit script.")

    youtube_url = st.text_input("1. Plak de YouTube URL:", "https://www.youtube.com/watch?v=B4s9iJBUqSE&t=91s")
    
    if st.button("🎬 Genereer Film & Start Prompter"):
        video_id = get_youtube_id(youtube_url)
        
        if video_id:
            if os.path.exists(VAST_SRT_BESTAND):
                # We lezen het vaste bestand direct in via Python's open()
                with open(VAST_SRT_BESTAND, "r", encoding="utf-8") as f:
                    srt_inhoud = f.read()
                
                st.session_state['raw_srt_data'] = parse_srt_raw(srt_inhoud)
                st.session_state['active_video_id'] = video_id
                st.session_state['fase'] = 'loading'
                st.rerun()
            else:
                st.error("Kan niet starten: het vaste .srt-bestand ontbreekt in de map.")

# --- FASE 2: LOADING ---
elif st.session_state['fase'] == 'loading':
    st.markdown("<div style='text-align: center; margin-top: 30vh;'><h3 style='color: #ffffff;'>⏳ Bioscoopomgeving initialiseren...</h3></div>", unsafe_allow_html=True)
    time.sleep(0.3)
    st.session_state['fase'] = 'theater'
    st.rerun()

# --- FASE 3: THEATER ---
elif st.session_state['fase'] == 'theater':
    
    st.markdown("""
        <style>
            html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container {
                overflow: hidden !important;
                height: 100vh !important;
                max-height: 100vh !important;
                margin: 0 !important;
                padding: 0 !important;
                background-color: #0b0f19 !important;
            }
            header, footer, [data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
            section[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
            [data-testid="stHtmlBlock"] { padding: 0 !important; margin: 0 !important; height: 100vh !important; }
        </style>
    """, unsafe_allow_html=True)

    json_data = json.dumps(st.session_state['raw_srt_data']).replace("'", "\\'")
    video_id = st.session_state['active_video_id']

    custom_interface = """
    <div class="app-container">
        <div style="width: 1px; height: 1px; opacity: 0; overflow: hidden; position: absolute;">
            <div id="player"></div>
        </div>

        <div class="top-bar">
            <div class="back-arrow" onclick="window.parent.location.reload();">&#x2190; <span class="video-title">Nieuwe Film</span></div>
            <div class="language-selector">
                <span class="lang-pill active-lang">AUTO-DETECT</span>
                <span class="arrow-separator">&#x2192;</span>
                <span id="display-target-lang" class="lang-pill target-lang">NEDERLANDS</span>
            </div>
            <div class="settings-wrapper">
                <div class="settings-icon" onclick="toggleSettingsMenu()">&#x2699;</div>
                <div id="settings-menu" class="dropdown-menu">
                    <div class="dropdown-title">Vertaal Doeltaal</div>
                    <div class="dropdown-item" onclick="changeLanguage('nl', 'NEDERLANDS')">Nederlands</div>
                    <div class="dropdown-item" onclick="changeLanguage('en', 'ENGLISH')">English</div>
                    <div class="dropdown-item" onclick="changeLanguage('de', 'DEUTSCH')">Deutsch</div>
                    <div class="dropdown-item" onclick="changeLanguage('es', 'ESPAÑOL')">Español</div>
                </div>
            </div>
        </div>
        
        <div id="story-container" class="story-scroll-zone"></div>

        <div class="hover-control-bar">
            <div class="time-info">
                <div class="time-block">
                    <span class="time-label">ELAPSED</span>
                    <span id="time-elapsed" class="time-value">00:00</span>
                </div>
                <div class="time-block">
                    <span class="time-label">TOTAL LENGTH</span>
                    <span id="time-total" class="time-value">00:00</span>
                </div>
            </div>

            <div class="core-controls">
                <button class="skip-btn" onclick="skipTime(-10)">&#x21ba;</button>
                <button id="play-trigger-btn" class="main-play-btn" onclick="togglePlayback()">&#x25b6;</button>
                <button class="skip-btn" onclick="skipTime(10)">&#x21bb;</button>
            </div>

            <div class="extra-controls">
                <div class="speed-wrapper">
                    <div id="speed-trigger" class="speed-pill" onclick="toggleSpeedMenu()">📝 1.0x</div>
                    <div id="speed-menu" class="dropdown-menu speed-dropdown">
                        <div class="dropdown-item" onclick="changeSpeed(0.5)">0.5x Snelheid</div>
                        <div class="dropdown-item" onclick="changeSpeed(1.0)">1.0x Normaal</div>
                        <div class="dropdown-item" onclick="changeSpeed(1.5)">1.5x Snel</div>
                        <div class="dropdown-item" onclick="changeSpeed(2.0)">2.0x Turbo</div>
                    </div>
                </div>
                <div class="mic-btn">🎙️</div>
            </div>
        </div>
    </div>

    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { background-color: #0b0f19; overflow: hidden !important; height: 100vh !important; width: 100vw !important; }

        .app-container {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: #f3f4f6;
            background-color: #0b0f19;
            height: 100vh !important;
            width: 100vw !important;
            position: relative;
            overflow: hidden !important;
            display: flex;
            flex-direction: column;
        }

        .top-bar {
            position: absolute; top: 0; left: 0; right: 0; height: 70px;
            display: flex; justify-content: space-between; align-items: center;
            padding: 0 40px; background: #111827; border-bottom: 1px solid #1f2937; z-index: 9999;
        }
        .back-arrow { font-weight: 600; cursor: pointer; color: #3b82f6; }
        .language-selector { display: flex; align-items: center; gap: 8px; }
        .lang-pill { padding: 5px 14px; border-radius: 15px; font-size: 0.72rem; font-weight: 800; }
        .active-lang { background: #064e3b; color: #34d399; }
        .target-lang { background: #1e3a8a; color: #60a5fa; }
        .settings-icon { font-size: 1.3rem; cursor: pointer; color: #9ca3af; }
        
        .settings-wrapper, .speed-wrapper { position: relative; display: inline-block; }
        .dropdown-menu {
            display: none; position: absolute; right: 0; background: #1f2937;
            border: 1px solid #374151; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            width: 180px; z-index: 10000; margin-top: 10px;
        }
        .speed-dropdown { bottom: 100%; margin-bottom: 15px; top: auto; }
        .dropdown-title { padding: 10px 15px; font-size: 0.75rem; color: #9ca3af; font-weight: bold; border-bottom: 1px solid #374151; }
        .dropdown-item { padding: 10px 15px; font-size: 0.85rem; color: #e5e7eb; cursor: pointer; }
        .dropdown-item:hover { background: #374151; color: white; }

        .story-scroll-zone {
            position: absolute; top: 70px; bottom: 95px; left: 0; right: 0;
            overflow-y: auto !important; padding: 40px 15%;
            background: #0b0f19; display: flex; align-items: center; justify-content: center;
        }
        .story-scroll-zone::-webkit-scrollbar { display: none; }

        .story-block { width: 100%; text-align: center; display: none !important; padding: 10px 20px;                            max-height: fit-content;
            font-size: small; }
        .context-block { display: none !important; }

        .active-block {
            display: block !important;
            background: #1f2937; border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.5);
            border: 1px solid #374151; padding: 45px 40px; margin: auto 0;
            width: 100%;
                max-height: fit-content;
            font-size: small;
        }
        .active-block::before {
            content: "• CURRENT VERSE"; display: block; font-size: 0.65rem;
            font-weight: 800; color: #34d399; margin-bottom: 15px; letter-spacing: 0.08em; 
        }
        .active-block .french-text { font-size: 1.8rem; font-weight: 700; color: #ffffff !important; line-height: 1.4; }
        .active-block .translation-text { font-size: 1.2rem; color: #d1d5db !important; margin-top: 12px; line-height: 1.4; }

        .hover-control-bar {
            position: absolute !important;
            bottom: 0 !important;
            left: 0 !important;
            right: 0 !important;
            height: 95px !important;
            background-color: rgba(17, 24, 39, 0.95) !important;
            backdrop-filter: blur(10px);
            border-top: 1px solid #1f2937;
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding: 0 40px !important;
            z-index: 999999 !important;
        }
        
        .time-info { display: flex; gap: 30px; min-width: 180px; }
        .time-block { display: flex; flex-direction: column; }
        .time-label { font-size: 0.6rem; font-weight: bold; color: #6b7280; letter-spacing: 0.05em; }
        .time-value { font-size: 1.2rem; font-weight: bold; color: #f3f4f6; }

        .core-controls { display: flex; align-items: center; gap: 25px; }
        .main-play-btn {
            background: #3b82f6; border: none; color: white; border-radius: 50%;
            width: 52px; height: 52px; font-size: 1.1rem; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3);
        }
        .main-play-btn:hover { background: #60a5fa; }
        .skip-btn { background: none; border: none; font-size: 1.4rem; color: #9ca3af; cursor: pointer; }

        .extra-controls { display: flex; align-items: center; gap: 15px; min-width: 180px; justify-content: flex-end; }
        .speed-pill {
            background: #1f2937; padding: 8px 16px; border-radius: 20px;
            font-size: 0.8rem; font-weight: 700; color: #d1d5db; cursor: pointer; border: 1px solid #374151;
        }
        .mic-btn {
            background: #064e3b; color: #34d399; width: 38px; height: 38px;
            border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer;
        }
    </style>

    <script>
        const storyData = __JSON_DATA__;
        const container = document.getElementById('story-container');
        let currentTargetLangCode = 'nl';
        const translationCache = {}; 
        let currentActiveId = 0;

        storyData.forEach(line => {
            const div = document.createElement('div');
            div.id = `block-${line.id}`;
            div.className = 'story-block';
            div.onclick = () => jumpToTime(line.start);
            div.innerHTML = `
                <div class="french-text">${line.text_orig}</div>
                <div id="trans-${line.id}" class="translation-text">...</div>
            `;
            container.appendChild(div);
        });

        renderLimitedBlocks(0);

        function renderLimitedBlocks(activeId) {
            storyData.forEach(line => {
                const block = document.getElementById(`block-${line.id}`);
                if (!block) return;
                block.className = 'story-block';
                if (line.id === activeId) {
                    block.classList.add('active-block');
                } else if (line.id === activeId - 1 || line.id === activeId + 1) {
                    block.classList.add('context-block');
                }
            });
        }

        function toggleSettingsMenu() {
            const menu = document.getElementById('settings-menu');
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
        }
        function toggleSpeedMenu() {
            const menu = document.getElementById('speed-menu');
            menu.style.display = menu.style.display === 'block' ? 'none' : 'block';
        }

        window.onclick = function(event) {
            if (!event.target.matches('.settings-icon')) {
                document.getElementById('settings-menu').style.display = 'none';
            }
            if (!event.target.matches('#speed-trigger')) {
                document.getElementById('speed-menu').style.display = 'none';
            }
        }

        function changeSpeed(rate) {
            if (player && typeof player.setPlaybackRate === 'function') {
                player.setPlaybackRate(rate);
                document.getElementById('speed-trigger').innerHTML = `📝 ${rate}x`;
            }
        }

        function changeLanguage(code, label) {
            currentTargetLangCode = code;
            document.getElementById('display-target-lang').innerText = label;
            storyData.forEach(line => {
                const el = document.getElementById(`trans-${line.id}`);
                if (el) el.innerText = "...";
            });
            for (let key in translationCache) delete translationCache[key];
            manageRollingTranslations(currentActiveId, true);
        }

        async function translateTextGoogle(text, lang) {
            try {
                const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${lang}&dt=t&q=${encodeURIComponent(text)}`;
                const res = await fetch(url);
                const json = await res.json();
                if (json && json[0]) {
                    let translatedSentence = "";
                    json[0].forEach(part => { if (part[0]) translatedSentence += part[0]; });
                    return translatedSentence;
                }
                return "[Vertaling onbeschikbaar]";
            } catch (err) { return "[Verbindingsfout]"; }
        }

        async function manageRollingTranslations(activeId, force = false) {
            let start = Math.max(0, activeId - 1);
            let end = Math.min(storyData.length - 1, activeId + 1);
            for (let i = start; i <= end; i++) {
                const cacheKey = `${i}_${currentTargetLangCode}`;
                if (!(cacheKey in translationCache) || force) {
                    translationCache[cacheKey] = "processing";
                    translateTextGoogle(storyData[i].text_orig, currentTargetLangCode).then(translatedText => {
                        translationCache[cacheKey] = translatedText;
                        const el = document.getElementById(`trans-${i}`);
                        if (el) el.innerText = translatedText;
                    });
                }
            }
        }

        var tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

        var player;
        window.onYouTubeIframeAPIReady = function() {
            player = new YT.Player('player', {
                height: '1', width: '1', videoId: '__VIDEO_ID__',
                playerVars: { 'autoplay': 0, 'playsinline': 1, 'controls': 0 },
                events: { 'onStateChange': onPlayerStateChange }
            });
        }

        function togglePlayback() {
            if (!player || typeof player.getPlayerState !== 'function') return;
            if (player.getPlayerState() == YT.PlayerState.PLAYING) { player.pauseVideo(); } 
            else { player.playVideo(); }
        }

        function skipTime(seconds) {
            if (!player || typeof player.getCurrentTime !== 'function') return;
            player.seekTo(player.getCurrentTime() + seconds, true);
        }

        var timeChecker;
        function onPlayerStateChange(event) {
            const btn = document.getElementById('play-trigger-btn');
            if (event.data == YT.PlayerState.PLAYING) {
                timeChecker = setInterval(checkLiveSync, 100); 
                btn.innerHTML = "&#x23f8;"; 
            } else {
                clearInterval(timeChecker);
                btn.innerHTML = "&#x25b6;"; 
            }
        }

        function formatTime(seconds) {
            if (isNaN(seconds)) return "00:00";
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }

        function checkLiveSync() {
            if (!player || typeof player.getCurrentTime !== 'function') return;
            const currentTime = player.getCurrentTime();
            
            document.getElementById('time-elapsed').innerText = formatTime(currentTime);
            document.getElementById('time-total').innerText = formatTime(player.getDuration());
            
            const activeLine = storyData.find(line => currentTime >= line.start && currentTime <= line.end);
            if (activeLine && activeLine.id !== currentActiveId) {
                currentActiveId = activeLine.id;
                renderLimitedBlocks(activeLine.id);
                manageRollingTranslations(activeLine.id);
                
                const currentBlock = document.getElementById(`block-${activeLine.id}`);
                if (currentBlock) {
                    container.scrollTo({
                        top: currentBlock.offsetTop - (container.clientHeight / 2) + (currentBlock.clientHeight / 2),
                        behavior: 'smooth'
                    });
                }
            }
        }

        function jumpToTime(seconds) {
            if (player && typeof player.seekTo === 'function') { player.seekTo(seconds, true); }
        }
    </script>
    """
    
    custom_interface = custom_interface.replace("__JSON_DATA__", json_data).replace("__VIDEO_ID__", video_id)
    st.components.v1.html(custom_interface, height=700, scrolling=False)