var attempt = 4; // Variable to count number of attempts.
// Below function Executes on click of login button.
function validate(){
var username = document.getElementById("username").value;
var password = document.getElementById("password").value;
window.location.href = "file:///C:\paywall.html";
// window.location.href("file:///C:\Users\User\Project5\paywall.html");
// location.replace("file:///C:\Users\User\Project5\paywall.html");
// location.replace("https://www.w3schools.com");
// window.location.replace('C:/Users/User/Project5/paywall.html');
// window.location.href = 'C:/Users/User/Project5/paywall.html';
// window.location.assign("C:/Users/User/Project5/paywall.html");
// window.location.replace("C:/Users/User/Project5/paywall.html");
// window.location.replace = 'C:/Users/User/Project5/paywall.html';
// window.location.replace = 'C:/Users/User/Project5/paywall.html';
// window.location.href = 'C:/Users/User/Project5/paywall.html';
if ( username == "facerek" && password == "1234"){
alert ("Login successfully");
// location.href = 'C:/Users/User/Project5/paywall.html';
return false;
}
else{
attempt --;// Decrementing by one.
alert("You have entered Invalid Username or Pasword; Please retry; You have "+attempt+" attempts left.");
// Disabling fields after 4 attempts.
if( attempt == 0){
document.getElementById("username").disabled = true;
document.getElementById("password").disabled = true;
document.getElementById("submit").disabled = true;
return false;
}
}
}