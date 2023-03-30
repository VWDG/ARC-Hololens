import os
import numpy as np
import shutil
import tarfile
import cv2
import subprocess
import json
import sys

from typing import *
from numpy.typing import *

def main() -> None:
	global name, path, out_path
	if len(sys.argv) < 2:
		print("please provide path to recording as a command line argument")
		return
	name = sys.argv[1]
	path =  name
	out_path = name + "-result"

	if (os.path.isdir(out_path)):
		shutil.rmtree(out_path)
	os.mkdir(out_path)
	identification, frame_count, cam_width, cam_height, depth_width, depth_height = create_depth()
	create_project(identification, frame_count, cam_width, cam_height, depth_width, depth_height)

class NumpyArrayEncoder(json.JSONEncoder):
	def default(self, o: Any):
		if isinstance(o, np.ndarray):
			return "[" + str(o.T.tolist()) + "]"
		return json.JSONEncoder.default(self, o)

def unpack_tar(path: str, folder: str) -> None:
    tar = tarfile.open(path)
    tar.extractall(folder)
    tar.close()

def time_to_sec(time: int) -> float:
	return float(time) / 10_000_000.0

def time_from_file(path: str):
	return time_to_sec(int(path.split(".")[0].split("/")[-1]))

def load_lut(lut_filename: str) ->NDArray[np.float32]:
	with open(lut_filename, mode='rb') as depth_file:
		return np.frombuffer(depth_file.read(), dtype="f").astype(np.float32).reshape((-1, 3))

def load_extrinsics(extrinsics_path: str) -> NDArray[np.float32]:
	return np.loadtxt(str(extrinsics_path), delimiter=',').astype(np.float32).reshape((4, 4))


try:
    import numba
    decorator = numba.njit
except ImportError as e:
    print("numba not avaible, conversion will be a lot slower")
    def decorator(f):
	    return f

@decorator
def project_points(points: NDArray[np.float32], focal_x: float, focal_y: float, o_x: float, o_y: float, width: int, height: float, result: NDArray[np.float32]):
	for i in range(points.shape[0]):
		x, y, z = points[i]
		z = -z
		if z < 0.001: continue
		a = int(x * focal_x / z + o_x)
		b = int(y * focal_y / z + o_y)
		if a < 0 or a >= width: continue
		if b < 0 or b >= height: continue
		result[height - 1 - b, a] = z #turn 90° anti-clockwise

