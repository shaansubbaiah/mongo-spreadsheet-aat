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


def diff_dashtable(data, data_previous, row_id_name=None):
    """Generate a diff of Dash DataTable data.

    Modified from: https://community.plotly.com/t/detecting-changed-cell-in-editable-datatable/26219/2

    Parameters
    ----------
    data: DataTable property (https://dash.plot.ly/datatable/reference)
        The contents of the table (list of dicts)
    data_previous: DataTable property
        The previous state of `data` (list of dicts).

    Returns
    -------
    A list of dictionaries in form of [{row_id_name:, column_name:, current_value:,
        previous_value:}]
    """
    df, df_previous = pd.DataFrame(data=data), pd.DataFrame(data_previous)

    if row_id_name is not None:
        # If using something other than the index for row id's, set it here
        for _df in [df, df_previous]:

            # Why do this?  Guess just to be sure?
            assert row_id_name in _df.columns

            _df = _df.set_index(row_id_name)
    else:
        row_id_name = "index"

    # Pandas/Numpy says NaN != NaN, so we cannot simply compare the dataframes.  Instead we can either replace the
    # NaNs with some unique value (which is fastest for very small arrays, but doesn't scale well) or we can do
    # (from https://stackoverflow.com/a/19322739/5394584):
    # Mask of elements that have changed, as a dataframe.  Each element indicates True if df!=df_prev
    df_mask = ~((df == df_previous) | (
        (df != df) & (df_previous != df_previous)))

    # ...and keep only rows that include a changed value
    df_mask = df_mask.loc[df_mask.any(axis=1)]
    print("df mask")
    print(df_mask)
    print(df.head())

    changes = []

    # This feels like a place I could speed this up if needed
    for idx, row in df_mask.iterrows():
        row_id = row.name

        # Act only on columns that had a change
        row = row[row.eq(True)]

        for change in row.iteritems():
            changes.append(
                {
                    row_id_name: row_id,
                    "_id": df.at[row.name, '_id'],
                    "column_name": change[0],
                    "current_value": df.at[row_id, change[0]],
                    "previous_value": df_previous.at[row_id, change[0]],
                }
            )

    return changes


app = dash.Dash(__name__, suppress_callback_exceptions=True)

client = MongoClient(config['MONGO_CONN_STRING'])

db = client.myFirstDatabase
recipesCollection = db.recipes

app.layout = html.Div([
    dcc.Store(id="diff-store"),

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
    html.Div(id="placeholder"),
    html.Div(id="test-box")
],
    id='container',
)

# Display Datatable with data from Mongo database *************************


@app.callback(Output('mongo-datatable', 'children'),
              [Input('interval_db', 'n_intervals')])
def populate_datatable(n_intervals):
    print(n_intervals)

    # # Fetch recipes from Mongo
    # recipesList = list(recipesCollection.find({}, {'_id': False}))
    # # Create dataframe from collection
    # recipesDF = pd.DataFrame(recipesList)

    # Fetch recipes from Mongo
    recipesList = list(recipesCollection.find({}))
    # Create dataframe from collection
    # print(recipesList[0])
    for recipe in recipesList:
        recipe['_id'] = str(recipe['_id'])
    # print(recipesList[0])
    recipesDF = pd.DataFrame(recipesList)
    recipesDF.set_index('_id')
    # print(recipesList[0])

    return [
        dash_table.DataTable(
            id='my-table',
            columns=[{"name": i, "id": i} for i in recipesDF.columns],
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


@app.callback(
    Output("diff-store", "data"),
    [Input("my-table", "data_timestamp")],
    [
        State("my-table", "data"),
        State("my-table", "data_previous"),
        State("diff-store", "data"),
    ],
)
def capture_diffs(ts, data, data_previous, diff_store_data):

    if ts is None:

        raise PreventUpdate

    diff_store_data = diff_store_data or {}

    diff_store_data[ts] = diff_dashtable(data, data_previous)

    print(diff_store_data)
    return diff_store_data


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
def add_row(data):
    df_graph = pd.DataFrame(data)
    rating_kebabs = px.box(
        df_graph[df_graph.category != 'uncategorized'],
        x="rating",
        y="category",
        orientation='h',
        # height=600,
        # width=800
    )
    return [
        html.Div([dcc.Graph(figure=rating_kebabs)])
    ]


if __name__ == '__main__':
    app.run_server(debug=True)
