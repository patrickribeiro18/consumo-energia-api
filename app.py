import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# Autenticação via st.secrets
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

# Link direto da planilha
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1RgQ1Q75CwlbVbCFWCxauO_Z6gJwAAvxuTAqNBfqRpyQ/edit"

# Abrir abas
sheet = client.open_by_url(spreadsheet_url).worksheet("leituras")
aba_tarifas = client.open_by_url(spreadsheet_url).worksheet("tarifas")

# Interface Streamlit
st.title("🔌 Controle de Consumo de Energia")
st.caption("Acompanhe, projete e compare o consumo de energia mês a mês.")

# Entradas
data_leitura = st.date_input("📅 Data da Leitura", datetime.date.today())
leitura = st.number_input("🔢 Numeração atual do relógio (kWh)", min_value=0)

if st.button("💾 Salvar Leitura"):
    dados = sheet.get_all_records()
    ultima_leitura = int(dados[-1]["leitura"]) if dados else 0
    data_ultima = pd.to_datetime(dados[-1]["data_leitura"]) if dados else data_leitura

    consumo_parcial = leitura - ultima_leitura
    dias_passados = (data_leitura - data_ultima).days or 1
    media_diaria = consumo_parcial / dias_passados
    dias_totais = 30
    projecao_kwh = round(media_diaria * dias_totais, 2)

    mes = data_leitura.strftime("%Y-%m")

    try:
        df_tarifas = pd.DataFrame(aba_tarifas.get_all_records())
        tarifa_do_mes = df_tarifas[df_tarifas["mes"] == mes]["tarifa"].values
        tarifa = float(tarifa_do_mes[0]) if len(tarifa_do_mes) > 0 else 0.91
    except Exception:
        st.warning("⚠️ Não foi possível buscar a tarifa atual, usando valor padrão.")
        tarifa = 0.91

    valor_estimado = round(projecao_kwh * tarifa, 2)

    nova_linha = [str(data_leitura), leitura, consumo_parcial, dias_passados,
                  round(media_diaria, 2), projecao_kwh, valor_estimado, mes]
    sheet.append_row(nova_linha)
    st.success(f"✅ Leitura salva! Estimativa da conta: R$ {valor_estimado:.2f}")

# Exibir histórico
st.subheader("📊 Histórico de Leituras")
df = pd.DataFrame(sheet.get_all_records())
st.dataframe(df)
