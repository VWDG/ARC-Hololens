if True:
	main_path = "Recordings/HoloConv"
	out = "holo"
	framedelay = 30
else:
	main_path = "Recordings/IOS"
	out = "ios"
	framedelay = 30

import os
import cv2
import numpy as np
import os.path
import struct
import subprocess
from typing import *
from numpy.typing import *

i = 0
images: List[str] = []
while (os.path.exists(main_path + "/" + str(i))):
	images.append(main_path + "/" + str(i) + "/depth.raw")
	i += 1

config = open("in.txt", "w")
files = ["in.txt"]

for image in images:
	fd = open(image, 'rb')
	width = struct.unpack("i", fd.read(4))[0]
	height = struct.unpack("i", fd.read(4))[0]
	f = np.fromfile(fd, dtype=np.float32, count=height*width)
	f = 1.0 / (f  + 1.0) * 255.0
	f = f.astype(dtype=np.byte)
	im = f.reshape(height, width)
	fd.close()

	rep = image.replace(".raw", ".png")
	cv2.imwrite(rep, im)
	files.append(rep)

	config.write("file " + rep + "\n")
	config.write("outpoint " + str(1.0 / framedelay) + "\n")

config.close()

subprocess.run("ffmpeg -f concat -i in.txt -framerate 1 -c:v libx264 -pix_fmt yuv420p " + out + ".mp4 -y", capture_output=True)

for file in files:
	os.remove(file)
