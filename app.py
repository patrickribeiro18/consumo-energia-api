import streamlit as st
import pandas as pd
import datetime
import gspread
import altair as alt
from google.oauth2.service_account import Credentials

# Autenticação com Google Sheets
info = {
    "type": st.secrets["google_service_account"]["type"],
    "project_id": st.secrets["google_service_account"]["project_id"],
    "private_key_id": st.secrets["google_service_account"]["private_key_id"],
    "private_key": st.secrets["google_service_account"]["private_key"],
    "client_email": st.secrets["google_service_account"]["client_email"],
    "token_uri": st.secrets["google_service_account"]["token_uri"]
}

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(info, scopes=scope)
client = gspread.authorize(creds)

# Planilhas
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1RgQ1Q75CwlbVbCFWCxauO_Z6gJwAAvxuTAqNBfqRpyQ/edit"
sheet = client.open_by_url(spreadsheet_url).worksheet("leituras")
aba_tarifas = client.open_by_url(spreadsheet_url).worksheet("tarifas")

# Interface do app
st.title("🔌 Controle de Consumo de Energia")
st.caption("Acompanhe, projete e compare o consumo de energia mês a mês.")

data_leitura = st.date_input("📅 Data da Leitura", datetime.date.today())
leitura = st.number_input("🔢 Numeração atual do relógio (kWh)", min_value=0)

if st.button("💾 Salvar Leitura"):
    dados = sheet.get_all_records()
    ultima_leitura = int(dados[-1]["leitura"]) if dados else 0
    data_ultima = pd.to_datetime(dados[-1]["data_leitura"]).date() if dados else data_leitura

    consumo_parcial = leitura - ultima_leitura
    dias_passados = (data_leitura - data_ultima).days or 1
    media_diaria = round(consumo_parcial / dias_passados, 2)
    dias_totais = 30
    projecao_kwh = round(media_diaria * dias_totais, 2)
    mes = data_leitura.strftime("%Y-%m")

    try:
        df_tarifas = pd.DataFrame(aba_tarifas.get_all_records())
        tarifa_do_mes = df_tarifas[df_tarifas["mes"] == mes]["tarifa"].values
        if len(tarifa_do_mes) > 0:
            tarifa_str = str(tarifa_do_mes[0]).replace(",", ".")
            tarifa = float(tarifa_str)
        else:
            tarifa = 1.05
    except Exception:
        tarifa = 1.05

    valor_estimado = round(projecao_kwh * tarifa, 2)

    nova_linha = [
        str(data_leitura),
        leitura,
        consumo_parcial,
        dias_passados,
        f"{media_diaria:.2f}".replace(".", ","),
        f"{projecao_kwh:.2f}".replace(".", ","),
        f"{valor_estimado:.2f}".replace(".", ","),
        mes
    ]
    sheet.append_row(nova_linha)
    st.success(f"✅ Leitura salva! Estimativa da conta: R$ {valor_estimado:.2f}")

# Leitura da planilha
df = pd.DataFrame(sheet.get_all_records())

# Conversão de valores com vírgula → ponto
colunas_numericas = ["leitura", "consumo_parcial", "dias_passados", "media_diaria", "projecao_kwh", "valor_estimado"]
for col in colunas_numericas:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace(",", ".").str.replace("R$", "").str.strip()
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Formatação visual
df["media_diaria"] = df["media_diaria"].map("{:.2f}".format)
df["projecao_kwh"] = df["projecao_kwh"].map("{:.2f}".format)
df["valor_estimado"] = df["valor_estimado"].map(lambda x: f"R$ {x:.2f}")

# Tabela moderna com CSS
st.markdown("### 📋 Histórico de Leituras")
tabela_html = """
<style>
.tabela-consumo {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Segoe UI', sans-serif;
    font-size: 15px;
}
.tabela-consumo thead {
    background-color: #f4f4f4;
    position: sticky;
    top: 0;
    z-index: 1;
}
.tabela-consumo th, .tabela-consumo td {
    border: 1px solid #ddd;
    padding: 8px;
    text-align: center;
}
.tabela-consumo tr:nth-child(even) {
    background-color: #f9f9f9;
}
.tabela-consumo tr:hover {
    background-color: #f1f1f1;
}
.tabela-consumo th {
    color: #333;
}
</style>
<table class='tabela-consumo'>
    <thead>
        <tr>
            <th>Data</th>
            <th>Leitura</th>
            <th>Consumo</th>
            <th>Dias</th>
            <th>Média diária</th>
            <th>Projeção (kWh)</th>
            <th>Valor estimado</th>
            <th>Mês</th>
        </tr>
    </thead>
    <tbody>
"""
for _, row in df.iterrows():
    tabela_html += "<tr>"
    tabela_html += f"<td>{row['data_leitura']}</td>"
    tabela_html += f"<td>{row['leitura']}</td>"
    tabela_html += f"<td>{row['consumo_parcial']}</td>"
    tabela_html += f"<td>{row['dias_passados']}</td>"
    tabela_html += f"<td>{row['media_diaria']}</td>"
    tabela_html += f"<td>{row['projecao_kwh']}</td>"
    tabela_html += f"<td>{row['valor_estimado']}</td>"
    tabela_html += f"<td>{row['mes']}</td>"
    tabela_html += "</tr>"
tabela_html += "</tbody></table>"
st.markdown(tabela_html, unsafe_allow_html=True)

# Gráfico mensal
st.subheader("📈 Consumo Acumulado por Mês")
if "mes" in df.columns and "consumo_parcial" in df.columns:
    grafico = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("mes:N", title="Mês"),
            y=alt.Y("sum(consumo_parcial):Q", title="Consumo (kWh)"),
            tooltip=["mes", "sum(consumo_parcial)"]
        )
        .properties(width=600, height=300)
    )
    st.altair_chart(grafico, use_container_width=True)
else:
    st.info("📌 Ainda não há dados suficientes para gerar o gráfico.")

# Excluir uma leitura
st.subheader("🗑️ Excluir uma Leitura")
if not df.empty:
    datas = df["data_leitura"].tolist()
    data_excluir = st.selectbox("Selecione a data da leitura a excluir", options=datas)

    if st.button("🚨 Excluir leitura selecionada"):
        linhas = sheet.get_all_values()
        for i, linha in enumerate(linhas[1:], start=2):  # pula cabeçalho
            if linha[0] == data_excluir:
                sheet.delete_rows(i)
                st.success(f"✅ Leitura de {data_excluir} foi excluída com sucesso.")
                st.experimental_rerun()
                break
        else:
            st.warning("⚠️ Leitura não encontrada.")
else:
    st.info("Ainda não há leituras para excluir.")
