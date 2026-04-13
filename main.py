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

def get_columns(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

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

        conn_source = sqlite3.connect(path_song_db)
        cols_source = get_columns(conn_source, "song")
        
        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo '{BASE_SIMP}' não encontrado.")
            st.stop()
            
        conn_dest_check = sqlite3.connect(BASE_SIMP)
        cols_dest = get_columns(conn_dest_check, "song")
        conn_dest_check.close()

        # Identifica colunas comuns (exceto chaves e durações tratadas manualmente)
        manual_cols = ['id', 'videoId', 'duration', 'durationSeconds']
        common_cols = [c for c in cols_source if c in cols_dest and c not in manual_cols]
        
        # Extração: Mapeia id -> videoId e trata a duração
        query_source = f"SELECT id as videoId, duration, {', '.join(common_cols)} FROM song"
        df_metadata = pd.read_sql_query(query_source, conn_source)
        
        # Converte milissegundos (do song2) para segundos (exigido pelo destino)
        if 'duration' in df_metadata.columns:
            df_metadata['durationSeconds'] = (df_metadata['duration'] / 1000).astype(int)
        
        lista_ids = pd.read_sql_query("SELECT songId FROM playlist_song_map ORDER BY rowid", conn_source)['songId'].tolist()
        conn_source.close()

        db_output_name = "Music Database"
        db_output_path = os.path.join(proc_dir, db_output_name)
        shutil.copy2(BASE_SIMP, db_output_path)

        try:
            conn_out = sqlite3.connect(db_output_path)
            cursor = conn_out.cursor()

            # Prepara colunas finais: videoId + duration + durationSeconds + colunas comuns
            final_cols = ['videoId', 'duration', 'durationSeconds'] + common_cols
            placeholders = ", ".join(["?"] * len(final_cols))
            sql_insert_song = f"INSERT OR REPLACE INTO song ({', '.join(final_cols)}) VALUES ({placeholders})"
            
            # Reordena o DataFrame para bater com final_cols
            cursor.executemany(sql_insert_song, df_metadata[final_cols].values.tolist())

            # Atualização da playlist
            cursor.execute("DELETE FROM pair_song_local_playlist")
            val_in_playlist = 1775992825264
            dados_pair = [(s_id, 1, i, val_in_playlist) for i, s_id in enumerate(lista_ids)]
            cursor.executemany(
                "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                dados_pair
            )

            # Atualização da coluna tracks
            tracks_json = json.dumps(lista_ids)
            cursor.execute("UPDATE local_playlist SET tracks = ? WHERE id = 1", (tracks_json,))

            conn_out.commit()
            conn_out.close()

            final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
            with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                zipf.write(db_output_path, arcname=db_output_name)
                if os.path.exists(SETTINGS_FILE):
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

            with open(final_backup_path, "rb") as f:
                st.success("✅ Backup gerado com sucesso!")
                st.download_button(
                    label="📥 BAIXAR SIMPMUSIC.BACKUP",
                    data=f.read(),
                    file_name="simpmusic.backup",
                    mime="application/octet-stream"
                )

        except Exception as e:
            st.error(f"Erro ao gravar dados: {e}")
            
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
    finally:
        shutil.rmtree(proc_dir, ignore_errors=True)
