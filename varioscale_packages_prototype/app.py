from flask import Flask, Response, send_from_directory
from flask_compress import Compress
from simplegeom.geometry import Envelope

from db import DATASET
from retrieval_a import DataRetriever as DataOptionA
from retrieval_a import map_bbox_imp
from retrieval_a_ringcreator import DataRetriever as DataOptionRingCreator
from stream import compressed_chunked
from ujson import dumps

app = Flask(__name__, static_folder="static")
app.debug = False
Compress(app)


# -- FRONTEND -----------------------------------------------------------------

@app.route('/')
@app.route('/index.html')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/ringcreator/')
def option_ringcreator():
    return send_from_directory(app.static_folder, 'a_ringcreator.html')


@app.route('/a/')
def option_a():
    return send_from_directory(app.static_folder, 'a.html')


@app.route('/p/')
def option_p():
    return send_from_directory(app.static_folder, 'p_main.html')


# -- BACKEND ------------------------------------------------------------------

@app.route('/_a/<int:optimal_ct>/<string:xmin>/<string:ymin>/<string:xmax>/'
           '<string:ymax>/')
def data_a(optimal_ct, xmin, ymin, xmax, ymax):
    """
    Retrieve data and send back to client
    """
    def do():
        env = Envelope(*map(float, [xmin, ymin, xmax, ymax]), srid=3857)
        dt = DataOptionA(optimal_ct, DATASET)
        answer = dt.retrieve_data(env)
        yield answer
    res = compressed_chunked(do(), 'deflate')
    # res = Response(do())  # This sends the response back uncompressed
    res.content_type = 'application/x-javascript'
    return res


@app.route('/_ringcreator/<int:optimal_ct>/<string:xmin>/<string:ymin>/'
           '<string:xmax>/<string:ymax>/')
def data_ringcreator(optimal_ct, xmin, ymin, xmax, ymax):
    """
    Retrieve data and send back to client
    """
    def do():
        env = Envelope(*map(float, [xmin, ymin, xmax, ymax]), srid=3857)
        dt = DataOptionRingCreator(optimal_ct, DATASET)
        answer = dt.retrieve_data(env)
        print answer
        yield answer
    res = compressed_chunked(do(), 'deflate')
    # res = Response(do())  # This sends the response back uncompressed
    res.content_type = 'application/x-javascript'
    return res


@app.route('/get_imp/<int:optimal_ct>/<string:xmin>/<string:ymin>/'
           '<string:xmax>/<string:ymax>/')
def get_imp(optimal_ct, xmin, ymin, xmax, ymax):
    """
    The client doesn't know which imp to use. It can call this function.
    """
    env = Envelope(*map(float, [xmin, ymin, xmax, ymax]), srid=3857)
    imp = map_bbox_imp(env, optimal_ct, DATASET)
    imp = dumps({"imp": imp})
    res = Response(imp)
    res.content_type = 'application/x-javascript'
    return res


# FIXME: Index should be compressed like the packages

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def static_file(path):
    if path == "":
        path = "index.html"
    if path[0:8] == "packages":
        return send_from_directory(app.static_folder, path,
                                   mimetype='application/json')
    return send_from_directory(app.static_folder, path)


if __name__ == '__main__':
    app.run(port=5000)
