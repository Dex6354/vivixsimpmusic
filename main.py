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
        st.success(f"✅ {len(lista_ids)} IDs. Extraindo AlbumId via Search (Lógica Go)...")

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
                dados_debugger = []
                tuplas_insercao = []
                
                for i, v_id in enumerate(lista_ids):
                    alb_id, dur, tit, art, explicit = "", 0, "Unknown", "Unknown", 0
                    raw_api = {}
                    
                    try:
                        # Lógica idêntica ao Search do Raitonoberu:
                        # Busca o ID da música e filtra por 'songs' para obter o objeto Track completo
                        search_results = yt.search(v_id, filter="songs")
                        
                        if search_results:
                            # Pega o primeiro resultado (que será a música exata do ID)
                            res = search_results[0]
                            raw_api = res
                            
                            tit = res.get('title', "Unknown")
                            art = res.get('artists', [{}])[0].get('name', "Unknown")
                            explicit = 1 if res.get('isExplicit') else 0
                            
                            # Extração do Album ID (browseId) - Onde o MPREb... fica no Search
                            album_obj = res.get('album', {})
                            alb_id = album_obj.get('id', "")
                            
                            # Duração (converte "3:45" para segundos)
                            dur_str = res.get('duration', "0")
                            if ":" in str(dur_str):
                                pts = list(map(int, dur_str.split(":")))
                                dur = pts[0] * 60 + pts[1] if len(pts) == 2 else pts[0] * 3600 + pts[1] * 60 + pts[2]
                    except Exception as e:
                        raw_api = {"error": str(e)}

                    dados_debugger.append({
                        "videoId": v_id,
                        "albumId": alb_id,
                        "raw": raw_api
                    })

                    tuplas_insercao.append((
                        v_id, tit, art, alb_id, dur, dur, 1, explicit
                    ))
                    progress_bar.progress((i + 1) / len(lista_ids))

                # --- DEBUGGER (VERIFICAÇÃO DO JSON RETORNADO) ---
                st.divider()
                st.subheader("🐞 Debugger: Comparação de IDs (Lógica Search)")
                for item in dados_debugger:
                    with st.expander(f"Música: {item['videoId']} | AlbumId: {item['albumId']}"):
                        st.json(item['raw'])

                # --- INSERÇÃO SQL ---
                cursor.executemany(
                    """INSERT INTO song (
                        videoId, title, artistName, albumId, 
                        duration, durationSeconds, isAvailable, isExplicit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    tuplas_insercao
                )

                # Atualização de tabelas relacionadas
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
