from build_sorted_table import SortedTable
from build_packages import PackagesConstructor
from build_index import IndexConstructor
from utilities import visualize_bboxes_3d

if __name__ == "__main__":
    # -- Settings -------------------------------------------------------------
    dbname = "drenthe"
    dataset = "web_drenthe_tgap"
    user = "postgres"
    password = "postgres"
    host = "localhost"
    table_settings = {
        "key_type": "hilbert",
        "scale_type": "imp",
        "scale_position": "centroid",
        "scale_factor": 1000
    }
    package_size = 500000
    index_degree = 20

    # -- Derive table name from settings --------------------------------------
    scale_factor_split = str(table_settings["scale_factor"]).split(".")
    if len(scale_factor_split) == 1:
        scale_factor_for_name = scale_factor_split[0]
    else:
        scale_factor_for_name = scale_factor_split[0] + scale_factor_split[1]
    table_name = dbname + "_sfc_" + table_settings["key_type"] + "_" \
                 + table_settings["scale_type"] + "_" \
                 + table_settings["scale_position"] + "_" \
                 + scale_factor_for_name

    # -- Initialize table with settings ---------------------------------------
    table = SortedTable(
        db=dbname, dataset=dataset, name=table_name, user=user,
        password=password, host=host, settings=table_settings)
    table.create(use_timer=True)

    # -- Build packages -------------------------------------------------------
    packages_constructor = PackagesConstructor(table, db=dbname)
    packages = packages_constructor.create(size=package_size)

    # -- Build index ----------------------------------------------------------
    index_constructor = IndexConstructor(
        packages, db=dbname, dataset=dataset, user=user, password=password,
        host=host, settings=table_settings)
    index = index_constructor.create(slots=index_degree)

    # -- Get info -------------------------------------------------------------
    print "Package with least edges:", packages_constructor.package_least_edges
    print "Package with most edges:", packages_constructor.package_most_edges
    print "Number of levels in index:", index_constructor.levels

    # -- Visualize packages ---------------------------------------------------
    visualize_bboxes_3d(packages, table_name + "_" + str(package_size))
