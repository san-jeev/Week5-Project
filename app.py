# -*- coding: utf-8 -*-

from scripts import tabledef
from scripts import forms
from scripts import helpers
from flask import Flask, redirect, url_for, render_template, request, session, jsonify, Response, flash
import json
import sys
import os
import stripe

import pickle
import face_recognition
import cv2
import numpy as np
from werkzeug.utils import secure_filename
from flask import send_from_directory
import time

app = Flask(__name__)
app.secret_key = os.urandom(12)  # Generic key for dev purposes only

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

#Create a video instance
video = cv2.VideoCapture(0)
#Path to known images (companys database)
KNOWN_IMAGES_PATH = './static/known-faces/'
KNOWN_IMAGES_RELATIVE_PATH = './known-faces/'
app.config['UPLOAD_FOLDER'] = KNOWN_IMAGES_PATH

# Heroku
#from flask_heroku import Heroku
#heroku = Heroku(app)

# Add the basic Stripe configuration
STRIPE_PUBLISHABLE_KEY = 'pk_test_xW6EPmoOAtKvUwBzYZA68Q0Q00urdf6g1O'
STRIPE_SECRET_KEY = 'sk_test_teP3S2mVubgQLPpSjXZEjlIy00FRWqogOm'

os.environ['STRIPE_SECRET_KEY'] = STRIPE_SECRET_KEY
os.environ['STRIPE_PUBLISHABLE_KEY'] = STRIPE_PUBLISHABLE_KEY

stripe_keys = {
  'secret_key': os.environ['STRIPE_SECRET_KEY'],
  'publishable_key': os.environ['STRIPE_PUBLISHABLE_KEY']
}

stripe.api_key = stripe_keys['secret_key']

# ======== Routing =========================================================== #
# -------- Login ------------------------------------------------------------- #
@app.route('/', methods=['GET', 'POST'])
def login():
    if not session.get('logged_in'):
        form = forms.LoginForm(request.form)
        if request.method == 'POST':
            username = request.form['username'].lower()
            password = request.form['password']
            if form.validate():
                if helpers.credentials_valid(username, password):
                    session['logged_in'] = True
                    session['username'] = username
                    return json.dumps({'status': 'Login successful'})
                return json.dumps({'status': 'Invalid user/pass'})
            return json.dumps({'status': 'Both fields required'})
        return render_template('login.html', form=form)
    user = helpers.get_user()
    return render_template('home.html', content=render_template('pages/dashboard.html', user=user))


@app.route("/logout")
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))


# -------- Signup ---------------------------------------------------------- #
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if not session.get('logged_in'):
        form = forms.LoginForm(request.form)
        if request.method == 'POST':
            username = request.form['username'].lower()
            password = helpers.hash_password(request.form['password'])
            email = request.form['email']
            if form.validate():
                if not helpers.username_taken(username):
                    helpers.add_user(username, password, email)
                    session['logged_in'] = True
                    session['username'] = username
                    return json.dumps({'status': 'Signup successful'})
                return json.dumps({'status': 'Username taken'})
            return json.dumps({'status': 'User/Pass required'})
        return render_template('login.html', form=form)
    return redirect(url_for('login'))

# -------- Settings ---------------------------------------------------------- #
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if session.get('logged_in'):
        if request.method == 'POST':
            password = request.form['password']
            if password != "":
                password = helpers.hash_password(password)
            email = request.form['email']
            helpers.change_user(password=password, email=email)
            return json.dumps({'status': 'Saved'})
        user = helpers.get_user()
        return render_template('settings.html', user=user)
    return redirect(url_for('login'))


# -------- Webcam ---------------------------------------------------------- #
@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""

    user = helpers.get_user()
    return Response(gen(user=user),mimetype='multipart/x-mixed-replace; boundary=frame')

