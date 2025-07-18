## app.py
import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt # Adicione esta linha

# Título da Aplicação
st.set_page_config(layout="wide")
st.title("Monitoramento de Eventos Adversos de Medicamentos (OpenFDA)")

st.write("Explorando dados de eventos adversos de medicamentos fornecidos pela OpenFDA API.")

# URL do endpoint da API que vamos usar
OPENFDA_API_URL = "https://api.fda.gov/drug/event.json"

@st.cache_data
def load_data(limit=100):
    """
    Carrega dados de eventos adversos da OpenFDA API.
    Utiliza st.cache_data para evitar múltiplas requisições desnecessárias.
    """
    params = {"limit": limit} # Define o limite de resultados
    try:
        response = requests.get(OPENFDA_API_URL, params=params)
        response.raise_for_status()  # Levanta um erro para status codes HTTP 4xx/5xx
        data = response.json()
        return data['results']
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar dados da API: {e}")
        return []

# Carrega os dados
data = load_data(limit=200) # Você pode ajustar o limite aqui

if data:
    st.subheader("Primeiros Registros de Eventos Adversos")
    # Mostra os primeiros 5 registros em um DataFrame para visualização inicial
    st.dataframe(pd.DataFrame(data).head())
    # --- NOVO: Imprimir a estrutura de um registro para depuração ---
    if len(data) > 0:
        st.subheader("Estrutura do Primeiro Registro (para Depuração)")
        st.json(data[0]) # Mostra o primeiro registro como JSON formatado
    # --- FIM NOVO ---
else:
    st.info("Nenhum dado carregado da API. Verifique a conexão ou o limite.")

# Linha horizontal para separar as seções
st.markdown("---")

st.subheader("Próximos Passos:")
st.write("Agora que temos os dados, podemos começar a extrair indicadores e visualizá-los!")
st.write("Continue acompanhando para as próximas partes do código.")

## app.py (Adicione estas linhas após a Parte 1)

# ... (código da Parte 1) ...

if data:
    df = pd.DataFrame(data)

    st.subheader("Indicadores Gerais")

    # Indicador 1: Número Total de Eventos
    total_events = len(df)
    st.metric(label="Total de Eventos Adversos Registrados", value=total_events)

    # Indicador 2: Top 10 Países de Origem dos Eventos
    # Precisamos verificar se 'occurrencemarker' ou outro campo similar existe e é adequado para país.
    # A estrutura dos dados da FDA é aninhada. Vamos tentar acessar 'primarysource.reporter_country'.
    # Será necessário um pré-processamento para extrair isso de forma robusta.
    # Por enquanto, vamos supor que exista um campo direto ou que iremos simplificar.

    # Exemplo simplificado (pode precisar de ajuste dependendo da estrutura exata do JSON retornado)
    # Vamos extrair o campo 'receiver.country' que geralmente indica o país que recebeu o relatório.
    # Se 'receiver.country' não for o ideal, você pode explorar outras chaves do JSON.
    #countries = df['receiver'].apply(lambda x: x['country'] if isinstance(x, dict) and 'country' in x else 'Desconhecido')
    countries = df['primarysource'].apply(lambda x: x['reportercountry'] if isinstance(x, dict) and 'reportercountry' in x else 'Desconhecido')
    country_counts = countries.value_counts().head(10)

    st.subheader("Eventos por País de Origem (Top 10)")
    st.bar_chart(country_counts)

    # Indicador 3: Contagem de Gênero (se disponível e pré-processado)
    # A informação de gênero geralmente está em patient.patientsex.

    if 'patient' in df.columns:
            # Extrai o valor de patientsex
            gender_raw = df['patient'].apply(lambda x: x['patientsex'] if isinstance(x, dict) and 'patientsex' in x else None)

            # Mapeamento dos valores numéricos para descrições legíveis
            # A documentação da FDA geralmente usa:
            # 1 = Male (Masculino)
            # 2 = Female (Feminino)
            # NULL/Outro = Not Specified (Não Informado)
            gender_mapped = gender_raw.map({
                '1': 'Masculino',
                '2': 'Feminino',
                'M': 'Masculino', # Adicionado caso encontre 'M' como string
                'F': 'Feminino'   # Adicionado caso encontre 'F' como string
            }).fillna('Não Informado') # Substitui valores não mapeados ou None por 'Não Informado'

            gender_counts = gender_mapped.value_counts()

            if not gender_counts.empty:
                st.subheader("Distribuição por Gênero")
                fig, ax = plt.subplots()
                ax.pie(gender_counts, labels=gender_counts.index, autopct='%1.1f%%', startangle=90)
                ax.axis('equal')
                st.pyplot(fig)
            else:
                st.info("Nenhum dado de gênero válido para plotar.")
    else:
            st.info("Coluna 'patient' não encontrada para análise de gênero.")    

else:
    st.info("Nenhum dado para análise de indicadores.")

# Adicione esta seção no seu app.py, após a análise de gênero, por exemplo.

st.markdown("---")
st.subheader("Medicamentos Mais Frequentes")

# Extrair medicamentos: Este é mais complexo devido à lista aninhada
def get_medicinal_products(patient_data):
    products = []
    if isinstance(patient_data, dict) and 'drug' in patient_data and isinstance(patient_data['drug'], list):
        for drug_info in patient_data['drug']:
            if isinstance(drug_info, dict) and 'medicinalproduct' in drug_info:
                products.append(drug_info['medicinalproduct'])
    return products

