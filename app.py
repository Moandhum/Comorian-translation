import streamlit as st
from audio_recorder_streamlit import audio_recorder
import speech_recognition as sr
import io
import os
import tempfile
import numpy as np
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont

# --- Whisper optionnel (trop lourd pour Streamlit Cloud) ---
try:
    import torch
    torch.classes.__path__ = []
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


def get_font(size=48):
    """Charge une police avec fallbacks selon l'OS."""
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    """Découpe le texte en lignes qui tiennent dans max_width."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines if lines else [""]


def create_frame(bg_image, text, size):
    """Crée une image (numpy array) : fond + sous-titre en bas."""
    img = bg_image.copy().resize(size, Image.LANCZOS)

    if not text.strip():
        return np.array(img.convert("RGB"))

    font = get_font(max(28, size[0] // 20))

    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    lines = wrap_text(draw, text, font, size[0] - 80)
    line_h = max(30, size[0] // 18)
    total_h = len(lines) * line_h + 24
    y0 = size[1] - total_h - 50

    # Fond semi-transparent derrière le texte
    draw.rounded_rectangle(
        [(30, y0 - 10), (size[0] - 30, y0 + total_h)],
        radius=15, fill=(0, 0, 0, 180)
    )

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (size[0] - (bbox[2] - bbox[0])) // 2
        y = y0 + i * line_h + 5
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 200))  # ombre
        draw.text((x, y), line, font=font, fill="white")

    result = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return np.array(result)


def generate_video(bg_image, audio_bytes, subtitle_lines, progress_bar=None):
    """Génère un MP4 : image de fond + audio + sous-titres."""
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

    audio_seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
    total_duration = len(audio_seg) / 1000.0

    # Taille vidéo : garder le ratio de l'image, max 720px de large
    w, h = bg_image.size
    if w > 720:
        h = int(h * (720 / w))
        w = 720
    w, h = w + (w % 2), h + (h % 2)  # dimensions paires (h264)
    size = (w, h)

    n = len(subtitle_lines)
    dur = total_duration / n

    clips = []
    for i, line in enumerate(subtitle_lines):
        frame = create_frame(bg_image, line, size)
        clips.append(ImageClip(frame).with_duration(dur))
        if progress_bar:
            progress_bar.progress(int(((i + 1) / (n + 1)) * 100))

    video = concatenate_videoclips(clips, method="compose")

    audio_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_seg.export(audio_tmp, format="wav")
    audio_tmp.close()

    audio_clip = AudioFileClip(audio_tmp.name)
    final = video.with_audio(audio_clip)

    out_tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    out_tmp.close()
    final.write_videofile(out_tmp.name, fps=24, codec="libx264", audio_codec="aac", logger=None)

    audio_clip.close()
    final.close()
    os.unlink(audio_tmp.name)

    if progress_bar:
        progress_bar.progress(100)

    return out_tmp.name


# ---- Helpers transcription ----

def normalize_audio(audio_bytes):
    """Normalise le volume et filtre le bruit de fond."""
    seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
    seg = seg.set_channels(1).set_frame_rate(16000)
    if seg.dBFS == float('-inf'):
        return seg
    target_dbfs = -14.0
    seg = seg.apply_gain(target_dbfs - seg.dBFS)
    seg = seg.high_pass_filter(80)
    return seg


def transcribe_by_phrases(audio_seg, lang_code, recognizer):
    """Découpe l'audio par silences et transcrit chaque segment → 1 ligne = 1 phrase."""
    from pydub.silence import split_on_silence

    # Découper aux silences (min_silence=400ms, seuil=-35 dBFS, garder 200ms de marge)
    silence_thresh = -40.0 if audio_seg.dBFS == float('-inf') else audio_seg.dBFS - 16
    segments = split_on_silence(
        audio_seg,
        min_silence_len=400,
        silence_thresh=silence_thresh,
        keep_silence=200
    )

    # Si pas de segments détectés, fallback : chunks de 8s
    if not segments:
        segments = [audio_seg[i:i + 8000] for i in range(0, len(audio_seg), 8000)]

    lines = []
    for seg in segments:
        if len(seg) < 200:  # segment trop court → ignorer
            continue
        buf = io.BytesIO()
        seg.export(buf, format="wav")
        buf.seek(0)
        with sr.AudioFile(buf) as src:
            data = recognizer.record(src)
            try:
                text = recognizer.recognize_google(data, language=lang_code)
                if text.strip():
                    lines.append(text.strip())
            except sr.UnknownValueError:
                pass
    return lines