def gen(user):

    """Video streaming generator function."""

    known_face_encodings = []
    known_face_names = []

    path_for_current_user = KNOWN_IMAGES_PATH + str(user.username) + "/"

    picklefilename = "pickle_"+user.username
    pickle_path = os.path.join(path_for_current_user, picklefilename)
    if not(os.path.isfile(pickle_path)):
        print("No images have been uploaded")
        return
    pickle_file = open(pickle_path, "rb")
    while True:
        try:
            person_name, face_encoding = pickle.load(pickle_file)
        except EOFError:
            break
        except:
            break
        known_face_encodings.append(face_encoding)
        player_name = person_name.split(".")[0]
        known_face_names.append(player_name)
    pickle_file.close()

    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True

    if len(known_face_encodings) < 1:
        return

    #Code for timeout
    timeout_time = 10 #10 seconds
    timeout = time.time() + timeout_time
    passed_time = 0

    while True:
        rval, frame = video.read()
        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
        rgb_small_frame = small_frame[:, :, ::-1]
        # Only process every other frame of video to save time
        if process_this_frame:
            # Find all the faces and face encodings in the current frame of video
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            face_names = []
            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"

                # # If a match was found in known_face_encodings, just use the first one.
                # if True in matches:
                #     first_match_index = matches.index(True)
                #     name = known_face_names[first_match_index]

                # Or instead, use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]

                face_names.append(name)

        process_this_frame = not process_this_frame

        # Display the results
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

            # # Display the resulting image
            # cv2.imshow('Video', frame)

        #TODO: MAKE A BUTTON TO STOP RECORDING
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break
        if time.time() > timeout - timeout_time + passed_time:
            # Countdown
            # print(timeout_time-passed_time)
            passed_time += 1
        if time.time() > timeout:
            break

        cv2.imwrite('tmp/webcam_last_image.jpg', frame)
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + open('tmp/webcam_last_image.jpg', 'rb').read() + b'\r\n')

    # video.release()
    # cv2.destroyAllWindows()

# -------- Routing ---------------------------------------------------------- #

# -------- Dashboard ---------------------------------------------------- #
@app.route('/dashboard')
def dashboard():
    # custommize your page title / description here
    page_title = 'Dashboard - Customize your cameras'
    page_description = 'A controller for cameras'

    return redirect(url_for('login'))

# -------- Insights ---------------------------------------------------- #
@app.route('/insights')
def insights():
    # custommize your page title / description here
    page_title = 'Insights - Customize your cameras'
    page_description = 'Page for insights'

    return render_template('home.html',
                            content=render_template( 'pages/insights.html') )

# -------- List the Services Offered ---------------------------------------------------- #
@app.route('/services')
def services():
    # custommize your page title / description here
    page_title = 'Services - Customize your cameras'
    page_description = 'Page describes face recognition services offered'

    return render_template('home.html',
                            content=render_template( 'pages/services.html') )

# -------- Give a Demo of the Services Offered ---------------------------------------------------- #
@app.route('/demo')
def demo():
    # custommize your page title / description here
    page_title = 'Demo - Customize your cameras'
    page_description = 'Page provides a demonstration of the face recognition service'

    return render_template('home.html',
                            content=render_template( 'pages/demo.html') )

# -------- Show Prices for Services Offered ---------------------------------------------------- #
@app.route('/pricing')
def pricing():
    # custommize your page title / description here
    page_title = 'Pricing - Customize your cameras'
    page_description = 'Page shows pricing for the face recognition services'

    return render_template('home.html',
                            content=render_template( 'pages/pricing.html') )

# -------- Show Company Contact Details ---------------------------------------------------- #
@app.route('/contact')
def contact():
    # custommize your page title / description here
    page_title = 'Contact - Customize your cameras'
    page_description = 'Page gives company contact information'

    return render_template('home.html',
                            content=render_template( 'pages/contact.html') )

# -------- Manage Team Members ---------------------------------------------------- #
@app.route('/manageteam')
def manageteam():
    # custommize your page title / description here
    page_title = 'Manage Team'
    page_description = 'Page allows you to manage the people for face recognition service'

    # try to match the pages defined in -> pages/
    return render_template('home.html',
                            content=render_template( 'pages/manageteam.html') )

