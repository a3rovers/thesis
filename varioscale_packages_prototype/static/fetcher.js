fetcher = {
    init: function ()
    {
        last_bbox = current_bbox();
        var bottomLeft = [last_bbox[0], last_bbox[1]];
        var topRight = [last_bbox[2], last_bbox[3]];
        enable_progressbar();
        var nr = d3.select("#optimalCount").node().value;
        d3.json("/_d/init/"+nr+"/" + bottomLeft[0] + "/" + bottomLeft[1] + "/" + topRight[0] + "/" + topRight[1] + "/", function(error, answer) {
        	if (error) return console.error(error);
        	console.log(answer);
            disable_progressbar();
	        // remove all old elements 
	        vector
	            .selectAll('path')
	            .data([])
	            .exit().remove();
	        /*
	        var epsg3857screen = d3.geo.transform({
	            point: function(px, py) { this.stream.point( 
	                 (px / RESOLUTION) * zoom.scale(),   // + zoom.translate()[0],
	                 (-py / RESOLUTION) * zoom.scale()); // + zoom.translate()[1]); 
	                }
	        });
	        var epsg3857path = d3.geo.path().projection(epsg3857screen);
	        */
	        //last_edges = makeEdgeFeatures(answer);
	        //console.log(answer.edges.features);
	        
	        last_edges = answer.edges.features;
	        last_imp = answer.impSel;
	        vector
	           .selectAll('path')
	           .data(last_edges, function edgeId(d) {return d.properties.edgeId; } )
	           .enter()
	           .append('path')
	           //.attr('d', epsg3857path)
	           .attr("class", function(d) { return "funky edge" + d.properties.edgeId; });
	        
	        vector
	            .attr("transform", "translate(" + zoom.translate() + ")");
	
	        update(); // will take care of setting projection 
        });
    },
    pan: function ()
    {
        var cb = current_bbox();
        var blc = [cb[0], cb[1]];
        var trc = [cb[2], cb[3]];
        var blp = [last_bbox[0], last_bbox[1]];
        var trp = [last_bbox[2], last_bbox[3]];
        last_bbox = cb;
        enable_progressbar();
        var nr = d3.select("#optimalCount").node().value;
        d3.json("/_d/pan/"+nr+"/" + blc[0] + "/" + blc[1] + "/" + trc[0] + "/" + trc[1] + "/" + blp[0] + "/" + blp[1] + "/" + trp[0] + "/" + trp[1] + "/", 
                function(error, answer) {
            disable_progressbar();
            last_imp = answer.impSel;

            d3.select('#myEdgeInfo')
	            .datum(answer.edges.features.length)
	            .text(String);
	        d3.select('#myFaceInfo')
	            .datum(answer.faces.features.length)
	            .text(String);
	        d3.select('#myStepInfo')
	            .datum("-")
	            .text(String);
	        d3.select('#myTotalStepInfo')
	            .datum("-")
	            .text(String);
            
	        console.log("@imp " + answer.impSel);
	        
            var new_edges = answer.edges.features;
            for (var last_idx in last_edges)
            {
                var last_edge = last_edges[last_idx];
                if (last_edge.properties.impLow <= last_imp && last_edge.properties.impHigh > last_imp && box_box_overlaps(cb, last_edge.bbox))
                {
                    new_edges.push(last_edge);
                }
            }
            last_edges = new_edges;
            
            // remove all old elements 
            var edges = vector
                .selectAll('path')
                .data(new_edges, function edgeId(d) {return d.properties.edgeId; });
            
            edges
                .exit()
                .remove();

            // add newly added edges 
            edges
                .enter()
                .append('path');
            
            // update zoom + translate  
            update();
        });
    }

    zoomin: function()
    {
        var cb = current_bbox();
        var blc = [cb[0], cb[1]];
        var trc = [cb[2], cb[3]];
        var blp = [last_bbox[0], last_bbox[1]];
        var trp = [last_bbox[2], last_bbox[3]];
        last_bbox = cb;
        enable_progressbar();
        var nr = d3.select("#optimalCount").node().value;
        var xhr = new XMLHttpRequest();
        var offset = 0;
        xhr.previous_text = '';
        var current = ''
        var prevseq = -1;
        var url = "/_d/zoomin/"+nr+"/" + blc[0] + "/" + blc[1] + "/" + trc[0] + "/" + trc[1] + "/" + blp[0] + "/" + blp[1] + "/" + trp[0] + "/" + trp[1] + "/";
        xhr.open("GET", url, true);
        xhr.onerror = function (e)
        {
            disable_progressbar();
        }
        var stream = "";
	    var streamLen = 0;
        const separator = "\r";
	    xhr.onreadystatechange = function() 
	    {
	        if(xhr.readyState == 2 && xhr.status == 200) {
	            // Connection is ok
	        } 
	        else if(xhr.readyState == 3)
	        { 
	            //Receiving stream 
		        if (streamLen < xhr.responseText.length) 
		        {
		          // console.log(streamLen +"-"+ xhr.responseText.length);
		          var chunk = xhr.responseText.substring(streamLen,xhr.responseText.length);
		          // add to message 
		          stream += chunk;
		          var separatorIndex = stream.indexOf(separator);
		          while (separatorIndex != -1)
		          {
		              var packet = stream.slice(0, separatorIndex);
		              var partial = JSON.parse(packet);
                      console.log(partial.seq + " @" + partial.impSel + " new edges: " + partial.edges.features.length);
		              var visualize = partial.edges.features.slice();
		              for (var i = 0; i < last_edges.length; i++)
		              {
		                  var last_edge = last_edges[i];
		                  if (last_edge.properties.impLow <= partial.impSel && last_edge.properties.impHigh > partial.impSel && box_box_overlaps(cb, last_edge.bbox))
		                  {
		                      visualize.push(last_edge);
		                  }
		              }
		              prog_update(visualize);
		              last_edges = visualize.slice();
		              stream = stream.slice(separatorIndex + 1);
		              separatorIndex = stream.indexOf(separator);
		          }
		      }
		      streamLen = xhr.responseText.length;                     
	      } else if(xhr.readyState == 4) {
	          disable_progressbar();
	      }    
	    };  
        xhr.send();
    }

    zoomout: function()
    {
        var cb = current_bbox();
        var blc = [cb[0], cb[1]];
        var trc = [cb[2], cb[3]];
        var blp = [last_bbox[0], last_bbox[1]];
        var trp = [last_bbox[2], last_bbox[3]];
        last_bbox = cb;
        enable_progressbar();
        var nr = d3.select("#optimalCount").node().value;
        var xhr = new XMLHttpRequest();
        var url = "/_d/zoomout/"+nr+"/" + blc[0] + "/" + blc[1] + "/" + trc[0] + "/" + trc[1] + "/" + blp[0] + "/" + blp[1] + "/" + trp[0] + "/" + trp[1] + "/";
        xhr.open("GET", url, true);
        xhr.onerror = function (e)
        {
            disable_progressbar();
        }
        var stream = "";
        var streamLen = 0;
        const separator = "\r";
        xhr.onreadystatechange = function() {
          if(xhr.readyState == 2 && xhr.status == 200) {
             // Connection is ok
          } else if(xhr.readyState == 3){ 
              // Receiving stream 
              if (streamLen < xhr.responseText.length) {
                  // console.log(streamLen +"-"+ xhr.responseText.length);
                  var chunk = xhr.responseText.substring(streamLen, xhr.responseText.length);
                  // add to message 
                  stream += chunk;
                  var separatorIndex = stream.indexOf(separator);
                  while (separatorIndex != -1)
                  {
                      var packet = stream.slice(0, separatorIndex);
                      var partial = JSON.parse(packet);
                      console.log(partial.seq + " @" + partial.impSel + " new edges: " + partial.edges.features.length);
                      var visualize = partial.edges.features.slice();
                      for (var i = 0; i < last_edges.length; i++)
                      {
                          var last_edge = last_edges[i];
                          if (last_edge.properties.impLow <= partial.impSel && last_edge.properties.impHigh > partial.impSel && box_box_overlaps(cb, last_edge.bbox))
                          {
                              visualize.push(last_edge);
                          }
                      }
                      prog_update(visualize);
                      last_edges = visualize.slice();
                      stream = stream.slice(separatorIndex + 1);
                      separatorIndex = stream.indexOf(separator);
                  }
              }
              streamLen = xhr.responseText.length;                     
          } else if(xhr.readyState == 4) {
              disable_progressbar();
          }    
        };  
        xhr.send();
    }
}
