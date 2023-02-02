# ARC-H

Convert Data from [StreamRecorder](https://github.com/microsoft/HoloLens2ForCV/tree/main/Samples/StreamRecorder) for further use.

## Format

- `project.json` with general information
- series of frames
	- `camera.json` with information about the camera location and properties
	- `depth.raw` with the depth information
- `color.mp4` with color information, synchronized to the frames
