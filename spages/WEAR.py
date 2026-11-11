import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Function to load data from Excel file
def load_excel_data(file_path):
    # Load all sheets from the Excel file
    xl_file = pd.ExcelFile(file_path)
    data = {}
    for sheet_name in xl_file.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        # Clean up column names (remove extra spaces, etc.)
        df.columns = df.columns.str.strip()
        data[sheet_name] = df
    return data

def app():
    # Load Excel files
    sb_lifter_path = 'wear/DE_SHELL_SB_LIFTER.xlsx'
    sb_plate_path = 'wear/DE_SHELL_SB_PLATE.xlsx'
    cb_lifter_path = 'wear/DE_SHELL_CB_LIFTER.xlsx'
    cb_plate_path = 'wear/DE_SHELL_CB_PLATE.xlsx'
    feo_lifter_path = 'wear/FE_OUTER_LIFTER.xlsx'
    feo_plate_path = 'wear/FE_OUTER_PLATE.xlsx'
    grate_lifter_path = 'wear/DE_Grate_LIFTER.xlsx'
    grate_plate_path = 'wear/DE_Grate_PLATE.xlsx'

    # Load data for each file
    sb_lifter_data = load_excel_data(sb_lifter_path)
    sb_plate_data = load_excel_data(sb_plate_path)
    cb_lifter_data = load_excel_data(cb_lifter_path)
    cb_plate_data = load_excel_data(cb_plate_path)
    feo_lifter_data = load_excel_data(feo_lifter_path)
    feo_plate_data = load_excel_data(feo_plate_path)
    grate_lifter_data = load_excel_data(grate_lifter_path)
    grate_plate_data = load_excel_data(grate_plate_path)


    # Streamlit app
    st.subheader("Liner Wear Tracking and Forecast", divider = 'rainbow')

    # Create tabs for each Excel file
    st.subheader("1. Feed End Liners")
    tabsFE = st.tabs(["FE_Outer_LIFTER", "FE_Outer_PLATE"])

    with tabsFE[0]:
        #st.markdown("Missing scan data, testing only!!")
        fig_FE_outer_lifter = go.Figure()

        for sheet_name, df in feo_lifter_data.items():
            if 'MT Processed - MT' in df.columns and 'Thickness - mm' in df.columns:
                fig_FE_outer_lifter.add_trace(go.Scatter(
                    x=df['MT Processed - MT'],
                    y=df['Thickness - mm'],
                    mode='lines+markers',
                    name=sheet_name,
                    hovertemplate='<b>%{text}</b><br>MT Processed: %{x} MT<br>Thickness: %{y} mm<extra></extra>',
                    text=[sheet_name]*len(df)
                ))
        
        fig_FE_outer_lifter.update_layout(
            title="FE_Outer_LIFTER - Thickness vs MT Processed",
            xaxis_title="MT Processed - MT",
            yaxis_title="Thickness - mm",
            hovermode='closest',
            template="simple_white"
        )

        # Update axes for grid lines and ticks
        fig_FE_outer_lifter.update_yaxes(range=[0, 510])
        fig_FE_outer_lifter.update_xaxes(range=[0, 6.0])

        # Optional: Modify grid lines (different from tick lines)
        fig_FE_outer_lifter.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_FE_outer_lifter.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

        # Update axes for grid lines and ticks
        fig_FE_outer_lifter.update_layout(yaxis=dict(tickmode='linear', tick0=0.0, dtick=50))
        fig_FE_outer_lifter.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=0.2))

        fig_FE_outer_lifter.update_layout(height=640)

        st.plotly_chart(fig_FE_outer_lifter, use_container_width=True, key="fe_outer_lifter_chart")

    with tabsFE[1]:
        #st.markdown("Missing scan data, testing only!!")
        fig_FE_outer_plate = go.Figure()

        for sheet_name, df in feo_plate_data.items():
            if 'MT Processed - MT' in df.columns and 'Thickness - mm' in df.columns:
                fig_FE_outer_plate.add_trace(go.Scatter(
                    x=df['MT Processed - MT'],
                    y=df['Thickness - mm'],
                    mode='lines+markers',
                    name=sheet_name,
                    hovertemplate='<b>%{text}</b><br>MT Processed: %{x} MT<br>Thickness: %{y} mm<extra></extra>',
                    text=[sheet_name]*len(df)
                ))
        
        fig_FE_outer_plate.update_layout(
            title="FE_Outer_PLATE - Thickness vs MT Processed",
            xaxis_title="MT Processed - MT",
            yaxis_title="Thickness - mm",
            hovermode='closest',
            template="simple_white"
        )

        # Update axes for grid lines and ticks
        fig_FE_outer_plate.update_yaxes(range=[0, 100])
        fig_FE_outer_plate.update_xaxes(range=[0, 6.0])

        # Optional: Modify grid lines (different from tick lines)
        fig_FE_outer_plate.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_FE_outer_plate.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

        # Update axes for grid lines and ticks
        fig_FE_outer_plate.update_layout(yaxis=dict(tickmode='linear', tick0=0.0, dtick=50))
        fig_FE_outer_plate.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=0.2))

        fig_FE_outer_plate.update_layout(height=640)

        st.plotly_chart(fig_FE_outer_plate, use_container_width=True, key="fe_outer_plate_chart")

