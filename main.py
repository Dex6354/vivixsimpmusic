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
            st.error(f"Arquivo base '{BASE_SIMP}' não encontrado na raiz.")
            st.stop()
            
        conn_dest_check = sqlite3.connect(BASE_SIMP)
        cols_dest = get_columns(conn_dest_check, "song")
        conn_dest_check.close()

        # Mapeamento manual de colunas críticas e obrigatórias
        manual_mapping = {
            'id': 'videoId',
            'duration': 'duration'
        }
        
        # Identifica colunas comuns (excluindo as que trataremos manualmente)
        exclude = ['id', 'videoId', 'duration', 'durationSeconds', 'isAvailable']
        common_cols = [c for c in cols_source if c in cols_dest and c not in exclude]
        
        # Extração dos dados da origem
        query_source = f"SELECT id, duration, {', '.join(common_cols)} FROM song"
        df = pd.read_sql_query(query_source, conn_source)
        
        # Pega a ordem da playlist
        lista_ids = pd.read_sql_query("SELECT songId FROM playlist_song_map ORDER BY rowid", conn_source)['songId'].tolist()
        conn_source.close()

        # --- TRATAMENTO DE DADOS PARA O DESTINO ---
        df_dest = pd.DataFrame()
        df_dest['videoId'] = df['id']
        df_dest['duration'] = df['duration']
        df_dest['durationSeconds'] = (df['duration'] / 1000).fillna(0).astype(int)
        df_dest['isAvailable'] = 1  # Preenche o NOT NULL que estava falhando
        
        for col in common_cols:
            df_dest[col] = df[col]

        # Criar o novo banco de dados
        db_output_name = "Music Database"
        db_output_path = os.path.join(proc_dir, db_output_name)
        shutil.copy2(BASE_SIMP, db_output_path)

        try:
            conn_out = sqlite3.connect(db_output_path)
            cursor = conn_out.cursor()

            # Inserção na tabela 'song'
            cols_to_insert = df_dest.columns.tolist()
            placeholders = ", ".join(["?"] * len(cols_to_insert))
            sql_insert = f"INSERT OR REPLACE INTO song ({', '.join(cols_to_insert)}) VALUES ({placeholders})"
            
            cursor.executemany(sql_insert, df_dest.values.tolist())

            # Limpeza e atualização da pair_song_local_playlist
            cursor.execute("DELETE FROM pair_song_local_playlist")
            val_in_playlist = 1775992825264
            dados_pair = [(s_id, 1, i, val_in_playlist) for i, s_id in enumerate(lista_ids)]
            cursor.executemany(
                "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                dados_pair
            )

            # Atualização da coluna tracks na local_playlist
            tracks_json = json.dumps(lista_ids)
            cursor.execute("UPDATE local_playlist SET tracks = ? WHERE id = 1", (tracks_json,))

            conn_out.commit()
            conn_out.close()

            # Gerar backup final
            final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
            with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                zipf.write(db_output_path, arcname=db_output_name)
                if os.path.exists(SETTINGS_FILE):
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

            with open(final_backup_path, "rb") as f:
                st.success(f"✅ Sucesso! {len(lista_ids)} músicas processadas com metadados.")
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
