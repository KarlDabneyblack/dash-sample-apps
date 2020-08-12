import numpy as np
import dash
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import plotly.graph_objects as go
import plotly.express as px
from dash_canvas.utils import array_to_data_url
from nilearn import image
from skimage import draw, segmentation, filters, exposure, color
from skimage import img_as_ubyte
import datashader.transfer_functions as tf
import datashader as ds
import pandas as pd
from scipy import ndimage

img = image.load_img("assets/radiopaedia_org_covid-19-pneumonia-7_85703_0-dcm.nii")
mat = img.affine
img = img.get_data()
img_1 = np.copy(np.moveaxis(img, -1, 0))[:, ::-1]
img_2 = np.copy(np.moveaxis(img, -1, 1))

l_h = img.shape[-1]
l_lat = img.shape[0]
print("L_h", l_h)
print("L_lat", l_lat)
print(img_1.shape)

size_factor = abs(mat[2, 2] / mat[0, 0])
print(size_factor)

slices_1 = [array_to_data_url(img_1[i]) for i in range(img_1.shape[0])]
slices_2 = [
    array_to_data_url(img_2[i]) for i in range(img_2.shape[0])[::-1]
]  # vertical



# -------- Datashader stuff for 2d histogram ----------------------------------
intensities = img_1.ravel()
#edges = ndimage.gaussian_gradient_magnitude(img_1, 3).ravel()
edges = np.abs(filters.difference_of_gaussians(img_1, [0.1, 3, 3]).ravel())
cvs = ds.Canvas(plot_width=256, plot_height=100, x_range=(0, 255), y_range=(0, 0.2))
delta_edges = 0.2 / 100
agg = cvs.points(pd.DataFrame({'x':intensities, 'y':edges}), 'x', 'y')
zero_mask = agg.values == 0
agg.values = np.log10(agg.values, where=np.logical_not(zero_mask))
agg.values[zero_mask] = np.nan
hi = exposure.histogram(img_1)

def path_to_indices(path):
    """From SVG path to numpy array of coordinates, each row being a (row, col) point
    """
    indices_str = [
        el.replace("M", "").replace("Z", "").split(",") for el in path.split("L")
    ]
    return np.array(indices_str, dtype=float)


