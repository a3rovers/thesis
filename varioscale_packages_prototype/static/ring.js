function Point(x,y)
{
    this.x = x;
    this.y = y;
};

function RingCreator()
{
    this.primitives = {};
    this.rings = {};
    this.nodeStars = {};
    this.visitsToMake = {};
    this.lookupEdges = [];
    this.totalVisitCount = 0;
    this.hasFailed = false;
    this.toBeProcessed = {};
    this.clippedEdges = {};
	this.allEdgeIds = {};
    this.edgeDirection = {};
}

RingCreator.prototype.setQueryWindow = function (queryWindow)
{
    this.bbox = queryWindow;
}

RingCreator.prototype.setPrimitives = function(obj)
{
    this.primitives = obj;
}

/*
RingCreator.prototype.edgeLength = function()
{
    var nr = 0;
    for (var i in primitives.edges)
    {
        nr += 1;
    }
    return nr;
}


RingCreator.prototype.faceLength = function()
{
    var nr;
    for (var i in primitives.faces)
    {
        nr += 1;
    }
    return nr;
}
*/

RingCreator.prototype.formRings = function()
{
    this.obtainClippedEdges();
    this.obtainNodeStars();
    this.obtainEdgeEdgeReferences();
	this.obtainRings();
}

RingCreator.prototype.clippedEdgesAsJson = function()
{
    var result = new Array();
    for (var edgeId in this.clippedEdges)
    {
        var cur = this.clippedEdges[edgeId];
        result.push(
            {
                type: "Feature",
    			geometry: {
    			    type: "LineString",
    				coordinates: cur.geometry.coordinates.slice()
    				},
				properties: {}
		    }
        )
    }
    return result;
}
// consider cohen sutherland and use just the first vertex over the edge as well
// http://en.wikipedia.org/wiki/Cohen%E2%80%93Sutherland_algorithm

