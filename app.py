import streamlit as st
import pandas as pd
import logging
from datetime import datetime
from utils import *

# Configuración del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

def main():
    try:
        # Configuración inicial
        setup_page()
        
        # Inicializar estado de la sesión si no existe
        if 'data_processed' not in st.session_state:
            st.session_state.data_processed = False
        
        # Carga de archivos
        last_week_file, current_week_file = load_files()
        
        if last_week_file is not None and current_week_file is not None:
            try:
                # Procesamiento de datos
                df_last = validate_and_process_data(last_week_file, "last_week")
                df_current = validate_and_process_data(current_week_file, "current_week")
                
                if df_last is None or df_current is None:
                    st.error("Error en la validación de datos. Por favor, verifica los archivos.")
                    return

                # Configuración de clasificación
                with st.expander("Configuración de Rate y UIT de referencia"):
                    user_rate = st.number_input(
                        "Rate de Referencia",
                        min_value=0.0,
                        value=float(round(df_current['RATES'].median(), 2)),
                        help="Rate objetivo para evaluación de rendimiento"
                    )
                    user_uit = st.number_input(
                        "UIT de Referencia",
                        min_value=0.0,
                        max_value=100.0,
                        value=float(round(df_current['UIT'].median(), 2)),
                        help="Porcentaje objetivo de Unknown Idle Time"
                    )
                
                # Aplicar clasificación por zonas
                df_last = apply_zone_classification(df_last, user_rate, user_uit)
                df_current = apply_zone_classification(df_current, user_rate, user_uit)
                
                # Visualización principal
                display_current_week_scatter(df_current, user_rate, user_uit)
                display_zone_distribution(df_current)
                
                # Análisis por zona
                st.subheader("Análisis por Zona")
                selected_zone = st.selectbox(
                    "Seleccionar zona para analizar:",
                    ['All Zones'] + list(df_current['Zone'].unique())
                )
                
                # Filtrar por zona seleccionada
                df_last_filtered, df_current_filtered = filter_by_zone(
                    df_last, df_current, selected_zone
                )
                
                # Mostrar métricas comparativas
                display_comparative_metrics(df_last_filtered, df_current_filtered)
                
                # Crear DataFrame de comparación
                comparison_df = create_comparison_dataframe(df_last, df_current)
                
                if comparison_df is not None:
                    # Mostrar sección de comparación
                    display_comparison_section(comparison_df, df_current)
                    
                    # Análisis de tendencias
                    display_trend_analysis(comparison_df)
                    
                    # Transiciones de zona
                    st.subheader("Análisis de Transiciones de Zona")
                    zone_transitions = calculate_zone_transitions(df_last, df_current)
                    if zone_transitions is not None:
                        st.write("Matriz de Transiciones de Zona:")
                        st.dataframe(zone_transitions)
                    
                    # Reporte individual
                    st.subheader("Reporte Individual")
                    selected_worker = st.selectbox(
                        "Seleccionar trabajador:",
                        comparison_df['ID'].unique()
                    )
                    
                    if selected_worker:
                        worker_report = generate_individual_report(
                            selected_worker, comparison_df
                        )
                        if worker_report:
                            st.write(worker_report)
                    
                    # Sección de exportación
                    export_section(comparison_df)
                
                st.session_state.data_processed = True
                
            except Exception as e:
                logging.error(f"Error durante el procesamiento: {str(e)}")
                st.error(f"Ocurrió un error durante el procesamiento: {str(e)}")
                display_error_details()
                
    except Exception as e:
        logging.error(f"Error crítico en la aplicación: {str(e)}")
        st.error("Ocurrió un error crítico. Por favor, contacta al administrador.")
        display_error_details()

def display_error_details():
    """Muestra detalles del error para debugging"""
    if st.checkbox("Mostrar Detalles del Error"):
        st.write("Para soporte, contacta al equipo técnico con el siguiente error:")
        st.code(logging.getLogger().handlers[0].baseFilename)

if __name__ == "__main__":
    main()