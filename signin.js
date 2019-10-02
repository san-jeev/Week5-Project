// Below function Executes on click of login button.

function validate(){

var username = document.getElementById("username").value;
var password = document.getElementById("password").value;

if (username == "facerek" && password == "1234"){
	setTimeout(function(){document.location.href = "https://project5.onrender.com/image-classify.html"},500);
	alert ("Login successfully");
	return false;
}
else{
	setTimeout(function(){document.location.href = "https://project5.onrender.com/index.html"},500);
	alert("You have entered Invalid Username or Pasword; Please Retry");
	return false;
}
}