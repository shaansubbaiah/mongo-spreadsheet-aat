import dash
from dash import dcc
from dash import html
from dash import dash_table
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.express as px
import pandas as pd
from pymongo import MongoClient
from dotenv import dotenv_values

config = dotenv_values(".env")
COLUMNS = ['_id', 'name', 'url', 'category', 'author', 'summary', 'rating',
       'rating_count', 'review_count', 'ingredients', 'directions', 'prep',
       'cook', 'total', 'servings', 'yield', 'calories']

app = dash.Dash(__name__, suppress_callback_exceptions=True)

client = MongoClient(config['MONGO_CONN_STRING'])

db = client.myFirstDatabase
recipesCollection = db.recipes

app.layout = html.Div([
    html.Div([
        html.H1('NoSQL - AAT ✨'),
        html.P('Frontend to perform CRUD operations on MongoDB.')
    ],
        id='heading'
    ),

    html.Div(id='mongo-datatable', children=[]),

    # activated once/week or when page refreshed
    dcc.Interval(id='interval_db', interval=86400000 * 7, n_intervals=0),

    html.Div(id='button-flex', children=[
        html.Button("↓ Save to Mongo Database",
                    id="save-it", className='button'),
        html.Button('+ Add Row', id='adding-rows-btn',
                    n_clicks=0, className='button'),
    ]),

    html.Div(id="show-graphs", children=[]),
    html.Div(id="placeholder")

],
    id='container',
)

# Display Datatable with data from Mongo database

@app.callback(Output('mongo-datatable', 'children'),
              [Input('interval_db', 'n_intervals')])
def populate_datatable(n_intervals):
    print(n_intervals)

    recipesList = list(recipesCollection.find({}))

    for recipe in recipesList:
        recipe['_id'] = str(recipe['_id'])

    # Create dataframe from collection
    recipesDF = pd.DataFrame(recipesList)
    recipesDF.set_index('_id')

    return [
        dash_table.DataTable(
            id='my-table',
            columns=[{"name": i, "id": i} for i in COLUMNS],
            data=recipesList,
            page_size=10,
            hidden_columns=['_id'],
            fixed_columns={'headers': True, 'data': 1},
            style_table={'minWidth': '100%'},
            style_cell={
                # all three widths are needed
                'minWidth': '180px', 'width': '180px', 'maxWidth': '180px',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'padding': '0px 5px 0px 5px'
            },
            style_data_conditional=[
                {
                    'if': {'column_id': 'name'},
                    'minWidth': 'auto', 'width': 'auto', 'maxWidth': 'auto',
                    'fontWeight': 'bold'
                },
            ],
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
            editable=True,
            row_deletable=True,
            export_format='xlsx',
            export_headers='display',
            merge_duplicate_headers=True,
        )
    ]


# Add new rows to DataTable
@app.callback(
    Output('my-table', 'data'),
    [Input('adding-rows-btn', 'n_clicks')],
    [State('my-table', 'data'),
     State('my-table', 'columns')],
)
def add_row(n_clicks, rows, columns):
    if n_clicks > 0:
        rows.append({c['id']: '' for c in columns})
    return rows


# Save new DataTable data to the Mongo database
@app.callback(
    Output("placeholder", "children"),
    Input("save-it", "n_clicks"),
    State("my-table", "data"),
    prevent_initial_call=True
)
def save_data(n_clicks, data):
    print('saving to db')
    dff = pd.DataFrame(data)
    
    recipesCollection.delete_many({})
    recipesCollection.insert_many(dff.to_dict('records'))

    return ""


# Create graphs from DataTable data
@app.callback(
    Output('show-graphs', 'children'),
    Input('my-table', 'data')
)
def display_kebabs(data):
    df_graph = pd.DataFrame(data)
    rating_kebabs = px.box(
        df_graph[df_graph.category != 'uncategorized'],
        x="rating",
        y="category",
        orientation='h'
    )
    return [
        html.Div([dcc.Graph(figure=rating_kebabs)])
    ]


if __name__ == '__main__':
    app.run_server(debug=True)
