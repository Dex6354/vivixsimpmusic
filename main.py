import streamlit as st
from ytmusicapi import YTMusic

# Inicializa cliente (modo sem autenticação)
yt = YTMusic()

st.title("Buscar albumId via videoId (YouTube Music)")

# Input do usuário
video_id = st.text_input("Digite o videoId / songId:", "ikFFVfObwss")

if st.button("Buscar albumId"):
    try:
        # Busca detalhes da música
        song_data = yt.get_song(video_id)

        # Estrutura da resposta
        video_details = song_data.get("videoDetails", {})
        microformat = song_data.get("microformat", {})
        player_microformat = microformat.get("microformatDataRenderer", {})

        # Tentativa 1: via playlistId (geralmente começa com 'OLAK5uy_')
        album_id = player_microformat.get("albumId")

        # Tentativa 2: fallback via browseId (mais confiável)
        if not album_id:
            music_data = yt.get_watch_playlist(video_id)
            tracks = music_data.get("tracks", [])

            if tracks:
                album_info = tracks[0].get("album", {})
                album_id = album_info.get("id")

        # Exibir resultados
        st.subheader("Resultado:")
        st.write("Título:", video_details.get("title"))
        st.write("Autor:", video_details.get("author"))
        st.write("albumId:", album_id)

        if album_id:
            st.success(f"Album ID encontrado: {album_id}")
        else:
            st.error("Não foi possível encontrar o albumId.")

    except Exception as e:
        st.error(f"Erro ao buscar dados: {str(e)}")
