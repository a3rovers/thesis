def as_python_linestring(geom):
    """Geo-JSON representation of a linestring geometry
    """
    # FIXME: make part of simplegeom package
    ln = []
    for pt in geom:
        ln.append([pt.x, pt.y])
    return ln
