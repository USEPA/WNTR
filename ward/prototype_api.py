from fastapi import FastAPI

from ward.simulation import load_preview_network

app = FastAPI(title="API prototype")


@app.get(
    "/preview"
)  # registers function below to handle GET requests to the /preview endpoint of the API
def preview():
    network = load_preview_network()  # call the function from simulation.py to load the preset network and return a dictionary with junctions and network HTML
    return {  # return a dictionary with the junctions, network HTML, and sample data for the dashboard to use
        "junctions": network["junctions"],
        "network_html": network["network_html"],
        "time_hours": [0, 1, 2, 3],
        "attack_hours": [1, 2],
        "sample_pressures": {
            "baseline": [50, 50, 50, 50],
            "attack": [50, 15, 18, 50],
        },
    }
