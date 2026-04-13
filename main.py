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
        st.success(f"✅ {len(lista_ids)} IDs encontrados.")

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
                debug_data = []
                tuplas_insercao = []
                
                for i, v_id in enumerate(lista_ids):
                    alb_id, dur, tit, art, explicit = "", 0, "Unknown", "Unknown", 0
                    raw_api = {}
                    
                    try:
                        # 1. Pega metadados básicos primeiro
                        basic_info = yt.get_song(v_id)
                        v_det = basic_info.get('videoDetails', {})
                        search_query = f"{v_det.get('title')} {v_det.get('author')}"
                        
                        # 2. Lógica Raitonoberu: Search para pegar o objeto 'Track' completo
                        search_results = yt.search(search_query, filter="songs")
                        
                        # Tenta encontrar o match exato pelo videoId nos resultados da busca
                        match = next((item for item in search_results if item.get('videoId') == v_id), None)
                        
                        # Se não achar match exato, pega o primeiro resultado da busca (mais provável ser a correta)
                        if not match and search_results:
                            match = search_results[0]

                        if match:
                            raw_api = match
                            tit = match.get('title', tit)
                            art = match.get('artists', [{}])[0].get('name', art)
                            explicit = 1 if match.get('isExplicit') else 0
                            
                            # EXTRAÇÃO DO ALBUM ID (browseId)
                            album_obj = match.get('album', {})
                            alb_id = album_obj.get('id', "")
                            
                            # Duração
                            dur_str = match.get('duration', "0")
                            if ":" in str(dur_str):
                                pts = list(map(int, dur_str.split(":")))
                                dur = pts[0] * 60 + pts[1] if len(pts) == 2 else pts[0] * 3600 + pts[1] * 60 + pts[2]
                            elif str(dur_str).isdigit():
                                dur = int(dur_str)
                    except Exception as e:
                        raw_api = {"error_api": str(e)}

                    debug_data.append({
                        "videoId": v_id,
                        "albumId": alb_id,
                        "full_json": raw_api
                    })

                    tuplas_insercao.append((
                        v_id, tit, art, alb_id, dur, dur, 1, explicit
                    ))
                    progress_bar.progress((i + 1) / len(lista_ids))

                # --- DEBUGGER ---
                st.divider()
                st.subheader("🐞 Debugger: Inspeção de Objetos Track")
                for item in debug_data:
                    with st.expander(f"ID: {item['videoId']} | AlbumId: {item['albumId']}"):
                        st.json(item['full_json'])

                # --- INSERÇÃO ---
                cursor.executemany(
                    """INSERT INTO song (
                        videoId, title, artistName, albumId, 
                        duration, durationSeconds, isAvailable, isExplicit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    tuplas_insercao
                )

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

                # Backup final
                final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
                with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                    zipf.write(db_output_path, arcname=db_output_name)
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

                with open(final_backup_path, "rb") as f:
                    st.download_button("📥 BAIXAR SIMPMUSIC.BACKUP", f.read(), "simpmusic.backup")

            except Exception as e:
                st.error(f"Erro no banco: {e}")
    except Exception as e:
        st.error(f"Erro no arquivo: {e}")
    finally:
        shutil.rmtree(proc_dir, ignore_errors=True)
