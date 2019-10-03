# -*- coding: utf-8 -*-

from scripts import tabledef
from scripts import forms
from scripts import helpers
from flask import Flask, redirect, url_for, render_template, request, session, jsonify, Response, flash
import json
import sys
import os

import face_recognition
import cv2
import numpy as np
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(12)  # Generic key for dev purposes only

#Create a video instance
video = cv2.VideoCapture(0)
#Path to known images (companys database)
KNOWN_IMAGES_PATH = './known-faces/'
app.config['UPLOAD_FOLDER'] = KNOWN_IMAGES_PATH

# Heroku
#from flask_heroku import Heroku
#heroku = Heroku(app)

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
    return render_template('home.html', user=user, content=render_template('pages/dashboard.html'))


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
    return Response(gen(),mimetype='multipart/x-mixed-replace; boundary=frame')

def gen():
    """Video streaming generator function."""
    known_face_encodings = []
    known_face_names = []
    #Making encoding for known players
    for filename in os.listdir(KNOWN_IMAGES_PATH):
        image = face_recognition.load_image_file(os.path.join(KNOWN_IMAGES_PATH, filename))
        known_face_encodings.append(face_recognition.face_encodings(image)[0])

        player_name = filename.split(".")[0]
        known_face_names.append(player_name)

    # Initialize some variables
    face_locations = []
    face_encodings = []
    face_names = []
    process_this_frame = True

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

        # Hit 'q' on the keyboard to quit!
        #TODO: MAKE A BUTTON TO STOP RECORDING
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        cv2.imwrite('tmp/webcam_last_image.jpg', frame)
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + open('tmp/webcam_last_image.jpg', 'rb').read() + b'\r\n')


# -------- Routing ---------------------------------------------------------- #
@app.route('/status')
def status():
    # custommize your page title / description here
    page_title = 'Current status'
    page_description = 'Check the current status of the cameras'

    # try to match the pages defined in -> pages/
    return render_template('home.html',
                            content=render_template( 'pages/status.html') )
@app.route('/dashboard')
def status():
    # custommize your page title / description here
    page_title = 'Current status'
    page_description = 'Check the current status of the cameras'

    # try to match the pages defined in -> pages/
    return render_template('home.html',
                            content=render_template( 'pages/dashboard.html') )
@app.route('/addmember')
def status():
    # custommize your page title / description here
    page_title = 'Current status'
    page_description = 'Check the current status of the cameras'

    # try to match the pages defined in -> pages/
    return render_template('home.html',
                            content=render_template( 'pages/addmember.html') )
# ======== Main ============================================================== #
if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