RingCreator.prototype.obtainClippedEdges = function()
{
	var N;
	var x, y;
	var toClip = new Array();
	var boundaryNodes = new Array();
    var bbox = this.bbox;
    var primitives = this.primitives;
    var allEdgeIds = this.allEdgeIds;
    var clippedEdges = this.clippedEdges;
    var center = new Array( ((bbox.right - bbox.left)/2) + bbox.left,
    							  ((bbox.top - bbox.bottom)/2) + bbox.bottom);
	// add nodes on corners
	boundaryNodes.push(
	{angle: fowlerAngle(center, new Array(bbox.left, bbox.bottom)),
	 point: new Point(bbox.left, bbox.bottom)}
	);
	boundaryNodes.push(
	{angle: fowlerAngle(center, new Array(bbox.left, bbox.top)),
	 point: new Point(bbox.left, bbox.top)}
	);
	boundaryNodes.push(
	{angle: fowlerAngle(center, new Array(bbox.right, bbox.bottom)),
	 point: new Point(bbox.right, bbox.bottom)}
	);
	boundaryNodes.push(
	{angle: fowlerAngle(center, new Array(bbox.right, bbox.top)),
	 point: new Point(bbox.right, bbox.top)}
	);
	// Find edges that have vertices outside/on queryWindow
	// Those need to be clipped
	var maxEdgeId = -1;
	var nrOutside = 0;
	var nrInside = 0;
    for (var edgeId in primitives.edges)
    {
    	allEdgeIds[edgeId] = undefined;
    	var outside = false;
    	if (parseInt(edgeId) > maxEdgeId)
    	{
    		maxEdgeId = parseInt(edgeId);
    	}
    	// bottom left
    	x = primitives.edges[edgeId].bbox[0]; // mbr.left;
    	y = primitives.edges[edgeId].bbox[1]; //mbr.bottom;
    	if (!contains(bbox, x, y))
    	{
    		// trace("I " + bbox + " "+ x + "outside" + y)
    		outside = true;
    	}
    	// top right
    	x = primitives.edges[edgeId].bbox[3]; //mbr.right;
    	y = primitives.edges[edgeId].bbox[4]; //mbr.top;
    	if (!contains(bbox, x, y))
    	{
    		// trace("I " + bbox + " "+ x + "outside" + y)
    		outside = true;
    	}
    	if (outside)
    	{
    		nrOutside += 1;
    	}
    	else
    	{
    		nrInside += 1;
    	}

    	
    	if (outside)
    	{
        	toClip.push(edgeId);
    	}
    	else
    	{
    		clippedEdges[edgeId] = {
    			leftFaceId: primitives.edges[edgeId].leftFaceId,
    			rightFaceId: primitives.edges[edgeId].rightFaceId,
    			startNodeId: primitives.edges[edgeId].startNodeId,
    			endNodeId: primitives.edges[edgeId].endNodeId,
    			draw: true,
    			impLow: primitives.edges[edgeId].impLow,
    			impLow: primitives.edges[edgeId].impHigh,
    			geometry: {
    				coordinates: primitives.edges[edgeId].geometry.coordinates.slice()
    			}
    		}
    	}
    }
    
    
	// make clipped edges a bit more distinguisable from the rest
    maxEdgeId += 1000000;
    // console.log("I out: "+nrOutside+ " in: " + nrInside + ", edges with id# >= " + maxEdgeId +" are clipped")

    // Do clipping and produce edge parts that are inside
	var edgeParts = new Object();
    var M = toClip.length;
    for (var j = 0; j < M; j++)
    {
    	var edgeId = toClip[j];
    	edgeParts[edgeId] = new Array();
    	N = primitives.edges[edgeId].geometry.coordinates.length;
    	for (var k = 0; k < (N - 1); k++)
    	{
    	    var x0, y0;
			var x1, y1;	
    		x0 = primitives.edges[edgeId].geometry.coordinates[k][0];
    		y0 = primitives.edges[edgeId].geometry.coordinates[k][1];
    		x1 = primitives.edges[edgeId].geometry.coordinates[k + 1][0];
    		y1 = primitives.edges[edgeId].geometry.coordinates[k + 1][1];
    		if ((Math.max(x0, x1) < bbox.left) || 
    			(Math.max(y0, y1) < bbox.bottom) || 
    			(Math.min(x0, x1) > bbox.right) || 
    			(Math.min(y0, y1) > bbox.top)) 			// segment is completely outside
    		{
    			// nothing here 
    		}

    		else if (bbox.left < x0 && x0 < bbox.right &&
        			 bbox.left < x1 && x1 < bbox.right &&
        			 bbox.bottom < y0 && y0 < bbox.top &&
        			 bbox.bottom < y1 && y1 < bbox.top) // segment is completely inside
    		{
    			var newStartPoint = new Point(x0, y0);
    			var newEndPoint = new Point(x1, y1);
    			var K = edgeParts[edgeId].length;
    			if (K == 0)
    			{
    				edgeParts[edgeId][K] = new Array();
    				edgeParts[edgeId][K].push(newStartPoint);
    				edgeParts[edgeId][K].push(newEndPoint);
    			} 
    			else
    			{
    				var lastPoint = edgeParts[edgeId][K-1][edgeParts[edgeId][K-1].length-1];
    				if (lastPoint.x == newStartPoint.x && lastPoint.y == newStartPoint.y)
    				{
    					edgeParts[edgeId][K-1].push(newEndPoint);
    				}
    				else
    				{
    					edgeParts[edgeId][K] = new Array();
        				edgeParts[edgeId][K].push(newStartPoint);
        				edgeParts[edgeId][K].push(newEndPoint);
    				}
    			}
    		}
    		else // segment on boundary -> clip
    		{
        		var dx = (x1 - x0);
        		var dy = (y1 - y0);
        		var u0 = 0.0;
        		var u1 = 1.0;
        		var P = new Array(-dx, dx, -dy, dy);
        		var q = new Array((x0 - bbox.left), (bbox.right - x0), 
        								(y0 - bbox.bottom), (bbox.top - y0));
        		var valid = true;
        		for (var i = 0; i < 4; i++)
        		{
        			var pi = P[i];
        			var qi = q[i];
        			if (pi == 0)
        			{
        				if (qi < 0.0)
        				{
        					valid = false;
        					break;
        				}
        			}
        			else
        			{
        				var r = qi / pi;
        				if (pi < 0.0)
        				{
        					if (r > u1)
        					{
        						valid = false;
        						break;
        					}
        					if (r > u0)
        					{
        						u0 = r
        					}
        				}
        				else
        				{
        					if (r < u0)
        					{
        						valid = false;
        						break;
        					}
        					if (r < u1)
        					{
        						u1 = r;
        					}
        				}
        			}
        		}
        		if (valid)
        		{
        			var newStartPoint = new Point( ((u0 * dx) + x0), ((u0 * dy) + y0) );
        			var newEndPoint = new Point( ((u1 * dx) + x0), ((u1 * dy) + y0) );
        			var qw = new Array(bbox.left, bbox.bottom, bbox.right, bbox.top);
        			for (var i = 0; i < 4; i ++)
        			{
        				if (qw[i] == newStartPoint.x || qw[i] == newStartPoint.y)
        				{
        					var node = new Object();
        					node.angle = fowlerAngle(center, 
        											 new Array(newStartPoint.x, newStartPoint.y));
        					node.point = newStartPoint;
        					boundaryNodes.push(node);
        					break;
        				}
        			}
        			for (var i = 0; i < 4; i ++)
        			{
        				if (qw[i] == newEndPoint.x || qw[i] == newEndPoint.y)
        				{
        					var node = new Object();
        					node.angle = fowlerAngle(center, 
        											 new Array(newEndPoint.x, newEndPoint.y));
        					node.point = newEndPoint;
        					boundaryNodes.push(node);
        					break;
        				}
        			}
        			// TODO: edge on clipping window -> would be nice if we can color that one differently
        			// ...
        			if (newStartPoint.x == newEndPoint.x && newStartPoint.y == newEndPoint.y)
        			{
        				console.log("W edge clipping collapse edge to point");
        			}
        			var K = edgeParts[edgeId].length;
        			if (K == 0)
        			{
        				edgeParts[edgeId][K] = new Array();
        				edgeParts[edgeId][K].push(newStartPoint);
        				edgeParts[edgeId][K].push(newEndPoint);
        			} 
        			else
        			{
        				var lastPoint = edgeParts[edgeId][K-1][edgeParts[edgeId][K-1].length-1];
        				if (lastPoint.x == newStartPoint.x && lastPoint.y == newStartPoint.y)
        				{
        					edgeParts[edgeId][K-1].push(newEndPoint);
        				}
        				else
        				{
        					edgeParts[edgeId][K] = new Array();
	        				edgeParts[edgeId][K].push(newStartPoint);
	        				edgeParts[edgeId][K].push(newEndPoint);
        				}
        			}
        		};
    		}
    	}
    }
    // Transform parts into edges
    for (var edgeId in edgeParts)
    {
    	for (var part = 0; part < edgeParts[edgeId].length; part++)
    	{
    		maxEdgeId += 1;
    		allEdgeIds[String(maxEdgeId)] = undefined;
    		
    		clippedEdges[String(maxEdgeId)] = {
    			leftFaceId: primitives.edges[edgeId].leftFaceId,
    			rightFaceId: primitives.edges[edgeId].rightFaceId,
    			startNodeId: edgeParts[edgeId][part][0].x+"::"+edgeParts[edgeId][part][0].y,
    			endNodeId: edgeParts[edgeId][part][edgeParts[edgeId][part].length-1].x+"::"+edgeParts[edgeId][part][edgeParts[edgeId][part].length-1].y,
    			draw: true,
    			impLow: primitives.edges[edgeId].impLow,
    			geometry: {
    				coordinates: new Array()
    			}
    		}
    		
    		if (part == 0) // first part
    		{
        		// detect whether start node is not clipped, or is clipped
				if (edgeParts[edgeId][part][0].x == primitives.edges[edgeId].geometry.coordinates[part][0] &&
	        		edgeParts[edgeId][part][0].y == primitives.edges[edgeId].geometry.coordinates[part][1])
	        	{
	        		//primitives.edges[String(maxEdgeId)].startNodeId = primitives.edges[edgeId].startNodeId;
	        		clippedEdges[String(maxEdgeId)].startNodeId = primitives.edges[edgeId].startNodeId;
	        	}	
    		}
        	if (part == edgeParts[edgeId].length - 1) // last part
        	{
        		// detect whether end node is not clipped, or is clipped
	        	var LL = edgeParts[edgeId][part].length - 1;
	        	var NN = primitives.edges[edgeId].geometry.coordinates.length;
				if (edgeParts[edgeId][part][LL].x == primitives.edges[edgeId].geometry.coordinates[NN-1][0] &&
	        		edgeParts[edgeId][part][LL].y == primitives.edges[edgeId].geometry.coordinates[NN-1][1])
	        	{
	        		//primitives.edges[String(maxEdgeId)].endNodeId = primitives.edges[edgeId].endNodeId;
	        		clippedEdges[String(maxEdgeId)].endNodeId = primitives.edges[edgeId].endNodeId;
	        	}
        	}
    		for (var k = 0; k < edgeParts[edgeId][part].length; k++)
    		{
    			//primitives.edges[String(maxEdgeId)].geometry.coordinates.push(new Array(edgeParts[edgeId][part][k].x, edgeParts[edgeId][part][k].y))
    			clippedEdges[String(maxEdgeId)].geometry.coordinates.push(new Array(edgeParts[edgeId][part][k].x, edgeParts[edgeId][part][k].y))
    		}
    	}
    	delete allEdgeIds[edgeId];
    }
    // sort boundaryNodes
    boundaryNodes.sort(sortByAngle);
	for (var j = 0; j < boundaryNodes.length; j++)
	{
		maxEdgeId = maxEdgeId + 1;
		this.clippedEdges[String(maxEdgeId)] = {
			geometry: {
				coordinates: new Array()
			},
			leftFaceId: undefined,
			rightFaceId: primitives.universeFaceId,
			impLow: -1,
			impHigh: -1
		}
		var jj = (j + 1) % boundaryNodes.length;
		this.clippedEdges[String(maxEdgeId)].geometry.coordinates.push(new Array(boundaryNodes[j].point.x, boundaryNodes[j].point.y))
		this.clippedEdges[String(maxEdgeId)].geometry.coordinates.push(new Array(boundaryNodes[jj].point.x, boundaryNodes[jj].point.y))
		this.clippedEdges[String(maxEdgeId)].startNodeId = boundaryNodes[j].point.x+"::"+boundaryNodes[j].point.y
		this.clippedEdges[String(maxEdgeId)].endNodeId = boundaryNodes[jj].point.x+"::"+boundaryNodes[jj].point.y
		this.clippedEdges[String(maxEdgeId)].draw = false;
	}
}