def transcribe_full(audio_seg, lang_code, recognizer):
    """Transcription complète en un seul texte (chunks de 45s)."""
    chunks = [audio_seg[i:i + 45000] for i in range(0, len(audio_seg), 45000)]
    parts = []
    for chunk in chunks:
        buf = io.BytesIO()
        chunk.export(buf, format="wav")
        buf.seek(0)
        with sr.AudioFile(buf) as src:
            data = recognizer.record(src)
            try:
                parts.append(recognizer.recognize_google(data, language=lang_code))
            except sr.UnknownValueError:
                pass
    return " ".join(parts)


# ===================== INTERFACE =====================

def main():
    st.set_page_config(page_title="Vidéo Sous-titrée ShiKomori", page_icon="🎬", layout="centered")

    st.markdown("""
        <h2 style="color: #00008B;">🎬 Générateur de Vidéo Sous-titrée ShiKomori</h2>
        <p style="color: #555;">Audio shiKomori → Sous-titres phrase par phrase → Traduction FR vocale → CSV + Vidéo</p>
    """, unsafe_allow_html=True)

    # ---- 1. IMAGE DE FOND ----
    st.markdown("### 🖼️ Image de fond")
    uploaded_img = st.file_uploader("Choisis une image", type=["png", "jpg", "jpeg", "webp"], key="img")
    bg_image = None
    if uploaded_img:
        bg_image = Image.open(uploaded_img)
        st.image(bg_image, caption="Image sélectionnée", use_container_width=True)

    # ---- 2. AUDIO SHIKOMORI ----
    st.markdown("### 🎤 Audio ShiKomori")

    engines = ["Google (Rapide)"]
    if WHISPER_AVAILABLE:
        engines.append("Whisper (précis)")
    engine = st.radio("Moteur :", engines)

    lang_map = {
        "Swahili (Tanzanie)": "sw-TZ",
        "Swahili (Kenya)": "sw-KE",
        "Français": "fr-FR",
    }
    whisper_map = {"sw-TZ": "sw", "sw-KE": "sw", "fr-FR": "fr"}
    lang = st.selectbox("Langue de base pour la transcription :", list(lang_map.keys()))
    lang_code = lang_map[lang]

    audio_bytes = None
    if "_active_km" not in st.session_state:
        st.session_state._active_km = None
    if "_last_rec_km" not in st.session_state:
        st.session_state._last_rec_km = None
    if "_last_up_km" not in st.session_state:
        st.session_state._last_up_km = None

    tab1, tab2 = st.tabs(["🎤 Enregistrer", "📁 Charger un fichier"])

    with tab1:
        rec = audio_recorder(
            text="Enregistrer shiKomori", recording_color="#e81c4f",
            neutral_color="#6aa36f", icon_name="microphone",
            icon_size="2x", key="rec_komori", sample_rate=16000
        )
        if rec and rec != st.session_state._last_rec_km:
            st.session_state._last_rec_km = rec
            st.session_state._active_km = rec

    with tab2:
        up = st.file_uploader(
            "Audio shiKomori (WAV, MP3, MP4, M4A, FLAC)",
            type=["wav", "mp3", "mp4", "m4a", "flac"], key="aud_komori"
        )
        if up and up.file_id != st.session_state._last_up_km:
            st.session_state._last_up_km = up.file_id
            try:
                seg = AudioSegment.from_file(io.BytesIO(up.read()))
                seg = seg.set_channels(1).set_frame_rate(16000)
                buf = io.BytesIO()
                seg.export(buf, format="wav")
                st.session_state._active_km = buf.getvalue()
            except Exception as e:
                st.error(f"Erreur audio : {e}")

    audio_bytes = st.session_state._active_km

    # ---- 3. TRANSCRIPTION SHIKOMORI (par phrases) ----
    if audio_bytes:
        if (st.session_state.get("_aud_km") != audio_bytes or
            st.session_state.get("_lang_km") != lang_code or
            st.session_state.get("_eng_km") != engine):

            st.session_state._aud_km = audio_bytes
            st.session_state._lang_km = lang_code
            st.session_state._eng_km = engine

            try:
                normalized_seg = normalize_audio(audio_bytes)
            except Exception:
                normalized_seg = AudioSegment.from_file(io.BytesIO(audio_bytes))

            with st.spinner("Transcription shiKomori phrase par phrase..."):
                try:
                    r = sr.Recognizer()
                    r.energy_threshold = 300
                    r.dynamic_energy_threshold = True
                    r.pause_threshold = 0.8

                    if "Whisper" in engine and WHISPER_AVAILABLE:
                        st.info("⏳ Whisper 'small' (~460 Mo au 1er lancement)...")
                        norm_buf = io.BytesIO()
                        normalized_seg.export(norm_buf, format="wav")
                        with sr.AudioFile(io.BytesIO(norm_buf.getvalue())) as src:
                            data = r.record(src)
                            wl = whisper_map.get(lang_code, "sw")
                            full = r.recognize_whisper(data, language=wl, model="small")
                            # Whisper retourne un texte continu → découper par ponctuation
                            import re
                            parts = re.split(r'[.!?،,]+', full)
                            st.session_state.subtitles_text = "\n".join(
                                p.strip() for p in parts if p.strip()
                            )
                    else:
                        lines = transcribe_by_phrases(normalized_seg, lang_code, r)
                        if lines:
                            st.session_state.subtitles_text = "\n".join(lines)
                        else:
                            st.warning("Aucun texte détecté.")
                            st.session_state.subtitles_text = ""
                except Exception as e:
                    st.error(f"Erreur transcription : {e}")
                    st.session_state.subtitles_text = ""

        st.audio(audio_bytes, format="audio/wav")

    # ---- 4. SOUS-TITRES SHIKOMORI (correction) ----
    st.markdown("### ✏️ Sous-titres ShiKomori")
    st.caption("**1 ligne = 1 sous-titre** (découpé automatiquement par phrase). Corrige si besoin.")

    if "subtitles_text" not in st.session_state:
        st.session_state.subtitles_text = ""

    subtitles = st.text_area("Sous-titres shiKomori :", height=200, key="subtitles_text")

    # ---- 5. TRADUCTION FRANÇAISE (vocale) ----
    st.markdown("### 🇫🇷 Traduction française (vocale)")
    st.caption("Enregistre ou charge l'audio de la traduction en français.")

    fr_audio_bytes = None
    if "_active_fr" not in st.session_state:
        st.session_state._active_fr = None
    if "_last_rec_fr" not in st.session_state:
        st.session_state._last_rec_fr = None
    if "_last_up_fr" not in st.session_state:
        st.session_state._last_up_fr = None

    fr_tab1, fr_tab2 = st.tabs(["🎤 Dicter en français", "📁 Charger audio français"])

    with fr_tab1:
        fr_rec = audio_recorder(
            text="Enregistrer français", recording_color="#3498db",
            neutral_color="#2ecc71", icon_name="microphone",
            icon_size="2x", key="rec_fr", sample_rate=16000
        )
        if fr_rec and fr_rec != st.session_state._last_rec_fr:
            st.session_state._last_rec_fr = fr_rec
            st.session_state._active_fr = fr_rec

    with fr_tab2:
        fr_up = st.file_uploader(
            "Audio français (WAV, MP3, MP4, M4A, FLAC)",
            type=["wav", "mp3", "mp4", "m4a", "flac"], key="aud_fr"
        )
        if fr_up and fr_up.file_id != st.session_state._last_up_fr:
            st.session_state._last_up_fr = fr_up.file_id
            try:
                seg = AudioSegment.from_file(io.BytesIO(fr_up.read()))
                seg = seg.set_channels(1).set_frame_rate(16000)
                buf = io.BytesIO()
                seg.export(buf, format="wav")
                st.session_state._active_fr = buf.getvalue()
            except Exception as e:
                st.error(f"Erreur audio FR : {e}")
    
    fr_audio_bytes = st.session_state._active_fr

    # Transcription française
    if fr_audio_bytes:
        if (st.session_state.get("_aud_fr") != fr_audio_bytes):
            st.session_state._aud_fr = fr_audio_bytes

            try:
                fr_seg = normalize_audio(fr_audio_bytes)
            except Exception:
                fr_seg = AudioSegment.from_file(io.BytesIO(fr_audio_bytes))

            with st.spinner("Transcription français..."):
                try:
                    r = sr.Recognizer()
                    r.energy_threshold = 300
                    r.dynamic_energy_threshold = True
                    fr_text = transcribe_full(fr_seg, "fr-FR", r)
                    if fr_text.strip():
                        st.session_state.french_text = fr_text
                    else:
                        st.warning("Aucun texte français détecté.")
                        st.session_state.french_text = ""
                except Exception as e:
                    st.error(f"Erreur transcription FR : {e}")
                    st.session_state.french_text = ""

        st.audio(fr_audio_bytes, format="audio/wav")

    if "french_text" not in st.session_state:
        st.session_state.french_text = ""

    french = st.text_area("Traduction française :", height=150, key="french_text")

    # ---- 6. EXPORT CSV ----
    st.markdown("### 📥 Export CSV")
    if subtitles.strip() or french.strip():
        import csv
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["shiKomori", "Français"])

        km_lines = [l.strip() for l in subtitles.strip().split("\n") if l.strip()] if subtitles.strip() else []
        fr_lines = [l.strip() for l in french.strip().split("\n") if l.strip()] if french.strip() else []

        # Si le français est un bloc continu, le mettre sur une seule ligne
        if len(fr_lines) == 0:
            fr_lines = [""]
        if len(km_lines) == 0:
            km_lines = [""]

        max_rows = max(len(km_lines), len(fr_lines))
        for i in range(max_rows):
            km = km_lines[i] if i < len(km_lines) else ""
            fr = fr_lines[i] if i < len(fr_lines) else ""
            writer.writerow([km, fr])

        st.download_button(
            "⬇️ Télécharger CSV (shiKomori + Français)",
            csv_buf.getvalue(),
            "traduction_shikomori_francais.csv",
            "text/csv"
        )

    # ---- 7. GÉNÉRATION VIDÉO ----
    st.markdown("### 🎬 Génération vidéo")
    if st.button("🎬 Générer la vidéo"):
        if not bg_image:
            st.error("Choisis une image de fond.")
        elif not audio_bytes:
            st.error("Enregistre ou charge un audio shiKomori.")
        elif not subtitles.strip():
            st.error("Les sous-titres sont vides.")
        else:
            lines = [l for l in subtitles.strip().split("\n") if l.strip()]
            bar = st.progress(0, text="Génération de la vidéo...")
            try:
                path = generate_video(bg_image, audio_bytes, lines, bar)
                bar.empty()

                with open(path, "rb") as f:
                    st.session_state.video_bytes = f.read()
                os.unlink(path)
                st.success("Vidéo générée avec succès !")

            except Exception as e:
                bar.empty()
                st.error(f"Erreur génération : {e}")

    if "video_bytes" in st.session_state:
        st.video(st.session_state.video_bytes)
        st.download_button("⬇️ Télécharger la vidéo", st.session_state.video_bytes, "video_sous_titree.mp4", "video/mp4")


if __name__ == "__main__":
    main()