import streamlit as st
from ytmusicapi import YTMusic

def get_album_id(video_id):
    try:
        ytmusic = YTMusic()
        # Obtém os detalhes da música/vídeo
        song_details = ytmusic.get_song(video_id)
        
        # O albumId fica dentro do dicionário 'videoDetails' ou 'microformat'
        # Tentamos extrair de forma segura
        album_id = song_details.get('videoDetails', {}).get('albumId')
        
        return album_id
    except Exception as e:
        return f"Erro ao buscar: {e}"

# Configuração da Interface Streamlit
st.set_page_config(page_title="YouTube Music Metadata Extractor", layout="centered")

st.title("🎵 Extrator de AlbumId")
st.write("Insira o ID do vídeo para capturar o parâmetro do álbum.")

# Input do usuário
video_id_input = st.text_input("Video ID / Song ID", value="ikFFVfObwss")

if st.button("Capturar albumId"):
    with st.spinner("Buscando dados no YouTube Music..."):
        res_album_id = get_album_id(video_id_input)
        
        if res_album_id:
            st.success(f"**albumId encontrado:** `{res_album_id}`")
            st.code(res_album_id, language=None)
            
            # Link direto para o álbum se quiser conferir
            st.markdown(f"[Acessar Álbum no YT Music](https://music.youtube.com/browse/{res_album_id})")
        else:
            st.warning("Não foi possível encontrar um albumId vinculado a este ID.")

# Rodapé informativo
st.divider()
st.caption("Nota: Alguns vídeos/singles podem não ter um albumId associado se não fizerem parte de um álbum ou EP oficial.")
