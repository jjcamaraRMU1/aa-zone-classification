import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Zone Classification", layout="centered")
st.title("Unknown Idle Time vs AA Rate")
st.markdown("Upload your CSV file to visualize and adjust the zone classification interactively.")

# Upload CSV
uploaded_file = st.file_uploader("Drag and drop or select a CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        # Drop unnecessary column if exists
        if 'xValue' in df.columns:
            df = df.drop('xValue', axis=1)

        # Rename columns for consistency
        df = df.rename(columns={
            'User_Id': 'ID',
            'Stow_Rate': 'RATES',
            'Turnaway_Percentage': 'UIT'
        })

        st.subheader("Preview of uploaded data")
        st.dataframe(df.head())

        # Calculate default median values
        median_rate = df['RATES'].median()
        median_uit = df['UIT'].median()

        st.markdown("Classification Settings")

        # User-adjustable input for thresholds
        user_rate = st.number_input("Reference Rate (RATES)", value=float(round(median_rate, 2)))
        user_uit = st.number_input("Reference Unknown Idle Time (UIT)", value=float(round(median_uit, 2)))

        # Zone classification based on thresholds
        def classify_zone(row):
            if row['RATES'] > user_rate and row['UIT'] > user_uit:
                return 'Zone 1: High Rate & High UIT'
            elif row['RATES'] > user_rate and row['UIT'] <= user_uit:
                return 'Zone 2: High Rate & Low UIT'
            elif row['RATES'] <= user_rate and row['UIT'] > user_uit:
                return 'Zone 3: Low Rate & High UIT'
            else:
                return 'Zone 4: Low Rate & Low UIT'

        df['Zone'] = df.apply(classify_zone, axis=1)

        # Plot the scatter chart
        fig = px.scatter(
            df,
            x='RATES',
            y='UIT',
            color='Zone',
            hover_name='ID',
            title='Zone Classification: Rate vs Unknown Idle Time',
            labels={'RATES': 'Rate', 'UIT': 'Unknown Idle Time (%)'},
                color_discrete_map={
                'Zone 1: High Rate & High UIT': 'red',
                'Zone 2: High Rate & Low UIT': 'green',
                'Zone 3: Low Rate & High UIT': 'orange',
                'Zone 4: Low Rate & Low UIT': 'blue'
            }
        )

        fig.update_layout(
            xaxis=dict(title='Rate', range=[df['RATES'].min() - 20, df['RATES'].max() + 20]),
            yaxis=dict(title='Unknown Idle Time (%)', range=[df['UIT'].min() - 5, df['UIT'].max() + 5])
        )

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error while processing the file: {e}")
