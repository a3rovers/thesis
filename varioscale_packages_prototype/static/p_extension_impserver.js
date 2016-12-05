function test_intersection(box, rectangle) {
  // input: box --> [[ll.x, ll.y, imp_low], [ur.x, ur.y, imp_high]]
  //        rectangle --> [ll.x, ll.y, ur.x, ur.y, imp]

  // Separating axes theorem
  var noOverlapAtRight = rectangle[0] > box[1][0];
  var noOverlapAtLeft = rectangle[2] < box[0][0];
  var noOverlapAtTop = rectangle[1] > box[1][1];
  var noOverlapAtBottom = rectangle[3] < box[0][1];

  // If one of the above is true then there can be no overlap
  var overlap2D = !(noOverlapAtRight || noOverlapAtLeft || noOverlapAtTop || noOverlapAtBottom);

  // If there is overlap, also check if the imp value of the rectangle is
  // between the imp range of the box
  if (overlap2D) {
    if (box[1][2] > rectangle[4] && rectangle[4] >= box[0][2]) {
      return true
    } else {
      return false
    }
  } else {
    return false
  }

}

function walk_index(start_outer, index_outer, viewport_outer) {
  var ids = [];

  function walk(start, index, viewport) {
    if (start["level"] == 0) {
      for (var i = 0; i < start["packages"].length; i++) {
        if (test_intersection(start["packages"][i]["bbox"], viewport)) {
          ids.push(start["packages"][i]["id"]);
        }
      }
    } else {
      for (var i = 0; i < start["child_nodes"].length; i++) {
        if (test_intersection(start["child_nodes"][i]["bbox"], viewport)) {
          var new_start = index[start["child_nodes"][i]["id"]];
          walk(new_start, index, viewport);
        }
      }
    }
  }

  if (test_intersection(start_outer["bbox"], viewport_outer)) {
    walk(start_outer, index_outer, viewport_outer)
  }
  return ids
}

function filter_packet(packet, vp) {
  var features_to_render = [];
  for (var i = 0; i < packet.features.length; i++) {
    var f = packet.features[i];
    // See retrieval_a_v0, line 54:
    //   Imp vp is smaller than imp_high, and larger or equal to imp_low
    if (f.properties.scale_high > vp[4] && vp[4] >= f.properties.scale_low) {
      features_to_render.push(f);
    }
  }
  return features_to_render;
}

// Filter_packet is faster than this native filter!
//
// function object_filter(packet, vp) {
//   return packet.features.filter(function(f){
//     return f.properties.imp_high > vp[4] && vp[4] >= f.properties.imp_low;
//   });
// }

Colors = {};
Colors.names = {
    black: "#000000",
    blue: "#0000ff",
    brown: "#a52a2a",
    darkblue: "#00008b",
    darkgrey: "#a9a9a9",
    darkgreen: "#006400",
    darkkhaki: "#bdb76b",
    darkmagenta: "#8b008b",
    darkolivegreen: "#556b2f",
    darkorange: "#ff8c00",
    darkorchid: "#9932cc",
    darkred: "#8b0000",
    darksalmon: "#e9967a",
    darkviolet: "#9400d3",
    fuchsia: "#ff00ff",
    gold: "#ffd700",
    green: "#008000",
    indigo: "#4b0082",
    lime: "#00ff00",
    magenta: "#ff00ff",
    maroon: "#800000",
    navy: "#000080",
    olive: "#808000",
    orange: "#ffa500",
    pink: "#ffc0cb",
    purple: "#800080",
    violet: "#800080",
    red: "#ff0000",
    yellow: "#ffff00"
};
randomColor = function() {
    var result;
    var count = 0;
    for (var prop in Colors.names)
        if (Math.random() < 1/++count)
           result = prop;
    return result;
};

