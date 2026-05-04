import pandas as pd
from pathlib import Path
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np

from shiny import App, ui, render
from shinywidgets import render_widget, output_widget

from ipyleaflet import (
    Map,
    Marker,
    MarkerCluster,
    basemaps,
    basemap_to_tiles,
    CircleMarker,
    WidgetControl
)

from ipywidgets import HTML
import plotly.express as px



# -----------------------------
# Load Data
# -----------------------------

file_path = Path(__file__).parent
df = pd.read_csv(file_path / "refined_collisions.csv")

df.columns = df.columns.str.strip().str.lower()

df["date"] = pd.to_datetime(
    df["date"],
    dayfirst=True,   
    errors="coerce"
)
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")

df = df.dropna(subset=["latitude", "longitude"])

# Remove invalid ranges EARLY (important)
loc_df = df[
    (df["latitude"].between(-90, 90)) &
    (df["longitude"].between(-180, 180))
]

# Sampling (keep smaller for stability)
if len(loc_df) > 1000:
    loc_df = loc_df.sample(1000, random_state=42)

print("Rows after cleaning:", len(df))

color_map = {
    "Fatal": "red",
    "Serious": "orange",
    "Slight": "green"
}

road_types=df.road_type.unique().tolist()
#road_types=["All"] + list(road_types)
weather_types= df.weather_conditions.unique()
weather_types= ["All"] + list(weather_types)
road_condition = df.road_surface_conditions.unique()
road_condition= ["All"] + list(road_condition)
light_condition = df.light_conditions.unique()
light_condition= ["All"] + list(light_condition)
urban_rural = df.urban_or_rural_area.unique()
urban_rural= ["All"] + list(urban_rural)