RingCreator.prototype.obtainNodeStars = function()
{
    var clippedEdges = this.clippedEdges;
    //var edgeDirection = this.edgeDirection;
    //var visitsToMake = this.visitsToMake;
    //var totalVisitCount = this.totalVisitCount;
    //var nodeStars = this.nodeStars;
    for (var edgeId in clippedEdges)
    {
    	// Direction
    	this.edgeDirection[edgeId] = {}
        this.edgeDirection[edgeId].nextLeftId = undefined;
        this.edgeDirection[edgeId].nextLeftDirection = undefined;
        this.edgeDirection[edgeId].nextRightId = undefined;
        this.edgeDirection[edgeId].nextRightDirection = undefined;
        
        this.visitsToMake[edgeId] = 2;
        this.totalVisitCount += 2;
        var startNodeId = clippedEdges[edgeId].startNodeId;
        var endNodeId = clippedEdges[edgeId].endNodeId;
        if (!this.nodeStars.hasOwnProperty(startNodeId))
        {
            this.nodeStars[startNodeId] = [];
        }
        if (!this.nodeStars.hasOwnProperty(endNodeId))
        {
            this.nodeStars[endNodeId] = [];
        }
        // Outgoing edge
        this.nodeStars[startNodeId].push( {id: edgeId,
                                      direction: 1,
                                      angle: -fowlerAngle(clippedEdges[edgeId].geometry.coordinates[0],
                                                          clippedEdges[edgeId].geometry.coordinates[1]) } );
        // Incoming edge
        var N = clippedEdges[edgeId].geometry.coordinates.length;
        this.nodeStars[endNodeId].push( {id: edgeId,
                                    direction: -1,
                                    angle: -fowlerAngle(clippedEdges[edgeId].geometry.coordinates[N - 1],
                                                        clippedEdges[edgeId].geometry.coordinates[N - 2]) } );
    }
    // Sort the nodeStars by angle with the sortByAngle function
    for (var nodeId in this.nodeStars)
    {
        this.nodeStars[nodeId].sort(sortByAngle);
    }
}