##########################################################################################################
    # Create tabs for each Excel file
    st.subheader("2. Shell Liner")
    tabs = st.tabs(["SHELL_DE_SB_LIFTER", "SHELL_DE_SB_PLATE", "SHELL_DE_CB_LIFTER", "SHELL_DE_CB_PLATE"])

    with tabs[0]:
        fig_sb_lifter = go.Figure()
        
        for sheet_name, df in sb_lifter_data.items():
            if 'MT Processed - MT' in df.columns and 'Thickness - mm' in df.columns:
                fig_sb_lifter.add_trace(go.Scatter(
                    x=df['MT Processed - MT'],
                    y=df['Thickness - mm'],
                    mode='lines+markers',
                    name=sheet_name,
                    hovertemplate='<b>%{text}</b><br>MT Processed: %{x} MT<br>Thickness: %{y} mm<extra></extra>',
                    text=[sheet_name]*len(df)
                ))
        
        fig_sb_lifter.update_layout(
            title="SHELL_DE_SB_LIFTER - Thickness vs MT Processed",
            xaxis_title="MT Processed - MT",
            yaxis_title="Thickness - mm",
            hovermode='closest',
            template="simple_white"
        )

        # Update axes for grid lines and ticks
        fig_sb_lifter.update_yaxes(range=[0, 450])
        fig_sb_lifter.update_xaxes(range=[0, 6.0])

        # Optional: Modify grid lines (different from tick lines)
        fig_sb_lifter.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_sb_lifter.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

        # Update axes for grid lines and ticks
        fig_sb_lifter.update_layout(yaxis=dict(tickmode='linear', tick0=0.0, dtick=50))
        fig_sb_lifter.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=0.2))

        fig_sb_lifter.update_layout(height=640)

        st.plotly_chart(fig_sb_lifter, use_container_width=True, key="sb_lifter_chart")

    with tabs[1]:
        fig_sb_plate = go.Figure()
        
        for sheet_name, df in sb_plate_data.items():
            if 'MT Processed - MT' in df.columns and 'Thickness - mm' in df.columns:
                fig_sb_plate.add_trace(go.Scatter(
                    x=df['MT Processed - MT'],
                    y=df['Thickness - mm'],
                    mode='lines+markers',
                    name=sheet_name,
                    hovertemplate='<b>%{text}</b><br>MT Processed: %{x} MT<br>Thickness: %{y} mm<extra></extra>',
                    text=[sheet_name]*len(df)
                ))
        
        fig_sb_plate.update_layout(
            title="SHELL_DE_SB_PLATE - Thickness vs MT Processed",
            xaxis_title="MT Processed - MT",
            yaxis_title="Thickness - mm",
            hovermode='closest',
            template="simple_white",
        )

        # Update axes for grid lines and ticks
        fig_sb_plate.update_yaxes(range=[0, 120])
        fig_sb_plate.update_xaxes(range=[0, 6.0])

        # Optional: Modify grid lines (different from tick lines)
        fig_sb_plate.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_sb_plate.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

        # Update axes for grid lines and ticks
        fig_sb_plate.update_layout(yaxis=dict(tickmode='linear', tick0=0.0, dtick=20))
        fig_sb_plate.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=0.2))

        fig_sb_plate.update_layout(height=640)
        
        st.plotly_chart(fig_sb_plate, use_container_width=True, key="sb_plate_chart")

    with tabs[2]:
        fig_cb_lifter = go.Figure()
        
        for sheet_name, df in cb_lifter_data.items():
            if 'MT Processed - MT' in df.columns and 'Thickness - mm' in df.columns:
                fig_cb_lifter.add_trace(go.Scatter(
                    x=df['MT Processed - MT'],
                    y=df['Thickness - mm'],
                    mode='lines+markers',
                    name=sheet_name,
                    hovertemplate='<b>%{text}</b><br>MT Processed: %{x} MT<br>Thickness: %{y} mm<extra></extra>',
                    text=[sheet_name]*len(df)
                ))
        
        fig_cb_lifter.update_layout(
            title="SHELL_DE_CB_LIFTER - Thickness vs MT Processed",
            xaxis_title="MT Processed - MT",
            yaxis_title="Thickness - mm",
            hovermode='closest',
            template="simple_white"
        )
        
        # Update axes for grid lines and ticks
        fig_cb_lifter.update_yaxes(range=[0, 450])
        fig_cb_lifter.update_xaxes(range=[0, 6.0])

        # Optional: Modify grid lines (different from tick lines)
        fig_cb_lifter.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_cb_lifter.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

        # Update axes for grid lines and ticks
        fig_cb_lifter.update_layout(yaxis=dict(tickmode='linear', tick0=0.0, dtick=50))
        fig_cb_lifter.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=0.2))

        fig_cb_lifter.update_layout(height=640)

        st.plotly_chart(fig_cb_lifter, use_container_width=True, key="cb_lifter_chart")

    with tabs[3]:
        fig_cb_plate = go.Figure()
        
        for sheet_name, df in cb_plate_data.items():
            if 'MT Processed - MT' in df.columns and 'Thickness - mm' in df.columns:
                fig_cb_plate.add_trace(go.Scatter(
                    x=df['MT Processed - MT'],
                    y=df['Thickness - mm'],
                    mode='lines+markers',
                    name=sheet_name,
                    hovertemplate='<b>%{text}</b><br>MT Processed: %{x} MT<br>Thickness: %{y} mm<extra></extra>',
                    text=[sheet_name]*len(df)
                ))
        
        fig_cb_plate.update_layout(
            title="SHELL_DE_CB_PLATE - Thickness vs MT Processed",
            xaxis_title="MT Processed - MT",
            yaxis_title="Thickness - mm",
            hovermode='closest',
            template="simple_white",
        )

        # Update axes for grid lines and ticks
        fig_cb_plate.update_yaxes(range=[0, 120])
        fig_cb_plate.update_xaxes(range=[0, 6.0])

        # Optional: Modify grid lines (different from tick lines)
        fig_cb_plate.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_cb_plate.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

        # Update axes for grid lines and ticks
        fig_cb_plate.update_layout(yaxis=dict(tickmode='linear', tick0=0.0, dtick=20))
        fig_cb_plate.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=0.2))

        fig_cb_plate.update_layout(height=640)
        
        st.plotly_chart(fig_cb_plate, use_container_width=True, key="cb_plate_chart")
    
