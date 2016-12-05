import cPickle
import functools
import json
import os
import timeit
from itertools import combinations

import numpy as np
from matplotlib import pyplot as plt
from shapely.geometry import MultiLineString, box
from simplegeom.wkt import loads as sg_loads

from build_sorted_table import SortedTable
from utilities import ViewportGridConstructor
from geojson import as_python_linestring

round2dig = functools.partial(round, ndigits=2)


class PackagesConstructor(object):
    def __init__(self, dataset, db="drenthe", write=True,
                 location="../static/packages/"):
        self._packages = []
        self._write = write
        self._location = location
        self.package_size = None
        self.db = db
        self.dataset = dataset

        # Info:
        self.count = 0
        self.total_volume = 0
        self.total_overlap = 0
        self.total_packages_for_viewport_grid = 0
        self.package_least_edges = np.inf
        self.package_most_edges = 0
        self.package_average_edges = 0

        # Info per package:
        self.volumes_per_package = []
        self.number_of_edges_per_package = []
        self.number_of_coors_per_package = []
        self.height_per_package = []

        # Info per viewport:
        self.total_packages_per_viewport_level = []
        self.packages_per_viewport_average = []
        self.packages_per_viewport_max = []

        if self.db == "drenthe":
            self.viewport_grid_constructor = ViewportGridConstructor(
                dataset="drenthe")
            self.viewport_grid = self.viewport_grid_constructor.create()

        if self.db == "atkis":
            self.viewport_grid_constructor = ViewportGridConstructor(
                dataset="atkis")
            self.viewport_grid = self.viewport_grid_constructor.create()

        if self._write:
            if not os.path.exists(self._location):
                os.makedirs(self._location)

    def _create_package(self, package_id, geom_2d, scale_low, scale_high,
                        edges_geojson):

        bbox_2d = geom_2d.bounds
        bbox_ll = (bbox_2d[0], bbox_2d[1], scale_low)
        bbox_ur = (bbox_2d[2], bbox_2d[3], scale_high)
        # Volume measures:
        volume = geom_2d.area * (scale_high - scale_low)
        self.total_volume += volume
        self.volumes_per_package.append(volume)

        if self._write:
            package_json = {
                "id": package_id,
                "type": "FeatureCollection",
                "bbox": (bbox_ll, bbox_ur),
                "features": edges_geojson
            }
            with open('{}package_{}.json'
                              .format(self._location, package_id),
                      'w') as outfile:
                # json.dump(package_json, outfile, sort_keys=True, indent=4)
                json.dump(package_json, outfile)
                # json.dump(package_json, outfile, separators=(',', ':'))

        package = {
            "id": package_id,
            "bbox": (bbox_ll, bbox_ur),
            "edges": "-",
            "geom": geom_2d,
            "scale_low": scale_low,
            "scale_high": scale_high
        }
        return package

    def create(self, size=100000, iter_size=50000, use_timer=True):
        print "\n** build_packages *******************************************"
        print "----"

        self.package_size = size
        timer_a = timeit.default_timer()  # Initialize timer

        # Containers for edges represented as GeoJSON and as shapely objects:
        container_edges_geojson = []
        container_edges_geom_2d = []

        # Statistics per package:
        package_scale_low = np.inf
        package_scale_high = 0
        package_count_edges = 0
        package_size_bytes = 0
        package_id = 1
        package_num_coords = 0

        for edges in self.dataset.get_generator(iter_size=iter_size):
            if use_timer:
                print "----"
                print "Processing new fetch from generator.."
            for edge in edges:

                # Add edge representations to containers for package:
                edge_geojson = {
                    "type": "Feature",
                    "geometry": {
                        "type": "LineString",
                        "coordinates": as_python_linestring(
                            sg_loads(edge["geom"].wkt))
                    },
                    "properties": {
                        "edge_id": edge["edge_id"],
                        "scale_low": edge["scale_low"],
                        "scale_high": edge["scale_high"],
                    }
                }

                package_num_coords += len(edge["geom"].coords)
                edge_bytes = len(bytes(edge_geojson))

                if package_size_bytes + edge_bytes > size:
                    if package_id % 500 == 0 and use_timer:
                        print "----"
                        print "Created", package_id, "packages.."

                        # print "Package: ", package_id
                        # print "# edges: ", package_count_edges
                        # print "# bytes: ", package_size_bytes
                        # print "-------- "

                    # Update info:
                    self.number_of_coors_per_package.append(package_num_coords)
                    self.number_of_edges_per_package.append(package_count_edges)
                    self.height_per_package.append(
                        package_scale_high - package_scale_low)
                    if package_count_edges < self.package_least_edges:
                        self.package_least_edges = package_count_edges
                    if package_count_edges > self.package_most_edges:
                        self.package_most_edges = package_count_edges
                    self.package_average_edges += package_count_edges

                    # Create package:
                    package_geom_2d = box(
                        *MultiLineString(container_edges_geom_2d).bounds)
                    package = self._create_package(
                        package_id, package_geom_2d, package_scale_low,
                        package_scale_high, container_edges_geojson)
                    self._packages.append(package)

                    # Empty containers:
                    container_edges_geojson = []
                    container_edges_geom_2d = []

                    # Reset statistics:
                    package_scale_low = np.inf
                    package_scale_high = 0
                    package_size_bytes = 0
                    package_count_edges = 0
                    package_id += 1
                    package_num_coords = 0

                container_edges_geojson.append(edge_geojson)
                container_edges_geom_2d.append(edge["geom"])

                # Keep track of package statistics:
                if edge["scale_low"] < package_scale_low:
                    package_scale_low = edge["scale_low"]
                if edge["scale_high"] > package_scale_high:
                    package_scale_high = edge["scale_high"]

                package_count_edges += 1
                package_size_bytes += edge_bytes

        # Create last package:
        if package_count_edges != 0:
            # print "Package: ", package_id
            # print "# edges: ", package_count_edges
            # print "# bytes: ", package_size_bytes
            # print "-------- "

            # Update info:
            self.number_of_coors_per_package.append(package_num_coords)
            self.number_of_edges_per_package.append(package_count_edges)
            self.height_per_package.append(
                package_scale_high - package_scale_low)
            if package_count_edges < self.package_least_edges:
                self.package_least_edges = package_count_edges
            if package_count_edges > self.package_most_edges:
                self.package_most_edges = package_count_edges
            self.package_average_edges += package_count_edges

            # Create last package:
            package_geom_2d = box(
                *MultiLineString(container_edges_geom_2d).bounds)
            package = self._create_package(
                package_id, package_geom_2d, package_scale_low,
                package_scale_high, container_edges_geojson)
            self._packages.append(package)

        self.count = package_id
        self.package_average_edges = self.package_average_edges / self.count

        timer_b = timeit.default_timer()
        if use_timer:
            print "----"
            print str(package_id), 'packages created in:', timer_b - timer_a, \
                'seconds'

        if self.db == "corine":
            packages = self._packages
            self._packages = []  # Remove packages from constructor for memory
            return packages
        else:
            # Calculate total overlap:
            print "----"
            print "Starting total overlap calculation between packages.."
            timer_overlap_a = timeit.default_timer()
            self.total_overlap = sum(
                [(pair[0]["geom"].intersection(pair[1]["geom"]).area
                  * overlap_1d(pair[0]["scale_low"], pair[0]["scale_high"],
                               pair[1]["scale_low"], pair[1]["scale_high"]))
                 for pair in combinations(self._packages, 2)])
            timer_overlap_b = timeit.default_timer()
            print 'Overlap between packages calculated in:', \
                timer_overlap_b - timer_overlap_a, 'seconds'

            return self._packages

    def benchmark(self):
        print "----"
        print "Starting overlap calculation with viewport grid.."
        timer_overlap_a = timeit.default_timer()

        for imp_slice, imp_level in enumerate(self.viewport_grid):
            temp_packages_overlap_vp_level = []
            for vp in imp_level:
                packages_intersecting = sum(
                    [int(vp.intersects(p["geom"])
                         * overlap_vp(p["scale_low"],
                                      p["scale_high"],
                                      self.viewportgrid.viewport_imps[imp_slice]
                                      )) for p in self._packages])
                temp_packages_overlap_vp_level.append(packages_intersecting)
            self.packages_per_viewport_average.append(
                sum(temp_packages_overlap_vp_level) / len(imp_level))
            self.packages_per_viewport_max.append(
                max(temp_packages_overlap_vp_level))

        timer_overlap_b = timeit.default_timer()
        print 'Overlap calculated in:', timer_overlap_b - timer_overlap_a, \
            'seconds'

        format_variables = [self.total_volume,
                            self.total_overlap,
                            sum(self.packages_per_viewport_average)/len(
                                self.packages_per_viewport_average),
                            max(self.packages_per_viewport_max)]
        with open('{}/{}.txt'.format("benchmarks", "bench_" + self.db), 'a') as outfile:
            outfile.write(
                "Benchmark:\n\\textbf{{{1}{{\smaller KB}} (x{2})}} & \\num{{{3}}} & \\num{{{4}}}& \\num{{{5}}}& \\num{{{6}}}\n\n".format(
                    self.package_size,
                    self.count,
                    '{:0.2e}'.format(format_variables[0]),
                    '{:0.2e}'.format(format_variables[1]),
                    format_variables[2],
                    format_variables[3]))

    def plot(self):
        plt.plot(self.packages_per_viewport_average, alpha=0.5, label="avg",
                 color="blue")
        plt.plot(self.packages_per_viewport_max, alpha=0.5, label="max",
                 color="green")
        plt.legend(loc='upper right')
        plt.xlabel('Viewport')
        plt.ylabel('Needed packages for query')
        plt.tight_layout()
        plt.show()


def overlap_1d(min1, max1, min2, max2):
    return max(0, min(max1, max2) - max(min1, min2))


def overlap_vp(scale_low, scale_high, vp):
    if scale_high > vp and vp >= scale_low:
        return 1
    else:
        return 0


def main():
    # -- Get a handle to specified table --------------------------------------
    table = SortedTable(db="atkis", dataset="web_test_atkis")

    # -- Build packages -------------------------------------------------------
    packages_constructor = PackagesConstructor(table, db="atkis")
    packages = packages_constructor.create(size=50000)

    # -- Pickle packages for later use ----------------------------------------
    packages_output = open('packages.pkl', 'wb')
    cPickle.dump(packages, packages_output, -1)
    packages_output.close()


if __name__ == "__main__":
    main()