@app.route('/showmembers')
def showmembers():
    # custommize your page title / description here
    page_title = 'Show Members'
    page_description = 'Page shows the face images or pictures of the members to be recognized'

    user = helpers.get_user()
    path_for_current_user = KNOWN_IMAGES_PATH + str(user.username) + "/"
    relative_path = KNOWN_IMAGES_RELATIVE_PATH + str(user.username) + "/"

    images = []
    for file in os.listdir(path_for_current_user):
        if file.endswith(".jpg") or file.endswith(".jpeg") or file.endswith(".png") or file.endswith(".gif") or file.endswith(".JPG") or file.endswith(".JPEG") or file.endswith(".PNG") or file.endswith(".GIF"):
            images.append(os.path.join(relative_path, file))
    # try to match the pages defined in -> pages/
    return render_template('home.html',
                            content=render_template( 'pages/showmembers.html', images=images) )

# -------- Add memeber ---------------------------------------------------- #
@app.route('/addmember', methods=['GET', 'POST'])
def addmember():
    # custommize your page title / description here
    page_title = 'Add a member'
    page_description = 'Add a new member face image in the system'

    user = helpers.get_user()
    #Configuring the upload folder
    # define the name of the directory to be created
    path = KNOWN_IMAGES_PATH + str(user.username) + "/"

    try:
        os.makedirs(path)
    except OSError:
        print ("Creation of the directory %s failed" % path)
    else:
        print ("Successfully created the directory %s" % path)
    app.config['UPLOAD_FOLDER'] = path

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print("File saved")
            image = face_recognition.load_image_file(os.path.join(path, filename))
            face_encoding = face_recognition.face_encodings(image)
            print("Encoded the image")
            if len(face_encoding)>0:
                picklefilename = "pickle_"+user.username
                pickle_file = open(os.path.join(path, picklefilename), "ab")
                pickle.dump([filename, face_encoding[0]], pickle_file)
                pickle_file.close()
            print("Dumped the file")
            return redirect(url_for('uploaded_file',
                                    filename=filename))

    return render_template('home.html',
                            content=render_template( 'pages/addmember.html') )

# -------- Remove memeber ---------------------------------------------------- #
@app.route('/removemember')
def removemember():
    # custommize your page title / description here
    page_title = 'Remove Member'
    page_description = 'Remove a Member'

    # try to match the pages defined in -> pages/
    return render_template('home.html',
                            content=render_template( 'pages/removemember.html') )

# -------- Team Setting ---------------------------------------------------- #
@app.route('/teamsettings')
def teamsettings():
    # custommize your page title / description here
    page_title = 'Team Setup'
    page_description = 'Setup a Team'

    return render_template('home.html',
                            content=render_template( 'pages/teamsettings.html') )

# -------- Camera Status ---------------------------------------------------- #
@app.route('/status')
def status():
    # custommize your page title / description here
    page_title = 'Camera Status'
    page_description = 'Show Camera Status'

    return render_template('home.html',
                            content=render_template( 'pages/status.html') )

# -------- Admin Reports ---------------------------------------------------- #
@app.route('/admimreports')
def adminreports():
    # custommize your page title / description here
    page_title = 'Admin Reports'
    page_description = 'Provide Administration Reports'

    return render_template('home.html',
                            content=render_template( 'pages/adminreports.html') )

# -------- Transactions ---------------------------------------------------- #
@app.route('/transactions')
def transactions():
    # custommize your page title / description here
    page_title = 'Transactions'
    page_description = 'Show Transactions'

    return render_template('home.html',
                            content=render_template( 'pages/transactions.html') )

# -------- Account ---------------------------------------------------- #
@app.route('/account')
def account():
    # custommize your page title / description here
    page_title = 'Account'
    page_description = 'Provide Financial Accounting Details'

    return render_template('home.html',
                            content=render_template( 'pages/account.html') )

# -------- Financial Reports ---------------------------------------------------- #
@app.route('/finreports')
def finreports():
    # custommize your page title / description here
    page_title = 'Financial Reports'
    page_description = 'Provide Financial Reports'

    return render_template('home.html',
                            content=render_template( 'pages/finreports.html') )

# -------- Upload images ---------------------------------------------------- #
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

# -------- Stripe Checkout ---------------------------------------------------- #

@app.route('/')
def stripepay():
    return render_template('stripepay.html', key=stripe_keys['publishable_key'])


# ======== Main ============================================================== #
if __name__ == "__main__":
    app.run(debug=True, threaded=True, use_reloader=True)
