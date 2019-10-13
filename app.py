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
import cfg

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

# -------- Pricing Table  ------------------------------------------------------------- #

# class Results(Table):
#    id = Col('Id', show=False)
#    serial_num = Col('#')
#    discription = Col('Description')
#    price = Col('Price')

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
    return render_template('home.html', content=render_template('pages/dashboard.html', user=user, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE))

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

# -------- Routing ---------------------------------------------------------- #

# -------- Dashboard ---------------------------------------------------- #
@app.route('/dashboard')
def dashboard():
    # custommize your page title / description here
    page_title = 'Dashboard - Customize your cameras'
    page_description = 'A controller for cameras'

     #
    cfg.CONTENT_PAGE = 'dashboard'

    return redirect(url_for('login'))

# -------- List the Services Offered ---------------------------------------------------- #
@app.route('/services')
def services():
    # customize your page title / description here
    page_title = 'Services'
    page_description = 'Page describes face recognition services offered'

    cfg.CONTENT_PAGE = 'services'

    return render_template('home.html',
                            content=render_template( 'pages/services.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Give a Demo of the Services Offered ---------------------------------------------------- #
@app.route('/demo')
def demo():
    # custommize your page title / description here
    page_title = 'Demo'
    page_description = 'Page provides a demonstration of the face recognition service'

    SAMPLE_IMAGES_PATH = "./static/sample_images/"
    SAMPLE_IMAGES_RELATIVE_PATH = "./sample_images/"

    cfg.CONTENT_PAGE = 'demo'
    #Just for the sake of demo files are hard coded
    #There are 6 images
    NUM_IMAGES = 6
    filenames_images = ["federer.jpg","messi.jpg","nadal.jpg","ronaldo.jpg","obama.jpg","grassland.jpg"]
    images=[SAMPLE_IMAGES_RELATIVE_PATH+x for x in filenames_images]

    federer_image = face_recognition.load_image_file(os.path.join(SAMPLE_IMAGES_PATH, filenames_images[0]))
    messi_image = face_recognition.load_image_file(os.path.join(SAMPLE_IMAGES_PATH, filenames_images[1]))
    nadal_image = face_recognition.load_image_file(os.path.join(SAMPLE_IMAGES_PATH, filenames_images[2]))
    ronaldo_image = face_recognition.load_image_file(os.path.join(SAMPLE_IMAGES_PATH, filenames_images[3]))
    obama_image = face_recognition.load_image_file(os.path.join(SAMPLE_IMAGES_PATH, filenames_images[4]))
    grassland_image = face_recognition.load_image_file(os.path.join(SAMPLE_IMAGES_PATH, filenames_images[5]))



    results = [0]*NUM_IMAGES

    #I am grabbing 0th index because I know that there exists one and only one face
    federer_face_encoding = face_recognition.face_encodings(federer_image)[0]
    messi_face_encoding = face_recognition.face_encodings(messi_image)[0]
    nadal_face_encoding = face_recognition.face_encodings(nadal_image)[0]
    ronaldo_face_encoding = face_recognition.face_encodings(ronaldo_image)[0]

    known_faces = [
        federer_face_encoding,
        messi_face_encoding,
        nadal_face_encoding,
        ronaldo_face_encoding
    ]
    unknown_images = [
        obama_image,
        grassland_image
    ]
    known_names = [
        "Federer",
        "Messi",
        "Nadal",
        "Ronaldo"
    ]
    exists_in_db = ["YES","YES","YES","YES","NO","NO"]
    # results is an array of True/False telling if the unknown face matched anyone in the known_faces array
    for i in range(NUM_IMAGES):
        #Compare with known_images first
        if i<len(known_faces):
            matches = face_recognition.compare_faces(known_faces, known_faces[i])
            if True in matches:
                results[i] = "Welcome, "+known_names[matches.index(True)]
            else:
                results[i] = "Unknown person. Contact your administrator."
        else:
            #We are checking the unknown images so first we have to encode them
            img = face_recognition.face_encodings(unknown_images[i-len(known_faces)])
            if img:
                matches = face_recognition.compare_faces(known_faces, img[0])
                if True in matches:
                    results[i] = "Welcome, "+known_names[matches.index(True)]
                else:
                    results[i] = "Unknown person. Contact your administrator."
            else:
                results[i] = "No face detected in the image"

    return render_template('home.html',
                            content=render_template('pages/demo.html',
                            num_rows=NUM_IMAGES,
                            images=images,
                            exists_in_db=exists_in_db,
                            results=results), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Show Prices for Services Offered ---------------------------------------------------- #
@app.route('/pricing')
def pricing():
    # Customize your page title / description here
    page_title = 'Pricing'
    page_description = 'Page shows pricing for the face recognition services'


    cfg.CONTENT_PAGE = 'pricing'
    # pass the stripe publishable key for stripe based credit card payment processing
    return render_template('home.html',
                            content=render_template( 'pages/pricing.html', key=stripe_keys['publishable_key']), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Show Company Contact Details ---------------------------------------------------- #
@app.route('/contact')
def contact():
    # Customize your page title / description here
    page_title = 'Contact'
    page_description = 'Page gives company contact information'


    cfg.CONTENT_PAGE = 'contact'

    return render_template('home.html',
                            content=render_template('pages/contact.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Manage Team Members ---------------------------------------------------- #
@app.route('/manageteam')
def manageteam():
    # Customize your page title / description here
    page_title = 'Manage Team'
    page_description = 'Page allows you to manage the people for face recognition service'


    cfg.CONTENT_PAGE = 'manageteam'

    print(cfg.PAYMENT_STRIPE_DONE)
    # try to match the pages defined in -> pages/
    return render_template('home.html',
                            content=render_template( 'pages/manageteam.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Show Team Members ---------------------------------------------------- #
@app.route('/showmembers')
def showmembers():
    # custommize your page title / description here
    page_title = 'Show Members'
    page_description = 'Page shows the face images or pictures of the members to be recognized'

    user = helpers.get_user()
    path_for_current_user = KNOWN_IMAGES_PATH + str(user.username) + "/"
    relative_path = KNOWN_IMAGES_RELATIVE_PATH + str(user.username) + "/"

    images = []
    if os.path.exists(path_for_current_user):
        for file in os.listdir(path_for_current_user):
            if file.endswith(".jpg") or file.endswith(".jpeg") or file.endswith(".png") or file.endswith(".gif") or file.endswith(".JPG") or file.endswith(".JPEG") or file.endswith(".PNG") or file.endswith(".GIF"):
                images.append(os.path.join(relative_path, file))

    cfg.CONTENT_PAGE = 'showmembers'
    # try to match the pages defined in -> pages/
    return render_template('home.html',
                            content=render_template( 'pages/showmembers.html', images=images), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

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

            image = face_recognition.load_image_file(os.path.join(path, filename))
            face_encoding = face_recognition.face_encodings(image)

            if len(face_encoding)>0:
                picklefilename = "pickle_"+user.username
                pickle_file = open(os.path.join(path, picklefilename), "ab")
                pickle.dump([filename, face_encoding[0]], pickle_file)
                pickle_file.close()

            return redirect(url_for('uploaded_file',
                                    filename=filename))


    cfg.CONTENT_PAGE = 'addmember'

    return render_template('home.html',
                            content=render_template( 'pages/addmember.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Remove memeber ---------------------------------------------------- #
@app.route('/removemember')
def removemember():
    # Customize your page title / description here
    page_title = 'Remove Member'
    page_description = 'Remove a Member'


    cfg.CONTENT_PAGE = 'removemember'

    # try to match the pages defined in -> pages/
    return render_template('home.html',
                            content=render_template( 'pages/removemember.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Team Setting ---------------------------------------------------- #
@app.route('/teamsettings')
def teamsettings():
    # Customize your page title / description here
    page_title = 'Team Setup'
    page_description = 'Setup a Team'


    cfg.CONTENT_PAGE = 'teamsettings'

    return render_template('home.html',
                            content=render_template( 'pages/teamsettings.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Camera Status ---------------------------------------------------- #
@app.route('/status')
def status():
    # Customize your page title / description here
    page_title = 'Camera Status'
    page_description = 'Show Camera Status'


    cfg.CONTENT_PAGE = 'status'

    return render_template('home.html',
                            content=render_template( 'pages/status.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Admin Reports ---------------------------------------------------- #
@app.route('/admimreports')
def adminreports():
    # Customize your page title / description here
    page_title = 'Admin Reports'
    page_description = 'Provide Administration Reports'


    cfg.CONTENT_PAGE = 'adminreports'

    return render_template('home.html',
                            content=render_template( 'pages/adminreports.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Transactions ---------------------------------------------------- #
@app.route('/transactions')
def transactions():
    # Customize your page title / description here
    page_title = 'Transactions'
    page_description = 'Show Transactions'


    cfg.CONTENT_PAGE = 'transactions'

    return render_template('home.html',
                            content=render_template( 'pages/transactions.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Account ---------------------------------------------------- #
@app.route('/account')
def account():
    # Customize your page title / description here
    page_title = 'Account'
    page_description = 'Provide Financial Accounting Details'


    cfg.CONTENT_PAGE = 'account'

    return render_template('home.html',
                            content=render_template( 'pages/account.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Financial Reports ---------------------------------------------------- #
@app.route('/finreports')
def finreports():
    # Customize your page title / description here
    page_title = 'Financial Reports'
    page_description = 'Provide Financial Reports'


    cfg.CONTENT_PAGE = 'finereports'

    return render_template('home.html',
                            content=render_template( 'pages/finreports.html'), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# -------- Upload images ---------------------------------------------------- #
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

# -------- Stripe Charge ---------------------------------------------------- #
@app.route('/charge', methods=['POST'])
def charge():

    # amount in cents
    amount = 2500

    customer = stripe.Customer.create(
        email='sample@customer.com',
        source=request.form['stripeToken']
    )

    stripe.Charge.create(
        customer=customer.id,
        amount=amount,
        currency='usd',
        description='Flask Charge'
    )

    cfg.CONTENT_PAGE = 'charge'
    # Assign true to know that the customer's payment has been processed successfully
    cfg.PAYMENT_STRIPE_DONE = 'true'
    return render_template('home.html', content=render_template('charge.html', amount=amount), CONTENT_PAGE = cfg.CONTENT_PAGE, PAYMENT_STRIPE_DONE=cfg.PAYMENT_STRIPE_DONE)

# ======== Main ============================================================== #
if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