app_ui = ui.page_navbar(

        ui.head_content(
        #styling page
        ui.tags.style("""
            body {
                background-color: #f0ffff ;
            }

            h1, h4 {
                font-weight: 600;
                color: grey;
            }
            h2 {
                font-weight: 600;
                color: black;
            }

            .subtitle-text {
            color: grey;
            font-size: 18px;
            margin-top: -10px;
            }
            
            #btn-primary{
            background-color:grey; 
            border-radius: 8px;
                      }
                      
            .navbar {
            background-color: grey !important;
            }

            .navbar .navbar-brand,
            .navbar .nav-link {
            color: white !important;
            }

            .navbar .nav-link:hover {
            color: black !important;
            }

            .card {
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                border: none;
                margin-bottom: 20px;
                background-color:whitesmoke
            }

            .card-header {
                background-color: #a9a9a9;
                color: white;
                font-weight: 500;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }

            .value-box {
                text-align: center;
                padding: 20px;
                border-radius: 12px;
                color: white;
                font-size: 28px;
                font-weight: bold;
            }

            

            .sidebar {
                background-color: wheat;
                padding: 15px;
                border-radius: 10px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }
        """)
    ),


    #the navbar
    ui.nav_panel("Introduction page",
        ui.div(
            ui.h1("2025 UK Road Collision Analysis Dashboard"),
            ui.p(
                "Interactive exploration of collision patterns, severity, and risk factors across the UK",
                class_="subtitle-text"
            ),
            ui.a(
            "Link to dataset Dataset",
            href="https://www.gov.uk/government/statistical-data-sets/road-safety-open-data",
            target="_blank",
            class_="btn btn-primary",
            id="btn-primary"
            ),
            class_="text-center mb-5"
        ),
    ui.row(
        ui.column(
        4,
        ui.card(
            ui.card_header("Total Collisions"),
            ui.h2(f"{len(df):,}", class_="text-center"),
        )
        ),
        ui.column(
        4,
        ui.card(
            ui.card_header("Total Casualties"),
            ui.h2(f"{df['number_of_casualties'].sum():,}", class_="text-center"),
            )
        ),
        ui.column(
        4,
        ui.card(
            ui.card_header("Avg Vehicles per Collision"),
            ui.h2(f"{df['number_of_vehicles'].mean():.2f}", class_="text-center"),
        )
        )
        ),
    ui.row(
    ui.column(
        12,
        ui.card(
            ui.card_header(" Sample Collision Dataset (1000 rows)"),

            ui.div(
                ui.output_data_frame("all_data"),
                style="max-height: 600px; overflow-y: auto;"
            )
        )
    )
    )
    ),

    ui.nav_panel("Collision severity",
        ui.div(
        ui.p("Zoom and click to view colision details", class_="subtitle-text"),
        class_="text-center mb-5" 
        ),

        ui.row(
        ui.column(
        12,
        ui.card(
            ui.card_header("Collision severity Map"),

            ui.div(
                output_widget("coloured_map_widget"),
                style="max-height: 600px; overflow-y: auto;"
            )
        )
        )
        )

    ),
    ui.nav_panel("Clustered Collision Map",
         ui.div(
        ui.p("Zoom and click to view colision details", class_="subtitle-text"),
        class_="text-center mb-5" 
        ),
        ui.row(
        ui.column(
        12,
        ui.card(
            ui.card_header("Clustered collision Map"),

            ui.div(
                output_widget("map_widget"),
                style="max-height: 600px; overflow-y: auto;"
            )
        )
        )
        )
    ),
     ui.nav_panel("Primary plots",
      
        ui.row(
        ui.column(6,     ui.card(
        ui.card_header("Collision Severity by Weather"),
        output_widget("severity_by_weather"))
        ),
        ui.column(
        6,       ui.card(
        ui.card_header("Collisions by Hour and Severity"), output_widget("hour_and_day"))
        ),
        ),
        ui.row(
        ui.column(6,      ui.card(
        ui.card_header("Vehicle Collision Frequency by Severity and Day"),output_widget("day_collision_plot"))),
        ui.column(6,      ui.card(
        ui.card_header("Vehicle Collision Frequency by Hour of Day"),output_widget("hour_vehicles_plot")))
        ),
        ui.row(
        ui.column(6,      ui.card(
        ui.card_header("Collision Frequency by Road Type and Severity"),output_widget("road_collision_plot"))),
        ui.column(6,      ui.card(
        ui.card_header("Collision Frequency by high risk and severity"),output_widget("high_risk_plot")))
        )

    ),
    ui.nav_panel("Advanced Filters",
                 
        ui.layout_sidebar(
            ui.sidebar(
                    ui.h4("Filters"),
                    ui.hr(),
                    ui.input_select(
                            "severity_filter",
                            "Severity for monthly chart",
                            ["All","Fatal","Serious","Slight"]
                            ),
                    ui.input_slider(
                            "hour_filter",
                            "Select time range for monthly chart:",
                            min=0,
                            max=23,
                            value=(0, 23)
                        ),
                    ui.input_date_range(
                            "daterange",
                            "Select Date Range for both charts",
                            start=df["date"].min(),
                            end=df["date"].max()
                            ),
                    ui.input_checkbox_group(
                            "day_filter",
                            "Select day(s): for both charts",
                            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday","Sunday"],
                            selected=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday","Sunday"]
                        ),
                    ui.input_checkbox_group(
                            "road_filter",
                            "select road type for both charts",
                            road_types,
                            selected=road_types
                            ),
                    ui.input_select(
                            "weather_filter",
                            "choose weather condition for both charts",
                            weather_types
                            ),
                    ui.input_select(
                            "road_condition_filter",
                            "choose road condition for both charts",
                            road_condition
                            ),
                    ui.input_select(
                            "light_filter",
                            "choose light condition for both charts",
                            light_condition
                            ),
                    ui.input_select(
                            "urban_rural_filter",
                            "Choose Area type for both charts",
                            urban_rural
                            )    
            ),     ui.card(
                    ui.card_header("Monthly Collision Diagnostics"),
                    output_widget("trend_plot")),
                    ui.card(
                    ui.card_header("Hourly Collision Severity Diagnostics"),
                    output_widget("col_hour_plot"))

        )
            
    ),
     ui.nav_panel("other plots",
        ui.row(
        ui.column(6,      ui.card(
        ui.card_header("Collision Frequency by Severity and Area Type"), output_widget("urban_casualties_plot"))),
        ui.column(6,      ui.card(
        ui.card_header("Collision Frequency by Severity and Speed Limit"),output_widget("speed_casualties_plot")))
        ),
        ui.row(
        ui.column(6,      ui.card(
        ui.card_header("All Collisions by Hour"), output_widget("hour_collision_plot"))),
        ui.column(6,      ui.card(
        ui.card_header("Weather and Light Risk interaction by collision"), output_widget("weather_light_plot")))
        ),
        ui.row(
        ui.column(6,      ui.card(
        ui.card_header("Vehicles frequency by weekend and severity"), output_widget("weekend_plot"))),
        ui.column(6,      ui.card(
        ui.card_header("Casualties frequency by wet_dark and high_risk"), output_widget("wet_dark_plot")))
        )
    ),

    title="🚗 UK Road Safety Dashboard",
    theme=ui.Theme("flatly")
)



