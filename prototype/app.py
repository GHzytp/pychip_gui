from flask import Flask, render_template, request, session, url_for, send_from_directory, send_file
from flask_session import Session
from flask_navigation import Navigation
import os
import cv2
import json
import shutil
from werkzeug.utils import secure_filename
from PIL import Image  # Python Image Library - Image Processing
import glob
import cv2

# library for chipping function
import math
import numpy as np
from matplotlib import pyplot as plt


from ncempy.io import dm


app = Flask(__name__)
SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)

# navigation bar items
nav = Navigation(app)
nav.Bar('side', [
    nav.Item('About pyChip', 'about'),
    nav.Item('Analyze and Predict', 'form')
])

# file paths
app.config['UPLOAD_PATH'] = 'protected'


@app.route('/protected/<filename>')
def upload(filename):
    # username = session.get('username')
    file_path = os.path.join(app.config['UPLOAD_PATH'], 'username', filename)
    return send_from_directory(file_path)


@app.route('/')
def about():
    return render_template('about.html')


@app.route('/upload')
def form():
    session.clear()
    return render_template('form.html')

@app.route('/download/<foldername>/<filename>')
def download(foldername, filename):
    #For windows you need to use drive name [ex: F:/Example.pdf]
    path = "static/username/" + foldername + "/" + filename
    return send_file(path, as_attachment=True)

@app.route('/grid_select', methods=["GET", "POST"])
def create_grid():
    if request.method == 'POST':
        f = request.files['file']

        if f.filename[-4:] == "tiff":
            f.save("static/username/images/" + f.filename)
            image = Image.open("static/username/images/" + f.filename)
            image.mode = 'I'
            new_image = image.point(lambda i:i*(1./256)).convert('L')
            current_name = f.filename[:-4] + "jpg"
            new_image.save("static/username/images/" + current_name)
        elif f.filename[-3:] == "dm4":
            f.save("static/username/images/" + f.filename)
            data = dm.dmReader("static/username/images/" + f.filename)['data']
            new_array = (data - np.min(data)) / (np.max(data) - np.min(data))
            im = Image.fromarray((255 * new_array).astype('uint8'))
            current_name = f.filename[:-3] + "jpg"
            im.save("static/username/images/" + current_name)
        else:
            current_name = f.filename
            f.save("static/username/images/" + current_name)

        session['file'] = current_name
        print(current_name)
        # load image and gets the image dimensions
        im_gray = cv2.imread("static/username/images/" + current_name, cv2.IMREAD_GRAYSCALE)
        dim = {'height': im_gray.shape[0], 'width': im_gray.shape[1], 'image': "static/username/images/" + current_name}
        print(dim)

        session['dim'] = dim
        return render_template('index.html', dim=dim)

    # default image (if nothing is uploaded)
    # load image and gets the image dimensions
    # do we need this if the user is required to upload a file to move on?
    im_gray = cv2.imread(os.path.join(app.static_folder, "images/", "intensity.jpg"), cv2.IMREAD_GRAYSCALE)
    dim = {'height': im_gray.shape[0], 'width': im_gray.shape[1], 'image': "static/images/intensity.jpg"}
    session['dim'] = dim
    return render_template('index.html', dim=dim)


@app.route('/support_select', methods=["GET", "POST"])
def save_file():
    if request.method == 'POST':
        current_file = session.get('file')
        print(current_file)

        # dim = {'height': height, 'width' : width, 'image': "protected/username/" + current_file}

        path_to_im = "static/username/images/" + current_file
        print(path_to_im)
        query_path = "static/username/query/all_chips/"

        try:
            shutil.rmtree(query_path)
            print("removed previous query set")
        except:
            print('There were no previous query sets')
        finally:
            os.mkdir(query_path)

        # Get the chip size from the slider
        chip_size = int(request.form["mySlider"])
        session["chip_size"] = chip_size
        # chipping image
        img = cv2.imread(path_to_im)
        width = int(img.shape[1])
        height = int(img.shape[0])
        size_of_img = chip_size
        num_crops_x = math.floor(width / size_of_img)
        num_crops_y = math.floor(height / size_of_img)
        total_num_crops = num_crops_x * num_crops_y

        pixels_ignored_in_x = width % size_of_img
        pixels_ignored_in_y = height % size_of_img
        print("Pixels ignored in x: last " + str(pixels_ignored_in_x))
        print("Pixels ignored in y: last " + str(pixels_ignored_in_y))

        #crop out unused part
        image = Image.open("static/username/images/" + current_file)
        im1 = image.crop((0, 0, width - pixels_ignored_in_x, height - pixels_ignored_in_y))
        im1.save("static/username/images/" + current_file)

        x_coords = list(range(0, width, size_of_img))
        y_coords = list(range(0, height, size_of_img))
        img_names = []

        crops = np.zeros((total_num_crops, size_of_img, size_of_img))
        count = 0

        for i in range(num_crops_x):
            for j in range(num_crops_y):
                x = x_coords[i]
                y = y_coords[j]
                new_img = img[y:y + size_of_img, x:x + size_of_img, 0]
                crops[count, :, :] = new_img

                count = count + 1
                name = "cropX_" + str(i) + "_Y_" + str(j) + ".jpg"

                img_names.append(name)
                plt.imsave(query_path+name, new_img, vmin=0, vmax=255)

        dim = session.get('dim')
        dim["num_crops_x"] = num_crops_x
        dim["num_crops_y"] = num_crops_y
        return render_template('predict.html', dim=dim)

    dim = session.get('dim')

    return render_template('predict.html', dim=dim)


@app.route('/results', methods=["GET", "POST"])
def send_supports():
    if request.method == 'POST':

        return render_template('results.html')
    return render_template('results.html')


app.run(debug=True)
