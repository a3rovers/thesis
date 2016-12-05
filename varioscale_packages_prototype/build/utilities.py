import os
from math import log

import psycopg2
from shapely.geometry import box
from shapely.wkt import loads

from external.hilbert import Hilbert_to_int
from external.morton import EncodeMorton3D


def get_dataset_statistics(dbname, dataset, scale_type="imp", user="postgres",
                           password="postgres", host="localhost"):
    # http://initd.org/psycopg/docs/usage.html#with-statement

    if scale_type == "step":
        scale_low = "MIN(step_low)"
        scale_high = "MAX(step_high)"
    else:
        scale_low = "MIN(imp_low)"
        scale_high = "MAX(imp_high)"

    conn = psycopg2.connect(
        "dbname=" + dbname + " user='" + user + "' host='"
        + host + "' password='" + password + "'")
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT " + scale_low + ", " + scale_high + ", "
                "ST_AsText(ST_Extent(geometry)), COUNT(edge_id) "
                "FROM " + dataset + "_tgap_edge;")
            record = cur.fetchone()
    conn.close()

    statistics = {
        "scale_low": log(record[0]+1, 10) if scale_type == "imp_log" else record[0],
        "scale_high": log(record[1]+1, 10) if scale_type == "imp_log" else record[1],
        "bbox_2d": loads(record[2]),
        "count": record[3]
    }
    return statistics


def calculate_dataset_factors(statistics, scale_factor=1):
    scale_range = statistics["scale_high"] - statistics["scale_low"]
    x_range = statistics["bbox_2d"].bounds[2] - statistics["bbox_2d"].bounds[0]
    y_range = statistics["bbox_2d"].bounds[3] - statistics["bbox_2d"].bounds[1]
    extent_2d = max(x_range, y_range)

    # print "SSC 2D bbox:", statistics["bbox_2d"].bounds
    # print "SSC area:", statistics["bbox_2d"].area  # x_range * y_range
    # print "x range:", x_range
    # print "y range:", y_range
    # print "scale range:", scale_range
    #
    # print "Ratio scale range/2D range:", scale_range / extent_2d

    factors = {
        "x_offset": statistics["bbox_2d"].bounds[0],
        "y_offset": statistics["bbox_2d"].bounds[1],
        "scale_ratio": scale_range / extent_2d,
        "scale_factor": scale_factor
    }
    return factors


def calculate_key_morton(x, y, z, factors=None):
    if factors is None:
        x_offset = 0
        y_offset = 0
        scale_ratio = 1
        stretch = 1
    else:
        x_offset = factors["x_offset"]
        y_offset = factors["y_offset"]
        scale_ratio = factors["scale_ratio"]
        stretch = factors["scale_factor"]

    if factors["scale_factor"] is None:
        scale_ratio = 1
        stretch = 1

    key = EncodeMorton3D(
        int(x - x_offset),
        int(y - y_offset),
        int((z * stretch) / scale_ratio)
    )
    return key


def calculate_key_hilbert(x, y, z, factors=None):
    if factors is None:
        x_offset = 0
        y_offset = 0
        scale_ratio = 1
        stretch = 1
    else:
        x_offset = factors["x_offset"]
        y_offset = factors["y_offset"]
        scale_ratio = factors["scale_ratio"]
        stretch = factors["scale_factor"]

    if factors["scale_factor"] is None:
        scale_ratio = 1
        stretch = 1

    key = Hilbert_to_int((
        int(x - x_offset),
        int(y - y_offset),
        int((z * stretch) / scale_ratio)
    ))
    return key


def calculate_key_hilbert_4d(x, y, z, q, factors=None):
    if factors is None:
        x_offset = 0
        y_offset = 0
        scale_ratio = 1
        stretch = 1
    else:
        x_offset = factors["x_offset"]
        y_offset = factors["y_offset"]
        scale_ratio = factors["scale_ratio"]
        stretch = factors["scale_factor"]

    if factors["scale_factor"] is None:
        scale_ratio = 1
        stretch = 1

    key = Hilbert_to_int((
        int(x - x_offset),
        int(y - y_offset),
        int((z * stretch) / scale_ratio),
        int((q * stretch) / scale_ratio)
    ))
    return key


