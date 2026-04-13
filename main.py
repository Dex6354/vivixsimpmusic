import streamlit as st
from ytmusicapi import YTMusic

yt = YTMusic()

st.title("Buscar albumId estilo SimpMusic")

video_id = st.text_input("Digite o videoId:", "ikFFVfObwss")

def get_album_id_simpmusic(video_id):
    try:
        data = yt.get_watch_playlist(video_id)

        # 🔥 Aqui é a chave (mesma ideia do SimpMusic)
        tracks = data.get("tracks", [])

        for track in tracks:
            album = track.get("album")

            if album and "id" in album:
                return album["id"]

        return None

    except Exception as e:
        return f"Erro: {str(e)}"


if st.button("Buscar"):
    album_id = get_album_id_simpmusic(video_id)

    st.subheader("Resultado")
    st.write("videoId:", video_id)
    st.write("albumId:", album_id)

    if album_id and not str(album_id).startswith("Erro"):
        st.success(f"Album ID encontrado: {album_id}")
    else:
        st.error("Não encontrado")