##########################################################################################################
    # Create tabs for each Excel file
    st.subheader("3. Discharge End Liners")
    # Add content for Discharge End Liners here when available
    tabsDE = st.tabs(["FE_Grate_LIFTER", "FE_Grate_PLATE"])

    with tabsDE[0]:
        #st.markdown("Missing scan data, testing only!!")
        fig_DE_grate_lifter = go.Figure()

        for sheet_name, df in grate_lifter_data.items():
            if 'MT Processed - MT' in df.columns and 'Thickness - mm' in df.columns:
                fig_DE_grate_lifter.add_trace(go.Scatter(
                    x=df['MT Processed - MT'],
                    y=df['Thickness - mm'],
                    mode='lines+markers',
                    name=sheet_name,
                    hovertemplate='<b>%{text}</b><br>MT Processed: %{x} MT<br>Thickness: %{y} mm<extra></extra>',
                    text=[sheet_name]*len(df)
                ))
        
        fig_DE_grate_lifter.update_layout(
            title="DE_GRATE_LIFTER - Thickness vs MT Processed",
            xaxis_title="MT Processed - MT",
            yaxis_title="Thickness - mm",
            hovermode='closest',
            template="simple_white"
        )

        # Update axes for grid lines and ticks
        fig_DE_grate_lifter.update_yaxes(range=[0, 350])
        fig_DE_grate_lifter.update_xaxes(range=[0, 6.0])

        # Optional: Modify grid lines (different from tick lines)
        fig_DE_grate_lifter.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_DE_grate_lifter.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

        # Update axes for grid lines and ticks
        fig_DE_grate_lifter.update_layout(yaxis=dict(tickmode='linear', tick0=0.0, dtick=50))
        fig_DE_grate_lifter.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=0.2))

        fig_DE_grate_lifter.update_layout(height=640)

        st.plotly_chart(fig_DE_grate_lifter, use_container_width=True, key="de_grate_lifter_chart")

    with tabsDE[1]:
        #st.markdown("DE Grate Plate data will be displayed here when available")
        # Add similar structure for FE_Outer_PLATE when data is available
        fig_DE_grate_plate = go.Figure()

        for sheet_name, df in grate_plate_data.items():
            if 'MT Processed - MT' in df.columns and 'Thickness - mm' in df.columns:
                fig_DE_grate_plate.add_trace(go.Scatter(
                    x=df['MT Processed - MT'],
                    y=df['Thickness - mm'],
                    mode='lines+markers',
                    name=sheet_name,
                    hovertemplate='<b>%{text}</b><br>MT Processed: %{x} MT<br>Thickness: %{y} mm<extra></extra>',
                    text=[sheet_name]*len(df)
                ))
        
        fig_DE_grate_plate.update_layout(
            title="DE_GRATE_PLATE - Thickness vs MT Processed",
            xaxis_title="MT Processed - MT",
            yaxis_title="Thickness - mm",
            hovermode='closest',
            template="simple_white"
        )

        # Update axes for grid lines and ticks
        fig_DE_grate_plate.update_yaxes(range=[0, 150])
        fig_DE_grate_plate.update_xaxes(range=[0, 6.0])

        # Optional: Modify grid lines (different from tick lines)
        fig_DE_grate_plate.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig_DE_grate_plate.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

        # Update axes for grid lines and ticks
        fig_DE_grate_plate.update_layout(yaxis=dict(tickmode='linear', tick0=0.0, dtick=50))
        fig_DE_grate_plate.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=0.2))

        fig_DE_grate_plate.update_layout(height=640)

        st.plotly_chart(fig_DE_grate_plate, use_container_width=True, key="de_grate_plate_chart")