def make_figure(filename_uri, width, height, row=None, col=None, size_factor=1,
                dragmode="drawclosedpath"):
    fig = go.Figure()
    # Add trace
    fig.add_trace(go.Scatter(x=[], y=[]))
    # Add images
    fig.add_layout_image(
        dict(
            source=filename_uri,
            xref="x",
            yref="y",
            x=0,
            y=0,
            sizex=width,
            sizey=height * size_factor,
            sizing="stretch",
            layer="below",
            opacity=1,
        )
    )
    fig.update_layout(template=None, margin=dict(t=10, b=0, l=0, r=0))
    fig.update_xaxes(
        showgrid=False, range=(0, width), showticklabels=False, zeroline=False
    )
    fig.update_yaxes(
        showgrid=False,
        scaleanchor="x",
        range=(height, 0),
        showticklabels=False,
        zeroline=False,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    if row is None:
        row = height // 2
    if col is None:
        col = width // 2
    fig.add_shape(
        type="line",
        x0=0,
        x1=width // 20 ,
        y0=row,
        y1=row,
        line=dict(width=3, color="red"),
        fillcolor="pink",
    )
    fig.add_shape(
        type="line",
        x0=width - width // 20,
        x1=width ,
        y0=row,
        y1=row,
        line=dict(width=3, color="red"),
        fillcolor="pink",
    )

    fig.update_layout(dragmode=dragmode, newshape_line_color="cyan", height=400)
    return fig


def mask_to_color(img):
    mask = np.zeros(img.shape + (4,), dtype=np.uint8)
    mask[img] = [255, 0, 0, 128]
    return mask


app = dash.Dash(__name__)

server = app.server

app.layout = html.Div(
    [
        html.Div(
            id="banner",
            children=[
                html.H2(
                    "Exploration and annotation of CT images",
                    id="title",
                    className="seven columns",
                ),
                html.Img(id="logo", src=app.get_asset_url("dash-logo-new.png"),),
            ],
            className="twelve columns app-background",
        ),
        html.Div(
            [
                dcc.Graph(
                    id="graph",
                    figure=make_figure(
                        slices_1[len(img_1) // 2], width=630, height=630
                    ),
                    config={
                        "modeBarButtonsToAdd": [
                            "drawline",
                            "drawclosedpath",
                            "drawrect",
                            "eraseshape",
                        ]
                    },
                ),
                dcc.Slider(
                    id="slider",
                    min=0,
                    max=len(img_1) - 1,
                    step=1,
                    value=len(img_1) // 2,
                    updatemode="drag",
                ),
                html.H6(id="slider-display"),
            ],
            className="app-background",
        ),
        html.Div(
            [
                dcc.Graph(
                    id="graph-2",
                    figure=make_figure(
                        slices_2[len(img_2) // 2], width=630, height=45 * size_factor,
                        dragmode='drawrect'
                    ),
                ),
                dcc.Slider(
                    id="slider-2",
                    min=0,
                    max=len(img_2) - 1,
                    step=1,
                    value=len(img_2) // 2,
                    updatemode="drag",
                ),
                html.H6(id="slider-2-display"),
            ],
            className="app-background",
        ),
         html.Div(
            [
                dcc.Graph(
                    id="graph-histogram",
                    # figure=px.imshow(agg, origin='lower '),
                    figure=px.bar(x=hi[1], y=hi[0]),
                    config={
                        "modeBarButtonsToAdd": [
                            "drawline",
                            "drawclosedpath",
                            "drawrect",
                            "eraseshape",
                        ]
                    },
                ),
            ],
            className="app-background",
        ),
         html.Div(
            [
                dcc.Graph(
                    id="graph-helper",
                    figure=px.imshow(img_1[32], color_continuous_scale='gray'),
                ),
            ],
            className="app-background",
        ),
        dcc.Store(id="small-slices", data=slices_1),
        dcc.Store(id="small-slices-2", data=slices_2),
        dcc.Store(id="z-pos", data=l_h // 2),
        dcc.Store(id="x-pos", data=l_lat // 2),
        dcc.Store(id="annotations", data={}),
        dcc.Store(id="segmentation-slices", data={}),
    ],
    className="twelve columns",
)

"""
@app.callback(
    Output("graph-histogram", "figure"),
    [Input("annotations", "data")],
)
def update_histo(annotations):
    if annotations is None or annotations.get('x') is None or annotations.get('z') is None:
        return dash.no_update
    # Horizontal mask
    path = path_to_indices(annotations['z']["path"])
    rr, cc = draw.polygon(path[:, 1], path[:, 0])
    mask = np.zeros((l_lat, l_lat))
    mask[rr, cc] = 1
    mask = ndimage.binary_fill_holes(mask)
    # top and bottom
    top = int(annotations['x']['y0']/size_factor)
    bottom = int(annotations['x']['y1']/size_factor)
    print(top, bottom)
    intensities = img_1[top:bottom, mask].ravel()
    edges = np.abs(filters.difference_of_gaussians(img_1, [0.1, 3, 3]))[top:bottom, mask].ravel()
    print(len(intensities), len(edges))
    cvs = ds.Canvas(plot_width=256, plot_height=100, x_range=(0, 255), y_range=(0, 0.2))
    agg = cvs.points(pd.DataFrame({'x':intensities, 'y':edges}), 'x', 'y')
    zero_mask = agg.values == 0
    agg.values = np.log10(agg.values, where=np.logical_not(zero_mask))
    agg.values[zero_mask] = np.nan
    fig = px.imshow(agg, origin='lower')
    fig.update_layout(dragmode='drawclosedpath')
    return fig
"""

@app.callback(
    Output("graph-histogram", "figure"),
    [Input("annotations", "data")],
)
def update_histo(annotations):
    if annotations is None or annotations.get('x') is None or annotations.get('z') is None:
        return dash.no_update
    # Horizontal mask
    path = path_to_indices(annotations['z']["path"])
    rr, cc = draw.polygon(path[:, 1], path[:, 0])
    mask = np.zeros((l_lat, l_lat))
    mask[rr, cc] = 1
    mask = ndimage.binary_fill_holes(mask)
    # top and bottom
    top = int(annotations['x']['y0']/size_factor)
    bottom = int(annotations['x']['y1']/size_factor)
    print(top, bottom)
    intensities = img_1[top:bottom, mask].ravel()
    hi = exposure.histogram(intensities)
    fig = px.bar(x=hi[1], y=hi[0], orientation='v')
    fig.update_layout(dragmode='select')
    return fig

"""
@app.callback(
    Output("segmentation-slices", "data"),
    [Input("graph-histogram", "selectedData")],
)
def update_segmentation_slices(relayout):
    print(relayout)
    if (
        relayout is not None
        and "shapes" in relayout
    ):
        shape = relayout["shapes"][-1]['path']
        print(shape)
        path = path_to_indices(shape)
        print(path)
        rr, cc = draw.polygon(path[:, 1]/delta_edges, path[:, 0])
        mask = np.zeros((100, 256))
        mask[rr, cc] = 1
        mask = ndimage.binary_fill_holes(mask)
        print("mask", mask.sum())
        intensities = img_1.ravel()
        edges = np.abs(filters.difference_of_gaussians(img, 3).ravel())
        img_mask = mask[(edges / delta_edges).astype(np.uint8), intensities].reshape(img_1.shape)
        print("img mask", img_mask.sum())
        # img_mask = img_as_ubyte(color.label2rgb(img_mask, bg_label=0))
        img_mask = mask_to_color(img_mask)
        return {str(i): array_to_data_url(img_mask[i]) for i in range(img_mask.shape[0])}
    else:
        return dash.no_update
"""


@app.callback(
    Output("segmentation-slices", "data"),
    [Input("graph-histogram", "selectedData")],
)
def update_segmentation_slices(selected):
    if (
        selected is not None
        and "range" in selected
    ):
        v_min, v_max = selected['range']['x']
        img_mask = np.logical_and(img_1 > v_min, img_1 <= v_max)
        # img_mask = img_as_ubyte(color.label2rgb(img_mask, bg_label=0))
        img_mask = mask_to_color(img_mask)
        return {str(i): array_to_data_url(img_mask[i]) for i in range(img_mask.shape[0])}
    else:
        return dash.no_update


@app.callback(
    Output("annotations", "data"),
    [Input("graph", "relayoutData"),
     Input("graph-2", "relayoutData"),
    ],
    [State('annotations', 'data')])
def update_store(relayout, relayout2, annotations):
    if relayout is None:
        return dash.no_update
    if (
        relayout is not None
        and "shapes" in relayout
        and len(relayout["shapes"]) > 1
    ):
        shape = relayout["shapes"][-1]
        annotations['z'] = shape
    if (
        relayout2 is not None
        and "shapes" in relayout2
        and len(relayout2["shapes"]) > 1
    ):
        shape = relayout2["shapes"][-1]
        annotations['x'] = shape
    return annotations


app.clientside_callback(
    """
function(n_slider, n_slider_2, seg_slices, slices, fig, annotations){
        var size_factor = 8.777;
        zpos = n_slider;
        xpos = n_slider_2;
        let fig_ = {...fig};
        console.log(n_slider);
        fig_.layout.images[0].source = slices[zpos];
        console.log(seg_slices);
        if (fig_.layout.images.length  == 1 && zpos in seg_slices){
            console.log('adding image')
            fig_.layout.images.push({...fig.layout.images[0]});
            fig_.layout.images[1].source = seg_slices[zpos];
        }
        if (fig_.layout.images.length  > 1 && zpos in seg_slices){
            fig_.layout.images[1].source = seg_slices[zpos];
        }
        fig_.layout.shapes = [fig.layout.shapes[0], fig.layout.shapes[1]];
        fig_.layout.shapes[0].y0 = xpos;
        fig_.layout.shapes[0].y1 = xpos;
        fig_.layout.shapes[1].y0 = xpos;
        fig_.layout.shapes[1].y1 = xpos;
        if (n_slider.toString() in annotations){
            fig_.layout.shapes.push(annotations[n_slider.toString()]);
        }
        return fig_;
    }
""",
    output=Output("graph", "figure"),
    inputs=[
        Input("slider", "value"), 
        Input("slider-2", "value"),
        Input("segmentation-slices", "data"),],
    state=[
        State("small-slices", "data"),
        
        State("graph", "figure"),
        State("annotations", "data"),
    ],
)

app.clientside_callback(
    """
function(n_slider, n_slider_2, slices_2, fig_2){
        var size_factor = 8.777;
        zpos = n_slider;
        xpos = n_slider_2;
        let fig_2_ = {...fig_2};
        fig_2_.layout.images[0].source = slices_2[xpos];
        fig_2_.layout.shapes[0].y0 = zpos * size_factor;
        fig_2_.layout.shapes[0].y1 = zpos * size_factor;
        fig_2_.layout.shapes[1].y0 = zpos * size_factor;
        fig_2_.layout.shapes[1].y1 = zpos * size_factor;
        return fig_2_;
    }
""",
    output=Output("graph-2", "figure"),
    inputs=[Input("slider", "value"), Input("slider-2", "value"),],
    state=[State("small-slices-2", "data"), State("graph-2", "figure"),],
)


if __name__ == "__main__":
    app.run_server(debug=True, port=8060)