RingCreator.prototype.obtainEdgeEdgeReferences = function()
{
    var nodeStars = this.nodeStars;
//    var edgeDirection = this.edgeDirection;
    
    for (var nodeId in nodeStars)
    {
        var N = nodeStars[nodeId].length;
        for (var i = 0; i < N; i++)
        {
            var j = (i + 1) % N;
            var currentEdgeId = nodeStars[nodeId][i].id;
            var currentDirection = nodeStars[nodeId][i].direction;
            var nextEdgeId = nodeStars[nodeId][j].id;
            var nextDirection = nodeStars[nodeId][j].direction;
            
            // Direction
            switch (currentDirection)
            {
                case -1:
                    this.edgeDirection[currentEdgeId].nextLeftId = nextEdgeId;
                    this.edgeDirection[currentEdgeId].nextLeftDirection = nextDirection;
                    break;
                case 1:
                    this.edgeDirection[currentEdgeId].nextRightId = nextEdgeId;
                    this.edgeDirection[currentEdgeId].nextRightDirection = nextDirection;
                    break;
            }
        }
    }
}


RingCreator.prototype.obtainRings = function()
{
//    var rings = this.rings;
    var primitives = this.primitives;
//    var totalVisitCount = this.totalVisitCount;
    
    for (var faceId in primitives.faces)
    {
        this.rings[faceId] = [];
    }
    while (this.totalVisitCount > 0)
    {
    	this.visitEdges();
    }
}