#The backend logic


#styling plots
def style_fig(fig):
    fig.update_layout(
        template="plotly_white",
        font=dict(size=12),
        margin=dict(l=40, r=20, t=50, b=40),
        title=dict(x=0.5),
        legend_title_text=""
    )
    return fig

#creating cluster map
def create_cluster_map():

    # Auto-center using smaller dataset (prevents “empty map” feeling) 
    center = (loc_df["latitude"].mean(), loc_df["longitude"].mean())

    #create map
    m = Map(
        center=center,
        zoom=6,
        basemap=basemap_to_tiles(basemaps.CartoDB.Positron),
        scroll_wheel_zoom=True
    )

    cluster = MarkerCluster()
    m.add_layer(cluster)

    marker_count = 0
    #loop through rows 
    for _, row in loc_df.iterrows():
        try:
            lat = row["latitude"]
            lon = row["longitude"]

            #if coordinates are not valid, skip row
            if pd.isna(lat) or pd.isna(lon):
                continue
            #create pop up
            popup_text = f"""
            <b>Police Force:</b> {row.get('police_force','N/A')}<br>
            <b>Severity:</b> {row.get('collision_severity','N/A')}<br>
            <b>Vehicles:</b> {row.get('number_of_vehicles','N/A')}<br>
            <b>Casualties:</b> {row.get('number_of_casualties','N/A')}<br>
            <b>Weather:</b> {row.get('weather_conditions','N/A')}<br>
            <b>Road Type:</b> {row.get('road_type','N/A')}
            """
            #creat marker attach pop up to marker
            marker = Marker(location=(lat, lon))
            marker.popup = HTML(value=popup_text)

            # add marker ,safer than passing full list at once
            cluster.markers = cluster.markers + (marker,)
            #count markers
            marker_count += 1

        except Exception as e:
            print("Error:", e)
    #print number of markers created
    print("Markers created:", marker_count)

    # Force frontend refresh (important for Shiny)
    m.zoom = m.zoom

    return m
#creating coloured map (severity map)
def create_coloured_map():
    #insert center 
    center = (loc_df["latitude"].mean(), loc_df["longitude"].mean())
    m = Map(
        center=center,   # UK center
        zoom=6,
        basemap=basemap_to_tiles(
            basemaps.OpenStreetMap.Mapnik
        ),
        scroll_wheel_zoom=True
    )
    #crate legend for map
    legend_html = HTML(value="""
    <div style="
    padding:10px;
    background:white;
    border-radius:8px;
    box-shadow:0px 2px 6px rgba(0,0,0,0.2);
    width:180px;
    font-size:12px;
    ">
    <b>Severity</b><br>
    <span style='color:red;'>●</span> Fatal<br>
    <span style='color:orange;'>●</span> Serious<br>
    <span style='color:green;'>●</span> Slight
    </div>
    """)

    #add and position legend
    legend = WidgetControl(widget=legend_html, position="bottomright")

    m.add_control(legend)
    
    #loop through rows
    for _, row in loc_df.iterrows():
        #creat pop up
        popup_text = f"""
        
        <b>Police Force:</b> {row['police_force']}<br>
        <b>Severity:</b> {row['collision_severity']}<br>
        <b>Vehicles:</b> {row['number_of_vehicles']}<br>
        <b>Casualties:</b> {row['number_of_casualties']}<br>
        <b>Weather:</b> {row['weather_conditions']}<br>
        <b>Road Type:</b> {row['road_type']}
        """

        popup = HTML(value=popup_text)
        #get marker colour 
        marker_color = color_map.get(
            row["collision_severity"],
            "blue"
        )
        #create circle marker
        marker = CircleMarker(
            location=(row["latitude"], row["longitude"]),
            radius=6,
            color=marker_color,
            fill_color=marker_color,
            fill_opacity=0.7
        )
        #add popup
        marker.popup = popup

        # ADD marker inside loop
        m.add_layer(marker)

    return m