def calculate_key_hilbert_5d(x, y, z, q, w, factors=None):
    if factors is None:
        x_offset = 0
        y_offset = 0
        scale_ratio = 1
        stretch = 1
    else:
        x_offset = factors["x_offset"]
        y_offset = factors["y_offset"]
        scale_ratio = factors["scale_ratio"]
        stretch = factors["scale_factor"]

    if factors["scale_factor"] is None:
        scale_ratio = 1
        stretch = 1

    key = Hilbert_to_int((
        int(x - x_offset),
        int(y - y_offset),
        int((z * stretch) / scale_ratio),
        int((q * stretch) / scale_ratio),
        int((w * stretch) / scale_ratio)
    ))
    return key


def visualize_bboxes_3d(collection, f_name, folder_location="visualize"):
    if not os.path.exists(folder_location):
        os.makedirs(folder_location)
    with open('{}/{}.txt'.format(folder_location, f_name), 'w') as outfile:
        if type(collection) == list:
            for bbox in collection:
                outfile.write('{}, {}, {}\n'.format(*bbox['bbox'][0]))
                outfile.write('{}, {}, {}\n'.format(*bbox['bbox'][1]))
        elif type(collection) == dict:
            for bbox in collection.values():
                outfile.write('{}, {}, {}\n'.format(*bbox['bbox'][0]))
                outfile.write('{}, {}, {}\n'.format(*bbox['bbox'][1]))


