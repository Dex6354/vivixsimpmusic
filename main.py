import streamlit as st
import sqlite3
import tempfile
import pandas as pd
import os
import shutil
import zipfile
import json

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

        # 1. Extrair IDs e Metadados do song.db original
        conn_v = sqlite3.connect(path_song_db)
        # Buscamos videoId e metadados para a exibição visual imediata
        query = "SELECT videoId, title, artist, duration, thumbnailUrl FROM song"
        df_metadata = pd.read_sql_query(query, conn_v)
        
        # Também pegamos a ordem correta da playlist
        query_order = "SELECT songId FROM playlist_song_map ORDER BY rowid"
        lista_ids = pd.read_sql_query(query_order, conn_v)['songId'].tolist()
        conn_v.close()

        st.success(f"✅ {len(lista_ids)} músicas e metadados processados.")

        if not os.path.exists(BASE_SIMP) or not os.path.exists(SETTINGS_FILE):
            st.error("Arquivos base ou settings não encontrados na raiz.")
        else:
            db_output_name = "Music Database"
            db_output_path = os.path.join(proc_dir, db_output_name)
            shutil.copy2(BASE_SIMP, db_output_path)

            try:
                conn_out = sqlite3.connect(db_output_path)
                cursor = conn_out.cursor()

                # 2. Atualizar tabela 'song' com metadados para exibição visual
                # Isso evita que as músicas fiquem "invisíveis" até o clique
                for _, row in df_metadata.iterrows():
                    cursor.execute("""
                        INSERT OR REPLACE INTO song (videoId, title, artist, duration, thumbnailUrl) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (row['videoId'], row['title'], row['artist'], row['duration'], row['thumbnailUrl']))

                # 3. Atualizar pair_song_local_playlist (Junção)
                cursor.execute("DELETE FROM pair_song_local_playlist")
                val_in_playlist = 1775992825264
                dados_pair = [(s_id, 1, i, val_in_playlist) for i, s_id in enumerate(lista_ids)]
                cursor.executemany(
                    "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                    dados_pair
                )

                # 4. Atualizar local_playlist (Coluna tracks)
                tracks_json = json.dumps(lista_ids)
                cursor.execute("UPDATE local_playlist SET tracks = ? WHERE id = 1", (tracks_json,))

                conn_out.commit()
                conn_out.close()

                # 5. Gerar arquivo final .backup
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

            except Exception as e:
                st.error(f"Erro no banco de dados: {e}")
            
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
    finally:
        shutil.rmtree(proc_dir, ignore_errors=True)
