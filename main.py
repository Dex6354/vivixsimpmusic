import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil
import zipfile
import json
from ytmusicapi import YTMusic

# Inicializa a API do YouTube Music
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
        st.success(f"✅ {len(lista_ids)} IDs encontrados. Puxando metadados via API...")

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
                dados_completos_song = []
                
                for i, v_id in enumerate(lista_ids):
                    # Padrões para evitar NOT NULL
                    alb_id, dur, tit, art = "Unknown_Album", 0, "Unknown Title", "Unknown Artist"
                    
                    try:
                        # Tenta obter detalhes da música
                        s_det = yt.get_song(v_id)
                        v_det = s_det.get('videoDetails', {})
                        
                        tit = v_det.get('title', tit)
                        art = v_det.get('author', art)
                        dur = int(v_det.get('lengthSeconds', 0))
                        
                        # Tentativa 1: Pegar albumId direto
                        alb_id = v_det.get('albumId')
                        
                        # Tentativa 2: Se falhar, tenta buscar via metadados de microformat
                        if not alb_id:
                            alb_id = s_det.get('microformat', {}).get('microformatDataRenderer', {}).get('unlisted')
                    except:
                        pass
                    
                    # Se mesmo assim for None, definimos uma string vazia ou padrão
                    if alb_id is None:
                        alb_id = ""

                    dados_completos_song.append((
                        v_id, tit, art, alb_id, dur, dur, 1, 0
                    ))
                    progress_bar.progress((i + 1) / len(lista_ids))

                # --- DEBUGGER NA TELA ---
                st.divider()
                st.subheader("🐞 Debugger: Verificação de Metadados")
                df_debug = pd.DataFrame(dados_completos_song, columns=[
                    'videoId', 'title', 'artistName', 'albumId', 
                    'duration', 'durationSeconds', 'isAvailable', 'isExplicit'
                ])
                st.dataframe(df_debug, use_container_width=True)

                # --- INSERÇÃO ---
                cursor.executemany(
                    """INSERT INTO song (
                        videoId, title, artistName, albumId, 
                        duration, durationSeconds, isAvailable, isExplicit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    dados_completos_song
                )

                # Atualização das outras tabelas
                cursor.execute("DELETE FROM pair_song_local_playlist")
                val_in_playlist = 1775992825264
                dados_insercao = [(s_id, 1, idx, val_in_playlist) for idx, s_id in enumerate(lista_ids)]
                cursor.executemany(
                    "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                    dados_insercao
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
