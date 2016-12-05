import pprint

from simplegeom.geometry import Envelope
from simplegeom.wkb import dumps

from db import get_db_cursor, srid, total_tgap_objects, world_area
from geojson import as_python_linestring
from timer import MeasureTime
from ujson import dumps


# Determine imp value for optimal_ct and bbox
# See PHD Martijn p.147
def map_bbox_imp(bbox, ct, dataset):
    screen_area = bbox.area
    assert screen_area != 0
    factor = round(world_area / screen_area, 2)
    new_count = ct * factor
    new_count = min(max(new_count, 2), total_tgap_objects)
    command = """
      SELECT imp
      FROM {0}_tgap_stats
      WHERE face_ct <= {1}
      ORDER BY imp
      LIMIT 1
    """.format(dataset, new_count)
    with get_db_cursor() as cursor:
        cursor.execute(command)
        imp, = cursor.fetchone()
    print imp
    if imp is None:
        imp = 0.0
    return imp


# See: http://postgis.net/docs/geometry_overlaps_nd.html
# &&& - Returns TRUE if A's n-D bounding box intersects B's n-D bounding box.
def overlap_2d(bbox, imp, geom_col_nm):
    where = """
      st_setsrid(
        st_makeline(
          st_makepoint(
            st_xmin({col_nm}::box3d), st_ymin({col_nm}::box3d), imp_low
          ),
          st_makepoint(
            st_xmax({col_nm}::box3d), st_ymax({col_nm}::box3d), imp_high
          )
        ), {srid}
      ) &&& st_setsrid(
        st_makeline(
          st_makepoint({box.xmin}, {box.ymin}, {imp}),
          st_makepoint({box.xmax}, {box.ymax}, {imp})
        ), {srid}
      ) and imp_low <= {imp} and imp_high > {imp}
    """.format(col_nm=geom_col_nm, box=bbox, imp=imp, srid=bbox.srid)

    return where


class DataRetriever(object):
    def __init__(self, optimal_count_per_layer, dataset):
        self.dataset = dataset
        self.imp = None
        self.ct = optimal_count_per_layer

    def retrieve_data(self, bbox):
        timer = MeasureTime()
        timer.measure('retrieve')
        UNIVERSE_ID = 0  # FIXME: make this different
        timer.measure('imp')
        imp = map_bbox_imp(bbox, self.ct, self.dataset)
        timer.measure('imp')

        timer.measure('face_query')
        face_where = overlap_2d(bbox, imp, geom_col_nm="mbr_geometry")
        command = """
          SELECT f.face_id, f.imp_low::float, f.imp_high::float,
            f.feature_class
          FROM {dataset}_tgap_face f
          WHERE {where}
        """.format(dataset=self.dataset, where=face_where)
        with get_db_cursor() as cursor:
            cursor.execute(command)
            timer.measure('face_query')

            timer.measure('face_query_fetch')
            resultset = cursor.fetchall()
        faces = {}
        for face_id, imp_low, imp_high, feature_class, in resultset:
            faces[face_id] = {
                "featureClass": feature_class
            }
        timer.measure('face_query_fetch')

        timer.measure('edge_query')
        edge_where = overlap_2d(bbox, imp, geom_col_nm="geometry")
        command = """
          SELECT edge_id, start_node_id as startNodeId,
            end_node_id as endNodeId, imp_low as impLow, imp_high as impHigh,
            {left_face} as leftFaceId, {right_face} as rightFaceId, geometry
          FROM {dataset}_tgap_edge
          WHERE {where}
        """.format(dataset=self.dataset,
                   left_face="""
                     case when left_face_id_low = {0} then {0} else
                     translate_face('{2}_tgap_face_hierarchy',
                     left_face_id_low, {1}) end
                   """.format(UNIVERSE_ID, imp, self.dataset),
                   right_face="""
                     case when right_face_id_low = {0} then {0} else
                     translate_face('{2}_tgap_face_hierarchy',
                     right_face_id_low, {1}) end
                   """.format(UNIVERSE_ID, imp, self.dataset),
                   where=edge_where)

        with get_db_cursor() as cursor:
            cursor.execute(command)
            timer.measure('edge_query')

            timer.measure('edge_query_fetch')
            resultset = cursor.fetchall()


        edges = {}
        for edge_id, start_node_id, end_node_id, imp_low, imp_high, \
                left_face_id, right_face_id, geom_wkb, in resultset:
            edges[edge_id] = {
                "startNodeId": start_node_id,
                "endNodeId": end_node_id,
                "leftFaceId": left_face_id,  # fixme
                "rightFaceId": right_face_id,
                # No reuse in option A, so imp values not needed.
                # "impLow": imp_low,
                # "impHigh": imp_high,
                "geometry": {
                    "type": "LineString",
                    "coordinates": as_python_linestring(geom_wkb)
                },
                "bbox": [
                    geom_wkb.envelope.xmin,
                    geom_wkb.envelope.ymin,
                    imp_low,
                    geom_wkb.envelope.xmax,
                    geom_wkb.envelope.ymax,
                    imp_high,
                ]
            }
        timer.measure('edge_query_fetch')

        result = {}
        result["edges"] = edges
        result["faces"] = faces
        result["impSel"] = imp
        result["universeFaceId"] = UNIVERSE_ID
        result["bbox"] = {
            "left": bbox.xmin, "bottom": bbox.ymin, "right": bbox.xmax,
            "top": bbox.ymax
        }  # needed for clipping at client side...
        result["timings"] = {
            "imp": "%imp%",
            "fq": "%face_query%",
            "fqr": "%face_query_fetch%",
            "eq": "%edge_query%",
            "eqr": "%edge_query_fetch%",
            "ser": "%serialization%",
            "res": "%retrieve%",
        }

        timer.measure('serialization')
        res = dumps(result)
        timer.measure('serialization')

        timer.measure('retrieve')
        # print type(res)
        for measure in ('imp', 'face_query', 'face_query_fetch', 'edge_query',
                        'edge_query_fetch', 'serialization', 'retrieve'):
            replace = "%{}%".format(measure)
            res = res.replace(replace, str(round(timer.duration(measure), 5)))
            # print measure, timer.duration(measure)
        return res


if __name__ == "__main__":
    from json import dumps

    env = Envelope(788401.6179225014, 6838868.413885655, 1462729.3387701975,
                   7225202.003954647, srid=3857)
    r = DataRetriever(20, "test_clc_00_000")
    result = r.retrieve_data(env)
    with open("/tmp/output.json", "w") as fh:
        fh.write(result)
