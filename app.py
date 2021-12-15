# Run this app with `python app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

import dash
from dash import dcc
from dash import html
from dash import dash_table
from dash.dependencies import Input, Output, State
import plotly.express as px
import pandas as pd
from pymongo import MongoClient
import pprint
from dotenv import dotenv_values

config = dotenv_values(".env")

app = dash.Dash(__name__)

client = MongoClient(config['MONGO_CONN_STRING'])

db = client.myFirstDatabase
recipesCollection = db.recipes

# Create dataframe from collection
recipesList = list(recipesCollection.find({}, {'_id': False}).limit(5))

recipesDF = pd.DataFrame(recipesList)

print(recipesDF.columns)

app.layout = dash_table.DataTable(
    columns=[{"name": i, "id": i} for i in recipesDF.columns],
    data = recipesList
)

if __name__ == '__main__':
    app.run_server(debug=False)