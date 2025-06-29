import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# Autenticação Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file("credenciais.json", scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("consumo_energia").worksheet("leituras")

# Interface
st.title("🔌 Controle de Consumo de Energia")
st.caption("Acompanhe, projete e compare o consumo de energia")

# Entradas do usuário
data_leitura = st.date_input("📅 Data da Leitura", datetime.date.today())
leitura = st.number_input("🔢 Numeração atual do relógio (kWh)", min_value=0)

if st.button("💾 Salvar Leitura"):
    dados = sheet.get_all_records()
    ultima_leitura = int(dados[-1]["leitura"]) if dados else 0
    data_ultima = pd.to_datetime(dados[-1]["data_leitura"]) if dados else data_leitura

    consumo_parcial = leitura - ultima_leitura
    dias_passados = (data_leitura - data_ultima.date()).days or 1
    media_diaria = consumo_parcial / dias_passados
    dias_totais = 30  # Pode ajustar depois
    projecao_kwh = round(media_diaria * dias_totais, 2)
    tarifa = 0.91  # Tarifa estimada (residencial Equatorial MA)
    valor_estimado = round(projecao_kwh * tarifa, 2)
    mes = data_leitura.strftime("%Y-%m")

    nova_linha = [str(data_leitura), leitura, consumo_parcial, dias_passados,
                  round(media_diaria, 2), projecao_kwh, valor_estimado, mes]
    sheet.append_row(nova_linha)

    st.success(f"✅ Leitura salva! Estimativa da conta: R$ {valor_estimado:.2f}")

# Mostrar histórico
st.subheader("📊 Histórico de Leituras")
df = pd.DataFrame(sheet.get_all_records())
st.dataframe(df)
