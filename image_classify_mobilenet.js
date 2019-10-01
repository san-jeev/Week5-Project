let net;

async function app(img) {
	console.log('Loading mobilenet..');
	// alert('Loading mobilenet..');
	
	// Load the model.
	net = await mobilenet.load();
	console.log('Sucessfully loaded MobileNet model');

	// Make a prediction through the model on the image.
	const imgEl = document.getElementById(img);

	// classify the image and predict 
	const result = await net.classify(imgEl);
	//log the prediction results on console
	console.log(result);

	//	set up to diaplay the prediction results on webpage
	document.getElementById("custom-text-results-1").innerHTML = "ClassName:  " + result[0].className + ";          " + "Probability: " + result[0].probability;
	document.getElementById("custom-text-results-2").innerHTML = "ClassName:  " + result[1].className + ";          " + "Probability: " + result[1].probability;
	document.getElementById("custom-text-results-3").innerHTML = "ClassName:  " + result[2].className + ";          " + "Probability: " + result[2].probability;
	document.getElementById("custom-text-done").innerHTML = "Done 🥳. Please refresh and proceed !!";
}

// app();