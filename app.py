import streamlit as st
import pandas as pd
import datetime
import gspread
import altair as alt
from google.oauth2.service_account import Credentials

# Autenticação
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

# Acessar planilhas
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1RgQ1Q75CwlbVbCFWCxauO_Z6gJwAAvxuTAqNBfqRpyQ/edit"
sheet = client.open_by_url(spreadsheet_url).worksheet("leituras")
aba_tarifas = client.open_by_url(spreadsheet_url).worksheet("tarifas")

# Interface principal
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

    # Buscar tarifa
    try:
        df_tarifas = pd.DataFrame(aba_tarifas.get_all_records())
        tarifa_do_mes = df_tarifas[df_tarifas["mes"] == mes]["tarifa"].values

        if len(tarifa_do_mes) > 0:
            tarifa_str = str(tarifa_do_mes[0]).replace(",", ".")
            try:
                tarifa = float(tarifa_str)
            except ValueError:
                st.warning("⚠️ Tarifa inválida. Usando padrão: 1.05")
                tarifa = 1.05
        else:
            tarifa = 1.05
    except Exception:
        st.warning("⚠️ Não foi possível buscar a tarifa. Usando padrão: 1.05")
        tarifa = 1.05

    valor_estimado = round(projecao_kwh * tarifa, 2)

    # Salvar na planilha com vírgula
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

# Histórico
st.subheader("📊 Histórico de Leituras")
df = pd.DataFrame(sheet.get_all_records())

# Colunas numéricas
colunas_numericas = ["leitura", "consumo_parcial", "dias_passados", "media_diaria", "projecao_kwh", "valor_estimado"]

# Corrigir vírgula → ponto e converter
for col in colunas_numericas:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace(",", ".").str.replace("R$", "").str.strip()
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Formatar para exibição
df["media_diaria"] = df["media_diaria"].map("{:.2f}".format)
df["projecao_kwh"] = df["projecao_kwh"].map("{:.2f}".format)
df["valor_estimado"] = df["valor_estimado"].map(lambda x: f"R$ {x:.2f}")

st.dataframe(df)

# Gráfico de consumo mensal
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