function retrieve_tgap() {
///////////////////////////////////////////////////////////////////////////////
// Main:                                                                     //
///////////////////////////////////////////////////////////////////////////////
                                                                             //
  var delta = 0;                                                             //
  var pix = [-delta, height + delta];                                        //
  var bottomLeft = [((-zoom.translate()[0] + pix[0]) * resolution),          //
    ((zoom.translate()[1] - pix[1]) * resolution)];                          //
  pix = [width + delta, -delta];                                             //
  var topRight = [((-zoom.translate()[0] + pix[0]) * resolution),            //
    ((zoom.translate()[1] - pix[1]) * resolution)];                          //
  d3.select("#nprogress")                                                    //
      .style("display", "inline");                                           //
  d3.select("#nprogress .spinner-icon")                                      //
      .style("-moz-animation", "nprogress-spinner 400ms linear infinite")    //
      .style("-ms-animation", "nprogress-spinner 400ms linear infinite")     //
      .style("-o-animation", "nprogress-spinner 400ms linear infinite")      //
      .style("-webkit-animation", "nprogress-spinner 400ms linear infinite") //
      .style("animation", "nprogress-spinner 400ms linear infinite");        //
                                                                             //
  var nr = d3.select("#optimalCount").node().value;                          //
                                                                             //
///////////////////////////////////////////////////////////////////////////////

  var edges_to_render_cached = []; // Container for colorCached
  var edges_to_render_new = []; // Container for colorCached
  var edges_to_render = []; // Container for colorChanges
  var packages_to_render = {}; // Container for colorPackage
  var counter = 0;

  d3.json("../get_imp/" + nr + "/" + bottomLeft[0] + "/" + bottomLeft[1] + "/"
      + topRight[0] + "/" + topRight[1] + "/", function (error, imp) {

    var epsg3857path = new_epsg3857path();
    var viewport = [bottomLeft[0], bottomLeft[1], topRight[0], topRight[1],
      imp["imp"]];
    var needed_packages = walk_index(index[root_id], index, viewport);
    var needed_count = needed_packages.length;

    var j;
    if (colorChanges) { // ** BEGIN SWITCH for color options ******************

      // Remove all edges from different color option:
      vector_default.selectAll("path").remove();
      vector_new.selectAll("path").remove();
      vector_cached.selectAll("path").remove();
      vector_packages.selectAll("g").remove();
      package_legend.selectAll("li").remove();

      for (j = 0; j < needed_count; j++) {

        d3.json("../packages/package_" + needed_packages[j] + ".json",
            function (error, answer) {

              edges_to_render.push.apply(
                  edges_to_render, filter_packet(answer, viewport));
              counter += 1;

              // Needed to keep track of cached and not cached packages:
              cached_package_ids.add(answer.id);

              if (counter == needed_count) {

                var edges = vector_incoming
                    .selectAll('path')
                    .data(edges_to_render, function (d) {
                      return d.properties.edge_id;
                    })
                    .attr("class", "edges")
                    .style('stroke', "blue");
                edges
                    .enter()
                    .append("path")
                    .attr('d', epsg3857path)
                    .attr("class", "edges")
                    .style('stroke', "red");
                edges
                    .exit()
                    .remove();

                // Update statistics:
                d3.select("#total_packages").text(cached_package_ids.size);
                d3.select("#screen_packages").text(needed_count);

              } // END IF statement for counter

            }); // END json request for package

      } // END for loop

    } else if (colorCached) { // ** SWITCH for color options ******************

      // Remove all edges from different color option:
      vector_default.selectAll("path").remove();
      vector_incoming.selectAll("path").remove();
      vector_packages.selectAll("g").remove();
      package_legend.selectAll("li").remove();

      for (j = 0; j < needed_count; j++) {

        d3.json("../packages/package_" + needed_packages[j] + ".json",
            function (error, answer) {

              if (cached_package_ids.has(answer.id)) {
                edges_to_render_cached
                    .push.apply(edges_to_render_cached, filter_packet(
                    answer, viewport));
              } else {
                edges_to_render_new
                    .push.apply(edges_to_render_new, filter_packet(
                    answer, viewport));
              }

              // Needed to keep track of cached and not cached packages:
              cached_package_ids.add(answer.id);

              counter += 1;
              if (counter == needed_count) {

                var edges_cached = vector_cached
                    .selectAll('path')
                    .data(edges_to_render_cached, function (d) {
                      return d.properties.edge_id;
                    })
                    .style('stroke', "blue");
                edges_cached
                    .enter()
                    .append("path")
                    .attr('d', epsg3857path)
                    .attr("class", "edges")
                    .style('stroke', "blue");
                edges_cached
                    .exit()
                    .remove();

                var edges_new = vector_new
                    .selectAll('path')
                    .data(edges_to_render_new, function (d) {
                      return d.properties.edge_id;
                    })
                    .style('stroke', "red");
                edges_new
                    .enter()
                    .append("path")
                    .attr('d', epsg3857path)
                    .attr("class", "edges")
                    .style('stroke', "red");
                edges_new
                    .exit()
                    .remove();

                // Update statistics:
                d3.select("#total_packages").text(cached_package_ids.size);
                d3.select("#screen_packages").text(needed_count);

              } // END if statement for counter

            }); // END json request for package

      } // END for loop

    } else if (colorPackage) { // ** SWITCH for color options *****************

      // Remove all edges from different color option:
      vector_default.selectAll("path").remove();
      vector_incoming.selectAll("path").remove();
      vector_new.selectAll("path").remove();
      vector_cached.selectAll("path").remove();

      for (j = 0; j < needed_count; j++) {

        d3.json("../packages/package_" + needed_packages[j] + ".json",
            function (error, answer) {

              packages_to_render[answer.id] =
                  filter_packet(answer, viewport);

              // Needed to keep track of cached and not cached packages:
              cached_package_ids.add(answer.id);

              counter += 1;
              if (counter == needed_count) {

                package_legend.selectAll("li").remove();
                vector_packages.selectAll("g").remove();

                var p;
                var package_color;
                for (p in packages_to_render) {

                  if (p in package_colors) {
                    package_color = package_colors[p];
                  } else {
                    package_color = randomColor();
                    package_colors[p] = package_color;
                  }

                  var package_new = vector_packages.append("g");

                  package_new
                      .selectAll('path')
                      .data(packages_to_render[p])
                      .enter()
                      .append("path")
                      .attr('d', epsg3857path)
                      .attr("class", "edges")
                      .style('stroke', package_color)
                      .style('stroke-width', '2pt');

                  // Update package legend
                  package_legend.append("li")
                      .style("padding-left", "1px")
                      .style("border-left", "1em solid " + package_color)
                      .text(p);

                } // END inner for loop (p in packages_to_render)

                // Update statistics:
                d3.select("#total_packages").text(cached_package_ids.size);
                d3.select("#screen_packages").text(needed_count);

              } // END if statement for counter

            }); // END json request for package

      } // END for loop

    } else { // ** SWITCH for no color options ********************************

      // Remove all edges from different color option:
      vector_incoming.selectAll("path").remove();
      vector_new.selectAll("path").remove();
      vector_cached.selectAll("path").remove();
      vector_packages.selectAll("g").remove();
      package_legend.selectAll("li").remove();

      for (j = 0; j < needed_count; j++) {

        d3.json("../packages/package_" + needed_packages[j] + ".json",
            function (error, answer) {

              edges_to_render.push.apply(
                  edges_to_render, filter_packet(answer, viewport));
              counter += 1;

              // Needed to keep track of cached and not cached packages:
              cached_package_ids.add(answer.id);

              if (counter == needed_count) {

                var edges = vector_default
                    .selectAll('path')
                    .data(edges_to_render, function (d) {
                      return d.properties.edge_id;
                    })
                    .attr("class", "edges")
                    .style('stroke', "blue");
                edges
                    .enter()
                    .append("path")
                    .attr('d', epsg3857path)
                    .attr("class", "edges");
                edges
                    .exit()
                    .remove();

                // Update statistics:
                d3.select("#total_packages").text(cached_package_ids.size);
                d3.select("#screen_packages").text(needed_count);

              } // END IF statement

            }); // END json request for package

      } // END for loop

    } // ** END SWITCH for color options **************************************

///////////////////////////////////////////////////////////////////////////////
// Main:                                                                     //
///////////////////////////////////////////////////////////////////////////////
                                                                             //
    vector                                                                   //
        .attr("transform", "translate(" + zoom.translate() + ")");           //
    d3.select("#nprogress .spinner-icon")                                    //
        .style("-moz-animation", "")                                         //
        .style("-ms-animation", "")                                          //
        .style("-o-animation", "")                                           //
        .style("-webkit-animation", "")                                      //
        .style("animation", "");                                             //
    d3.select("#nprogress")                                                  //
        .style("display", "none");                                           //
                                                                             //
  }); // END imp request                                                     //
                                                                             //
  update();                                                                  //
                                                                             //
///////////////////////////////////////////////////////////////////////////////
}