var camera, scene, renderer;

var fov = 55,
imgsize=800,
texture_placeholder,
isUserInteracting = false,
onMouseDownMouseX = 0, onMouseDownMouseY = 0,
lon = 90, onMouseDownLon = 0,
lat = 0, onMouseDownLat = 0,
phi = 0, theta = 0;
var allmeshes = new Array();
//$(window).load(function() {
//	init();
//	animate();
//});

function addImage(filename, yaw, pitch, roll, view) {
	mesh = new THREE.Mesh( new THREE.PlaneGeometry( imgsize, imgsize, 1, 1 ), new THREE.MeshBasicMaterial( { map: THREE.ImageUtils.loadTexture( filename ) } ) );
	distance = (imgsize / 2) / Math.cos((180-view)/2 * Math.PI / 180); 
	mesh.rotation.y = 90-yaw * Math.PI / 180;
	mesh.rotation.z = roll * Math.PI / 180;
	mesh.rotation.x = pitch * Math.PI / 180; 
	phi = (90-pitch) * Math.PI / 180;
	theta = yaw * Math.PI / 180;
	mesh.position.x = distance * Math.sin( phi ) * Math.cos( theta );
	mesh.position.y = distance * Math.cos( phi );
	mesh.position.z = distance * Math.sin( phi ) * Math.sin( theta );

	scene.add( mesh );
	mesh.flipsided = true;
	mesh.scale.x = -1;
	allmeshes.push(mesh);
}

function init(data) {

	var container, mesh;

	container = document.getElementById( 'renderercontainer' );

	camera = new THREE.PerspectiveCamera( fov, window.innerWidth / window.innerHeight, 1, 10000 );

	camera.target = new THREE.Vector3( 0, 0, 0 );

	scene = new THREE.Scene();
	scene.add(camera);

	//--------------------------------------- world XYZ lines
	camera.position = new THREE.Vector3( 1, 1, 1 );
	geom = new THREE.Geometry();
	geom.vertices.push(new THREE.Vertex(new THREE.Vector3(400,0,0)));
	geom.vertices.push(new THREE.Vertex(new THREE.Vector3(-400,0,0)));
	theLine = new THREE.Line( geom, new THREE.LineBasicMaterial( { color: 0xff0000, opacity: 1, linewidth: 7 } ) );
	scene.add(theLine);
	
	geom = new THREE.Geometry();
	geom.vertices.push(new THREE.Vertex(new THREE.Vector3(0, 400,0)));
	geom.vertices.push(new THREE.Vertex(new THREE.Vector3(0, -400,0)));
	theLine = new THREE.Line( geom, new THREE.LineBasicMaterial( { color: 0x00ff00, opacity: 1, linewidth: 7 } ) );
	scene.add(theLine);
	
	geom = new THREE.Geometry();
	geom.vertices.push(new THREE.Vertex(new THREE.Vector3(0,0, 400)));
	geom.vertices.push(new THREE.Vertex(new THREE.Vector3(0,0, -400)));
	theLine = new THREE.Line( geom, new THREE.LineBasicMaterial( { color: 0x0000ff, opacity: 1, linewidth: 7 } ) );
	scene.add(theLine);
	
	$.each(data, function(index, item) {
		addImage('/static/img/small/' + item['name'], item['yaw'], item['pitch'], item['roll'], data[0]['view']);
	});

	renderer = new THREE.WebGLRenderer();
	renderer.setSize( window.innerWidth, window.innerHeight - 200);

	container.appendChild( renderer.domElement );

	document.addEventListener( 'mousedown', onDocumentMouseDown, false );
	document.addEventListener( 'mousemove', onDocumentMouseMove, false );
	document.addEventListener( 'mouseup', onDocumentMouseUp, false );
	document.addEventListener( 'mousewheel', onDocumentMouseWheel, false );
	document.addEventListener( 'DOMMouseScroll', onDocumentMouseWheel, false);

}

function onDocumentMouseDown( event ) {

	event.preventDefault();

	isUserInteracting = true;

	onPointerDownPointerX = event.clientX;
	onPointerDownPointerY = event.clientY;

	onPointerDownLon = lon;
	onPointerDownLat = lat;

}

function onDocumentMouseMove( event ) {

	if ( isUserInteracting ) {

		lon = ( onPointerDownPointerX - event.clientX ) * 0.1 + onPointerDownLon;
		lat = ( event.clientY - onPointerDownPointerY ) * 0.1 + onPointerDownLat;

	}
}

function onDocumentMouseUp( event ) {

	isUserInteracting = false;

}

function onDocumentMouseWheel( event ) {

	// WebKit

	if ( event.wheelDeltaY ) {

		fov -= event.wheelDeltaY * 0.05;

	// Opera / Explorer 9

	} else if ( event.wheelDelta ) {

		fov -= event.wheelDelta * 0.05;

	// Firefox

	} else if ( event.detail ) {

		fov += event.detail * 1.0;

	}

	camera.projectionMatrix = THREE.Matrix4.makePerspective( fov, window.innerWidth / window.innerHeight, 1, 1100 );
	render();

}

function animate() {

	requestAnimationFrame( animate );
	render();

}

function render() {

	lat = Math.max( - 85, Math.min( 85, lat ) );
	phi = ( 90 - lat ) * Math.PI / 180;
	theta = lon * Math.PI / 180;
//	$.each(allmeshes, function(index, item) {
//		item.rotation.y += 0.01;
//	});
	camera.target.x = 500 * Math.sin( phi ) * Math.cos( theta );
	camera.target.y = 500 * Math.cos( phi );
	camera.target.z = 500 * Math.sin( phi ) * Math.sin( theta );

	camera.lookAt( camera.target );

	renderer.render( scene, camera );

}
