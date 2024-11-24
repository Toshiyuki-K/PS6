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



# Define the file path for the CSV 
file_path = "C:/Users/sumos/OneDrive/ドキュメント/GitHub/PS6"
csv_relative_path = "./top_alerts_map_byhour/top_alerts_map_byhour.csv"
top_alerts_map_byhour_file_path = os.path.join(file_path, csv_relative_path)

# GeoJSON files
geojson_path = "C:/Users/sumos/OneDrive/ドキュメント/GitHub/PS6/top_alerts_map/chicago-boundaries.geojson"

# UI for the app
app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_select(
        id = 'type_subtype',  # Unique ID for the dropdown
        label = 'Choose Type and Subtype:',  # Label for the dropdown
        choices = []  # Initially, the dropdown list is empty
        ),
        ui.input_slider(
            id = 'hour',  # Unique ID for the slider
            label = 'Select Hour:',  # Label for the slider
            min = 0,  # Minimum 
            max = 23,  # Maximum 
            value = 12,  # Default
            step = 1  # Step size
            ),
        title="Filter controls",
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
        selected_hour = input.hour()

        # Split the selection into type and subtype
        selected_type, selected_subtype = selected_type_subtype.split(" - ")

        # Filter the data based on the selected type, subtype, and hour
        filtered_data_byhour = app_top_alerts_map_byhour()[
            (app_top_alerts_map_byhour()['updated_type'] == selected_type)
            & (app_top_alerts_map_byhour()['updated_subtype'] == selected_subtype)
            & (app_top_alerts_map_byhour()['hour'] == int(selected_hour)) # Ensure the datatype to be int
        ]
        
        # Handle empty data
        if filtered_data_byhour.empty:
            fig, ax = plt.subplots(figsize = (12, 12))
            ax.text(0.5, 0.5, f"No data available for {selected_hour}:00", 
                    fontsize = 16, ha = 'center', va = 'center')
            ax.axis('off')
            return fig

        # Create the Matplotlib plot
        fig, ax = plt.subplots(figsize = (12, 12))
        # Set scale factor to adjust the size of the scatter points
        scale_factor = 2

        # Plot the Chicago GeoJSON map
        chicago_geo_data.plot(ax = ax, color = 'lightgray', edgecolor = 'white')

        # Overlay the scatter plot
        scatter = ax.scatter(
            filtered_data_byhour['binned_longitude'],
            filtered_data_byhour['binned_latitude'],
            s = filtered_data_byhour['alert_count'] / scale_factor, 
            alpha = 0.7  
        )

        # Automatically determine legend sizes
        min_alerts = filtered_data_byhour['alert_count'].min()  
        max_alerts = filtered_data_byhour['alert_count'].max()  
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
            bbox_to_anchor = (1, 1), # Ask chatGPT how to adjust its location
            title = 'Alert Count', 
            loc = 'upper left',
            fontsize = 16
            )

        # Set the title and axis labels
        ax.set_title(f"Top 10 Longitude-Latitude Location for {selected_type} - {selected_subtype} at {selected_hour}:00", fontsize = 16)
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