RingCreator.prototype.visitEdges = function()
{
	/*
	 * Apparently holes are drawn alright by the flash drawing api, even 
	 * if you do not give the rings in the correct order.
	 * Therefore, we now skip the signed area calculation (which is expensive
	 * if the number of coordinates goes up... as currently still is the case)
	 */
	var clippedEdges = this.clippedEdges;
	var primitives = this.primitives;
	
	var lookupEdges = []; // ???
	
	var edgeId, startEdgeId, nextEdgeId, faceId;
    var nextDirection, direction, N;
    var impLow, impHigh;
    var result = new Array();
    var first = true;
    for (edgeId in this.visitsToMake)
    {
		break;
    }
	faceId = undefined;
    startEdgeId = edgeId;
    // signedArea = 0.0;
    var maxImpLow = -1.0;
    var maxImpHigh = -1.0;
    var lookupEdgeId = edgeId;
    // faceId = clippedEdges[edgeId].leftFaceId;
    //console.log(this.rings);
    while (true)
    {
        if (first != true && startEdgeId == edgeId)
        {
			if (!(faceId == undefined) && faceId != primitives.universeFaceId && this.rings.hasOwnProperty(faceId) )
			{
				this.rings[faceId].push(result);
	            if (primitives.faces[faceId].featureClass == undefined)
	            {
	            	console.log('W ... faceId found, without feature class, ring starts at edge # ' + startEdgeId)
	            	console.log('W ... ' + primitives.faces[faceId].impLow + ' ' + primitives.faces[faceId].impHigh);
	            	lookupEdges.push(startEdgeId);
	            	toBeProcessed[faceId] = result;
	            }
			}
			else if (faceId == undefined)
			{
				console.log('W ... undefined faceId found, ring starts at edge # ' + startEdgeId)
				lookupEdges.push(startEdgeId);
			}
			// FIXME: universe face id is not strange that it is not there...
			else
			{
				console.log('W ... not in faces at the moment ' + faceId)
			}
            return;
        }
        else if (first == true)
        {
        	first = false;
        	if (this.edgeDirection[edgeId].nextLeftId != undefined)
    		{
    			if (faceId == undefined && (clippedEdges[edgeId].leftFaceId in this.primitives.faces))
            	{
                	faceId = clippedEdges[edgeId].leftFaceId;
            	}
    			direction = 1;
    		}
	        else if (this.edgeDirection[edgeId].nextRightId != undefined)
	        {
	        	//faceId = clippedEdges[edgeId].rightFaceId;
	        	if (faceId == undefined && (clippedEdges[edgeId].rightFaceId in this.primitives.faces))
	        	{
	            	faceId = clippedEdges[edgeId].rightFaceId;
	        	}
	        	direction = -1;
	        }
	        else
	        {
				direction = 0;
	        }
        }
   		impLow = parseFloat(clippedEdges[edgeId].impLow); 
   		impHigh = parseFloat(clippedEdges[edgeId].impHigh);

        this.visitsToMake[edgeId] -= 1;
        this.totalVisitCount -= 1;
        if (this.visitsToMake[edgeId] == 0)
        {
            delete this.visitsToMake[edgeId];
        }
        N = clippedEdges[edgeId].geometry.coordinates.length;
        if (direction > 0)
        {
            nextEdgeId = this.edgeDirection[edgeId].nextLeftId;
            nextDirection = this.edgeDirection[edgeId].nextLeftDirection;
            
            if (faceId == undefined && (clippedEdges[edgeId].leftFaceId in this.primitives.faces))
        	{
            	faceId = clippedEdges[edgeId].leftFaceId;
        	}
            /*
        	if (impLow > maxImpLow)
        	{
        		faceId = clippedEdges[edgeId].leftFaceId;
        		maxImpLow = impLow;
        		lookupEdgeId = edgeId;
        	}
        	*/
            this.edgeDirection[edgeId].nextLeftId = undefined;
            result.push( [edgeId, true] ); // [edgeId, correctDirection]
        }
        else if (direction < 0)
        {
            nextEdgeId = this.edgeDirection[edgeId].nextRightId;
            nextDirection = this.edgeDirection[edgeId].nextRightDirection;
            
            if (faceId == undefined && (clippedEdges[edgeId].rightFaceId in this.primitives.faces))
        	{
            	faceId = clippedEdges[edgeId].rightFaceId;
        	}
        	/*
            if (faceId === undefined && this.rings.hasOwnProperty(clippedEdges[edgeId].rightFaceId))
        	{
            	faceId = clippedEdges[edgeId].rightFaceId;
        	}
        	*/
            /*
        	if (impLow > maxImpLow)
        	{
        		faceId = clippedEdges[edgeId].rightFaceId;
        		maxImpLow = impLow;
        		lookupEdgeId = edgeId;
        	}
        	*/
            this.edgeDirection[edgeId].nextRightId = undefined;
            result.push( [edgeId, false] ); // [edgeId, correctDirection]
        }
        else
        {
            throw new Error("No edge to continue - continueRing. Started at edge: " + startEdgeId);
            return;
        }
        edgeId = nextEdgeId;
        direction = nextDirection;
    }
}

