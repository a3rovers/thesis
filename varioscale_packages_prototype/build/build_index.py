import cPickle
import json
import math
import os
import pprint

import numpy
from shapely.geometry import MultiPolygon, box

from utilities import (calculate_dataset_factors, calculate_key_hilbert,
                       calculate_key_morton, get_dataset_statistics)


class IndexConstructor(object):
    def __init__(self, packages, db, dataset, user="postgres",
                 password="postgres", host="localhost", settings=None,
                 write=True, location="../static/index/"):
        self._index = {}
        self._index_json = {}
        self._write = write
        self._location = location
        self.packages = packages
        self.nodes_count = 0
        self.levels = 0

        self.dbname = db
        self.dataset = dataset
        self.user = user
        self.password = password
        self.host = host

        if settings:
            self.setting_key_type = settings["key_type"]
            self.setting_scale_type = settings["scale_type"]
            self.setting_scale_position = settings["scale_position"]
            self.setting_scale_factor = settings["scale_factor"]
        else:
            self.setting_key_type = "hilbert"
            self.setting_scale_type = "imp"
            self.setting_scale_position = "centroid"
            self.setting_scale_factor = 1

        self.statistics = get_dataset_statistics(
            self.dbname, self.dataset, scale_type=self.setting_scale_type,
            user=self.user, password=self.password, host=self.host)
        self.factors = calculate_dataset_factors(
            self.statistics, scale_factor=self.setting_scale_factor)

    def _sort_nodes(self, nodes):
        for node in nodes:
            x = node["geom"].centroid.x
            y = node["geom"].centroid.y
            scale_high = node["scale_high"]
            scale_low = node["scale_low"]

            if self.setting_scale_type == "imp_log":
                z_low = math.log(
                    scale_low, 2) if scale_low > 0 else 0
                z_high = math.log(
                    scale_high, 2) if scale_high > 0 else 0
            else:
                z_low = scale_low
                z_high = scale_high

            if self.setting_scale_position == "high":
                z = scale_high
            else:
                centroid = z_low + (abs(z_high - z_low) / 2)
                z = centroid

            if self.setting_key_type == "morton":
                key = calculate_key_morton(x, y, z, factors=self.factors)
            else:
                key = calculate_key_hilbert(x, y, z, factors=self.factors)
            node["key"] = key

        collection_sorted = sorted(nodes, key=lambda k: k['key'])
        return collection_sorted

    def _create_higher_nodes(self, lower_nodes, slots):
        lower_nodes_sorted = self._sort_nodes(lower_nodes)

        higher_nodes = []
        higher_nodes_json = []  # Used to create the json_dict

        # Container for representations of lower_nodes:
        container_lower_nodes_geom_2d = []
        container_lower_nodes_reference = []
        container_lower_nodes_reference_json = []  # Used for the json_dict

        # Statistics of lower nodes per higher node:
        higher_node_scale_l = numpy.inf
        higher_node_scale_h = 0
        higher_node_count_lower_nodes = 0

        last = len(lower_nodes_sorted) - 1
        for e, lower_node in enumerate(lower_nodes_sorted):

            # Add representations to containers:
            container_lower_nodes_geom_2d.append(lower_node["geom"])
            container_lower_nodes_reference.append({
                "id": lower_node["id"],
                "geom": lower_node["geom"],
                "scale_low": lower_node["scale_low"],
                "scale_high": lower_node["scale_high"],
            })
            if self._write:
                lower_node_bbox_2d = lower_node["geom"].bounds
                lower_node_bbox_ll = (lower_node_bbox_2d[0],
                                      lower_node_bbox_2d[1],
                                      lower_node["scale_low"])
                lower_node_bbox_ur = (lower_node_bbox_2d[2],
                                      lower_node_bbox_2d[3],
                                      lower_node["scale_high"])
                container_lower_nodes_reference_json.append({
                    "id": lower_node["id"],
                    "bbox": (lower_node_bbox_ll, lower_node_bbox_ur)
                })

            # Keep track of higher node statistics:
            if lower_node["scale_low"] < higher_node_scale_l:
                higher_node_scale_l = lower_node["scale_low"]
            if lower_node["scale_high"] > higher_node_scale_h:
                higher_node_scale_h = lower_node["scale_high"]
            higher_node_count_lower_nodes += 1

            if higher_node_count_lower_nodes == slots or e == last:
                self.nodes_count += 1

                higher_node_geom_2d = box(
                    *MultiPolygon(container_lower_nodes_geom_2d).bounds)
                bbox_2d = higher_node_geom_2d.bounds
                bbox_ll = (bbox_2d[0], bbox_2d[1], higher_node_scale_l)
                bbox_ur = (bbox_2d[2], bbox_2d[3], higher_node_scale_h)

                if self.levels == 0:
                    higher_nodes.append({
                        "id": self.nodes_count,
                        "bbox": (bbox_ll, bbox_ur),
                        "level": self.levels,
                        "packages": container_lower_nodes_reference,
                        # Properties below are used for convenience only:
                        "geom": higher_node_geom_2d,
                        "scale_low": higher_node_scale_l,
                        "scale_high": higher_node_scale_h
                    })
                else:
                    higher_nodes.append({
                        "id": self.nodes_count,
                        "bbox": (bbox_ll, bbox_ur),
                        "level": self.levels,
                        "child_nodes": container_lower_nodes_reference,
                        # Properties below are used for convenience only:
                        "geom": higher_node_geom_2d,
                        "scale_low": higher_node_scale_l,
                        "scale_high": higher_node_scale_h
                    })

                if self._write:
                    if self.levels == 0:
                        p = {
                            "id": self.nodes_count,
                            "bbox": (bbox_ll, bbox_ur),
                            "level": self.levels,
                            "packages": container_lower_nodes_reference_json
                        }
                        higher_nodes_json.append(p)
                    else:
                        p = {
                            "id": self.nodes_count,
                            "bbox": (bbox_ll, bbox_ur),
                            "level": self.levels,
                            "child_nodes": container_lower_nodes_reference_json
                        }
                        higher_nodes_json.append(p)

                # Empty containers:
                container_lower_nodes_geom_2d = []
                container_lower_nodes_reference = []
                container_lower_nodes_reference_json = []

                # Reset statistics:
                higher_node_scale_l = numpy.inf
                higher_node_scale_h = 0
                higher_node_count_lower_nodes = 0

        return higher_nodes_json, higher_nodes

    def create(self, slots):
        print "\n** build_index **********************************************"
        print "----"

        nodes_json, nodes = self._create_higher_nodes(self.packages, slots)
        for node in nodes:
            id1 = node["id"]
            self._index[id1] = node
        if self._write:
            for node in nodes_json:
                id1 = node["id"]
                self._index_json[id1] = node

        if self.nodes_count == 1:
            root_node_id = id1
        else:
            while len(nodes) > 1:
                self.levels += 1
                nodes_json, nodes = self._create_higher_nodes(nodes, slots)
                for node in nodes:
                    id2 = node["id"]
                    self._index[id2] = node
                if self._write:
                    for node in nodes_json:
                        id2 = node["id"]
                        self._index_json[id2] = node
                if len(nodes) == 1:
                    root_node_id = nodes[0]["id"]

        if self._write:
            if not os.path.exists(self._location):
                os.makedirs(self._location)

            index_send = [self._index_json, {"root": root_node_id}]
            with open('{}index.json'.format(self._location), 'w') as outfile:
                # json.dump(index_send, outfile, sort_keys=True, indent=4)
                json.dump(index_send, outfile, separators=(',', ':'))
                # json.dump(index_send, outfile)
            self._index_json = None

        index = self._index
        self._index = None  # Remove index from constructor

        return index, root_node_id


def main():
    # -- Open packages from pickle file ---------------------------------------
    packages_input = open('packages.pkl', 'rb')
    packages_from_pickle = cPickle.load(packages_input)

    # -- Build index from packages --------------------------------------------
    index_constructor = IndexConstructor(
        packages_from_pickle, db="atkis", dataset="web_test_atkis")
    print "index:"
    index = index_constructor.create(4)
    pprint.pprint(index)
    print "----"
    print "Number of levels in index", index_constructor.levels


if __name__ == "__main__":
    main()
