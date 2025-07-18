import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns # Opcional, para melhorar a estética dos gráficos, se quiser

# --- Configurações Iniciais do Streamlit ---
st.set_page_config(layout="wide", page_title="OpenFDA - Análise de Eventos Adversos")

# --- Constantes ---
# URL base da API OpenFDA para eventos adversos de medicamentos
BASE_URL = "https://api.fda.gov/drug/event.json"

# --- Funções de Carregamento de Dados ---
@st.cache_data(ttl=3600) # Cache os dados por 1 hora para evitar requisições repetidas
def load_data(limit=100):
    """
    Carrega dados de eventos adversos da OpenFDA API.
    """
    params = {
        "limit": limit
    }
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status() # Lança um erro para status de resposta ruins (4xx ou 5xx)
        data = response.json()
        return data.get('results', [])
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao conectar à OpenFDA API: {e}")
        return []

# --- Título e Descrição do Aplicativo ---
st.title("Análise de Eventos Adversos de Medicamentos - OpenFDA")
st.markdown("""
Este aplicativo consulta a API OpenFDA para recuperar e analisar eventos adversos de medicamentos.
Explore os dados através de diversos indicadores visuais.
""")

# --- Carregamento e Pré-processamento de Dados ---
limit_input = st.sidebar.slider("Número de Eventos para Carregar (Max 2500)", 100, 2500, 500)
data = load_data(limit=limit_input)