if 'patient' in df.columns:
    # Aplica a função para extrair todos os medicamentos de cada linha
    all_products = df['patient'].apply(get_medicinal_products)
    # Explode a lista de listas em uma única série de medicamentos
    flat_products = [item for sublist in all_products if sublist for item in sublist]

    if flat_products:
        product_series = pd.Series(flat_products)
        top_products = product_series.value_counts().head(10)

        st.bar_chart(top_products)
    else:
        st.info("Nenhum dado de medicamento encontrado para análise.")
else:
    st.info("Coluna 'patient' não encontrada para análise de medicamentos.")


# Adicione esta seção no seu app.py

st.markdown("---")
st.subheader("Reações Adversas Mais Comuns")

# Extrair reações: Similar aos medicamentos
def get_reactions(patient_data):
    reactions = []
    if isinstance(patient_data, dict) and 'reaction' in patient_data and isinstance(patient_data['reaction'], list):
        for reaction_info in patient_data['reaction']:
            if isinstance(reaction_info, dict) and 'reactionmeddrapt' in reaction_info:
                reactions.append(reaction_info['reactionmeddrapt'])
    return reactions

if 'patient' in df.columns:
    all_reactions = df['patient'].apply(get_reactions)
    flat_reactions = [item for sublist in all_reactions if sublist for item in sublist]

    if flat_reactions:
        reaction_series = pd.Series(flat_reactions)
        top_reactions = reaction_series.value_counts().head(10)

        st.bar_chart(top_reactions)
    else:
        st.info("Nenhuma reação adversa encontrada para análise.")
else:
    st.info("Coluna 'patient' não encontrada para análise de reações.")


# Adicione esta seção no seu app.py

st.markdown("---")
st.subheader("Distribuição por Idade do Paciente")

# Mapear unidades de idade para um fator de conversão para anos
AGE_UNIT_MAP = {
    '800': 10,  # Décadas
    '801': 1,   # Anos
    '802': 1/12, # Meses
    '803': 1/365, # Dias
    '804': 1/(365*24) # Horas
}

def get_normalized_age(patient_data):
    if isinstance(patient_data, dict) and 'patientonsetage' in patient_data and 'patientonsetageunit' in patient_data:
        try:
            age = float(patient_data['patientonsetage'])
            unit = patient_data['patientonsetageunit']
            if unit in AGE_UNIT_MAP:
                return age * AGE_UNIT_MAP[unit]
        except (ValueError, TypeError):
            pass # Ignora idades não numéricas ou unidades inválidas
    return None # Retorna None para idades inválidas/ausentes

if 'patient' in df.columns:
    df['normalized_age'] = df['patient'].apply(get_normalized_age)
    valid_ages = df['normalized_age'].dropna()

    if not valid_ages.empty:
        st.write(f"Idade média dos pacientes: **{valid_ages.mean():.1f} anos**")

        # Criar histograma para distribuição de idade
        st.subheader("Histograma de Idade")
        fig_hist, ax_hist = plt.subplots()
        ax_hist.hist(valid_ages, bins=20, edgecolor='black')
        ax_hist.set_xlabel("Idade (Anos)")
        ax_hist.set_ylabel("Número de Pacientes")
        st.pyplot(fig_hist)
    else:
        st.info("Nenhum dado de idade válido encontrado para análise.")
else:
    st.info("Coluna 'patient' não encontrada para análise de idade.")

## app.py (Adicione ou ajuste estas linhas após a Parte 2)

# ... (código das Partes 1 e 2) ...

if data:
    df = pd.DataFrame(data)

    # Pré-processamento da data para gráficos temporais
    # A data do evento geralmente está em 'receiptdate' ou 'receivedate'
    # Vamos usar 'receiptdate' para simplificar, mas pode variar na API
    if 'receiptdate' in df.columns:
        df['receipt_date'] = pd.to_datetime(df['receiptdate'], errors='coerce')
        df.dropna(subset=['receipt_date'], inplace=True) # Remove linhas com datas inválidas

        st.subheader("Análise Temporal de Eventos Adversos")

        # Slider de data para filtrar
        min_date = df['receipt_date'].min().date() if not df['receipt_date'].empty else pd.to_datetime("2000-01-01").date()
        max_date = df['receipt_date'].max().date() if not df['receipt_date'].empty else pd.to_datetime("2025-01-01").date()

        date_range = st.slider(
            "Selecione o Intervalo de Datas",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD"
        )

        filtered_df = df[(df['receipt_date'].dt.date >= date_range[0]) & (df['receipt_date'].dt.date <= date_range[1])]

        st.write(f"Eventos no período selecionado: {len(filtered_df)}")

        if not filtered_df.empty:
            events_over_time = filtered_df.groupby(pd.Grouper(key='receipt_date', freq='ME')).size().reset_index(name='count')
            events_over_time.columns = ['Data', 'Contagem'] # Renomear colunas para o gráfico

            st.line_chart(events_over_time, x='Data', y='Contagem')
        else:
            st.info("Nenhum evento encontrado no intervalo de datas selecionado.")

    else:
        st.info("Coluna 'receiptdate' não encontrada para análise temporal.")

else:
    st.info("Nenhum dado disponível para análise temporal.")

st.markdown("---")
st.subheader("Próximos Passos e Desafios:")
st.write("A OpenFDA API é poderosa, mas exige um bom pré-processamento dos dados JSON aninhados. Explore a documentação da OpenFDA para identificar os campos que você precisa e como acessá-los.")
st.write("Você pode criar mais indicadores, como os medicamentos mais citados, os tipos de eventos adversos mais comuns e aplicar filtros interativos.")
st.write("Podemos também integrar com Django para armazenar os dados localmente e ter um controle maior, mas isso é um passo futuro!")