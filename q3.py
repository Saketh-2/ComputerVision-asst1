import cv2
import numpy as np
import depthai as dai
import time
rgbWeight = 0.6
depthWeight = 0.4

def updateBlendWeights(percent_rgb):
    global depthWeight
    global rgbWeight
    rgbWeight = float(percent_rgb)/100.0
    depthWeight = 1.0 - rgbWeight

downscaleColor = True
fps = 30
# The disparity is computed at this resolution, then upscaled to RGB resolution
monoResolution = dai.MonoCameraProperties.SensorResolution.THE_400_P

# Create pipeline
pipeline = dai.Pipeline()
queueNames = []

# Define sources and outputs
camRgb = pipeline.create(dai.node.ColorCamera)
left = pipeline.create(dai.node.MonoCamera)
right = pipeline.create(dai.node.MonoCamera)
stereo = pipeline.create(dai.node.StereoDepth)

rgbOut = pipeline.create(dai.node.XLinkOut)
depthOut = pipeline.create(dai.node.XLinkOut)

rgbOut.setStreamName("rgb")
queueNames.append("rgb")
depthOut.setStreamName("depth")
queueNames.append("depth")

#Properties
camRgb.setBoardSocket(dai.CameraBoardSocket.RGB)
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
camRgb.setFps(fps)
if downscaleColor: camRgb.setIspScale(2, 3)
# For now, RGB needs fixed focus to properly align with depth.
# This value was used during calibration
camRgb.initialControl.setManualFocus(130)

left.setResolution(monoResolution)
left.setBoardSocket(dai.CameraBoardSocket.LEFT)
left.setFps(fps)
right.setResolution(monoResolution)
right.setBoardSocket(dai.CameraBoardSocket.RIGHT)
right.setFps(fps)

stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
# LR-check is required for depth alignment
stereo.setLeftRightCheck(True)
stereo.setDepthAlign(dai.CameraBoardSocket.RGB)

# Linking
camRgb.isp.link(rgbOut.input)
left.out.link(stereo.left)
right.out.link(stereo.right)
stereo.disparity.link(depthOut.input)
start_time1 = time.time()
start_time2 = time.time()
start_time3 = time.time()
x = 1
counter1 = 0
counter2 = 0
counter3 = 0
# Connect to device and start pipeline
with dai.Device(pipeline) as device:

    device.getOutputQueue(name="rgb",   maxSize=4, blocking=False)
    device.getOutputQueue(name="depth", maxSize=4, blocking=False)

    frameRgb = None
    frameDepth = None
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Configure windows; trackbar adjusts blending ratio of rgb/depth
    rgbWindowName = "rgb"
    depthWindowName = "depth"
    blendedWindowName = "rgb-depth"
    cv2.namedWindow(rgbWindowName)
    cv2.namedWindow(depthWindowName)
    cv2.namedWindow(blendedWindowName)
    cv2.createTrackbar('RGB Weight %', blendedWindowName, int(rgbWeight*100), 100, updateBlendWeights)

    while True:
        counter1 += 1
        counter2 += 1
        counter3 += 1
        latestPacket = {}
        latestPacket["rgb"] = None
        latestPacket["depth"] = None

        queueEvents = device.getQueueEvents(("rgb", "depth"))
        for queueName in queueEvents:
            packets = device.getOutputQueue(queueName).tryGetAll()
            if len(packets) > 0:
                latestPacket[queueName] = packets[-1]

        if latestPacket["rgb"] is not None:
            if (time.time() - start_time1) >= 1 :
                fps1=counter1
                counter1 = 0
                start_time1 = time.time()
            frameRgb = latestPacket["rgb"].getCvFrame()
            cv2.putText(frameRgb, str(fps1)+' '+str(camRgb.getVideoSize()), (7, 70), font, 1, (100, 255, 0), 1, cv2.LINE_AA)
            cv2.imshow(rgbWindowName, frameRgb)

        if latestPacket["depth"] is not None:
            frameDepth = latestPacket["depth"].getFrame()
            maxDisparity = stereo.initialConfig.getMaxDisparity()
            # Optional, extend range 0..95 -> 0..255, for a better visualisation
            if 1: frameDepth = (frameDepth * 255. / maxDisparity).astype(np.uint8)
            # Optional, apply false colorization
            if 1: frameDepth = cv2.applyColorMap(frameDepth, cv2.COLORMAP_HOT)
            frameDepth = np.ascontiguousarray(frameDepth)
            if (time.time() - start_time2) >= 1 :
                fps2=counter2
                counter2 = 0
                start_time2 = time.time()
            cv2.putText(frameDepth, str(fps2)+' '+str(camRgb.getVideoSize()), (7, 70), font, 1, (100, 255, 0), 1, cv2.LINE_AA)
            cv2.imshow(depthWindowName, frameDepth)
    

        # Blend when both received
        if frameRgb is not None and frameDepth is not None:
            # Need to have both frames in BGR format before blending
            if len(frameDepth.shape) < 3:
                frameDepth = cv2.cvtColor(frameDepth, cv2.COLOR_GRAY2BGR)
            blended = cv2.addWeighted(frameRgb, rgbWeight, frameDepth, depthWeight, 0)
            if (time.time() - start_time3) >= 1 :
                fps3=counter3
                counter3 = 0
                start_time3 = time.time()
            cv2.putText(blended, str(fps3)+' '+str(camRgb.getVideoSize()), (7, 70), font, 1, (100, 255, 0), 1, cv2.LINE_AA)
            cv2.imshow(blendedWindowName, blended)
            frameRgb = None
            frameDepth = None

        if cv2.waitKey(1) == ord('q'):
            break
        
