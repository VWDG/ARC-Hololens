# Target Format for Recordings

## Data order

- data for binary files or matrices is saved in column-major order

## Required Data

### `project.json`

- information about the recording
- single JSON-object with
	- `name: String`: project name
	- `modelName: String`: device name
	- `sessionid: String`: unique identifier for the session
	- `viewportSize: String`: size of the display of the device
	- `creationData: Number`: time of recording
	- `numberOfFrames: Number`: total amount of frames
	- `colorSize: [Number, Number]`: width and height of the color video
	- `description: String`: description for the recording
	- `depthSize: [Number, Number]`: width and height of the depth images

### `camera.json`

- information about the used camera
- concatenation of JSON-objects with
	- `frame: Number`: index of the frame
	- `orientation: Number`: raw value of [`UIKit UIInterfaceOrientation`](https://developer.apple.com/documentation/uikit/uiinterfaceorientation)
	- `viewMatrix: String`: 4x4 matrix with world to camera space transformation
	- `projectionMatrix: String`: 4x4 matrix with camera to display space transformation
	- `transform: String`: 4x4 matrix with camera transformation in world space
	- `intrinsics: String`: 3x3 matrix with color camera intrinsics
	- `depthIntrinsics: String`: 3x3 matrix with depth camera intrinsics

### Frames

- every frame is saved in a folder with the index as name
- one frame contains
	- `depth.raw`: binary file with depth as pinhole projection with
		- `int32`: width
		- `int32`: height
		- `float32 x (width * height)`: depth as distance to the camera in meters

### `color.mp4` or `color.mov`

- video file with color information
- every frame in the video corresponds to one frame in the recording

## Additional Data

- additional data can be saved for future use, but replay software programs should not require the data
	- if the data is thematic close to one existing JSON file the data can be saved as an additional key
	- if the data contains images or binary files it can be saved as additional file in the frame folder
	- other data can be saved as a new JSON file
