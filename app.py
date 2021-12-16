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
recipesList = list(recipesCollection.find({}, {'_id': False}).limit(20))

recipesDF = pd.DataFrame(recipesList)

app.layout = html.Div([
    html.H1('READ'),
    dash_table.DataTable(
        columns=[{"name": i, "id": i} for i in recipesDF.columns],
        data = recipesList,
        page_size = 10,
        fixed_columns={ 'headers': True, 'data': 1 },
        style_table={'minWidth': '100%'},
        style_cell={
            # all three widths are needed
            'minWidth': '180px', 'width': '180px', 'maxWidth': '180px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'padding': '5px'
        },
        style_data_conditional=[
            {
                'if': {
                    'column_id': 'name'
                },
                'minWidth': 'auto', 'width': 'auto', 'maxWidth': 'auto',
                'fontWeight': 'bold'
            },
        ],
        style_as_list_view=True,
        style_header={
            'backgroundColor': 'white',
            'fontWeight': 'bold'
        },
        filter_action="native",
        tooltip_data=[
            {
                column: {'value': str(value), 'type': 'markdown'}
                for column, value in row.items()
            } for row in recipesList
        ],
        css=[{
            'selector': '.dash-table-tooltip',
            'rule': 'font-family: monospace;'
        }],
    )
])

if __name__ == '__main__':
    app.run_server(debug=True)