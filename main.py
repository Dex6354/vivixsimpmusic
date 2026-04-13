import streamlit as st
from ytmusicapi import YTMusic

def get_album_id_v2(video_id):
    ytmusic = YTMusic()
    try:
        # A lógica do SimpMusic/InnerTune consiste em obter a 'watch playlist'
        # do vídeo. Isso força o YouTube a retornar o contexto do álbum/set.
        playlist = ytmusic.get_watch_playlist(videoId=video_id)
        
        # O primeiro item da lista (index 0) costuma ser a própria música com metadados expandidos
        tracks = playlist.get('tracks', [])
        if tracks:
            album_info = tracks[0].get('album', {})
            return album_info.get('id') # Este é o browseId do álbum
        
        return None
    except Exception as e:
        return f"Erro: {e}"

# Interface Streamlit
st.set_page_config(page_title="Extrator AlbumId (SimpMusic Logic)", layout="centered")

st.title("🎵 Extrator de AlbumId Profissional")
st.write("Utilizando a lógica de extração via `watch_playlist`.")

video_id_input = st.text_input("Video ID", value="ikFFVfObwss")

if st.button("Capturar albumId"):
    with st.spinner("Extraindo metadados avançados..."):
        album_id = get_album_id_v2(video_id_input)
        
        if album_id:
            st.success(f"**albumId extraído:** `{album_id}`")
            st.code(album_id, language=None)
            
            # Verificação visual
            url = f"https://music.youtube.com/browse/{album_id}"
            st.markdown(f"🔗 [Abrir Álbum no YT Music]({url})")
        else:
            st.error("Não foi possível encontrar o albumId. O vídeo pode ser um upload de usuário (não oficial) ou um arquivo sem álbum vinculado.")

st.divider()
st.info("Dica: Se o resultado for nulo, tente com um vídeo oficial (Official Audio) em vez de um videoclipe.")
