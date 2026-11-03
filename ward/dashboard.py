import os

import httpx
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components


def pressure_figure(data):  # take in API data, return a pressure chart
    pressures = data["sample_pressures"]  # store the sample pressures in a variable
    figure = go.Figure()  # create a new figure
    figure.add_scatter(  # add a data series to the figure for the baseline pressures
        x=data[
            "time_hours"
        ],  # defines the x-axis values as the time in hours from the data
        y=pressures["baseline"],  # baseline pressures
        name="Sample baseline",
        mode="lines+markers",  # draw lines and markers for the data points
    )
    figure.add_scatter(  # same as above but for the attack pressures
        x=data["time_hours"],
        y=pressures["attack"],
        name="Sample attack",
        mode="lines+markers",
        line={"dash": "dash"},  # make attack line dashed so it's easy to distinguish
    )
    figure.add_vrect(  # highlight attack period with a vertical rectangle
        x0=data["attack_hours"][
            0
        ],  # attack_hours is a list consisting of 2 values: start and end time of the attack.
        x1=data["attack_hours"][1],
        fillcolor="gray",
        opacity=0.15,  # make slightly transparent so it doesn't obscure the data
        line_width=0,  # remove border line so it looks cleaner
    )
    figure.update_layout(  # configure layout of the chart
        xaxis_title="Time (hours)",  # axis titles
        yaxis_title="Pressure (psi)",
        height=360,  # chart height in pixels
        margin={
            "t": 30,
            "b": 80,
            "l": 10,
            "r": 10,
        },  # space around plotting area (top, bottom, left, right)
        legend={
            "orientation": "h",
            "y": -0.3,
        },  # arrange legend horizontally and move it below the chart
    )
    return figure  # return chart


def main():
    st.set_page_config(
        page_title="Dashboard Prototype", layout="wide"
    )  # set the page title and layout to wide so it uses the full width of the browser window
    st.title("Dashboard Prototype")  # dashboard title
    st.button("Reload data")
    api_url = os.environ.get(
        "WNTR_API_URL", "http://127.0.0.1:8000"
    )  # get the API URL from the environment variable WNTR_API_URL (not currently used), or use the default http://
    try:
        response = httpx.get(
            f"{api_url.rstrip('/')}/preview", timeout=5
        )  # send a GET to the /preview endpoint of the API, timeout is 5 seconds
        response.raise_for_status()  # throws an exception if the response status code is not 200
        data = response.json()  # put the response JSON into a dictionary
    except (
        httpx.HTTPError,
        ValueError,
    ):  # if there is an error, show an error message and stop the app
        st.error(
            "Cannot load sample data. Check that the prototype API is running, then reload."
        )
        st.stop()

    network_column, detail_column = st.columns(
        [3, 2]
    )  # create two columns, one for the network and one for the details. 3 = ~60% of the width, 2 = ~40% of the width
    with detail_column:
        selected_node = st.selectbox(
            "Node", data["junctions"]
        )  # create a selectbox with the junctions from the data and store the selected value in selected_node
    with network_column:
        st.subheader("Network")  # create a subheader for the network column
        components.html(
            data["network_html"], height=470, scrolling=True
        )  # embed the network HTML from the data into the network column, with a height of 470 pixels and scrolling enabled
    with detail_column:
        st.subheader(
            f"Sample pressure — node {selected_node}"
        )  # create a subheader for the detail column, showing the selected node
        st.plotly_chart(
            pressure_figure(data), use_container_width=True
        )  # call pressure_figure with the data, create a plotly chart with the returned figure
        pressures = data["sample_pressures"]  # store the sample pressures in a variable
        st.dataframe(  # create a dataframe (table) with time, baseline pressure, and attack pressure. Hide index column
            {
                "Time (hours)": data["time_hours"],
                "Baseline (psi)": pressures["baseline"],
                "Attack (psi)": pressures["attack"],
            },
            hide_index=True,
        )


if __name__ == "__main__":
    main()
