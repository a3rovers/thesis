from contextlib import contextmanager

import psycopg2
from psycopg2.extras import register_default_json
from psycopg2.pool import ThreadedConnectionPool

# DBNAME = "atkis"
DBNAME = "drenthe"
# DBNAME = "corine"
DBHOST = "localhost"
DBUSER = "postgres"
DBPASS = "postgres"
DBPORT = "5432"
DBSSL = "prefer"
MAX_THREADS = 8

# DATASET = "web_test_atkis"
DATASET = "web_drenthe_tgap"
# DATASET = "web_test_clc_xl_nosea"


def register_geom():
    """Find the correct OID and register the input/output function
     as psycopg2 extension type for automatic type conversion to happen.
    
    .. note::
        Should be called *only* once
    """
    from simplegeom.wkb import loads
    conn = psycopg2.connect('host=' + DBHOST + ' dbname=' + DBNAME
                            + ' user=' + DBUSER + ' password=' + DBPASS
                            + ' port=' + DBPORT)
    cursor = conn.cursor()
    # See: http: // postgis.net / docs / reference.html  # PostGIS_Types
    # See: http: // postgis.net / docs / geometry.html
    cursor.execute("SELECT NULL::geometry")
    geom_oid = cursor.description[0][1]
    cursor.close()
    conn.close()
    # See: http://nusoft.fnal.gov/nova/commissioning/ActiveChannelbyCoating/psycopg2-2.4.5/doc/html/extensions.html#database-types-casting-functions
    GEOMETRY = psycopg2.extensions.new_type((geom_oid,), "GEOMETRY", loads)
    psycopg2.extensions.register_type(GEOMETRY)


# See: https://docs.python.org/2/library/contextlib.html
@contextmanager
def get_db_connection():
    """psycopg2 connection context manager.
    Fetch a connection from the connection pool and release it.
    """
    try:
        connection = pool.getconn()
        yield connection
    finally:
        pool.putconn(connection)


@contextmanager
def get_db_cursor(commit=False):
    """psycopg2 connection.cursor context manager.
    Creates a new cursor and closes it, committing changes if specified.
    """
    with get_db_connection() as connection:
        cursor = connection.cursor()
        try:
            yield cursor
            if commit:
                connection.commit()
        finally:
            cursor.close()


def atserverstart(dataset):
    # print "Run at server start"
    # FIXME: NOT PER REQUEST
    # This assumes that the following DBMS function exists:
    # FIXME: 
    # table name of hierarchy table should be parameter!

    function = """
      CREATE OR REPLACE FUNCTION
        translate_face(_tbl REGCLASS, face_id INTEGER, imp NUMERIC)
      RETURNS INTEGER AS
      $BODY$
      DECLARE
          result INTEGER := -1;
      BEGIN
        EXECUTE format(
          'with recursive walk_hierarchy(id, parentid, il, ih) as (
            select face_id, parent_face_id, imp_low, imp_high
            from %s where face_id = %s
            UNION ALL
            select fh.face_id, fh.parent_face_id, fh.imp_low, fh.imp_high
            from walk_hierarchy w
            join %s fh on w.parentid = fh.face_id and w.il <= %s
          )
            select id
            from walk_hierarchy
            where il <= %s and ih > %s',
          _tbl, face_id, _tbl, imp, imp, imp
        )
        INTO result; -- STRICT does not allow None to be returned...
        RETURN result;
      END;
      $BODY$
      LANGUAGE plpgsql;
    """
    if False:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute(function)

    # FIXME: NOT PER REQUEST
    command = """select max(face_ct) from {0}_tgap_stats;""".format(dataset)
    with get_db_cursor() as cursor:
        cursor.execute(command)
        total_tgap_objects, = cursor.fetchone()

    # FIXME: NOT PER REQUEST
    # FIXME: SRID
    command = """
      select distinct st_srid(geometry) from {0}_tgap_edge;
    """.format(dataset)
    with get_db_cursor() as cursor:
        cursor.execute(command)
        srid, = cursor.fetchone()

    # ST_Extent - an aggregate function that returns the bounding box that
    # bounds rows of geometries.
    # See: http: // postgis.net / docs / ST_Extent.html
    command = """
      select
        st_area(st_setsrid(st_extent(geometry), {1})::geometry(Polygon, {1}))
      from {0}_tgap_edge;
    """.format(dataset, srid)
    with get_db_cursor() as cursor:
        cursor.execute(command)
        area, = cursor.fetchone()
    return total_tgap_objects, area, srid


pool = ThreadedConnectionPool(2, MAX_THREADS, database=DBNAME, user=DBUSER,
                              password=DBPASS, host=DBHOST, port=int(DBPORT))

# See: http://initd.org/psycopg/docs/extras.html#additional-data-types
register_default_json(loads=lambda x: x)
register_geom()

# FIXME: how to get the right data in here...
# Find them per tGAP at server start ???
total_tgap_objects, world_area, srid = atserverstart(DATASET)

# total_tgap_objects, world_area, srid = 95446, 2.55525026983e+12, 3857
# print total_tgap_objects, world_area, srid
