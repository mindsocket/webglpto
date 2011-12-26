function loadPano(filename) {
	$.getJSON("/load/" + filename, function(data) {
		console.log(data);
		init(data);
		animate();
//		var items = [];
//		$.each(data, function(i, item) {
//			//
//        });     
		//
	});

}

$(function() {
	// Set up pano list
	$.getJSON("/list", function(data) {
		console.log(data);
		var items = [];
		$.each(data, function(i, item) {
			items.push("<option value\"" + item + "\">" + item + "</option>");
        });     
		$("#panolist").append(items.join(''));

	});
	
	// Pano load on selection change
	$("#panolist").change(function() {
		var filename = $(this).find("option:selected:first").val();
		if (filename != '') {
			console.log(filename);
			loadPano(filename);
		}
	});
});