#creating bar chart for collision frequency by weather condition and severity
def severity_Weather():   
    severity_weather = (
        df.groupby(
        ["weather_conditions","collision_severity"]
        )
        .size()
        .reset_index(name="count")
    )

    fig = px.bar(
        severity_weather,
        x="weather_conditions",
        y="count",
        color="collision_severity",
        barmode="stack",
        #title="Collision Severity by Weather"
    )

    return style_fig(fig)

#creating heatmap for collision frequency by hour and day
def hour_day():

    pivot = pd.crosstab(
        df["hour"],
        df["day_of_week"]
    )

    fig = px.imshow(
        pivot,
        color_continuous_scale="YlOrRd",
        aspect="auto",
        #title="Collisions by Hour and Day"
    )

    fig.update_layout(
        xaxis_title="Day of Week",
        yaxis_title="Hour"
    )

    return style_fig(fig)

#creating line chart for monthly collisions, with multiple filters
def time_collision(input):

        filtered = df[
            (df["date"] >= pd.to_datetime(input.daterange()[0])) &
            (df["date"] <= pd.to_datetime(input.daterange()[1]))
        ]

        if input.severity_filter() != "All":
            filtered = filtered[
            filtered["collision_severity"]== input.severity_filter()
            ]

        filtered = filtered[
            filtered["day_of_week"].isin(input.day_filter())
        ]

        min_val= input.hour_filter()[0]
        max_val= input.hour_filter()[1]

        filtered = filtered[(filtered['hour']>=min_val) &  (filtered['hour']<=max_val)]

        filtered = filtered[filtered["road_type"].isin(input.road_filter())]

        if input.weather_filter()!="All":
            filtered=filtered[filtered["weather_conditions"]==input.weather_filter()]
        
        if input.road_condition_filter()!="All":
            filtered=filtered[filtered["road_surface_conditions"]==input.road_condition_filter()]

        if input.urban_rural_filter()!="All":
            filtered=filtered[filtered["urban_or_rural_area"]==input.urban_rural_filter()]

        if input.light_filter()!="All":
            filtered=filtered[filtered["light_conditions"]==input.light_filter()]
        

        monthly = (
            filtered
            .groupby(
                filtered["date"].dt.to_period("M")
            )
            .size()
            .reset_index(name="collisions")
        )

        monthly["date"] = monthly["date"].astype(str)

        fig = px.line(
            monthly,
            x="date",
            y="collisions",
            markers=True
        )

        return style_fig(fig)

#creating bar chart for  collision frequency by speed limit and severity
def speed_casualties():
    dt=df.groupby(["speed_limit","collision_severity"])["collision_severity"].count().reset_index(name='collisions')
    dt = dt.loc[dt["speed_limit"]>=20, :]
    fig = px.bar(
    dt,
    x="speed_limit",
    y="collisions",
    color="collision_severity",
    barmode="stack",
    )

    fig.update_xaxes(type="linear", range=[20, None])

    return style_fig(fig)

#creating bar chart for  collision frequency by area type and severity
def urban_casualties():

    tab = df.groupby(["urban_or_rural_area","collision_severity"])["collision_severity"].count().reset_index(name='collisions')

    fig = px.histogram(
        tab,
        x="urban_or_rural_area",
        y="collisions",  # all severity columns
        color='collision_severity'
    
    )

    return style_fig(fig)

#creating scatter plot for collision frequency by weather and light conditions
def weather_light():
    agg = (
    df.groupby(
    ['weather_conditions',
    'light_conditions']
    )
    .size()
    .reset_index(name='collisions')
    )

    #fig, ax = plt.subplots(figsize=(10, 6))

    fig = px.scatter(
    agg,
    x='weather_conditions',
    y='light_conditions',
    size='collisions',
    color='collisions',  # adds meaning
    #title='Weather and Light Risk Interaction'
    )

    return style_fig(fig)

#creating plot for vehicles frequency by day and severity
def day_collision():
    dt=df.groupby(["day_of_week","collision_severity"])["number_of_vehicles"].sum().reset_index(name='number_of_vehicles')

    fig= px.histogram(
        dt,
        x='day_of_week',
        y='number_of_vehicles',
        color='collision_severity'
    )
    return style_fig(fig)

#creating line chart for vehicles frequency by hour and severity
def hour_vehicles():
    dt=df.groupby(["hour","collision_severity"])["number_of_vehicles"].sum().reset_index(name='vehicles')

    fig= px.line(
        dt,
        x='hour',
        y='vehicles',
        color='collision_severity'
    )
    return style_fig(fig)

