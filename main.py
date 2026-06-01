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

# --- DEFINIEER DE BOEKENBIBLIOTHEEK ---
BOEKEN_DATABASE = [
    {
        "id": "boek_1",
        "titel": "La Faiseuse d'étoiles",
        "auteur": "Mélissa Da Costa",
        "youtube_url": "https://www.youtube.com/watch?v=B4s9iJBUqSE",
        "srt_bestand": "transscriptie_film.srt",
        "cover_emoji": "🚀",
        "tijd_offset": 0.0  
    },
    {
        "id": "boek_2",
        "titel": "Un secret",
        "auteur": "Philippe GRIMBERT",
        "youtube_url": "https://www.youtube.com/watch?v=dIKudSy7d-U",
        "srt_bestand": "youtube_video_transcript.srt",
        "cover_emoji": "🔍",
        "tijd_offset": 0.0
    },
]

# --- INITIALISEER SESSION STATE ---
if 'fase' not in st.session_state:
    st.session_state['fase'] = 'setup'
if 'raw_srt_data' not in st.session_state:
    st.session_state['raw_srt_data'] = None
if 'active_video_id' not in st.session_state:
    st.session_state['active_video_id'] = ""
if 'active_book_title' not in st.session_state:
    st.session_state['active_book_title'] = ""

def get_youtube_id(url):
    match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', url)
    return match.group(1) if match else None

def srt_tijd_naar_seconden(tijd_str):
    tijd_str = tijd_str.strip().replace(',', '.')
    delen = tijd_str.split(':')
    return (int(delen[0]) * 3600) + (int(delen[1]) * 60) + float(delen[2])

def parse_srt_raw(srt_tekst, offset=0.0):
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
                
                is_chapter = tekst.lower().strip().startswith("chapitre") or tekst.lower().strip().startswith("chapter")
                
                start_tijd = max(0.0, srt_tijd_naar_seconden(tijd_delen[0]) + offset)
                end_tijd = max(0.0, srt_tijd_naar_seconden(tijd_delen[1]) + offset)
                
                data.append({
                    "id": idx,
                    "start": start_tijd,
                    "end": end_tijd,
                    "text_orig": tekst,
                    "is_chapter": is_chapter
                })
                idx += 1
    return data

