// Below function Executes on click of login button.

function validate(){

var username = document.getElementById("username").value;
var password = document.getElementById("password").value;

if (username == "facerek" && password == "1234"){
	document.location.assign('https://project5.onrender.com/image-classify.html');
        alert("location.assign done");	
	document.location.replace('https://project5.onrender.com/image-classify.html');
        alert("location.replace done");
	document.location.href('https://project5.onrender.com/image-classify.html');
        alert("location.href done");
	alert ("Login successfully");
        alert("In Validate signin.js now going returning");
	return false;
}
else{
	alert("You have entered Invalid Username or Pasword; Please Retry");
	return false;
}
}