RingCreator.prototype.myFaces = function()
{
    var features = [];
    for (var faceId in this.primitives.faces)
    {
//    	var mc:MovieClip = scene.createEmptyMovieClip("face" + faceId, scene.getNextHighestDepth())
    	
		// mc.onRollOver = Delegate.create(this, faceToggle, faceId, 0xFFFF00)
    	// mc.onRollOut = Delegate.create(this, faceToggle, faceId, styles[primitives.faces[faceId].featureClass])
    	
		var face_rings = [];
		/*
		var colour = styles[klass]
		
		if colour == undefined
		{
			mc.beginFill(0xFFFF00, 100);	
		}
		else
		{
        	mc.beginFill(colour, 60);
		}
		*/
        
        var P = this.rings[faceId].length;
        for (var p = 0; p < P; p++)
        {
            var ring = [];
        	var firstCoord = true;
            var L = this.rings[faceId][p].length;
            for (var i = 0; i < L; i++)
            {
                var edgeId = this.rings[faceId][p][i][0];
                var correctDirection = this.rings[faceId][p][i][1];
                // pop last coordinate of ring
                if (ring != [])
                {
                    ring.pop();
                }
                // add coordinates of this polyline to ring in correct direction
                var g = this.clippedEdges[edgeId].geometry.coordinates.slice();                
                if (correctDirection == false) // walk backwards
                {
                    g.reverse();
                }
                // this comes as close to extend() as possible as far as I know
                // will only work with small arrays (i.e. < 150k elements)
                ring.push.apply(ring, g); 
                //ring = ring.concat(g); 
            }
            face_rings.push(ring);
        }
        f = {
            type: "Feature",
			geometry: {
			    type: "Polygon", // FIXME: this can be MultiPolygon after clipping
				coordinates: face_rings
				},
			properties: {klass: this.primitives.faces[faceId].featureClass}
		};
		features.push(f)
//        mc.endFill();
    }
    return features;
}
   
