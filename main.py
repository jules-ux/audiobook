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

# VASTE BESTANDSNAAM INSTELLEN
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
                tekst = " ".join(regels[tekst_start_index:])
                
                # STRIKTE CHECK: Moet verplicht starten met "chapitre"
                is_chapter = tekst.lower().strip().startswith("chapitre")
                
                data.append({
                    "id": idx,
                    "start": srt_tijd_naar_seconden(tijd_delen[0]),
                    "end": srt_tijd_naar_seconden(tijd_delen[1]),
                    "text_orig": tekst,
                    "is_chapter": is_chapter
                })
                idx += 1
    return data

# --- FASE 1: SETUP ---
if st.session_state['fase'] == 'setup':
    st.title("📚 AI Audioboek Bioscoop")
    
    if os.path.exists(VAST_SRT_BESTAND):
        st.success(f"🔗 Vaste transcriptie gekoppeld: `{VAST_SRT_BESTAND}`")
    else:
        st.error(f"❌ Bestand `{VAST_SRT_BESTAND}` niet gevonden!")

    youtube_url = st.text_input("1. Plak de YouTube URL:", "https://www.youtube.com/watch?v=B4s9iJBUqSE&t=91s")
    
    if st.button("🎬 Genereer Film & Start Prompter"):
        video_id = get_youtube_id(youtube_url)
        
        if video_id:
            if os.path.exists(VAST_SRT_BESTAND):
                with open(VAST_SRT_BESTAND, "r", encoding="utf-8") as f:
                    srt_inhoud = f.read()
                
                st.session_state['raw_srt_data'] = parse_srt_raw(srt_inhoud)
                st.session_state['active_video_id'] = video_id
                st.session_state['fase'] = 'loading'
                st.rerun()
            else:
                st.error("Kan niet starten: het vaste .srt-bestand ontbreekt.")

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
            
            <div class="middle-controls">
                <button class="menu-trigger-btn" onclick="toggleChaptersOverlay(event)">🔖 Hoofdstukken</button>

                <div class="language-selector">
                    <span class="lang-pill active-lang">AUTO-DETECT</span>
                    <span class="arrow-separator">&#x2192;</span>
                    <span id="display-target-lang" class="lang-pill target-lang">NEDERLANDS</span>
                </div>
            </div>

            <div class="settings-wrapper">
                <div class="settings-icon" onclick="toggleSettingsMenu(event)">&#x2699;</div>
                <div id="settings-menu" class="dropdown-menu">
                    <div class="dropdown-title">Vertaal Doeltaal</div>
                    <div class="dropdown-item" onclick="changeLanguage('nl', 'NEDERLANDS')">Nederlands</div>
                    <div class="dropdown-item" onclick="changeLanguage('en', 'ENGLISH')">English</div>
                    <div class="dropdown-item" onclick="changeLanguage('de', 'DEUTSCH')">Deutsch</div>
                    <div class="dropdown-item" onclick="changeLanguage('es', 'ESPAÑOL')">Español</div>
                </div>
            </div>
        </div>
        
        <div class="main-layout">
            <div id="chapters-overlay" class="chapters-overlay" onclick="closeChaptersOverlay()">
                <div class="sidebar-content" onclick="event.stopPropagation()">
                    <div class="sidebar-header">
                        <span class="sidebar-title">🔖 Hoofdstukken</span>
                        <button class="close-sidebar-btn" onclick="closeChaptersOverlay()">✕ Sluiten</button>
                    </div>
                    <div id="chapters-list-container" class="chapters-list">
                        </div>
                </div>
            </div>

            <div id="story-container" class="story-scroll-zone"></div>
        </div>

        <div class="hover-control-bar">
            <div class="progress-bar-container">
                <input type="range" id="timeline-slider" min="0" max="100" value="0" step="0.1" oninput="onSliderDrag(this.value)" onchange="onSliderRelease(this.value)">
            </div>

            <div class="controls-row">
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
                        <div id="speed-trigger" class="speed-pill" onclick="toggleSpeedMenu(event)">📝 1.0x</div>
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
            padding: 0 20px; background: #111827; border-bottom: 1px solid #1f2937; z-index: 9999;
        }
        .back-arrow { font-weight: 600; cursor: pointer; color: #3b82f6; }
        .middle-controls { display: flex; align-items: center; gap: 15px; }
        
        .menu-trigger-btn {
            background: #1f2937; border: 1px solid #374151; color: #ffffff;
            padding: 8px 16px; border-radius: 20px; font-weight: 600; font-size: 0.85rem;
            cursor: pointer; transition: background 0.2s;
        }
        .menu-trigger-btn:hover { background: #374151; }

        .language-selector { display: flex; align-items: center; gap: 6px; }
        .lang-pill { padding: 5px 10px; border-radius: 15px; font-size: 0.68rem; font-weight: 800; }
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

        /* VASTE HOOGTE VOOR DE LAYOUT ZONE */
        .main-layout {
            position: absolute; top: 70px; bottom: 115px; left: 0; right: 0;
            display: flex; overflow: hidden;
        }

        /* OVERLAY ZIJBALK SYSTEM */
        .chapters-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px);
            z-index: 99999; display: none; opacity: 0; transition: opacity 0.3s ease;
        }
        .chapters-overlay.open { display: block; opacity: 1; }
        
        .sidebar-content {
            position: absolute; top: 0; left: -340px; width: 340px; height: 100%;
            background: #111827; box-shadow: 10px 0 30px rgba(0,0,0,0.5);
            display: flex; flex-direction: column; padding: 20px 0;
            transition: left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .chapters-overlay.open .sidebar-content { left: 0; }

        @media (max-width: 480px) {
            .sidebar-content { width: 85%; left: -85%; }
        }

        .sidebar-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 0 20px 15px 20px; border-bottom: 1px solid #1f2937;
        }
        .sidebar-title { font-size: 1.1rem; font-weight: 700; color: #ffffff; }
        .close-sidebar-btn {
            background: #ef4444; border: none; color: white; padding: 6px 12px;
            border-radius: 8px; font-size: 0.8rem; font-weight: bold; cursor: pointer;
        }

        .chapters-list { flex: 1; overflow-y: auto; padding: 15px; }
        .chapter-sidebar-item {
            display: flex; align-items: center; justify-content: space-between;
            padding: 14px; margin-bottom: 8px; border-radius: 10px;
            background: #1f2937; border: 1px solid transparent; cursor: pointer;
        }
        .chapter-sidebar-item.current-active-chapter { border-color: #3b82f6; background: rgba(59, 130, 246, 0.15); }
        .chapter-title-text { font-size: 0.85rem; font-weight: 500; color: #d1d5db; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .chapter-sidebar-item.current-active-chapter .chapter-title-text { color: #60a5fa; font-weight: 700; }
        .status-badge { font-size: 0.95rem; color: #4b5563; }
        .status-badge.completed { color: #10b981; }

        /* PROMPTER SCROLL FLOW (Gecorrigeerd voor absolute hoogtebehoud) */
        .story-scroll-zone { 
            position: relative;
            width: 100%;
            height: 100%;
            overflow-y: scroll !important; 
            padding: 35vh 8% 45vh 8%; 
            background: #0b0f19; 
            scroll-behavior: smooth; 
        }
        .story-scroll-zone::-webkit-scrollbar { display: none; }

        .story-block { width: 100%; text-align: center; padding: 25px 30px; margin: 15px 0; border-radius: 16px; border: 1px solid transparent; cursor: pointer; opacity: 0.25; transition: all 0.4s ease; }
        .story-block:hover { opacity: 0.6; background: rgba(31, 41, 55, 0.3); border-color: #374151; }
        .chapter-marker-block { border-left: 4px solid #3b82f6 !important; font-style: italic; }

        .active-block { opacity: 1 !important; background: #1f2937; border-color: #374151; box-shadow: 0 20px 40px rgba(0,0,0,0.5); transform: scale(1.02); }
        .active-block::before { content: "• CURRENT VERSE"; display: block; font-size: 0.65rem; font-weight: 800; color: #34d399; margin-bottom: 12px; }
        
        .story-block .french-text { font-size: 1.6rem; font-weight: 700; color: #ffffff; line-height: 1.4; }
        .story-block .translation-text { font-size: 1.1rem; color: #9ca3af; margin-top: 10px; }
        .active-block .french-text { font-size: 2.1rem; }
        .active-block .translation-text { font-size: 1.4rem; color: #d1d5db !important; }

        /* TIMELINE CONTROLS */
        .hover-control-bar { position: absolute !important; bottom: 0 !important; left: 0 !important; right: 0 !important; height: 115px !important; background-color: rgba(17, 24, 39, 0.95) !important; backdrop-filter: blur(10px); border-top: 1px solid #1f2937; display: flex !important; flex-direction: column !important; justify-content: center !important; padding: 0 20px !important; z-index: 999999 !important; }
        .progress-bar-container { width: 100%; margin-bottom: 10px; display: flex; align-items: center; }
        #timeline-slider { width: 100%; -webkit-appearance: none; background: #374151; height: 6px; border-radius: 3px; outline: none; cursor: pointer; }
        #timeline-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 14px; height: 14px; border-radius: 50%; background: #3b82f6; }

        .controls-row { display: flex; justify-content: space-between; align-items: center; width: 100%; }
        .time-info { display: flex; gap: 15px; min-width: 140px; }
        .time-block { display: flex; flex-direction: column; }
        .time-label { font-size: 0.55rem; font-weight: bold; color: #6b7280; }
        .time-value { font-size: 1.1rem; font-weight: bold; color: #f3f4f6; }

        .core-controls { display: flex; align-items: center; gap: 20px; }
        .main-play-btn { background: #3b82f6; border: none; color: white; border-radius: 50%; width: 50px; height: 50px; font-size: 1.1rem; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3); }
        .skip-btn { background: none; border: none; font-size: 1.3rem; color: #9ca3af; cursor: pointer; }
        .extra-controls { display: flex; align-items: center; gap: 15px; min-width: 140px; justify-content: flex-end; }
        .speed-pill { background: #1f2937; padding: 6px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; color: #d1d5db; cursor: pointer; border: 1px solid #374151; }
        .mic-btn { background: #064e3b; color: #34d399; width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; }
    </style>

    <script>
        const storyData = __JSON_DATA__;
        const videoId = '__VIDEO_ID__';
        
        const container = document.getElementById('story-container');
        const sidebarContainer = document.getElementById('chapters-list-container');
        const slider = document.getElementById('timeline-slider');
        
        let currentTargetLangCode = 'nl';
        const translationCache = {}; 
        let currentActiveId = null;
        let isDraggingSlider = false;

        // LOCALSTORAGE KEYS
        const storageKeyChapters = `completed_chapters_${videoId}`;
        const storageKeyTime = `last_time_${videoId}`;
        
        let completedChapters = JSON.parse(localStorage.getItem(storageKeyChapters)) || [];
        const chaptersList = storyData.filter(line => line.is_chapter);

        // Bouw prompter
        storyData.forEach(line => {
            const div = document.createElement('div');
            div.id = `block-${line.id}`;
            div.className = 'story-block';
            if (line.is_chapter) div.classList.add('chapter-marker-block');
            div.onclick = () => jumpToTime(line.start);
            div.innerHTML = `
                <div class="french-text">${line.text_orig}</div>
                <div id="trans-${line.id}" class="translation-text">...</div>
            `;
            container.appendChild(div);
        });

        // Zijbalk Rendering
        function renderSidebarChapters() {
            sidebarContainer.innerHTML = '';
            chaptersList.forEach((chap) => {
                const isDone = completedChapters.includes(chap.id);
                const item = document.createElement('div');
                item.id = `sidebar-chap-${chap.id}`;
                item.className = 'chapter-sidebar-item';
                item.onclick = () => {
                    jumpToTime(chap.start);
                    closeChaptersOverlay();
                };
                item.innerHTML = `
                    <div class="chapter-title-text" title="${chap.text_orig}">${chap.text_orig}</div>
                    <div id="badge-${chap.id}" class="status-badge ${isDone ? 'completed' : ''}">
                        ${isDone ? '&#x2714;' : '&#x25cb;'}
                    </div>
                `;
                sidebarContainer.appendChild(item);
            });
        }

        // OVERLAY FUNCTIONS
        function toggleChaptersOverlay(e) {
            e.stopPropagation();
            closeAllMenus();
            const overlay = document.getElementById('chapters-overlay');
            overlay.classList.toggle('open');
        }
        function closeChaptersOverlay() {
            document.getElementById('chapters-overlay').classList.remove('open');
        }

        renderSidebarChapters();

        // EXACTE CENTERING SCROLL MECHANISME HERSTELD
        function syncActiveBlock(activeId) {
            if (currentActiveId === activeId) return;
            currentActiveId = activeId;

            storyData.forEach(line => {
                const block = document.getElementById(`block-${line.id}`);
                if (block) {
                    if (line.id === activeId) block.classList.add('active-block');
                    else block.classList.remove('active-block');
                }
            });

            manageRollingTranslations(activeId);

            const currentLine = storyData.find(l => l.id === activeId);
            if (currentLine) {
                let activeChap = null;
                for (let i = 0; i < chaptersList.length; i++) {
                    const chap = chaptersList[i];
                    const nextChap = chaptersList[i + 1];
                    
                    if (currentLine.start >= chap.start) {
                        activeChap = chap;
                        if (nextChap && currentLine.start >= nextChap.start) {
                            if (!completedChapters.includes(chap.id)) {
                                completedChapters.push(chap.id);
                                localStorage.setItem(storageKeyChapters, JSON.stringify(completedChapters));
                                renderSidebarChapters();
                            }
                        }
                    }
                }

                document.querySelectorAll('.chapter-sidebar-item').forEach(el => el.classList.remove('current-active-chapter'));
                if (activeChap) {
                    const activeSidebarItem = document.getElementById(`sidebar-chap-${activeChap.id}`);
                    if (activeSidebarItem) activeSidebarItem.classList.add('current-active-chapter');
                }
            }

            // Gecorrigeerde scroll-to-center berekening
            const currentBlock = document.getElementById(`block-${activeId}`);
            if (currentBlock) {
                const targetScrollTop = currentBlock.offsetTop - (container.offsetHeight / 2) + (currentBlock.offsetHeight / 2);
                container.scrollTo({
                    top: targetScrollTop,
                    behavior: 'smooth'
                });
            }
        }

        function toggleSettingsMenu(e) { e.stopPropagation(); closeAllMenus(); const menu = document.getElementById('settings-menu'); menu.style.display = menu.style.display === 'block' ? 'none' : 'block'; }
        function toggleSpeedMenu(e) { e.stopPropagation(); closeAllMenus(); const menu = document.getElementById('speed-menu'); menu.style.display = menu.style.display === 'block' ? 'none' : 'block'; }
        function closeAllMenus() { document.getElementById('settings-menu').style.display = 'none'; document.getElementById('speed-menu').style.display = 'none'; }
        window.onclick = function() { closeAllMenus(); }

        function changeSpeed(rate) { if (player && typeof player.setPlaybackRate === 'function') { player.setPlaybackRate(rate); document.getElementById('speed-trigger').innerHTML = `📝 ${rate}x`; } }

        function changeLanguage(code, label) {
            currentTargetLangCode = code;
            document.getElementById('display-target-lang').innerText = label;
            storyData.forEach(line => { const el = document.getElementById(`trans-${line.id}`); if (el) el.innerText = "..."; });
            for (let key in translationCache) delete translationCache[key];
            manageRollingTranslations(currentActiveId, true);
        }

        async function translateTextGoogle(text, lang) {
            try {
                const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${lang}&dt=t&q=${encodeURIComponent(text)}`;
                const res = await fetch(url); const json = await res.json();
                if (json && json[0]) {
                    let trans = ""; json[0].forEach(p => { if (p[0]) trans += p[0]; }); return trans;
                }
                return "[Vertaling onbeschikbaar]";
            } catch (err) { return "[Verbindingsfout]"; }
        }

        async function manageRollingTranslations(activeId, force = false) {
            let start = Math.max(0, activeId - 2); let end = Math.min(storyData.length - 1, activeId + 3);
            for (let i = start; i <= end; i++) {
                const cacheKey = `${i}_${currentTargetLangCode}`;
                if (!(cacheKey in translationCache) || force) {
                    translationCache[cacheKey] = "processing";
                    translateTextGoogle(storyData[i].text_orig, currentTargetLangCode).then(txt => {
                        translationCache[cacheKey] = txt; const el = document.getElementById(`trans-${i}`); if (el) el.innerText = txt;
                    });
                }
            }
        }

        // YOUTUBE PLAYER CONFIG
        var tag = document.createElement('script'); tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0]; firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

        var player;
        window.onYouTubeIframeAPIReady = function() {
            player = new YT.Player('player', {
                height: '1', width: '1', videoId: videoId,
                playerVars: { 'autoplay': 0, 'playsinline': 1, 'controls': 0 },
                events: { 
                    'onStateChange': onPlayerStateChange,
                    'onReady': onPlayerReady
                }
            });
        }

        function onPlayerReady() {
            const savedTime = localStorage.getItem(storageKeyTime);
            if (savedTime) {
                const targetSec = parseFloat(savedTime);
                jumpToTime(targetSec);
            } else {
                syncActiveBlock(0);
            }
        }

        function togglePlayback() {
            if (!player || typeof player.getPlayerState !== 'function') return;
            if (player.getPlayerState() == YT.PlayerState.PLAYING) player.pauseVideo(); else player.playVideo();
        }

        function skipTime(seconds) { if (!player || typeof player.getCurrentTime !== 'function') return; jumpToTime(player.getCurrentTime() + seconds); }

        var timeChecker;
        function onPlayerStateChange(event) {
            const btn = document.getElementById('play-trigger-btn');
            if (event.data == YT.PlayerState.PLAYING) {
                timeChecker = setInterval(checkLiveSync, 100); btn.innerHTML = "&#x23f8;"; 
            } else {
                clearInterval(timeChecker); btn.innerHTML = "&#x25b6;"; 
            }
        }

        function formatTime(seconds) {
            if (isNaN(seconds)) return "00:00";
            const mins = Math.floor(seconds / 60); const secs = Math.floor(seconds % 60);
            return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }

        function checkLiveSync() {
            if (!player || typeof player.getCurrentTime !== 'function' || isDraggingSlider) return;
            
            const currentTime = player.getCurrentTime();
            const duration = player.getDuration();
            
            document.getElementById('time-elapsed').innerText = formatTime(currentTime);
            document.getElementById('time-total').innerText = formatTime(duration);
            
            if (currentTime > 0) {
                localStorage.setItem(storageKeyTime, currentTime);
            }
            
            if (duration > 0) {
                slider.value = (currentTime / duration) * 100;
            }
            
            const activeLine = storyData.find(line => currentTime >= line.start && currentTime <= line.end);
            if (activeLine) {
                syncActiveBlock(activeLine.id);
            }
        }

        function onSliderDrag(value) {
            isDraggingSlider = true;
            if (!player || typeof player.getDuration !== 'function') return;
            const targetTime = (value / 100) * player.getDuration();
            document.getElementById('time-elapsed').innerText = formatTime(targetTime);
        }

        function onSliderRelease(value) {
            isDraggingSlider = false;
            if (!player || typeof player.getDuration !== 'function') return;
            const targetTime = (value / 100) * player.getDuration();
            jumpToTime(targetTime);
        }

        function jumpToTime(seconds) {
            if (player && typeof player.seekTo === 'function') { 
                player.seekTo(seconds, true);
                localStorage.setItem(storageKeyTime, seconds);
                const activeLine = storyData.find(line => seconds >= line.start && seconds <= line.end);
                if (activeLine) syncActiveBlock(activeLine.id);
            }
        }
    </script>
    """
    
    custom_interface = custom_interface.replace("__JSON_DATA__", json_data).replace("__VIDEO_ID__", video_id)
    st.components.v1.html(custom_interface, height=700, scrolling=False)