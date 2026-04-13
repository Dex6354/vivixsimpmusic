import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil
import zipfile
import json
from ytmusicapi import YTMusic

# Inicializa a API
yt = YTMusic()

st.set_page_config(page_title="Music Database Generator", layout="wide")

BASE_SIMP = "simpmusic.db"
SETTINGS_FILE = "settings.preferences_pb"

st.title("📂 Gerador de base: Music Database")

vivi_file = st.file_uploader("Importe o arquivo .backup", type=["backup"])

if vivi_file:
    proc_dir = tempfile.mkdtemp()
    path_vivi_backup = os.path.join(proc_dir, "vivi_upload.backup")
    path_song_db = os.path.join(proc_dir, "song.db")

    with open(path_vivi_backup, "wb") as f:
        f.write(vivi_file.read())

    try:
        with zipfile.ZipFile(path_vivi_backup, 'r') as z:
            if "song.db" in z.namelist():
                z.extract("song.db", proc_dir)
            else:
                st.error("Arquivo 'song.db' não encontrado.")
                st.stop()

        conn_v = sqlite3.connect(path_song_db)
        query = "SELECT songId FROM playlist_song_map ORDER BY rowid"
        df_ids = pd.read_sql_query(query, conn_v)
        conn_v.close()

        lista_ids = df_ids['songId'].tolist()
        st.success(f"✅ {len(lista_ids)} IDs. Seguindo lógica de extração do player...")

        if not os.path.exists(BASE_SIMP) or not os.path.exists(SETTINGS_FILE):
            st.error("Arquivos base ausentes na raiz.")
        else:
            db_output_name = "Music Database"
            db_output_path = os.path.join(proc_dir, db_output_name)
            shutil.copy2(BASE_SIMP, db_output_path)

            try:
                conn_out = sqlite3.connect(db_output_path)
                cursor = conn_out.cursor()
                cursor.execute("DELETE FROM song")
                
                progress_bar = st.progress(0)
                debug_list = []
                tuplas_insercao = []
                
                for i, v_id in enumerate(lista_ids):
                    alb_id, dur, tit, art = "", 0, "Unknown", "Unknown"
                    full_data = {}
                    
                    try:
                        # Lógica: get_watch_playlist captura o estado atual do player (similar ao ytmusic do Raitonoberu)
                        res = yt.get_watch_playlist(v_id)
                        full_data = res
                        
                        if 'tracks' in res and len(res['tracks']) > 0:
                            track = res['tracks'][0]
                            tit = track.get('title', "Unknown")
                            dur = int(track.get('lengthSeconds', 0)) if track.get('lengthSeconds') else 0
                            
                            # Tenta capturar o nome do artista
                            if track.get('artists'):
                                art = track['artists'][0].get('name', "Unknown")
                            
                            # FOCO: Captura do albumId (browseId)
                            album_obj = track.get('album', {})
                            if album_obj:
                                alb_id = album_obj.get('id', "")
                    except Exception as e:
                        full_data = {"error_api": str(e)}

                    debug_list.append({
                        "videoId": v_id,
                        "albumId_final": alb_id,
                        "api_response": full_data
                    })

                    tuplas_insercao.append((
                        v_id, tit, art, alb_id, dur, dur, 1, 0
                    ))
                    progress_bar.progress((i + 1) / len(lista_ids))

                # --- DEBUGGER (LOGICA DE INSPEÇÃO) ---
                st.divider()
                st.subheader("🐞 Debugger: Extração de Dados")
                for item in debug_list:
                    col1, col2 = st.columns([1, 4])
                    col1.code(f"ID: {item['videoId']}\nALBUM: {item['albumId_final']}")
                    with col2.expander("Ver JSON Completo da API"):
                        st.json(item['api_response'])

                # --- INSERÇÃO ---
                cursor.executemany(
                    """INSERT INTO song (
                        videoId, title, artistName, albumId, 
                        duration, durationSeconds, isAvailable, isExplicit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    tuplas_insercao
                )

                # Atualiza playlists e mapas
                cursor.execute("DELETE FROM pair_song_local_playlist")
                val_in_playlist = 1775992825264
                dados_playlist = [(d[0], 1, idx, val_in_playlist) for idx, d in enumerate(tuplas_insercao)]
                cursor.executemany(
                    "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                    dados_playlist
                )

                tracks_json = json.dumps(lista_ids)
                cursor.execute("UPDATE local_playlist SET tracks = ? WHERE id = 1", (tracks_json,))

                conn_out.commit()
                conn_out.close()

                # Download
                final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
                with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                    zipf.write(db_output_path, arcname=db_output_name)
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

                with open(final_backup_path, "rb") as f:
                    st.download_button("📥 BAIXAR SIMPMUSIC.BACKUP", f.read(), "simpmusic.backup")

            except Exception as e:
                st.error(f"Erro no banco: {e}")
    except Exception as e:
        st.error(f"Erro no backup: {e}")
    finally:
        shutil.rmtree(proc_dir, ignore_errors=True)
