import math
import timeit
from io import StringIO

import psycopg2
from shapely.wkt import loads

from utilities import (calculate_dataset_factors, calculate_key_hilbert,
                       calculate_key_hilbert_4d, calculate_key_hilbert_5d,
                       calculate_key_morton, get_dataset_statistics)


class SortedTable(object):
    def __init__(self, db, dataset, name="sfc_default", user="postgres",
                 password="postgres", host="localhost", settings=None):
        self.dbname = db
        self.dataset = dataset
        self.name = name
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

    def _check_if_exists(self, conn):
        with conn:
            with conn.cursor() as cur:
                # Check if schema exists:
                cur.execute(
                    "SELECT EXISTS(SELECT * FROM information_schema.tables "
                    "WHERE table_name=%s)", (self.name,))
                schema_exists = cur.fetchone()[0]
                # FIXME: Also check if table has any data!?
                return schema_exists

    def _drop(self, conn):
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DROP TABLE IF EXISTS " + self.name + "; "
                    "DROP INDEX IF EXISTS " + self.dbname + "_" + self.name +
                    "__key__idx;")

    def _set_schema(self, conn, use_timer=False):
        with conn:
            with conn.cursor() as cur:
                timer_1 = timeit.default_timer()

                cur.execute(
                    "CREATE TABLE " + self.name +
                    " (edge_id integer NOT NULL PRIMARY KEY,"
                    " scale_low double precision, scale_high double precision,"
                    " geometry geometry, key numeric);")

                timer_2 = timeit.default_timer()
                if use_timer:
                    print "Created new table schema in:", timer_2 - timer_1, \
                        "seconds"
                    print "----"

    def _insert_edges(self, conn, iter_size=100000, use_timer=False):
        # Determine scale_type (imp or step):
        if self.setting_scale_type == "step":
            db_query = "imp_low, imp_high, step_low, step_high"
        else:
            db_query = "imp_low, imp_high"

        with conn:
            with conn.cursor() as cur_get:
                with conn.cursor() as cur_set:
                    timer_1 = timeit.default_timer()

                    # Get data in order to calculate key on sfc:
                    cur_get.execute(
                        "SELECT edge_id, ST_X(ST_Centroid(geometry)) AS x, "
                        "ST_Y(ST_Centroid(geometry)) AS y, "
                        "ST_AsText(geometry), " + db_query + " FROM "
                        + self.dataset + "_tgap_edge;")

                    timer_2 = timeit.default_timer()
                    if use_timer:
                        print "Retrieved data from base table in", \
                            timer_2 - timer_1, "seconds"
                        print "----"

                    # Set variables for printing fetches from database:
                    fetches_ct = int(
                        math.ceil(self.statistics["count"] / iter_size)) + 1
                    fetch = 0

                    records = cur_get.fetchmany(iter_size)
                    while records:
                        timer_3 = timeit.default_timer()
                        fetch += 1
                        print "Inserting fetch", fetch, "of", fetches_ct, \
                            "in sorted table"

                        cpy = StringIO()
                        for record in records:
                            edge_id = record[0]
                            x = record[1]
                            y = record[2]
                            geom = record[3]
                            imp_low = record[4]
                            imp_high = record[5]
                            if self.setting_scale_type == "imp":
                                scale_low = imp_low
                                scale_high = imp_high
                            elif self.setting_scale_type == "imp_log":
                                scale_low = math.log(imp_low + 1, 10)
                                scale_high = math.log(imp_high + 1, 10)
                            elif self.setting_scale_type == "step":
                                scale_low = record[6]
                                scale_high = record[7]
                            else:
                                scale_low = imp_low
                                scale_high = imp_high
                                print "Unknown scale_type: imp is used!"

                            if self.setting_scale_position == "centroid":
                                centroid = scale_low + (
                                    abs(scale_high - scale_low) / 2)
                                z = centroid
                            elif self.setting_scale_position == "high":
                                z = scale_high
                            else:
                                centroid = scale_low + (
                                    abs(scale_high - scale_low) / 2)
                                z = centroid
                                print "Unknown scale_position: centroid used!"

                            if self.setting_key_type == "morton":
                                key = calculate_key_morton(
                                    x, y, z, factors=self.factors)
                            elif self.setting_key_type == "hilbert":
                                key = calculate_key_hilbert(
                                    x, y, z, factors=self.factors)
                            elif self.setting_key_type == "hilbert_4d_low":
                                key = calculate_key_hilbert_4d(
                                    x, y, scale_high, scale_low,
                                    factors=self.factors)
                            elif self.setting_key_type == "hilbert_4d_height":
                                q = (scale_high - scale_low)
                                key = calculate_key_hilbert_4d(
                                    x, y, z, q, factors=self.factors)
                            elif self.setting_key_type == "hilbert_4d_volume":
                                q = (scale_high - scale_low)
                                volume = loads(geom).area * q
                                key = calculate_key_hilbert_4d(
                                    x, y, z, volume, factors=self.factors)
                            elif self.setting_key_type == "hilbert_5d_low_volume":
                                q = (scale_high - scale_low)
                                volume = loads(geom).area * q
                                key = calculate_key_hilbert_5d(
                                    x, y, scale_high, scale_low, volume,
                                    factors=self.factors)
                            else:
                                print "Unknown key_type: 3D Hilbert SFC is used!"
                                key = calculate_key_hilbert(
                                    x, y, z, factors=self.factors)

                            fields = [edge_id, imp_low, imp_high, geom, key]
                            cpy.write('\t'.join(
                                [unicode(field) for field in fields]) + '\n')

                        cpy.seek(0)
                        cur_set.copy_from(cpy, self.name)

                        timer_4 = timeit.default_timer()
                        if use_timer:
                            print '(Finished in', timer_4 - timer_3, 'seconds)'
                            print '----'

                        records = cur_get.fetchmany(iter_size)

    def _create_index(self, conn, use_timer=False):
        with conn:
            with conn.cursor() as cur:
                timer_1 = timeit.default_timer()
                cur.execute(
                    "CREATE INDEX " + self.dbname + "_" + self.name +
                    "__key__idx ON " + self.name + " USING btree (key);")
                timer_2 = timeit.default_timer()
                if use_timer:
                    print "Created index on table in:", timer_2 - timer_1, \
                        "seconds"
                    print "----"

    def create(self, iter_size=100000, use_timer=True, skip_duplicates=False):
        # http://initd.org/psycopg/docs/usage.html#with-statement
        # https://www.postgresql.org/docs/current/static/populate.html

        print "\n** build_sorted_table ***************************************"
        print "----"

        conn = psycopg2.connect(
            "dbname=" + self.dbname + " user='" + self.user + "' host='"
            + self.host + "' password='" + self.password + "'")

        if self._check_if_exists(conn):
            answer = None
            if skip_duplicates:
                print "Schema already exists.. Existing table is used.."
                print "----"
                return
            while answer != "y" and answer != "n":
                answer = raw_input(
                    "Schema already exists! Drop table and recreate it? "
                    "[y/n]\n")
            if answer == "n":
                return
            print "----"

        self._drop(conn)
        self._set_schema(conn)

        timer_1 = timeit.default_timer()
        self._insert_edges(conn, iter_size=iter_size, use_timer=use_timer)
        self._create_index(conn, use_timer=use_timer)
        conn.close()

        timer_2 = timeit.default_timer()
        if use_timer:
            print 'Sorted table build in', timer_2 - timer_1, 'seconds'
            print "----"

    def get_generator(self, iter_size=100000):
        conn = psycopg2.connect(
            "dbname=" + self.dbname + " user='" + self.user + "' host='"
            + self.host + "' password='" + self.password + "'")

        with conn:
            with conn.cursor() as cur:
                timer_a = timeit.default_timer()

                cur.execute("SELECT edge_id, scale_low, scale_high, key, "
                            "ST_AsText(geometry) "
                            "FROM " + self.name + " ORDER BY key;")

                timer_b = timeit.default_timer()
                print "Created generator on sorted table in:", \
                    timer_b - timer_a, "seconds"

                records = cur.fetchmany(iter_size)
                while records:
                    geodata = []
                    for record in records:
                        geom = loads(record[4])
                        geodata.append({
                            "edge_id": record[0],
                            "scale_low": record[1],
                            "scale_high": record[2],
                            "key": record[3],
                            "geom": geom
                        })
                    yield geodata
                    records = cur.fetchmany(iter_size)
        conn.close()


def main():
    base_data = [
        ("atkis", "web_test_atkis"),
        # ("drenthe", "web_drenthe_tgap"),
        # ("corine", "web_test_clc_xl_nosea")
    ]

    # -- Default settings -----------------------------------------------------
    for database, dataset in base_data:
        table = SortedTable(db=database, dataset=dataset)
        table.create()


if __name__ == "__main__":
    main()
