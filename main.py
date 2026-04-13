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

def get_table_info(conn, table_name):
    """Retorna informações detalhadas das colunas (nome, tipo, se é NOT NULL)."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    # row[1] é o nome, row[3] é a flag NOTNULL (1 se for obrigatória)
    return {row[1]: {"notnull": row[3]} for row in cursor.fetchall()}

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
        
        if not os.path.exists(BASE_SIMP):
            st.error(f"Arquivo base '{BASE_SIMP}' não encontrado.")
            st.stop()
            
        conn_dest_check = sqlite3.connect(BASE_SIMP)
        dest_info = get_table_info(conn_dest_check, "song")
        cols_dest = list(dest_info.keys())
        conn_dest_check.close()

        # 1. Extração da origem
        # Pegamos tudo que for possível da origem
        df_src = pd.read_sql_query("SELECT * FROM song", conn_source)
        lista_ids = pd.read_sql_query("SELECT songId FROM playlist_song_map ORDER BY rowid", conn_source)['songId'].tolist()
        conn_source.close()

        # 2. Construção do DataFrame de Destino dinamicamente
        df_dest = pd.DataFrame()
        
        # Mapeamentos fundamentais
        if 'id' in df_src.columns:
            df_dest['videoId'] = df_src['id']
        
        if 'duration' in df_src.columns:
            df_dest['duration'] = df_src['duration']
            df_dest['durationSeconds'] = (df_src['duration'] / 1000).fillna(0).astype(int)

        # Copia colunas com nomes idênticos
        for col in df_src.columns:
            if col in cols_dest and col not in df_dest.columns:
                df_dest[col] = df_src[col]

        # 3. CORREÇÃO GLOBAL: Preencher TODAS as colunas NOT NULL que ainda estão vazias
        # Dicionário de tipos para preenchimento inteligente
        default_values = {
            'isAvailable': 1,
            'isExplicit': 0,
            'isOffline': 0,
            'liked': 0,
            'inLibrary': 1,
            'likeStatus': 'INDIFFERENT',
            'videoType': 'MUSIC_VIDEO_TYPE_ATV', # Valor padrão comum para o erro atual
            'totalPlayTime': 0,
            'albumId': '',
            'albumName': '',
            'thumbnailUrl': ''
        }

        for col_name, info in dest_info.items():
            if info['notnull'] == 1 and col_name not in df_dest.columns:
                # Se for obrigatória e não existir no nosso DF, usa o default ou um valor vazio seguro
                val = default_values.get(col_name, 0 if "int" in str(col_name).lower() else "")
                df_dest[col_name] = val

        # 4. Gravação no Banco de Dados
        db_output_name = "Music Database"
        db_output_path = os.path.join(proc_dir, db_output_name)
        shutil.copy2(BASE_SIMP, db_output_path)

        try:
            conn_out = sqlite3.connect(db_output_path)
            cursor = conn_out.cursor()

            cols_to_insert = df_dest.columns.tolist()
            placeholders = ", ".join(["?"] * len(cols_to_insert))
            sql_insert = f"INSERT OR REPLACE INTO song ({', '.join(cols_to_insert)}) VALUES ({placeholders})"
            
            cursor.executemany(sql_insert, df_dest.values.tolist())

            # Atualização das tabelas de playlist
            cursor.execute("DELETE FROM pair_song_local_playlist")
            val_in_playlist = 1775992825264
            dados_pair = [(s_id, 1, i, val_in_playlist) for i, s_id in enumerate(lista_ids)]
            cursor.executemany(
                "INSERT INTO pair_song_local_playlist (songId, playlistId, position, inPlaylist) VALUES (?, ?, ?, ?)", 
                dados_pair
            )

            tracks_json = json.dumps(lista_ids)
            cursor.execute("UPDATE local_playlist SET tracks = ? WHERE id = 1", (tracks_json,))

            conn_out.commit()
            conn_out.close()

            # 5. Backup final
            final_backup_path = os.path.join(proc_dir, "simpmusic.backup")
            with zipfile.ZipFile(final_backup_path, 'w') as zipf:
                zipf.write(db_output_path, arcname=db_output_name)
                if os.path.exists(SETTINGS_FILE):
                    zipf.write(SETTINGS_FILE, arcname=SETTINGS_FILE)

            with open(final_backup_path, "rb") as f:
                st.success(f"✅ Sucesso! {len(lista_ids)} músicas processadas sem erros de restrição.")
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