# Verifica se os dados foram carregados com sucesso
if data:
    df = pd.DataFrame(data)

    st.sidebar.success(f"Dados brutos carregados: {len(df)} eventos.")

    # --- NOVO: Pré-processamento de datas e SLIDER DE DATA GLOBAL na SIDEBAR ---
    # Processa a coluna de data globalmente, antes de qualquer filtragem.
    if 'receiptdate' in df.columns:
        df['receipt_date'] = pd.to_datetime(df['receiptdate'], errors='coerce')
        # Remove linhas com datas inválidas logo no início do processamento.
        df.dropna(subset=['receipt_date'], inplace=True)

        if not df['receipt_date'].empty:
            min_date_raw = df['receipt_date'].min().date()
            max_date_raw = df['receipt_date'].max().date()

            st.sidebar.markdown("---") # Separador visual na sidebar
            st.sidebar.subheader("Filtrar por Intervalo de Datas")
            try:
                # O slider agora está na sidebar e afetará todos os gráficos
                date_range = st.sidebar.slider(
                    "Selecione o Intervalo de Datas",
                    min_value=min_date_raw,
                    max_value=max_date_raw,
                    value=(min_date_raw, max_date_raw),
                    format="YYYY-MM-DD"
                )
                # Filtra o DataFrame principal com base na seleção do slider
                # .copy() é importante para evitar SettingWithCopyWarning
                filtered_df = df[(df['receipt_date'].dt.date >= date_range[0]) &
                                 (df['receipt_date'].dt.date <= date_range[1])].copy()
            except Exception as e:
                st.sidebar.warning(f"Não foi possível criar o slider de data ou aplicar filtro. Exibindo todos os dados. Erro: {e}")
                filtered_df = df.copy() # Fallback para usar todos os dados
        else:
            st.sidebar.warning("Nenhuma data válida encontrada para filtrar. Exibindo todos os dados.")
            filtered_df = df.copy() # Se não houver datas válidas, use o DF completo
    else:
        st.sidebar.warning("Coluna 'receiptdate' não encontrada. Exibindo todos os dados sem filtro de data.")
        filtered_df = df.copy() # Se não houver coluna de data, use o DF completo

    # Verifica se o filtered_df está vazio após a filtragem
    if filtered_df.empty:
        st.warning("Nenhum evento encontrado no intervalo de datas selecionado. Tente ajustar o filtro de datas.")
    else:
        st.markdown("---")
        st.header("Indicadores Gerais e Detalhados")

        # Indicador 1: Número Total de Eventos (agora do filtered_df)
        total_events = len(filtered_df)
        st.metric(label="Total de Eventos Adversos Registrados (no período selecionado)", value=total_events)

        st.markdown("---")

        # --- Organização dos Gráficos em Colunas ---

        # Colunas para Gênero e País de Origem
        col1, col2 = st.columns(2)

        # Coluna 1: Distribuição por Gênero
        with col1:
            if 'patient' in filtered_df.columns:
                gender_raw = filtered_df['patient'].apply(lambda x: x['patientsex'] if isinstance(x, dict) and 'patientsex' in x else None)
                gender_mapped = gender_raw.map({
                    '1': 'Masculino',
                    '2': 'Feminino',
                    'M': 'Masculino',
                    'F': 'Feminino'
                }).fillna('Não Informado')

                gender_counts = gender_mapped.value_counts()

                if not gender_counts.empty:
                    st.subheader("Distribuição por Gênero")

                    fig_pie, ax_pie = plt.subplots(figsize=(3.8, 3.8))
                    fig_pie.patch.set_facecolor('none')
                    ax_pie.set_facecolor('none')

                    wedges, texts, autotexts = ax_pie.pie(
                        gender_counts,
                        labels=gender_counts.index,
                        autopct='%1.1f%%',
                        startangle=90,
                        textprops={'color': 'white', 'fontsize': 10}
                    )

                    for autotext in autotexts:
                        autotext.set_color('white')
                        autotext.set_fontsize(10)

                    ax_pie.axis('equal')

                    ax_pie.spines['top'].set_visible(False)
                    ax_pie.spines['right'].set_visible(False)
                    ax_pie.spines['bottom'].set_visible(False)
                    ax_pie.spines['left'].set_visible(False)

                    st.pyplot(fig_pie)
                    plt.close(fig_pie)
                else:
                    st.info("Nenhum dado de gênero válido para plotar no período selecionado.")
            else:
                st.info("Coluna 'patient' não encontrada para análise de gênero.")

        # Coluna 2: Eventos por País de Origem
        with col2:
            st.subheader("Eventos por País de Origem (Top 10)")
            countries = filtered_df['primarysource'].apply(lambda x: x['reportercountry'] if isinstance(x, dict) and 'reportercountry' in x else 'Desconhecido')
            country_counts = countries.value_counts().head(10)

            if not country_counts.empty:
                fig_bar, ax_bar = plt.subplots(figsize=(6, 4))
                ax_bar.bar(country_counts.index, country_counts.values, color='#1f77b4')

                ax_bar.set_xlabel("País", color='white', fontsize=10)
                ax_bar.set_ylabel("Contagem", color='white', fontsize=10)

                ax_bar.tick_params(axis='x', labelcolor='white', rotation=45, labelsize=9)
                ax_bar.tick_params(axis='y', labelcolor='white', labelsize=9)

                for tick in ax_bar.get_xticklabels():
                    tick.set_horizontalalignment('right')

                ax_bar.set_facecolor('none')
                fig_bar.patch.set_facecolor('none')

                plt.tight_layout()
                st.pyplot(fig_bar)
                plt.close(fig_bar)
            else:
                st.info("Nenhum dado de país encontrado para análise no período selecionado.")

        st.markdown("---")

        # Colunas para Medicamentos e Reações
        col3, col4 = st.columns(2)

        # Coluna 3: Medicamentos Mais Frequentes
        with col3:
            st.subheader("Medicamentos Mais Frequentes (Top 10)")
            def get_medicinal_products(patient_data):
                products = []
                if isinstance(patient_data, dict) and 'drug' in patient_data and isinstance(patient_data['drug'], list):
                    for drug_info in patient_data['drug']:
                        if isinstance(drug_info, dict) and 'medicinalproduct' in drug_info:
                            products.append(drug_info['medicinalproduct'])
                return products

            if 'patient' in filtered_df.columns:
                all_products = filtered_df['patient'].apply(get_medicinal_products)
                flat_products = [item for sublist in all_products if sublist for item in sublist]

                if flat_products:
                    product_series = pd.Series(flat_products)
                    top_products = product_series.value_counts().head(10)

                    fig_prod, ax_prod = plt.subplots(figsize=(6, 4))
                    ax_prod.bar(top_products.index, top_products.values, color='#2ca02c')

                    ax_prod.set_xlabel("Medicamento", color='white', fontsize=10)
                    ax_prod.set_ylabel("Contagem", color='white', fontsize=10)
                    ax_prod.tick_params(axis='x', labelcolor='white', rotation=45, labelsize=9)
                    ax_prod.tick_params(axis='y', labelcolor='white', labelsize=9)
                    for tick in ax_prod.get_xticklabels():
                        tick.set_horizontalalignment('right')

                    ax_prod.set_facecolor('none')
                    fig_prod.patch.set_facecolor('none')
                    plt.tight_layout()
                    st.pyplot(fig_prod)
                    plt.close(fig_prod)
                else:
                    st.info("Nenhum dado de medicamento encontrado para análise no período selecionado.")
            else:
                st.info("Coluna 'patient' não encontrada para análise de medicamentos.")

        # Coluna 4: Reações Adversas Mais Comuns
        with col4:
            st.subheader("Reações Adversas Mais Comuns (Top 10)")
            def get_reactions(patient_data):
                reactions = []
                if isinstance(patient_data, dict) and 'reaction' in patient_data and isinstance(patient_data['reaction'], list):
                    for reaction_info in patient_data['reaction']:
                        if isinstance(reaction_info, dict) and 'reactionmeddrapt' in reaction_info:
                            reactions.append(reaction_info['reactionmeddrapt'])
                return reactions

            if 'patient' in filtered_df.columns:
                all_reactions = filtered_df['patient'].apply(get_reactions)
                flat_reactions = [item for sublist in all_reactions if sublist for item in sublist]

                if flat_reactions:
                    reaction_series = pd.Series(flat_reactions)
                    top_reactions = reaction_series.value_counts().head(10)

                    fig_react, ax_react = plt.subplots(figsize=(6, 4))
                    ax_react.bar(top_reactions.index, top_reactions.values, color='#d62728')

                    ax_react.set_xlabel("Reação", color='white', fontsize=10)
                    ax_react.set_ylabel("Contagem", color='white', fontsize=10)
                    ax_react.tick_params(axis='x', labelcolor='white', rotation=45, labelsize=9)
                    ax_react.tick_params(axis='y', labelcolor='white', labelsize=9)
                    for tick in ax_react.get_xticklabels():
                        tick.set_horizontalalignment('right')

                    ax_react.set_facecolor('none')
                    fig_react.patch.set_facecolor('none')
                    plt.tight_layout()
                    st.pyplot(fig_react)
                    plt.close(fig_react)
                else:
                    st.info("Nenhuma reação adversa encontrada para análise no período selecionado.")
            else:
                st.info("Coluna 'patient' não encontrada para análise de reações.")

        st.markdown("---")

        # --- NOVAS COLUNAS PARA IDADE E TEMPORAL ---
        col5, col6 = st.columns(2)

        # Coluna 5: Análise de Idade do Paciente (Histograma)
        with col5:
            st.subheader("Análise de Idade do Paciente")

            if 'patient' in filtered_df.columns:
                AGE_UNIT_MAP = {
                    '800': 10,
                    '801': 1,
                    '802': 1/12,
                    '803': 1/365,
                    '804': 1/(365*24)
                }

                def get_normalized_age(patient_data):
                    if isinstance(patient_data, dict) and 'patientonsetage' in patient_data and 'patientonsetageunit' in patient_data:
                        try:
                            age = float(patient_data['patientonsetage'])
                            unit = str(patient_data['patientonsetageunit'])
                            if unit in AGE_UNIT_MAP:
                                return age * AGE_UNIT_MAP[unit]
                        except (ValueError, TypeError):
                            pass
                    return None

                # Aplica a função no filtered_df, não no df original
                filtered_df['normalized_age'] = filtered_df['patient'].apply(get_normalized_age)
                valid_ages = filtered_df['normalized_age'].dropna()

                if not valid_ages.empty:
                    st.write(f"Idade média dos pacientes: **{valid_ages.mean():.1f} anos**")

                    fig_hist, ax_hist = plt.subplots(figsize=(6, 3.5))
                    ax_hist.hist(valid_ages, bins=20, edgecolor='black', color='#9467bd')

                    ax_hist.set_xlabel("Idade (Anos)", color='white', fontsize=10)
                    ax_hist.set_ylabel("Número de Pacientes", color='white', fontsize=10)
                    ax_hist.tick_params(axis='x', labelcolor='white', labelsize=9)
                    ax_hist.tick_params(axis='y', labelcolor='white', labelsize=9)

                    ax_hist.set_facecolor('none')
                    fig_hist.patch.set_facecolor('none')

                    plt.tight_layout()
                    st.pyplot(fig_hist)
                    plt.close(fig_hist)
                else:
                    st.info("Nenhum dado de idade válido encontrado para análise no período selecionado.")
            else:
                st.info("Coluna 'patient' não encontrada para análise de idade.")

        # Coluna 6: Análise Temporal de Eventos Adversos (Gráfico de Linha)
        with col6:
            st.subheader("Análise Temporal de Eventos Adversos")

            # A filtragem de data já foi feita no início do script para o 'filtered_df'
            # e a coluna 'receipt_date' já foi processada.

            if not filtered_df.empty and 'receipt_date' in filtered_df.columns and not filtered_df['receipt_date'].empty:
                # Agrupa diretamente o filtered_df
                events_over_time = filtered_df.groupby(pd.Grouper(key='receipt_date', freq='ME')).size().reset_index(name='count')
                events_over_time.columns = ['Data', 'Contagem']

                if not events_over_time.empty:
                    fig_line, ax_line = plt.subplots(figsize=(10, 5))
                    ax_line.plot(events_over_time['Data'], events_over_time['Contagem'], color='#ff7f0e', marker='o', markersize=4)

                    ax_line.set_xlabel("Data", color='white', fontsize=10)
                    ax_line.set_ylabel("Contagem de Eventos", color='white', fontsize=10)
                    ax_line.tick_params(axis='x', labelcolor='white', rotation=45, labelsize=9)
                    ax_line.tick_params(axis='y', labelcolor='white', labelsize=9)

                    formatter = mdates.DateFormatter('%Y-%m')
                    ax_line.xaxis.set_major_formatter(formatter)
                    plt.xticks(rotation=45, ha='right')

                    ax_line.set_facecolor('none')
                    fig_line.patch.set_facecolor('none')

                    plt.tight_layout()
                    st.pyplot(fig_line)
                    plt.close(fig_line)
                else:
                    st.info("Nenhum evento encontrado no intervalo de datas selecionado para a análise temporal.")
            else:
                st.info("Nenhum dado de data válido para análise temporal no período selecionado.")
        # --- FIM DAS NOVAS COLUNAS PARA IDADE E TEMPORAL ---

else: # Caso os dados da API não sejam carregados
    st.warning("Nenhum dado carregado da API. Verifique a conexão com a internet ou o limite de requisição da API.")

st.markdown("---")
st.subheader("Próximos Passos e Desafios:")
st.markdown("""
* **Mais Indicadores:** Explore outros campos da API (ex: `seriousnessdeath`, `patientonsetageunit`) para criar mais gráficos.
* **Mais Filtros:** Adicione outros filtros interativos na barra lateral (sidebar) para medicamentos específicos, países, reações, etc.
* **Tratamento de Dados:** Melhore o tratamento de valores ausentes ou inconsistentes (ex: diferentes unidades para idade) de forma mais robusta.
* **Performance:** Para grandes volumes de dados, considere salvar os dados em um arquivo local (CSV, Parquet) após a primeira requisição para evitar chamar a API repetidamente.
""")