// FIXME: global scope of these functions!!!

/**
 * sortByAngle
 *
 * Return values are as follows for a custom sortBy method:
 * -1, if A should appear before B in the sorted sequence
 * 0, if A equals B
 * 1, if A should appear after B in the sorted sequence
 */
sortByAngle = function(one, other)
{
    if (one.angle < other.angle) 
    {
        return -1;
    }
    else if (one.angle > other.angle) 
    {
        return 1;
    }
    else
    {
        return 0;
    }
}


contains = function (rectangle, x, y)
{
	if (rectangle.left < x &&
		x < rectangle.right &&
		rectangle.bottom < y &&
		y < rectangle.top)
	{
		return true;
	}
	else
	{
		return false;
	}
}

area = function (bbox)
{
	return (bbox.right - bbox.left) * (bbox.top - bbox.bottom)
}
    
intersects = function(one, other)
{
	if (other.bottom > one.top || other.top < one.bottom || other.right < one.left || other.left > other.right)
	{
		// disjoint
		return false;
	} 
	else
	{
		// must be an intersection
		return true;
	}
}

intersection = function(one, other)
{
	var left = Math.max(one.left, other.left)
	var right = Math.min(one.right, other.right)

	var bottom = Math.max(one.bottom, other.bottom)
	var top = Math.min(one.top, other.top)
	
	return {left:left, right:right, bottom:bottom, top:top}
}

fowlerAngle = function(one, other)
{
    var x0, y0, x1, y1;
    var dx, dy, adx, ady;
    var code = 0;
    
    x0 = one[0];
    y0 = one[1];
    x1 = other[0];
    y1 = other[1];
    
    dx = x1 - x0;
    dy = y1 - y0;
    
    
    if (dx < 0)
    {
        adx = -dx;
    }
    else
    {
        adx = dx;
    }
    
    if (dy < 0)
    {
        ady = -dy;
    }
    else
    {
        ady = dy;
    }
    
    if (adx <= 0.001 && ady <= 0.001)
    {
    	console.log("W small dx and dy for angle; location: "+ x0 + " " + y0 + "; " + x1 + " " + y1);
    }
    
    if (adx == 0 && ady == 0) 
    {
    	console.log("E angle not defined, fowlerAngle encountered two points at the same location; location: "+ x0 + " " + y0 + "; " + x1 + " " + y1);
    	// throw new Error("fowlerAngle undefined, because points are on same location");
    	return undefined;
    }
    
    if (adx < ady)
    {
        code = 1;
    }
        
    if (dx < 0)
    {
        code += 2;
    }
    if (dy < 0)
    {
        code += 4;
    }

    switch(code)
    {
        case 0: // [0, 45]
            switch(dx)
            {
                case 0:
                    return 0;
                default:
                    return ady / adx;
            }
        case 1: // ( 45, 90]
            return 2.0 - (adx/ady);
        case 3: // ( 90,135)
            return 2.0 + (adx/ady);
        case 2: // [135,180]
            return 4.0 - (ady/adx);
        case 6: // (180,225]
            return 4.0 + (ady/adx);
        case 7: // (225,270)
            return 6.0 - (adx/ady);
        case 5: // [270,315)
            return 6.0 + (adx/ady);
        case 4: // [315,360)
            return 8.0 - (ady/adx);
    }
}