# --- FASE 1: SETUP (DASHBOARD - READIUM STIJL) ---
if st.session_state['fase'] == 'setup':
    st.markdown("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;700;800&family=Inter:wght@400;600;700&display=swap');
            
            /* Algemene achtergrond */
            html, body, [data-testid="stAppViewContainer"] {
                background-color: #F4F0E6 !important; 
                font-family: 'Nunito', sans-serif;
                color: #2B2D42;
            }
            
            /* Header Styling */
            .header-container {
                text-align: center;
                padding: 40px 20px 30px 20px;
            }
            .main-title { 
                color: #2B2D42; 
                font-weight: 800; 
                font-size: 3.2rem; 
                margin-bottom: 8px; 
                line-height: 1.2;
            }
            .sub-title { 
                color: #6C757D; 
                font-size: 1.1rem; 
                font-family: 'Inter', sans-serif;
            }
            
            /* Kaart Styling */
            .book-card {
                background: #FFFFFF; 
                border-radius: 24px; 
                padding: 30px; 
                margin-bottom: 15px; 
                display: flex; 
                gap: 20px; 
                align-items: center; 
                box-shadow: 0 10px 30px rgba(0,0,0,0.03); 
                position: relative; 
                overflow: hidden;
            }
            .book-card-deco {
                position: absolute; 
                top: -20px; right: -20px; 
                width: 80px; height: 80px; 
                background-color: #F4A261; 
                border-radius: 50%; 
                opacity: 0.8;
            }
            .book-cover {
                font-size: 4rem; 
                background: #F4F0E6; 
                min-width: 100px; 
                height: 130px; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                border-radius: 16px; 
                box-shadow: 0 4px 10px rgba(0,0,0,0.05); 
                z-index: 1;
            }
            .book-info {
                flex: 1; 
                z-index: 1;
            }
            .book-title {
                margin: 0; 
                color: #2B2D42; 
                font-size: 1.5rem; 
                font-weight: 800;
            }
            .book-author {
                margin: 4px 0 15px 0; 
                color: #6C757D; 
                font-size: 0.95rem; 
                font-family: "Inter", sans-serif;
            }
            .book-badge {
                background: #F4F0E6; 
                color: #2B2D42; 
                padding: 6px 12px; 
                border-radius: 20px; 
                font-size: 0.75rem; 
                font-weight: 700; 
                font-family: "Inter", sans-serif; 
                display: inline-block; 
                margin-bottom: 8px;
            }
            .progress-indicator { 
                font-size: 0.85rem; 
                color: #F4A261; 
                font-weight: 700; 
                margin-top: 8px; 
                font-family: 'Inter', sans-serif;
            }
            
            /* Streamlit Knoppen overschrijven naar Navy Blue */
            div.stButton > button {
                background-color: #2B2D42 !important;
                color: #FFFFFF !important;
                border-radius: 30px !important;
                border: none !important;
                padding: 10px 24px !important;
                font-weight: 700 !important;
                width: 100% !important;
                box-shadow: 0 4px 10px rgba(43, 45, 66, 0.2) !important;
                transition: all 0.3s ease !important;
            }
            div.stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 15px rgba(43, 45, 66, 0.3) !important;
            }

            /* --- Mobiele Responsiviteit --- */
            @media (max-width: 768px) {
                .main-title { 
                    font-size: 2.2rem; 
                }
                .book-card {
                    flex-direction: column;
                    text-align: center;
                    padding: 25px 20px;
                }
                .book-cover {
                    min-width: 100%;
                    height: 120px;
                }
                .header-container {
                    padding: 30px 10px 20px 10px;
                }
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Geïntegreerde Header
    st.markdown("""
        <div class='header-container'>
            <h1 class='main-title'>Readium Sync</h1>
            <p class='sub-title'>Start reading your favorite books today!</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Streamlit kolommen (stapelen automatisch op mobiel)
    cols = st.columns(2)
    
    for i, boek in enumerate(BOEKEN_DATABASE):
        with cols[i % 2]:
            card_html = f"""
            <div class="book-card">
                <div class="book-card-deco"></div>
                <div class="book-cover">{boek['cover_emoji']}</div>
                <div class="book-info">
                    <h3 class="book-title">{boek['titel']}</h3>
                    <p class="book-author">By {boek['auteur']}</p>
                    <span class="book-badge">📄 {boek['srt_bestand']}</span>
                    <div id="dashboard-progress-{get_youtube_id(boek['youtube_url'])}" class="progress-indicator">⏱️ Loading...</div>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            if st.button(f"Continue reading", key=f"btn_{boek['id']}"):
                video_id = get_youtube_id(boek['youtube_url'])
                if video_id:
                    if os.path.exists(boek['srt_bestand']):
                        with open(boek['srt_bestand'], "r", encoding="utf-8") as f:
                            srt_inhoud = f.read()
                        
                        st.session_state['raw_srt_data'] = parse_srt_raw(srt_inhoud, offset=boek.get('tijd_offset', 0.0))
                        st.session_state['active_video_id'] = video_id
                        st.session_state['active_book_title'] = boek['titel']
                        st.session_state['fase'] = 'loading'
                        st.rerun()
                    else:
                        st.error(f"Fout: Kan `{boek['srt_bestand']}` niet vinden.")

    # Script om de voortgang op te halen uit localStorage
    html_progress_reader = """
    <script>
        setTimeout(() => {
            const divs = window.parent.document.querySelectorAll('[id^="dashboard-progress-"]');
            divs.forEach(div => {
                const vId = div.id.replace('dashboard-progress-', '');
                const savedTime = window.parent.localStorage.getItem(`last_time_${vId}`);
                if(savedTime) {
                    const mins = Math.floor(parseFloat(savedTime) / 60);
                    const secs = Math.floor(parseFloat(savedTime) % 60);
                    div.innerHTML = `⏱️ Resuming from: ${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                } else {
                    div.innerHTML = `⏱️ Start reading`;
                }
            });
        }, 300);
    </script>
    """
    st.components.v1.html(html_progress_reader, height=0)

# --- FASE 2: LOADING SCREEN ---
elif st.session_state['fase'] == 'loading':
    st.markdown("<div style='text-align: center; margin-top: 30vh;'><h3 style='color: #2B2D42; font-family: Nunito;'>⏳ Preparing your book...</h3></div>", unsafe_allow_html=True)
    time.sleep(0.4)
    st.session_state['fase'] = 'theater'
    st.rerun()

# --- FASE 3: THEATER EN AUTOMATISCHE PROMPTER (LIRE EN SYNC STIJL) ---
elif st.session_state['fase'] == 'theater':
    st.markdown("""
        <style>
            html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"], .main, .block-container {
                overflow: hidden !important;
                height: 100vh !important;
                max-height: 100vh !important;
                margin: 0 !important;
                padding: 0 !important;
                background-color: #F8F9FA !important; /* Lichte achtergrond */
            }
            header, footer, [data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
            section[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
            [data-testid="stHtmlBlock"] { padding: 0 !important; margin: 0 !important; height: 100vh !important; }
        </style>
    """, unsafe_allow_html=True)

    json_data = json.dumps(st.session_state['raw_srt_data']).replace("'", "\\'")
    video_id = st.session_state['active_video_id']
    boek_titel = st.session_state['active_book_title']

    custom_interface = f"""
    <div class="app-container">
        <div style="width: 1px; height: 1px; opacity: 0; overflow: hidden; position: absolute;">
            <div id="player"></div>
        </div>

        <div class="top-bar">
            <div class="top-header">
                <div class="back-area">
                    <div class="back-arrow" onclick="gaTerugNaarDashboard();">&#x2190;</div>
                    <div class="current-chapter-label" id="current-chapter-label">Huidig hoofdstuk</div>
                </div>
                <button id="open-settings-btn" class="btn-secondary" onclick="openSettings()">Instellingen</button>
            </div>

            <div class="progress-summary">
                <div class="progress-label">Voortgang</div>
                <div class="progress-bar-wrapper">
                    <input type="range" id="timeline-slider" min="0" max="100" value="0" step="0.1" oninput="onSliderDrag(this.value)" onchange="onSliderRelease(this.value)">
                </div>
            </div>
        </div>

        <div id="settings-overlay" class="settings-overlay">
            <div class="overlay-panel">
                <div class="overlay-header">
                    <div class="back-arrow" onclick="closeSettings();">&#x2190;</div>
                    <div class="overlay-title">Instellingen</div>
                </div>
                <div class="overlay-info">
                    <div class="overlay-current-chapter" id="overlay-current-chapter">Huidig hoofdstuk</div>
                    <div class="overlay-progress-text" id="overlay-progress-text">0%</div>
                </div>
                <div class="overlay-controls">
                    <div class="overlay-buttons-group">
                        <button id="play-trigger-btn" class="btn-play" onclick="togglePlayback()">Play</button>
                        <button class="btn-secondary" onclick="skipTime(-10)">-10s</button>
                        <button class="btn-secondary" onclick="skipTime(10)">+10s</button>
                        <button class="btn-secondary" onclick="changeSpeed(0.75, event)">0.75x</button>
                        <button id="speed-indicator" class="btn-active" onclick="changeSpeed(1.0, event)">1x</button>
                        <button class="btn-secondary" onclick="changeSpeed(1.25, event)">1.25x</button>
                        <button class="btn-secondary" onclick="changeSpeed(1.5, event)">1.5x</button>
                        <button class="btn-secondary" style="background: #EDE9FE; color: #5B21B6; border: 1px solid #DDD6FE;" onclick="toggleChapters()">Hoofdstukken 📖</button>
                    </div>
                    <div id="overlay-chapters" class="overlay-chapters-menu">
                        <div class="chapters-menu-header">📚 Alle Hoofdstukken</div>
                        <div id="chapters-list" class="chapters-menu-list"></div>
                    </div>
                </div>
            </div>
        </div>

        <div class="main-layout">
            <div id="story-container" class="story-scroll-zone"></div>
        </div>
    </div>

    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html, body {{ background-color: #F8F9FA; overflow: hidden !important; height: 100vh !important; width: 100vw !important; }}

        .app-container {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #111827;
            background-color: #F8F9FA;
            height: 100vh !important;
            width: 100vw !important;
            position: relative;
            overflow: hidden !important;
            display: flex;
            flex-direction: column;
        }}

        /* TOP BAR STYLING */
        .top-bar {{
            background: #FFFFFF; 
            border-bottom: 1px solid #E5E7EB; 
            padding: 15px 30px 0 30px;
            z-index: 9999;
            box-shadow: 0 4px 6px rgba(0,0,0,0.02);
        }}
        
        .top-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 15px;
        }}
        .back-arrow {{ font-weight: 800; font-size: 1.5rem; cursor: pointer; color: #111827; display: flex; align-items: center; gap: 10px; }}
        .video-title {{ font-size: 1.8rem; font-weight: 800; letter-spacing: -0.5px; }}
        .lang-info {{ color: #4B5563; font-weight: 500; font-size: 0.95rem; }}

        .control-row {{
            display: none;
        }}
        
        .top-header {{
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 15px;
        }}
        .back-area {{
            display: flex; align-items: center; gap: 14px;
        }}
        .current-chapter-label, .overlay-current-chapter {{
            font-size: 1rem; color: #111827; font-weight: 700;
            max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .progress-summary {{
            display: flex; flex-direction: column; gap: 8px;
            margin-bottom: 8px;
        }}
        .progress-label {{ color: #6B7280; font-size: 0.85rem; font-weight: 600; }}
        .progress-bar-wrapper {{ width: 100%; }}
        .overlay-info {{ padding: 16px 20px; border-bottom: 1px solid #E5E7EB; }}
        .overlay-progress-text {{ color: #6B7280; font-size: 0.9rem; margin-top: 8px; }}
        .overlay-controls {{ padding: 16px 20px 24px; }}
        .overlay-buttons-group {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
        .settings-overlay {{
            position: fixed; inset: 0;
            display: none; align-items: center; justify-content: center;
            background: rgba(15, 23, 42, 0.45);
            z-index: 10001;
            padding: 16px;
        }}
        .settings-overlay.open {{ display: flex; }}
        .overlay-panel {{
            width: 100%; max-width: 650px;
            background: #FFFFFF;
            border-radius: 24px;
            box-shadow: 0 24px 80px rgba(15, 23, 42, 0.22);
            overflow: hidden;
            animation: appear 0.18s ease-out;
        }}
        @keyframes appear {{
            from {{ opacity: 0; transform: translateY(12px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .overlay-header {{ display: flex; align-items: center; justify-content: space-between; padding: 20px; gap: 12px; }}
        .overlay-title {{ font-size: 1rem; font-weight: 800; color: #111827; }}
        .overlay-current-chapter {{ font-size: 1rem; font-weight: 700; color: #111827; }}
        .overlay-progress-text {{ font-size: 0.95rem; color: #4B5563; }}
        .overlay-buttons-group button {{ width: 100%; }}
        
        .buttons-group {{ display: flex; gap: 8px; align-items: center; position: relative; }}
        
        .btn-play {{
            background: #A855F7; color: white; border: none; border-radius: 20px;
            padding: 8px 24px; font-weight: 600; font-size: 0.9rem; cursor: pointer;
            box-shadow: 0 2px 5px rgba(168, 85, 247, 0.3); transition: all 0.2s;
        }}
        .btn-play:hover {{ background: #9333EA; }}
        
        .btn-secondary, .btn-active {{
            background: #F3E8FF; color: #6B21A8; border: 1px solid #E9D5FF;
            border-radius: 20px; padding: 6px 14px; font-weight: 600; font-size: 0.85rem;
            cursor: pointer; transition: all 0.2s;
        }}
        .btn-secondary:hover {{ background: #E9D5FF; }}
        .btn-active {{ background: #A855F7; color: white; border: none; }}

        .sentence-counter {{ color: #4B5563; font-weight: 500; font-size: 0.9rem; }}

        .progress-bar-container {{ width: 100%; display: flex; align-items: center; padding-bottom: 10px; }}
        #timeline-slider {{ width: 100%; -webkit-appearance: none; background: #E5E7EB; height: 8px; border-radius: 999px; outline: none; cursor: pointer; }}
        #timeline-slider::-webkit-slider-thumb {{ -webkit-appearance: none; appearance: none; width: 16px; height: 16px; border-radius: 50%; background: #A855F7; }}

        /* STYLING VOOR HOOFDSTUKKEN DROPDOWN */
        .overlay-chapters-menu {{
            position: relative;
            width: 100%;
            max-height: 300px;
            background: #FFFFFF;
            border: 1px solid #E5E7EB;
            border-radius: 20px;
            display: none;
            flex-direction: column;
            overflow: hidden;
            margin-top: 16px;
            animation: fadeIn 0.18s ease-out;
        }}
        .overlay-chapters-menu.open {{ display: flex; }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .chapters-menu-header {{
            padding: 14px 20px;
            font-weight: 800;
            background: #F9FAFB;
            border-bottom: 1px solid #E5E7EB;
            font-size: 1rem;
            color: #111827;
        }}
        .chapters-menu-list {{
            overflow-y: auto;
            flex: 1;
        }}
        .chapter-item {{
            padding: 12px 20px;
            font-size: 0.95rem;
            color: #374151;
            cursor: pointer;
            border-bottom: 1px solid #F3F4F6;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .chapter-item:hover {{
            background: #F3E8FF;
            color: #6B21A8;
            padding-left: 25px;
        }}

        .main-layout {{
            flex: 1;
            display: flex; overflow: hidden;
            background: #F8F9FA;
        }}

        /* PROMPTER CARDS STYLING (LIRE EN SYNC) */
        .story-scroll-zone {{ 
            position: relative; width: 100%; height: 100%;
            overflow-y: scroll !important; padding: 25vh 10% 45vh 10%; 
            scroll-snap-type: y mandatory;
        }}
        .story-scroll-zone::-webkit-scrollbar {{ display: none; }}

        .story-block {{ 
            width: 100%; padding: 32px; margin: 18px 0; 
            border-radius: 24px; border: 1px solid transparent; 
            cursor: pointer; opacity: 0.4; transition: all 0.4s ease-in-out; 
            background: #F3F4F6; /* Lichte grijze kaart inactief */
            scroll-snap-align: center;
        }}
        .story-block:hover {{ opacity: 0.8; background: #FFFFFF; border-color: #E5E7EB; }}

        .active-block {{ 
            opacity: 1 !important; 
            background: #FFFFFF; 
            border: 1px solid #F3E8FF; 
            box-shadow: 0 10px 40px rgba(168, 85, 247, 0.08); 
            transform: scale(1.01); 
        }}
        
        .french-text {{ font-size: 1.8rem; font-weight: 700; color: #111827; line-height: 1.4; transition: all 0.3s; }}
        .translation-text {{ font-size: 1rem; color: #6B7280; margin-top: 15px; font-weight: 500; transition: all 0.3s; }}
        
        .active-block .french-text {{ font-size: 2.2rem; letter-spacing: -0.5px; color: #000000; }}
        .active-block .translation-text {{ font-size: 1.25rem; color: #4B5563 !important; }}

        /* Icoontje voor actieve regel */
        .icon-lu {{
            display: none; background: #FCD34D; color: #92400E; 
            font-size: 1rem; font-weight: bold; padding: 4px 8px; 
            border-radius: 8px; margin-right: 15px; vertical-align: middle;
        }}
        .active-block .icon-lu {{ display: inline-block; }}

        /* Mobile adjustments */
        @media (max-width: 768px) {{
            .top-bar {{
                padding: 12px 16px 0 16px;
            }}
            .top-header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }}
            .back-arrow {{ font-size: 1.2rem; }}
            .video-title {{ font-size: 1.25rem; }}
            .lang-info {{ font-size: 0.85rem; }}
            .control-row {{
                flex-direction: column;
                align-items: stretch;
                gap: 10px;
            }}
            .url-bar-fake {{
                max-width: 100%;
                font-size: 0.8rem;
                padding: 8px 12px;
            }}
            .buttons-group {{
                flex-wrap: wrap;
                gap: 6px;
            }}
            .btn-play, .btn-secondary, .btn-active {{
                padding: 8px 12px;
                font-size: 0.8rem;
            }}
            .sentence-counter {{ font-size: 0.85rem; }}
            .overlay-chapters-menu {{
                width: 100%;
                max-height: 220px;
            }}
            .story-scroll-zone {{
                padding: 18vh 6% 40vh 6%;
            }}
            .story-block {{
                padding: 24px;
            }}
            .french-text {{ font-size: 1.2rem; }}
            .translation-text {{ font-size: 0.95rem; }}
            .active-block .french-text {{ font-size: 1.5rem; }}
            .active-block .translation-text {{ font-size: 1.05rem; }}
        }}

    </style>

    <script>
        const storyData = {json_data};
        const videoId = '{video_id}';
        const totalSentences = storyData.length;
        
        const container = document.getElementById('story-container');
        const slider = document.getElementById('timeline-slider');
        const currentChapterLabel = document.getElementById('current-chapter-label');
        const overlayCurrentChapter = document.getElementById('overlay-current-chapter');
        const overlayProgressText = document.getElementById('overlay-progress-text');
        const overlayChapters = document.getElementById('overlay-chapters');
        
        let currentTargetLangCode = 'nl';
        const translationCache = {{}}; 
        let currentActiveId = null;
        let currentActiveBlockEl = null;
        let isDraggingSlider = false;
        let scrollAnimationId = null;
        const blockElements = new Map();

        const storageKeyTime = `last_time_${{videoId}}`;
        const storageKeyLang = `target_lang_${{videoId}}`;

        const savedLang = localStorage.getItem(storageKeyLang);
        if(savedLang) {{
            currentTargetLangCode = savedLang;
        }}

        function gaTerugNaarDashboard() {{
            window.parent.location.reload();
        }}

        // Render de witte kaarten
        storyData.forEach((line, index) => {{
            const div = document.createElement('div');
            div.id = `block-${{line.id}}`;
            div.className = 'story-block';
            div.onclick = () => jumpToTime(line.start);
            div.innerHTML = `
                <div class="french-text"><span class="icon-lu">lu</span>${{line.text_orig}}</div>
                <div id="trans-${{line.id}}" class="translation-text">...</div>
            `;
            container.appendChild(div);
            blockElements.set(line.id, div);
        }});

        // --- APART SCROLL MECHANISME MET CUBIC EASE-OUT VERTRAGING ---
        function smoothScrollTo(targetY, duration) {{
            if (scrollAnimationId) cancelAnimationFrame(scrollAnimationId);
            
            const startY = container.scrollTop;
            const distance = targetY - startY;
            let startTime = null;

            function easeOutCubic(t) {{
                return 1 - Math.pow(1 - t, 3);
            }}

            function animation(currentTime) {{
                if (startTime === null) startTime = currentTime;
                const timeElapsed = currentTime - startTime;
                const progress = Math.min(timeElapsed / duration, 1);
                
                container.scrollTop = startY + distance * easeOutCubic(progress);

                if (progress < 1) {{
                    scrollAnimationId = requestAnimationFrame(animation);
                }}
            }}
            scrollAnimationId = requestAnimationFrame(animation);
        }}

        function syncActiveBlock(activeId) {{
            if (currentActiveId === activeId) return;
            const prevActiveId = currentActiveId;
            currentActiveId = activeId;

            if (prevActiveId !== null && prevActiveId !== undefined) {{
                const prevBlock = blockElements.get(prevActiveId);
                if (prevBlock) prevBlock.classList.remove('active-block');
            }}
            currentActiveBlockEl = blockElements.get(activeId);
            if (currentActiveBlockEl) currentActiveBlockEl.classList.add('active-block');
            
            updateCurrentChapterLabel(activeId);
            updateProgressUI();
            manageRollingTranslations(activeId);

            const currentLine = storyData.find(l => l.id === activeId);
            
            if (currentActiveBlockEl && !isDraggingSlider) {{
                const targetScrollTop = currentActiveBlockEl.offsetTop - (container.offsetHeight / 2) + (currentActiveBlockEl.offsetHeight / 2);
                let duration = 800;
                if (currentLine && typeof player !== 'undefined' && typeof player.getCurrentTime === 'function') {{
                    const resterendeTijd = currentLine.end - player.getCurrentTime();
                    if (resterendeTijd > 0) {{
                        duration = Math.min(resterendeTijd * 1000, 2500);
                    }}
                }}
                smoothScrollTo(targetScrollTop, duration);
            }}
        }}

        function changeSpeed(rate, event) {{ 
            if (player && typeof player.setPlaybackRate === 'function') {{ 
                player.setPlaybackRate(rate); 
                
                // Update UI Buttons
                document.querySelectorAll('.buttons-group button').forEach(btn => {{
                    if (btn.innerText.includes('x')) {{
                        btn.className = 'btn-secondary';
                    }}
                }});
                if (event && event.currentTarget) {{
                    event.currentTarget.className = 'btn-active';
                }}
            }} 
        }}

        async function translateTextGoogle(text, lang) {{
            try {{
                const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${{lang}}&dt=t&q=${{encodeURIComponent(text)}}`;
                const res = await fetch(url); const json = await res.json();
                if (json && json[0]) {{
                    let trans = ""; json[0].forEach(p => {{ if (p[0]) trans += p[0]; }}); return trans;
                }}
                return "[Vertaling onbeschikbaar]";
            }} catch (err) {{ return "[Verbindingsfout]"; }}
        }}

        async function manageRollingTranslations(activeId, force = false) {{
            let start = Math.max(0, activeId - 1);
            let end = Math.min(storyData.length - 1, activeId + 1);
            for (let i = start; i <= end; i++) {{
                const cacheKey = `${{i}}_${{currentTargetLangCode}}`;
                if (!(cacheKey in translationCache) || force) {{
                    translationCache[cacheKey] = "processing";
                    const el = document.getElementById(`trans-${{i}}`);
                    if (el) el.innerText = "Vertaling laden...";
                    translateTextGoogle(storyData[i].text_orig, currentTargetLangCode).then(txt => {{
                        translationCache[cacheKey] = txt;
                        const translatedEl = document.getElementById(`trans-${{i}}`);
                        if (translatedEl) translatedEl.innerText = txt;
                    }});
                }} else {{
                    const cached = translationCache[cacheKey];
                    if (cached && cached !== "processing") {{
                        const el = document.getElementById(`trans-${{i}}`);
                        if (el) el.innerText = cached;
                    }}
                }}
            }}
        }}

        function getCurrentChapterText(activeId) {{
            let chapterText = 'Huidig hoofdstuk';
            for (let i = activeId; i >= 0; i--) {{
                if (storyData[i] && storyData[i].is_chapter) {{
                    chapterText = storyData[i].text_orig;
                    break;
                }}
            }}
            return chapterText;
        }}

        function updateCurrentChapterLabel(activeId) {{
            const chapterText = getCurrentChapterText(activeId);
            currentChapterLabel.innerText = chapterText;
            overlayCurrentChapter.innerText = chapterText;
        }}

        function updateProgressUI() {{
            if (!player || typeof player.getCurrentTime !== 'function' || typeof player.getDuration !== 'function') return;
            const currentTime = player.getCurrentTime();
            const duration = player.getDuration();
            if (duration > 0) {{
                const percent = Math.min(100, Math.max(0, (currentTime / duration) * 100));
                slider.value = percent;
                overlayProgressText.innerText = `Voortgang: ${{percent.toFixed(0)}}%`;
            }}
        }}

        function openSettings() {{
            document.getElementById('settings-overlay').classList.add('open');
            document.body.style.overflow = 'hidden';
            updateProgressUI();
        }}

        function closeSettings() {{
            document.getElementById('settings-overlay').classList.remove('open');
            document.body.style.overflow = ''; 
        }}

        var tag = document.createElement('script'); tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0]; firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

        var player;
        window.onYouTubeIframeAPIReady = function() {{
            player = new YT.Player('player', {{
                height: '1', width: '1', videoId: videoId,
                playerVars: {{ 'autoplay': 0, 'playsinline': 1, 'controls': 0 }},
                events: {{ 'onStateChange': onPlayerStateChange, 'onReady': onPlayerReady }}
            }});
        }}

        function onPlayerReady() {{
            // Initialiseer ook de hoofdstukken zodra de speler klaar is
            initChapters();

            const savedTime = localStorage.getItem(storageKeyTime);
            if (savedTime) {{
                const targetSec = parseFloat(savedTime);
                jumpToTime(targetSec);
                syncActiveBlock(findActiveLineId(targetSec));
            }} else {{
                syncActiveBlock(0);
            }}
        }}

        function findActiveLineId(currentTime) {{
            const withinLines = storyData.filter(line => currentTime >= line.start && currentTime <= line.end);
            if (withinLines.length > 0) {{
                return withinLines.reduce((best, line) => (line.start > best.start ? line : best), withinLines[0]).id;
            }}
            if (currentTime < storyData[0].start) {{
                return storyData[0].id;
            }}
            let bestLine = storyData[0];
            for (let i = 0; i < storyData.length; i++) {{
                if (storyData[i].start <= currentTime) {{
                    bestLine = storyData[i];
                }} else {{
                    break;
                }}
            }}
            return bestLine.id;
        }}

        function togglePlayback() {{
            if (!player || typeof player.getPlayerState !== 'function') return;
            const btn = document.getElementById('play-trigger-btn');
            if (player.getPlayerState() == YT.PlayerState.PLAYING) {{
                player.pauseVideo();
            }} else {{
                player.playVideo();
            }}
        }}

        function skipTime(seconds) {{ if (!player || typeof player.getCurrentTime !== 'function') return; jumpToTime(player.getCurrentTime() + seconds); }}

        var timeChecker;
        function onPlayerStateChange(event) {{
            const btn = document.getElementById('play-trigger-btn');
            if (event.data == YT.PlayerState.PLAYING) {{
                timeChecker = setInterval(checkLiveSync, 200);
                btn.innerHTML = "Pause";
            }} else {{
                clearInterval(timeChecker);
                btn.innerHTML = "Play";
            }}
        }}

        function checkLiveSync() {{
            if (!player || typeof player.getCurrentTime !== 'function' || isDraggingSlider) return;
            
            const huidig = player.getCurrentTime();
            const duur = player.getDuration();
            
            localStorage.setItem(storageKeyTime, huidig);
            
            if (duur > 0) {{
                slider.value = (huidig / duur) * 100;
            }}

            const matchedId = findActiveLineId(huidig);
            syncActiveBlock(matchedId);
        }}

        function jumpToTime(seconds) {{
            if (!player || typeof player.seekTo !== 'function') return;
            player.seekTo(seconds, true);
            localStorage.setItem(storageKeyTime, seconds);
            setTimeout(() => {{
                isDraggingSlider = false;
                checkLiveSync();
            }}, 50);
        }}

        function onSliderDrag(val) {{
            isDraggingSlider = true;
        }}

        function onSliderRelease(val) {{
            if (!player) return;
            const duur = player.getDuration();
            if (duur > 0) {{
                const targetSecs = (val / 100) * duur;
                jumpToTime(targetSecs);
            }}
            isDraggingSlider = false;
        }}

        // --- HOOFDSTUK LOGICA ---
        function initChapters() {{
            const listContainer = document.getElementById('chapters-list');
            // Filter alle regels die als hoofdstuk gemarkeerd zijn
            const chapters = storyData.filter(line => line.is_chapter);
            
            if (chapters.length === 0) {{
                listContainer.innerHTML = '<div class="chapter-item" style="color: #9CA3AF; cursor: default; font-weight: normal;">Geen hoofdstukken herkend</div>';
                return;
            }}
            
            chapters.forEach(ch => {{
                const item = document.createElement('div');
                item.className = 'chapter-item';
                item.innerText = ch.text_orig;
                item.onclick = () => {{
                    jumpToTime(ch.start);
                    toggleChapters(); // Sluit menu na klik
                }};
                listContainer.appendChild(item);
            }});
        }}

        function toggleChapters() {{
            if (!overlayChapters) return;
            if (overlayChapters.classList.contains('open')) {{
                overlayChapters.classList.remove('open');
            }} else {{
                overlayChapters.classList.add('open');
            }}
        }}

        // Sluit het hoofdstukkenmenu als men buiten het menu klikt
        window.addEventListener('click', function(e) {{
            if (!overlayChapters) return;
            const btnClicked = e.target.closest('button');
            const isToggleButton = btnClicked && btnClicked.innerText.includes('Hoofdstukken');
            if (overlayChapters.classList.contains('open') && !overlayChapters.contains(e.target) && !isToggleButton) {{
                overlayChapters.classList.remove('open');
            }}
        }});
    </script>
    """
    
    st.components.v1.html(custom_interface, height=700, scrolling=False)