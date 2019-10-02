// var attempt = 4; // Variable to count number of attempts.

// Below function Executes on click of login button.

function validate(){

var username = document.getElementById("username").value;
var password = document.getElementById("password").value;

if ( username == "facerek" && password == "1234"){
	location.replace("https://project5.onrender.com/image-classify.html");
	alert ("Login successfully");
	location.replace("https://project5.onrender.com/image-classify.html");
	return false;
}
else{
	alert("You have entered Invalid Username or Pasword; Please Retry");
//	attempt --;// Decrementing by one.
// 	Disabling fields after 4 attempts.
//	if( attempt == 0){
//		document.getElementById("username").disabled = true;
//		document.getElementById("password").disabled = true;
//		document.getElementById("submit").disabled = true;
//	}
	return false;
}
}