class ViewportGridConstructor(object):
    def __init__(self, dataset="drenthe"):
        self.vp_grid = []
        self.ct = 0

        if dataset == "drenthe":
            self.viewport_imps = [
                1515369545.93,
                702448015.053,
                498117980.718,
                330067400.52,
                252558202.578,
                185146803.932,
                169028933.524,
                127809224.258,
                94182041.1326,
                67018738.1028,
                48637752.3404,
                35603362.6875,
                25965102.3938,
                20715543.6957,
                16544030.6576,
                12410759.7618,
                9061433.90888,
                6940497.52735,
                4881908.95512,
                3718649.18978,
                2771407.93179,
                2126111.14052,
                1646109.16149,
                1240106.20527,
                917089.320885,
                689949.716029,
                519552.143898,
                381852.805297,
                307986.978821,
                269496.795314,
                242862.726623,
                218150.468221,
                175347.89012,
                157822.331952,
                144350.331952,
                130259.711166,
                118823.975166,
                99800,
                74600,
                56584,
                34920,
                12412.7847365,
                1.0698625001]
            viewport_extents = [
                 [387299.5718333239, 221890.37969617546],
                 [337163.8604238472, 193166.79503449518],
                 [293518.1886150761, 168161.46222738735],
                 [255522.42443651264, 146393.05566675216],
                 [222445.19052799756, 127442.55707333237],
                 [193649.78591666196, 110945.18984808773],
                 [168581.93021192355, 96583.39751724713],
                 [146759.094307538, 84080.73111369368],
                 [127761.2122182562, 73196.52783337608],
                 [111222.59526399884, 63721.278536666185],
                 [96824.89295833092, 55472.594924043864],
                 [84290.96510596189, 48291.698758624494],
                 [73379.54715376894, 42040.36555684637],
                 [63880.6061091281, 36598.26391668804],
                 [55611.29763199936, 31860.63926833216],
                 [48412.44647916546, 27736.297462021],
                 [42145.48255298089, 24145.849379312247],
                 [36689.77357688453, 21020.18277842272],
                 [31940.30305456405, 18299.13195834402],
                 [27805.648815999622, 15930.319634166546],
                 [24206.22323958273, 13868.148731010035],
                 [21072.741276490502, 12072.924689656124],
                 [18344.886788442265, 10510.091389211826],
                 [15970.151527282083, 9149.565979172476],
                 [13902.82440799987, 7965.159817082807],
                 [12103.111619791249, 6934.074365505017],
                 [10536.370638245251, 6036.462344828062],
                 [9172.443394221133, 5255.045694606379],
                 [7985.075763641042, 4574.782989585772],
                 [6951.412203999935, 3982.5799085414037],
                 [6051.555809895624, 3467.0371827529743],
                 [5268.185319122509, 3018.231172413565],
                 [4586.22169711045, 2627.5228473031893],
                 [3992.537881820579, 2287.391494792886],
                 [3475.7061019999674, 1991.2899542702362],
                 [3025.7779049478704, 1733.5185913760215],
                 [2634.0926595613128, 1509.1155862072483],
                 [2293.110848555225, 1313.761423651129],
                 [1996.2689409103477, 1143.6957473959774],
                 [1737.853051000042, 995.6449771355838],
                 [1512.888952473877, 866.7592956880108],
                 [1317.0463297805982, 754.5577931040898],
                 [1146.5554242776707, 656.8807118255645]]
            bounds = [
                682191.655404283,
                6912102.54792009,
                790072.061791224,
                7020704.04768337]

        if dataset == "atkis":
            self.viewport_imps = [
                # Way larger than the vp and not relevant for testing:
                # 5689388.37689,
                # 4380395.77057,
                # 4102401.84016,
                # 3696850.30169,
                # 2151593.64613,
                # 1605755.21936,
                1521261.49848,
                1119514.76257,
                802650.606865,
                572205.95425,
                418723.53727,
                254262.222724,
                176149.854831,
                119527.195637,
                84735.9550036,
                48638.9629363,
                30561.9608927,
                17883.2981452,
                10374.3111546,
                5181.32262123,
                384.463456571]
            viewport_extents = [
                # Way larger than the vp and not relevant for testing:
                # [55611.29763199948, 31860.639268333092],
                # [48412.44647916546,27736.297462021932],
                # [42145.48255298077,24145.849379312247],
                # [36689.77357688453,21020.182778423652],
                # [31940.303054564167,18299.13195834402],
                # [27805.64881599974,15930.319634166546],
                [24206.22323958273,13868.148731010966],
                [21072.741276490502,12072.924689656124],
                [18344.886788442265,10510.091389211826],
                [15970.151527282083,9149.565979171544],
                [13902.824407999637,7965.159817083739],
                [12103.111619791249,6934.074365505017],
                [10536.370638245251,6036.46234482713],
                [9172.443394221133,5255.045694605447],
                [7985.075763640925,4574.782989585772],
                [6951.412203999935,3982.5799085414037],
                [6051.555809895741,3467.0371827529743],
                [5268.185319122393,3018.231172413565],
                [4586.22169711045,2627.5228473031893],
                [3992.5378818204626,2287.391494792886],
                [3475.706101999851,1991.2899542711675]]
            bounds = [
                1092310.4636242,
                7021151.20915155,
                1108570.20220683,
                7034852.81658783]

        ssc_extents = [
            bounds[2] - bounds[0],
            bounds[3] - bounds[1]]

        for e, extents in enumerate(viewport_extents):
            vps = []
            x_extent = extents[0]
            y_extent = extents[1]
            viewports_fit_horizontal = int(ssc_extents[0] / x_extent) \
                if int(ssc_extents[0] / x_extent) != 0 else 1
            viewports_fit_vertical = int(ssc_extents[1] / y_extent) \
                if int(ssc_extents[1] / y_extent) != 0 else 1
            for x in range(viewports_fit_horizontal):
                x_low = bounds[0] + (x * x_extent)
                x_high = bounds[0] + ((x + 1) * x_extent)
                for y in range(viewports_fit_vertical):
                    y_low = bounds[1] + (y * y_extent)
                    y_high = bounds[1] + ((y + 1) * y_extent)
                    measures = box(x_low, y_low, x_high, y_high)  # Create shapely geometry
                    vps.append(measures)
                    self.ct += 1
            if dataset == "atkis":
                if e == 10 or e == 11 or e == 12 or e == 13:
                    del vps[0]
                    self.ct -= 1
                elif e == 14:
                    del vps[0:2]
                    del vps[viewports_fit_vertical-2]
                    self.ct -= 3
            self.vp_grid.append(vps)

    def create(self):
        return self.vp_grid


def main():
    dataset = "atkis"
    viewport_grid_constructor = ViewportGridConstructor(dataset=dataset)
    viewport_grid = viewport_grid_constructor.create()

    with open('{}/{}.txt'.format(
            "visualize", "viewport_grid_" + dataset), 'w') as outfile:
        for e, vp_level in enumerate(viewport_grid):
            for bbox in vp_level:
                outfile.write('{}, {}, {}\n'.format(
                    bbox.bounds[0],
                    bbox.bounds[1],
                    viewport_grid_constructor.viewport_imps[e]))
                outfile.write('{}, {}, {}\n'.format(
                    bbox.bounds[2],
                    bbox.bounds[3],
                    viewport_grid_constructor.viewport_imps[e]))


if __name__ == "__main__":
    main()
