import config
import requests
import streamlit as st
import pathlib

icon_path = "assets/logo-azul-fundo-transparente.png"  

# Set basic page configuration
st.set_page_config(
    page_title="Chat Diário Oficial",
    page_icon=icon_path,
)

css_path = pathlib.Path("./assets/style.css")
with open(css_path) as f:
    st.markdown(
        f"<style>{f.read()}</style>", 
        unsafe_allow_html=True
    )

col1, col2 = st.columns([1, 9])  
with col1:
    st.image(icon_path, width=200)  

with col2:
    st.markdown(
        "<h1 style='font-family: Arial, sans-serif; font-size: 40px; color: #255CA5; margin: 0;'>Chat Diário Oficial</h1>",
        unsafe_allow_html=True,
    )

st.write("Faça uma pergunta referente a algum documento ou tópico disponibilizado no Diário Oficial que você deseja obter uma resposta.")

# Caixa de entrada e botão com melhor alinhamento
col_input, col_button = st.columns([8, 2], gap="small")
with col_input:
    user_input = st.text_input(
        "Você pergunta:",
        key="styledinput",
        help="💡 Certifique-se de que sua pergunta seja específica. Por exemplo:\n- O que diz a ementa do Acórdão nº XX.XXX/Xª?\n- Quem representou a empresa XXXXXXXXXX no recurso XXXXXX?"
    )
with col_button:
    st.write("")  # Espaço para alinhamento
    enviar = st.button("Enviar", key="pulse")

if enviar:
    if user_input:
        reply = None
        if config.DEBUG: 
            reply = 'A justificativa para a abertura dos créditos suplementares varia de acordo com o anexo em questão.No Anexo II referente ao Decreto nº 18.889, de 28 de novembro de 2024, os créditos suplementares são justificados pela necessidade de reforçar a dotação para despesas com auxílio-alimentação no quarto trimestre de 2024, devido a um reajuste concedido aos funcionários. O valor total de R$45.138.516,26 é destinado ao Fundo Municipal de Saúde (FMS) para cobrir despesas com serviços de água e esgoto, locação, aquisição de insumos, terceirização de mão de obra, Contratos Administrativos (CADM) e repasses aos hospitais da rede SUS e conveniados.No Anexo II referente ao Decreto nº 18.904, de 11 de dezembro de 2024, a abertura de créditos suplementares é autorizada com base na Lei federal nº 4.320, de 17 de março de 1964, e na Lei nº 11.644, de 29 de dezembro de 2023. O valor de R$7.223.836,33, proveniente de Excesso de Arrecadação, é destinado à Secretaria Municipal de Educação (SMED) para a aquisição de uniformes escolares.No Anexo II referente ao Decreto nº 18.886, de 28 de novembro de 2024, a justificativa é semelhante à do decreto anterior, com base na Lei federal nº 4.320/1964 e na Lei nº 11.644/2023. No entanto, o valor de R$2.213.500,00 é destinado à Secretaria Municipal de Educação (SMED) para atender a objetivos não especificados no texto fornecido.'
        else:
            response = requests.post(
                config.FASTAPI_BACKEND_URL, 
                json={"message": user_input}
            )
            
            if response.status_code == 200:
                reply = response.json().get("answer", "Sem resposta.")

                if isinstance(reply, list) and len(reply) > 0: 
                    reply = reply[0]
                
        if reply is None:
            st.error("Falha ao obter resposta do chat.")
        else:
            CHARS_PER_ROW = 70
            MAX_ROWS = 100

            num_rows = (len(reply) // CHARS_PER_ROW) + 1  # Calculate rows based on text length
            num_rows = min(num_rows, MAX_ROWS)  # Restrict to MAX_ROWS

            # Display the output in a dynamically sized text area
            st.text_area(
                "Chat responde:",
                value=reply,
                height=max(70, num_rows * 20),  # Estimate height based on rows (20px per row is approximate)
            )
    else:
        st.warning("Por favor, digite uma mensagem antes de enviar.")
