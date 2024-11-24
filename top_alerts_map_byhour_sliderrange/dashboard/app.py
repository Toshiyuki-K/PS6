import seaborn as sns
from faicons import icon_svg
import pandas as pd
import os
import geopandas as gpd 
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from shared import app_dir, df
from shiny import App, ui, reactive, render

# Define absolute paths for the CSV and GeoJSON files
top_alerts_map_byhour_file_path = "C:/Users/sumos/OneDrive/ドキュメント/GitHub/PS6/top_alerts_map_byhour/top_alerts_map_byhour.csv"
geojson_path = "C:/Users/sumos/OneDrive/ドキュメント/GitHub/PS6/top_alerts_map/chicago-boundaries.geojson"

# UI for the app
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
            id = 'type_subtype',  # Unique ID for the dropdown
            label = 'Choose Type and Subtype:',  # Label for the dropdown
            choices = []  # Initial state
        ),
        ui.input_switch(
            id = 'switch_button',  # Switch button ID
            label = 'Toggle to switch to single hour',  # Label for the switch button
            value = False  # Initial state (Off)
        ),
        # Conditional panel for single hour slider
        ui.panel_conditional(
            "input.switch_button",  # when switch is off
            ui.input_slider(
                id = 'single_hour',  # Slider for a single hour
                label='Select Single Hour:',
                min = 0,
                max = 23,
                value = 12,  # Default
                step = 1
            )
        ),
        # Conditional panel for range of hour slider
        ui.panel_conditional(
            "!input.switch_button",  # when switch is ON
            ui.input_slider(
                id = 'hour_range',  # Slider for hour range
                label = 'Select Hour Range:',
                min = 0,
                max = 23,
                value = [6, 9],  # Default range 
                step = 1
            )
        ),
        title = 'Filter controls'  # Ensure title is the last argument
    ),
    ui.output_plot('alert_plot', width = '1000px', height = '550px')  # Output for the plot
)


# Server logic
def server(input, output, session):

    # Reactive calc: Load and process the CSV file
    @reactive.calc
    def app_top_alerts_map_byhour():
        # Read the CSV file
        df_byhour = pd.read_csv(top_alerts_map_byhour_file_path)

        # Convert 'hour' column from '00:00' string to integer 
        df_byhour['hour'] = df_byhour['hour'].str.split(':').str[0].astype(int)

        return df_byhour

    # Load GeoJSON data for the map
    chicago_geo_data = gpd.read_file(geojson_path)

    # Reactive effect to update the dropdown choices
    @reactive.effect
    def _():
        # Create a list of "type - subtype" combinations
        type_subtype_list = (
            app_top_alerts_map_byhour()[['updated_type', 'updated_subtype']]
            .drop_duplicates()  
            .apply(lambda row: f"{row['updated_type']} - {row['updated_subtype']}", axis = 1)
            .tolist()
        )
        # Sort the list alphabetically
        type_subtype_list.sort()

        # Update the dropdown menu with the sorted list
        ui.update_select('type_subtype', choices = type_subtype_list)

    # Define the plot output using Matplotlib
    @output
    @render.plot
    def alert_plot():
        selected_type_subtype = input.type_subtype()
        # Current switch status
        switch_status = input.switch_button()

        # Split the selection into type and subtype
        selected_type, selected_subtype = selected_type_subtype.split(" - ")

        # Filter data for single hour or range of hours with switch status
        if switch_status: # Switch status is True, meaning ON (single hour display)
            selected_hour = input.single_hour()
            filtered_data_byhour = app_top_alerts_map_byhour()[
                (app_top_alerts_map_byhour()['updated_type'] == selected_type) &
                (app_top_alerts_map_byhour()['updated_subtype'] == selected_subtype) &
                (app_top_alerts_map_byhour()['hour'] == selected_hour)
            ]
            # Directly use the filtered data for the plot
            aggregated_data = filtered_data_byhour  # No further processing required since the dataset has already top10 by hour

        else: # Switch status is False, meaning Off (range of hour display)
            selected_hour_range = input.hour_range()
            filtered_data_byhour = app_top_alerts_map_byhour()[
                (app_top_alerts_map_byhour()['updated_type'] == selected_type) &
                (app_top_alerts_map_byhour()['updated_subtype'] == selected_subtype) &
                (app_top_alerts_map_byhour()['hour'] >= selected_hour_range[0]) &
                (app_top_alerts_map_byhour()['hour'] <= selected_hour_range[1])
            ]

            # Aggregate alert counts for the selected range of hours
            aggregated_data = (
                filtered_data_byhour.groupby(['binned_coordinates', 'binned_longitude', 'binned_latitude'])
                .agg({'alert_count': 'sum'})  # Sum alert counts across the hour range
                .reset_index()
                .nlargest(10, 'alert_count')  # Select the top 10 locations
            )
       
        # Handle empty data
        if aggregated_data.empty:
            fig, ax = plt.subplots(figsize = (12, 12))
            message = f"No data available for the selected time range" if not switch_status else f"No data available for {selected_hour}:00"
            ax.text(0.5, 0.5, message, fontsize = 16, ha = 'center', va = 'center')
            ax.axis('off')
            return fig

        # Create the Matplotlib plot
        fig, ax = plt.subplots(figsize = (12, 12))
        # Set scale factor
        scale_factor = 2

        # Plot the Chicago GeoJSON map
        chicago_geo_data.plot(ax = ax, color = "lightgray", edgecolor = "white")

        # Overlay the scatter plot
        scatter = ax.scatter(
            aggregated_data["binned_longitude"],
            aggregated_data["binned_latitude"],
            s = aggregated_data["alert_count"] / scale_factor,  
            alpha = 0.7  
        )
      
        # Automatically determine legend sizes
        min_alerts = aggregated_data["alert_count"].min()  
        max_alerts = aggregated_data["alert_count"].max()  
        num_steps = 4  
        legend_sizes = [int(x) for x in np.linspace(min_alerts, max_alerts, num_steps)]

        # Add dynamic legend for alert sizes
        for size in legend_sizes:
            ax.scatter(
                [], 
                [], 
                s = size / scale_factor, 
                c = 'blue', 
                alpha = 0.7, 
                label = f"{size} Alerts")
        ax.legend(
            bbox_to_anchor = (1, 1), 
            title = "Alert Count", 
            loc = "upper left",
            fontsize = 16
            )
        
        # Determine the title based on the switch button status
        title = (
            f"Top 10 Longitude-Latitude Location for {selected_type} - {selected_subtype} at {selected_hour}:00"
            if switch_status else
            f"Top 10 Longitude-Latitude Location for {selected_type} - {selected_subtype} between {selected_hour_range[0]}:00 and {selected_hour_range[1]}:00"
            )

        # Set the title and axis labels
        ax.set_title(title, fontsize=16)
        ax.set_xlabel('Longitude', fontsize = 12)
        ax.set_ylabel('Latitude', fontsize = 12)

        # Add a grid to the plot
        ax.grid(True, linestyle = '--', alpha = 0.5)

        # Enable minor grid lines
        ax.xaxis.set_major_locator(ticker.MultipleLocator(0.05))  
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.01))  
        ax.yaxis.set_major_locator(ticker.MultipleLocator(0.05))  
        ax.yaxis.set_minor_locator(ticker.MultipleLocator(0.01)) 
        ax.grid(True, which = 'minor', linestyle = ':', linewidth = 0.5, alpha = 0.5)  

        # Rotate the label for easy view
        ax.tick_params(axis='x', labelrotation = 45)  

        return fig

# Create and run the app
app = App(app_ui, server)