def create_depth() -> Tuple[str, int, int, int, int, int]:

	print("unpacking raw images")
	unpack_tar(path + "/PV.tar", "Temp/PV/")
	config_name = [x for x in os.listdir(path) if x.endswith("pv.txt")][0]
	config = open(path + "/" + config_name, 'r')
	lines = config.readlines()
	header = lines[0].split(",")
	principal_point_x = float(header[0])
	principal_point_y = float(header[1])
	cam_width = int(header[2])
	cam_height = int(header[3])
	identification = config_name.split("_")[0]

	in_txt = open("Temp/in.txt", "w")

	print("creating frames")
	lut = load_lut(path + "/Depth Long Throw_lut.bin")
	rig2cam = load_extrinsics(path + "/Depth Long Throw_extrinsics.txt")

	unpack_tar(path + "/Depth Long Throw.tar", "Temp/Depth")

	depth_files = [x for x in os.listdir("Temp/Depth") if x.endswith(".pgm") and not x.endswith("_ab.pgm")]

	camera = open(out_path + "/camera.json", "w")

	config = open(path + "/Depth Long Throw_rig2world.txt" , 'r')
	transforms: List[Tuple[float, NDArray[np.float32]]] = []
	for line in config.readlines():
		data = line.split(",")
		time = time_to_sec(int(data[0]))
		transform = np.array(data[1:17]).astype(np.float32).reshape((4, 4))
		transforms.append((time, transform))
	config.close()

	width = 500
	height = width
	focal_x = 300.0
	focal_y = focal_x
	o_x = float(width) * 0.5
	o_y = float(width) * 0.5 + 100.0

	intrinsic = np.array([
		[focal_x, 0.0, o_x],
		[0.0, focal_y, o_y],
		[0.0, 0.0, 1.]
	])

	depth_file_idx = 0

	for count in range(len(lines) - 1):

		line = lines[count + 1].split(",") #first line is header
		cam_time = time_to_sec(int(line[0]))
		file = line[0] + ".bytes"

		cam_focal_x = float(line[1])
		cam_focal_y = float(line[2])
		cam_intrinsics = np.array([[cam_focal_x, 0, cam_width - principal_point_x], [0, cam_focal_y, principal_point_y], [0, 0, 1]])
		pv_to_world = np.array(line[3:19]).astype(np.float32).reshape((4, 4))

		name = "Temp/PV/" + file
		with open(name, 'rb') as data:
			image = np.frombuffer(data.read(), dtype=np.uint8)
		image = image.reshape((cam_height, cam_width, 4))
		image = image[:, :, :3]

		name = name.replace(".bytes", ".png")
		cv2.imwrite(name, image)
		name = name.replace("Temp/", "")
		in_txt.write("file " + name + "\n")

		diff = abs(transforms[depth_file_idx][0] - cam_time)
		if depth_file_idx < len(transforms) - 1 and abs(transforms[depth_file_idx + 1][0] - cam_time) < diff:
			depth_file_idx += 1

		transform = transforms[depth_file_idx][1]
		world_to_pv = np.linalg.inv(pv_to_world)

		#create points in depth space
		img = cv2.imread("Temp/Depth/" + depth_files[depth_file_idx], -1)
		img = np.tile(img.flatten().astype(np.float32).reshape((-1, 1)), (1, 3))
		points = img * lut #shape (n, 3)
		points /= 1000.0

		#move points to cam space
		view = transform @ np.linalg.inv(rig2cam)

		points = np.hstack([points, np.ones(shape=(points.shape[0], 1), dtype=np.float32)])
		points = (world_to_pv @ view) @ points.T

		points = points.T[:, 0:3]

		height = cam_height
		width = cam_width
		intrinsic = cam_intrinsics

		result = np.zeros((height, width), dtype=np.float32)
		project_points(points, focal_x, focal_y, o_x, o_y, width, height, result)

		folder = out_path + "/" + str(count)
		os.mkdir(folder)
		file = open(folder + "/depth.raw", "wb")
		file.write(width.to_bytes(4, "little"))
		file.write(height.to_bytes(4, "little"))
		file.write(result.tobytes())
		file.close()

		projection = calculate_projection(intrinsic, width, height)
		json.dump({
			"frame": count,
			"orientation": 3, #https://developer.apple.com/documentation/uikit/uiinterfaceorientation
			"viewMatrix": world_to_pv,
			"intrinsics": cam_intrinsics,
			"depthIntrinsics": intrinsic,
			"projectionMatrix": projection,
			"transform": transform,
		}, camera, cls=NumpyArrayEncoder)

		print("\r\t" + str(count) + " / " + str(len(lines)-1), end="")

	clear_line()

	in_txt.close()
	print("creating video")
	subprocess.run("ffmpeg.exe -y -r 30 -f concat -safe 0 -i Temp/in.txt -c:v libx264 -vf fps=30,format=yuv420p " + out_path + "/color.mp4", capture_output=True)

	shutil.rmtree("Temp")

	return identification, len(lines), cam_width, cam_height, width, height

def clear_line():
	print("\r                                    \r", end="")

def serialize_matrix(mat: NDArray[np.float32]) -> str:
	res = "\"[["
	x, y = mat.shape
	for i in range(x):
		res += "["
		for j in range(y):
			res += str(mat[j, i])
			if j < y - 1:
				res += ","
		res += "]"
		if i < x - 1:
			res += ","
	return res + "]]\""

#arw does not use the projection matrix, so no clue if this is right
def calculate_projection(intrinsics: NDArray[np.float32], width: int, height: int) -> NDArray[np.float32]:
	mat = np.zeros(shape=(4, 4), dtype=np.float32)
	mat[0, 0] = intrinsics[0, 0] / float(width)
	mat[1, 1] = intrinsics[1, 1] / float(height)
	mat[2, 2] = -0.1
	mat[2, 3] = -1
	mat[3, 2] = -1
	return mat

def create_project(id: str, frames: int, cam_width: int, cam_height: int, depth_width: int, depth_height: int) -> None:
	print("creating project")
	project = {
		"name": "Hololens 2",
		"modelName": "Hololens 2",
		"sessionid": id,
		"viewportSize": [0, 0],
		"creationDate": 0.0,
		"numberOfFrames": frames,
		"colorSize": [cam_width, cam_height],
		"description": "",
		"depthSize": [depth_width, depth_height],
	}

	file = open(out_path + "/project.json", "w")
	json.dump(project, file)
	file.close()

	#create additional empty files because replay software requires them
	for name in ["anchor", "env_probe", "lightestimation", "plane_anchor"]:
		file = open(out_path + "/" + name + ".json", "w")
		file.close()

main()