#creating plot for collision frequency by road type and severity
def road_collision():
    dt=df.groupby(["road_type","collision_severity"])["collision_severity"].count().reset_index(name='collisions')

    fig= px.bar(
        dt,
        x='road_type',
        y='collisions',
        color='collision_severity'
    )
    return style_fig(fig)

#creating line plot for hourly collisions by severity, with multiple filters 
def col_hour(input):

        filtered=df
        filtered = filtered[filtered["road_type"].isin(input.road_filter())]

        if input.weather_filter()!="All":
            filtered=filtered[filtered["weather_conditions"]==input.weather_filter()]
        
        if input.road_condition_filter()!="All":
            filtered=filtered[filtered["road_surface_conditions"]==input.road_condition_filter()]

        if input.urban_rural_filter()!="All":
            filtered=filtered[filtered["urban_or_rural_area"]==input.urban_rural_filter()]

        if input.light_filter()!="All":
            filtered=filtered[filtered["light_conditions"]==input.light_filter()]
        
        filtered = filtered[
            filtered["day_of_week"].isin(input.day_filter())
        ]

        filtered = df[
            (df["date"] >= pd.to_datetime(input.daterange()[0])) &
            (df["date"] <= pd.to_datetime(input.daterange()[1]))
        ]

        hour_severity = (
        filtered.groupby(["hour","collision_severity"])
        .size()
        .reset_index(name="count")
        )

        fig = px.line(
        hour_severity,
        x="hour",
        y="count",
        color="collision_severity",
        markers=True,
        #title="Severity Trend by Hour"
        )

        return style_fig(fig)

#creating plot for combined hourly collisions
def hour_collision():
    hourly = (
    df.groupby("hour")
      .size()
      .reset_index(name="collisions")
    )

    fig= px.line(
        hourly,
        x='hour',
        y='collisions',
    )
    return style_fig(fig)

#creating bar plot for collision frequency by high risk and severity
def high_risk():
    dt=df.groupby(["high_risk","collision_severity"])["collision_severity"].count().reset_index(name='collisions')
    fig= px.bar(
        dt,
        x='high_risk',
        y='collisions',
        color='collision_severity'
    )
    return style_fig(fig)

#creating bar plot for casualties frequency by high risk and wet_dark
def wet_dark():
    dt=df.groupby(["wet_dark","high_risk"])["number_of_casualties"].sum().reset_index(name='number_of_casualties')
    fig= px.bar(
        dt,
        x='wet_dark',
        y='number_of_casualties',
        color='high_risk'
    )
    return style_fig(fig)

#creating bar plot for vehicles frequency by weekend and severity
def weekend():
    dt=df.groupby(["weekend","collision_severity"])["number_of_vehicles"].sum().reset_index(name='number_of_vehicles')
    fig= px.bar(
        dt,
        x='weekend',
        y='number_of_vehicles',
        color='collision_severity'
    )
    return style_fig(fig)


#Rendering all plots 

def server(input, output, session):

    @output
    @render_widget
    def map_widget():
        return create_cluster_map()
    
    @output
    @render_widget
    def coloured_map_widget():
        return create_coloured_map()
    
    @output
    @render_widget
    def severity_by_weather():
        return severity_Weather()
    
    @output
    @render_widget
    def hour_and_day():
        return hour_day()
    
    @output
    @render_widget
    def urban_casualties_plot():
        return urban_casualties()
    
    @output
    @render_widget
    def speed_casualties_plot():
        return speed_casualties()
    
    @output
    @render_widget
    def weather_light_plot():
        return weather_light()
    
    @output
    @render_widget
    def day_collision_plot():
        return day_collision()
    
    @output
    @render_widget
    def hour_vehicles_plot():
        return hour_vehicles()
    @output
    @render_widget
    def road_collision_plot():
        return road_collision()

    @output
    @render_widget
    def hour_collision_plot():
        return hour_collision()

    @output
    @render_widget
    def trend_plot():
        return time_collision(input)

    @output
    @render_widget
    def col_hour_plot():
        return col_hour(input)

    @output
    @render.data_frame
    def all_data():
        return render.DataGrid(loc_df)
    
    @output
    @render_widget
    def high_risk_plot():
        return high_risk()
    
    @output
    @render_widget
    def wet_dark_plot():
        return wet_dark()
    
    @output
    @render_widget
    def weekend_plot():
        return weekend()

app = App(app_ui, server)
