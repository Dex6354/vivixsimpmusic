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

# Arquivos necessários na raiz do projeto
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
                st.error("Arquivo 'song.db' não encontrado dentro do backup.")
                st.stop()

        conn_v = sqlite3.connect(path_song_db)
        query = "SELECT songId FROM playlist_song_map ORDER BY rowid"
        df_ids = pd.read_sql_query(query, conn_v)
        conn_v.close()

        lista_ids = df_ids['songId'].tolist()
        st.success(f"✅ {len(lista_ids)} IDs encontrados. Capturando metadados...")

        if not os.path.exists(BASE_SIMP) or not os.path.exists(SETTINGS_FILE):
            st.error("Arquivos base (db ou settings) ausentes na raiz.")
        else:
            db_output_name = "Music Database"
            db_output_path = os.path.join(proc_dir, db_output_name)
            shutil.copy2(BASE_SIMP, db_output_path)

            try:
                conn_out = sqlite3.connect(db_output_path)
                cursor = conn_out.cursor()

                # --- LIMPEZA E ATUALIZAÇÃO DA TABELA song ---
                cursor.execute("DELETE FROM song")
                
                progress_bar = st.progress(0)
                dados_completos_song = []
                
                for i, v_id in enumerate(lista_ids):
                    # Valores padrão (None para campos que permitem NULL, 0 ou string para NOT NULL)
                    album_id = None
                    duration = 0
                    title = "Unknown"
                    artist = "Unknown"
                    
                    try:
                        song_details = yt.get_song(v_id)
                        v_details = song_details.get('videoDetails', {})
                        
                        album_id = v_details.get('albumId') # Pode ser None
                        duration = int(v_details.get('lengthSeconds', 0))
                        title = v_details.get('title', "Unknown")
                        artist = v_details.get('author', "Unknown")
                    except:
                        pass
                    
                    # Ordem das colunas depende do esquema da sua tabela 'song'
                    # Ajustado para incluir title, artistName, albumId e duration
                    dados_completos_song.append((v_id, title, artist, album_id, duration))
                    progress_bar.progress((i + 1) / len(lista_ids))

                # Ajuste a query abaixo conforme as colunas exatas do seu simpmusic.db
                cursor.executemany(
                    "INSERT INTO song (videoId, title, artistName, albumId, duration) VALUES (?, ?, ?, ?, ?)",
                    dados_completos_song
                )

                # --- ATUALIZAÇÃO DA TABELA pair_song_local_playlist ---
                cursor.execute("DELETE FROM pair_song_local_playlist")
                val_in_playlist = 1775992825264
                dados_insercao = [(s_id, 1, i, val_in_playlist) for i, s_id in enumerate(lista_ids)]

                cursor.executemany(
                    "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                    dados_insercao
                )

                # --- ATUALIZAÇÃO DA TABELA local_playlist ---
                tracks_json = json.dumps(lista_ids)
                cursor.execute("UPDATE local_playlist SET tracks = ? WHERE id = 1", (tracks_json,))

                conn_out.commit()
                conn_out.close()

                final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
                with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                    zipf.write(db_output_path, arcname=db_output_name)
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

                with open(final_backup_path, "rb") as f:
                    st.download_button(
                        label="📥 BAIXAR SIMPMUSIC.BACKUP",
                        data=f.read(),
                        file_name="simpmusic.backup",
                        mime="application/octet-stream"
                    )
                st.success("Tabela 'song' renovada com sucesso!")

            except Exception as e:
                st.error(f"Erro no banco: {e}")
    except Exception as e:
        st.error(f"Erro no arquivo: {e}")
    finally:
        shutil.rmtree(proc_dir, ignore_errors=True)
