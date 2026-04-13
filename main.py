import streamlit as st
from ytmusicapi import YTMusic
import json

# Inicializa a API (Modo público/sem auth para este teste)
yt = YTMusic()

st.set_page_config(page_title="Debugger JSON - AlbumId", layout="wide")

st.title("🐞 Debugger de Metadados: AC/DC - Highway to Hell")

# Dados fixos do item
VIDEO_ID = "ikFFVfObwss"
QUERY = "Highway to Hell AC/DC - Topic"

if st.button("Executar Busca e Gerar JSON"):
    try:
        # Lógica: Busca textual filtrando por 'songs' para obter o objeto oficial de prateleira
        # Esse é o método que retorna a estrutura {"album": {"name": "...", "id": "..."}}
        search_results = yt.search(QUERY, filter="songs")
        
        if search_results:
            # Filtra o resultado que corresponde ao videoId exato, ou pega o primeiro
            match = next((item for item in search_results if item.get('videoId') == VIDEO_ID), search_results[0])
            
            # Captura o AlbumId se ele existir no objeto
            album_info = match.get('album', {})
            album_id_final = album_info.get('id', "NÃO ENCONTRADO NO JSON")

            # Exibição do Debugger
            st.success(f"Busca finalizada!")
            
            col1, col2 = st.columns(2)
            col1.metric("Video ID", VIDEO_ID)
            col2.metric("Album ID Encontrado", album_id_final)

            st.divider()
            st.subheader("📦 JSON Bruto da API")
            st.write("Verifique abaixo a chave `'album'` -> `'id'`")
            st.json(match)
            
        else:
            st.error("Nenhum resultado encontrado para a busca.")
            
    except Exception as e:
        st.error(f"Erro na API: {e}")

st.info("Nota: Se o 'albumId' ainda não aparecer como MPREb..., o YouTube Music pode estar tratando este vídeo 'Topic' apenas como vídeo. Nesse caso, tente buscar apenas por 'Highway to Hell AC/DC' (sem o '- Topic').")
