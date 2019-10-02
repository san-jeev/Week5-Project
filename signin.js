// Below function Executes on click of login button.

function validate(){

var username = document.getElementById("username").value;
var password = document.getElementById("password").value;

if (username == "facerek" && password == "1234"){
	location.replace("https://project5.onrender.com/image-classify.html");
	alert ("Login successfully");
	location.href("https://project5.onrender.com/image-classify.html");
	return true;
}
else{
	alert("You have entered Invalid Username or Pasword; Please Retry");
	return false;
}
}