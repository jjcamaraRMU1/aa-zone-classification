import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import logging
from datetime import datetime
import io
import openpyxl
from io import BytesIO
# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Constantes
REQUIRED_COLUMNS = ['User_Id', 'Stow_Rate', 'Turnaway_Percentage']
COLUMN_MAPPINGS = {
    'User_Id': 'ID',
    'Stow_Rate': 'RATES',
    'Turnaway_Percentage': 'UIT'
}
ZONE_COLORS = {
    'Zone 1: High Rate & High UIT': 'red',
    'Zone 2: High Rate & Low UIT': 'green',
    'Zone 3: Low Rate & High UIT': 'orange',
    'Zone 4: Low Rate & Low UIT': 'blue'
}

@st.cache_data
def setup_page():
    """Configura la página de Streamlit"""
    st.set_page_config(
        page_title="Weekly Performance Comparison",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    st.title("Weekly Performance Comparison")
    st.markdown("Compare performance between last week and current week")

def load_files():
    """Carga y valida los archivos CSV"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Last Week's Data")
        last_week_file = st.file_uploader(
            "Upload last week's data (CSV)",
            type=["csv"],
            key='last_week',
            help="Upload CSV file with last week's performance data"
        )
    
    with col2:
        st.subheader("Current Week's Data")
        current_week_file = st.file_uploader(
            "Upload current week's data (CSV)",
            type=["csv"],
            key='current_week',
            help="Upload CSV file with current week's performance data"
        )
    
    return last_week_file, current_week_file

def validate_and_process_data(file, period):
    """Valida y procesa los datos del archivo CSV"""
    try:
        df = pd.read_csv(file)
        
        # Validar columnas requeridas
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_columns:
            st.error(f"Missing required columns in {period} file: {', '.join(missing_columns)}")
            return None
        
        # Renombrar columnas
        df.rename(columns=COLUMN_MAPPINGS, inplace=True)
        
        # Validar datos
        if df['RATES'].isnull().any() or df['UIT'].isnull().any():
            st.warning(f"Found null values in {period} data. These rows will be removed.")
            df = df.dropna(subset=['RATES', 'UIT'])
        
        # Validar rangos
        if (df['RATES'] < 0).any() or (df['UIT'] < 0).any() or (df['UIT'] > 100).any():
            st.error(f"Invalid values found in {period} data")
            return None
        
        return df
        
    except Exception as e:
        logging.error(f"Error processing {period} file: {str(e)}")
        st.error(f"Error processing {period} file: {str(e)}")
        return None

def apply_zone_classification(df, user_rate, user_uit):
    """Aplica la clasificación por zonas"""
    try:
        df['Zone'] = df.apply(
            lambda row: classify_zone(row, user_rate, user_uit),
            axis=1
        )
        return df
    except Exception as e:
        logging.error(f"Error in zone classification: {str(e)}")
        st.error("Error classifying zones")
        return None

def classify_zone(row, user_rate, user_uit):
    """Clasifica una fila en su zona correspondiente"""
    if row['RATES'] > user_rate and row['UIT'] > user_uit:
        return 'Zone 1: High Rate & High UIT'
    elif row['RATES'] > user_rate and row['UIT'] <= user_uit:
        return 'Zone 2: High Rate & Low UIT'
    elif row['RATES'] <= user_rate and row['UIT'] > user_uit:
        return 'Zone 3: Low Rate & High UIT'
    else:
        return 'Zone 4: Low Rate & Low UIT'

def display_current_week_scatter(df_current, user_rate, user_uit):
    """Muestra el gráfico de dispersión de la semana actual"""
    try:
        fig = px.scatter(
            df_current,
            x='RATES',
            y='UIT',
            color='Zone',
            hover_name='ID',
            title='Current Week Zone Classification',
            labels={'RATES': 'Rate', 'UIT': 'Unknown Idle Time (%)'},
            color_discrete_map=ZONE_COLORS
        )
        
        # Agregar líneas de referencia
        fig.add_hline(
            y=user_uit,
            line_dash="dash",
            line_color="gray",
            annotation_text="UIT Reference"
        )
        fig.add_vline(
            x=user_rate,
            line_dash="dash",
            line_color="gray",
            annotation_text="Rate Reference"
        )
        
        # Configurar rangos dinámicos
        rate_padding = (df_current['RATES'].max() - df_current['RATES'].min()) * 0.1
        uit_padding = (df_current['UIT'].max() - df_current['UIT'].min()) * 0.1
        
        fig.update_layout(
            xaxis=dict(
                title='Rate',
                range=[df_current['RATES'].min() - rate_padding,
                       df_current['RATES'].max() + rate_padding]
            ),
            yaxis=dict(
                title='Unknown Idle Time (%)',
                range=[max(0, df_current['UIT'].min() - uit_padding),
                       min(100, df_current['UIT'].max() + uit_padding)]
            ),
            hoverlabel=dict(bgcolor="white"),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        logging.error(f"Error en scatter plot: {str(e)}")
        st.error("Error al mostrar el gráfico de dispersión")

def display_zone_distribution(df_current):
    """Muestra la distribución de zonas"""
    try:
        st.subheader("Current Week Zone Distribution")
        zone_counts = df_current['Zone'].value_counts()
        
        col1, col2 = st.columns([2,1])
        
        with col1:
            fig_pie = px.pie(
                values=zone_counts.values,
                names=zone_counts.index,
                title="Associates Distribution by Zone",
                color=zone_counts.index,
                color_discrete_map=ZONE_COLORS
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie)
            
        with col2:
            st.write("Associates per Zone:")
            total_associates = len(df_current)
            for zone, count in zone_counts.items():
                percentage = (count/total_associates) * 100
                st.write(f"**{zone}:** {count} associates ({percentage:.1f}%)")
                
    except Exception as e:
        logging.error(f"Error en distribución de zonas: {str(e)}")
        st.error("Error al mostrar la distribución de zonas")

def filter_by_zone(df_last, df_current, selected_zone):
    """Filtra los DataFrames por zona seleccionada"""
    try:
        if selected_zone != 'All Zones':
            df_last_filtered = df_last[df_last['Zone'] == selected_zone]
            df_current_filtered = df_current[df_current['Zone'] == selected_zone]
        else:
            df_last_filtered = df_last
            df_current_filtered = df_current
            
        return df_last_filtered, df_current_filtered
        
    except Exception as e:
        logging.error(f"Error en filtrado por zona: {str(e)}")
        return df_last, df_current

def create_comparison_dataframe(df_last, df_current):
    """Crea el DataFrame de comparación"""
    try:
        comparison_df = pd.merge(
            df_last[['ID', 'RATES', 'UIT', 'Zone']].rename(
                columns={'RATES': 'Last_Rate', 'UIT': 'Last_UIT', 'Zone': 'Last_Zone'}
            ),
            df_current[['ID', 'RATES', 'UIT', 'Zone']].rename(
                columns={'RATES': 'Current_Rate', 'UIT': 'Current_UIT'}
            ),
            on='ID',
            how='inner'
        )
        
        # Calcular cambios
        comparison_df['Rate_Change'] = comparison_df['Current_Rate'] - comparison_df['Last_Rate']
        comparison_df['UIT_Change'] = comparison_df['Current_UIT'] - comparison_df['Last_UIT']
        comparison_df['Zone_Changed'] = comparison_df['Zone'] != comparison_df['Last_Zone']
        
        return comparison_df
        
    except Exception as e:
        logging.error(f"Error en creación de DataFrame de comparación: {str(e)}")
        st.error("Error al crear la comparación de datos")
        return None

def display_comparative_metrics(df_last_filtered, df_current_filtered):
    """Muestra métricas comparativas"""
    try:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            display_metric(
                "Number of Associates",
                len(df_current_filtered),
                len(df_current_filtered) - len(df_last_filtered)
            )
        
        with col2:
            display_metric(
                "Average Rate",
                df_current_filtered['RATES'].mean(),
                df_current_filtered['RATES'].mean() - df_last_filtered['RATES'].mean()
            )
        
        with col3:
            display_metric(
                "Average UIT",
                df_current_filtered['UIT'].mean(),
                df_current_filtered['UIT'].mean() - df_last_filtered['UIT'].mean(),
                suffix="%"
            )
            
        with col4:
            display_metric(
                "Median Rate",
                df_current_filtered['RATES'].median(),
                df_current_filtered['RATES'].median() - df_last_filtered['RATES'].median()
            )
            
    except Exception as e:
        logging.error(f"Error en métricas comparativas: {str(e)}")
        st.error("Error al mostrar métricas comparativas")

def display_metric(label, current_value, delta, suffix=""):
    """Muestra una métrica individual con formato"""
    st.metric(
        label,
        f"{round(current_value, 2)}{suffix}",
        f"{round(delta, 2)}{suffix}",
        delta_color="normal" if label == "Number of Associates" else "inverse" if "UIT" in label else "normal"
    )

@st.cache_data
def create_excel_report(df):
    """Crea un reporte en Excel con múltiples hojas"""
    try:
        # Crear el buffer de memoria
        buffer = BytesIO()
        
        # Asegurarnos de que el DataFrame no es None y no está vacío
        if df is None or df.empty:
            raise ValueError("No hay datos para exportar")

        # Crear el Excel writer especificando el engine
        with pd.ExcelWriter(
            buffer,
            engine='openpyxl',
            mode='w'
        ) as writer:
            # Hoja 1: Comparación Detallada
            comparison_sheet = df[[
                'ID',
                'Last_Rate', 'Current_Rate', 'Rate_Change',
                'Last_UIT', 'Current_UIT', 'UIT_Change',
                'Zone_Changed'  # Cambiado de 'Zone' a 'Zone_Changed'
            ]].copy()
            
            # Redondear valores numéricos
            for col in comparison_sheet.select_dtypes(include=['float64']):
                comparison_sheet[col] = comparison_sheet[col].round(2)
            
            comparison_sheet.to_excel(
                writer,
                sheet_name='Detailed Comparison',
                index=False
            )

            # Hoja 2: Resumen
            summary_data = pd.DataFrame({
                'Metric': [
                    'Total Associates',
                    'Associates with Improved Rate',
                    'Associates with Improved UIT',
                    'Overall Improvement',
                    'Average Rate Change',
                    'Average UIT Change',
                    'Associates that Changed Zone'  # Nueva métrica agregada
                ],
                'Value': [
                    len(df),
                    len(df[df['Rate_Change'] > 0]),
                    len(df[df['UIT_Change'] < 0]),
                    len(df[(df['Rate_Change'] > 0) & (df['UIT_Change'] < 0)]),
                    round(df['Rate_Change'].mean(), 2),
                    round(df['UIT_Change'].mean(), 2),
                    len(df[df['Zone_Changed']])  # Conteo de cambios de zona
                ]
            })
            
            summary_data.to_excel(
                writer,
                sheet_name='Summary',
                index=False
            )

        # Importante: mover el puntero al inicio del buffer
        buffer.seek(0)
        
        return buffer.getvalue()

    except Exception as e:
        logging.error(f"Error en la creación del reporte Excel: {str(e)}")
        st.error(f"Error al crear el archivo Excel: {str(e)}")
        return None

def export_section(comparison_df):
    """Gestiona la exportación de datos"""
    try:
        st.subheader("Export Data")
        
        if comparison_df is None or comparison_df.empty:
            st.warning("No hay datos disponibles para exportar")
            return

        col1, col2 = st.columns(2)
        
        with col1:
            # Exportar a CSV
            csv = convert_to_csv(comparison_df)
            if csv is not None:
                st.download_button(
                    label="📄 Download CSV",
                    data=csv,
                    file_name=f'performance_comparison_{datetime.now().strftime("%Y%m%d")}.csv',
                    mime='text/csv',
                    help="Descargar datos en formato CSV"
                )

        with col2:
            # Exportar a Excel
            excel_data = create_excel_report(comparison_df)
            if excel_data is not None:
                st.download_button(
                    label="📊 Download Excel Report",
                    data=excel_data,
                    file_name=f'performance_comparison_{datetime.now().strftime("%Y%m%d")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    help="Descargar reporte completo en Excel"
                )
            
    except Exception as e:
        logging.error(f"Error en exportación: {str(e)}")
        st.error("Error al preparar la exportación de datos")

@st.cache_data
def convert_to_csv(df):
    """Convierte DataFrame a CSV"""
    try:
        return df.to_csv(index=False).encode('utf-8')
    except Exception as e:
        logging.error(f"Error en conversión a CSV: {str(e)}")
        st.error("Error al convertir a CSV")
        return None
        
def display_comparison_section(comparison_df, df_current):
    """Muestra la sección de comparación detallada"""
    try:
        if comparison_df is None or comparison_df.empty:
            st.warning("No hay datos disponibles para la comparación")
            return

        st.subheader("Análisis Comparativo Detallado")

        # Dividir en tabs para mejor organización
        tab1, tab2, tab3 = st.tabs(["Análisis de Rendimiento", "Movers", "Recomendaciones"])

        with tab1:
            display_performance_analysis(comparison_df)

        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                display_top_movers(comparison_df)
            with col2:
                display_bottom_movers(comparison_df)

        with tab3:
            display_recommendations(comparison_df, df_current)

    except Exception as e:
        logging.error(f"Error en la sección de comparación: {str(e)}")
        st.error(f"Error al mostrar la comparación detallada: {str(e)}")

def display_performance_analysis(comparison_df):
    """Muestra el análisis de rendimiento"""
    try:
        if comparison_df.empty:
            st.warning("No hay datos disponibles para el análisis de rendimiento")
            return

        st.subheader("Tendencias de Rendimiento")

        # Análisis de mejoras
        improvement_data = {
            'Metric': [],
            'Value': [],
            'Percentage': []
        }

        total_associates = len(comparison_df)
        
        # Rate improvements
        rate_improved = len(comparison_df[comparison_df['Rate_Change'] > 0])
        rate_improved_pct = (rate_improved / total_associates * 100)
        improvement_data['Metric'].append('Mejora en Rate')
        improvement_data['Value'].append(rate_improved)
        improvement_data['Percentage'].append(f"{rate_improved_pct:.1f}%")

        # UIT improvements
        uit_improved = len(comparison_df[comparison_df['UIT_Change'] < 0])
        uit_improved_pct = (uit_improved / total_associates * 100)
        improvement_data['Metric'].append('Mejora en UIT')
        improvement_data['Value'].append(uit_improved)
        improvement_data['Percentage'].append(f"{uit_improved_pct:.1f}%")

        # Overall improvements
        overall_improved = len(comparison_df[
            (comparison_df['Rate_Change'] > 0) &
            (comparison_df['UIT_Change'] < 0)
        ])
        overall_improved_pct = (overall_improved / total_associates * 100)
        improvement_data['Metric'].append('Mejora General')
        improvement_data['Value'].append(overall_improved)
        improvement_data['Percentage'].append(f"{overall_improved_pct:.1f}%")

        # Mostrar tabla de mejoras
        st.write("Resumen de Mejoras:")
        improvement_df = pd.DataFrame(improvement_data)
        st.dataframe(improvement_df, use_container_width=True)

    except Exception as e:
        logging.error(f"Error en análisis de rendimiento: {str(e)}")
        st.error("Error al mostrar el análisis de rendimiento")

def display_top_movers(comparison_df):
    """Muestra los mejores movers"""
    try:
        if comparison_df.empty:
            st.warning("No hay datos disponibles para mostrar top movers")
            return

        st.subheader("Top Mejoras")

        # Mejores en Rate
        st.write("Mayor Mejora en Rate")
        top_rate = comparison_df.nlargest(5, 'Rate_Change')[
            ['ID', 'Last_Rate', 'Current_Rate', 'Rate_Change']
        ].round(2)
        st.dataframe(top_rate, use_container_width=True)

        # Mejores en UIT
        st.write("Mayor Mejora en UIT (Reducción)")
        top_uit = comparison_df.nsmallest(5, 'UIT_Change')[
            ['ID', 'Last_UIT', 'Current_UIT', 'UIT_Change']
        ].round(2)
        st.dataframe(top_uit, use_container_width=True)

    except Exception as e:
        logging.error(f"Error en top movers: {str(e)}")
        st.error("Error al mostrar los top movers")

def display_bottom_movers(comparison_df):
    """Muestra los casos que necesitan más atención"""
    try:
        if comparison_df.empty:
            st.warning("No hay datos disponibles para mostrar bottom movers")
            return

        st.subheader("Necesitan Atención")

        # Peores en Rate
        st.write("Mayor Disminución en Rate")
        bottom_rate = comparison_df.nsmallest(5, 'Rate_Change')[
            ['ID', 'Last_Rate', 'Current_Rate', 'Rate_Change']
        ].round(2)
        st.dataframe(bottom_rate, use_container_width=True)

        # Peores en UIT
        st.write("Mayor Incremento en UIT")
        bottom_uit = comparison_df.nlargest(5, 'UIT_Change')[
            ['ID', 'Last_UIT', 'Current_UIT', 'UIT_Change']
        ].round(2)
        st.dataframe(bottom_uit, use_container_width=True)

    except Exception as e:
        logging.error(f"Error en bottom movers: {str(e)}")
        st.error("Error al mostrar los bottom movers")

def display_recommendations(comparison_df, df_current):
    """Genera y muestra recomendaciones"""
    try:
        if comparison_df.empty:
            st.warning("No hay datos suficientes para generar recomendaciones")
            return

        st.subheader("Recomendaciones")

        # Análisis de casos críticos
        critical_cases = len(comparison_df[
            (comparison_df['Rate_Change'] < -10) &
            (comparison_df['UIT_Change'] > 5)
        ])

        improvement_cases = len(comparison_df[
            (comparison_df['Rate_Change'] > 0) &
            (comparison_df['UIT_Change'] < 0)
        ])

        # Generar recomendaciones
        recommendations = []

        if critical_cases > 0:
            recommendations.append(f"⚠️ {critical_cases} asociados muestran deterioro significativo (Rate -10% y UIT +5%)")

        if improvement_cases > 0:
            recommendations.append(f"✅ {improvement_cases} asociados muestran mejora general")

        # Análisis por zona
        for zone in df_current['Zone'].unique():
            zone_data = comparison_df[comparison_df['Zone'] == zone]
            if not zone_data.empty:
                avg_rate_change = zone_data['Rate_Change'].mean()
                avg_uit_change = zone_data['UIT_Change'].mean()
                
                if avg_rate_change < -5:
                    recommendations.append(f"👉 {zone}: Requiere atención en Rate (cambio promedio: {avg_rate_change:.1f})")
                if avg_uit_change > 3:
                    recommendations.append(f"👉 {zone}: Requiere atención en UIT (cambio promedio: {avg_uit_change:.1f}%)")

        # Mostrar recomendaciones
        if recommendations:
            for rec in recommendations:
                st.write(rec)
        else:
            st.write("No se encontraron problemas significativos que requieran atención inmediata.")

    except Exception as e:
        logging.error(f"Error en recomendaciones: {str(e)}")
        st.error("Error al generar recomendaciones")

def calculate_zone_transitions(df_last, df_current):
    """Analiza las transiciones entre zonas"""
    try:
        transitions = pd.crosstab(
            df_last['Zone'],
            df_current['Zone'],
            margins=True
        )
        return transitions
    except Exception as e:
        logging.error(f"Error en análisis de transiciones: {str(e)}")
        return None

def generate_individual_report(worker_id, comparison_df):
    """Genera reporte individual para un trabajador"""
    try:
        if worker_id not in comparison_df['ID'].values:
            return None
            
        worker_data = comparison_df[comparison_df['ID'] == worker_id].iloc[0]
        
        report = {
            'ID': worker_id,
            'Current_Zone': worker_data['Zone'],
            'Previous_Zone': worker_data['Last_Zone'],
            'Rate_Change': worker_data['Rate_Change'],
            'UIT_Change': worker_data['UIT_Change'],
            'Improvement_Areas': []
        }
        
        # Identificar áreas de mejora
        if worker_data['Rate_Change'] < 0:
            report['Improvement_Areas'].append('Rate')
        if worker_data['UIT_Change'] > 0:
            report['Improvement_Areas'].append('UIT')
            
        return report
    except Exception as e:
        logging.error(f"Error en reporte individual: {str(e)}")
        return None

def calculate_performance_trends(comparison_df):
    """Calcula tendencias de rendimiento"""
    try:
        trends = {
            'rate_trend': comparison_df['Rate_Change'].mean(),
            'uit_trend': comparison_df['UIT_Change'].mean(),
            'improved_overall': len(comparison_df[
                (comparison_df['Rate_Change'] > 0) &
                (comparison_df['UIT_Change'] < 0)
            ]),
            'zone_stability': (comparison_df['Zone'] == comparison_df['Last_Zone']).mean() * 100
        }
        return trends
    except Exception as e:
        logging.error(f"Error en cálculo de tendencias: {str(e)}")
        return None

@st.cache_data
def generate_summary_statistics(df):
    """Genera estadísticas resumidas del DataFrame"""
    try:
        stats = {
            'total_associates': len(df),
            'average_rate': df['RATES'].mean(),
            'median_rate': df['RATES'].median(),
            'average_uit': df['UIT'].mean(),
            'median_uit': df['UIT'].median(),
            'zone_distribution': df['Zone'].value_counts().to_dict()
        }
        return stats
    except Exception as e:
        logging.error(f"Error en estadísticas resumidas: {str(e)}")
        return None

def display_trend_analysis(comparison_df):
    """Muestra análisis de tendencias"""
    try:
        trends = calculate_performance_trends(comparison_df)
        if trends:
            st.subheader("Análisis de Tendencias")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Tendencia Rate", f"{trends['rate_trend']:.2f}")
                st.metric("Estabilidad de Zonas", f"{trends['zone_stability']:.1f}%")
            with col2:
                st.metric("Tendencia UIT", f"{trends['uit_trend']:.2f}")
                st.metric("Mejora General", trends['improved_overall'])
                
    except Exception as e:
        logging.error(f"Error en análisis de tendencias: {str(e)}")
        st.error("Error al mostrar análisis de tendencias")