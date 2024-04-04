# SPDX-FileCopyrightText: Copyright (c) 2023 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: MIT
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

# pip install pandas
# pip install paho-mqtt

import asyncio
import os
import omni.client
from pxr import Usd, Sdf, Gf
from pathlib import Path
import pandas as pd
import time
from paho.mqtt import client as mqtt_client
import random
import json
from omni.live import LiveEditSession, LiveCube, getUserNameFromToken

OMNI_HOST = os.environ.get("OMNI_HOST", "localhost")
OMNI_USER = os.environ.get("OMNI_USER", "ov")
if OMNI_USER.lower() == "omniverse":
    OMNI_USER = "ov"
elif OMNI_USER.lower() == "$omni-api-token":
    OMNI_USER = getUserNameFromToken(os.environ.get("OMNI_PASS"))

BASE_FOLDER = "omniverse://" + OMNI_HOST + "/Users/" + OMNI_USER + "/iot-samples"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
CONTENT_DIR = Path(SCRIPT_DIR).resolve().parents[1].joinpath("content")

messages = []
live_cube : LiveCube
stage : Usd.Stage


def log_handler(thread, component, level, message):
    # print(message)
    messages.append((thread, component, level, message))


def initialize_device_prim(live_layer, iot_topic):
    iot_root = live_layer.GetPrimAtPath("/iot")
    iot_spec = live_layer.GetPrimAtPath(f"/iot/{iot_topic}")
    if not iot_spec:
        iot_spec = Sdf.PrimSpec(iot_root, iot_topic, Sdf.SpecifierDef, "ConveyorBelt Type")
    if not iot_spec:
        raise Exception("Failed to create the IoT Spec.")

    # clear out any attrubutes that may be on the spec
    for attrib in iot_spec.attributes:
        iot_spec.RemoveProperty(attrib)

    IOT_TOPIC_DATA = f"{CONTENT_DIR}/{iot_topic}_iot_data.csv"
    data = pd.read_csv(IOT_TOPIC_DATA)
    data.head()

    # create all the IoT attributes that will be written
    attr = Sdf.AttributeSpec(iot_spec, "_ts", Sdf.ValueTypeNames.Double)
    if not attr:
        raise Exception(f"Could not define the attribute: {attrName}")

    # infer the unique data points in the CSV.
    # The values may be known in advance and can be hard coded
    grouped = data.groupby("Id")
    for attrName, group in grouped:
        attr = Sdf.AttributeSpec(iot_spec, attrName, Sdf.ValueTypeNames.Double)
        if not attr:
            raise Exception(f"Could not define the attribute: {attrName}")


async def initialize_async(iot_topic):
    # copy a the Conveyor Belt to the target nucleus server
    stage_name = f"{iot_topic}"
    local_folder = f"file:{CONTENT_DIR}/{stage_name}"
    stage_folder = f"{BASE_FOLDER}/{stage_name}"
    stage_url = f"{stage_folder}/crimp_machine.usd"

    global stage
    stage = Usd.Stage.Open(stage_url)
    if not stage:
        raise Exception(f"Could load the stage {stage_url}.")

    print("Open live session")
    live_session = LiveEditSession(stage_url)
    live_layer = await live_session.ensure_exists()

    print("Open session layer")
    session_layer = stage.GetSessionLayer()
    session_layer.subLayerPaths.append(live_layer.identifier)

    # set the live layer as the edit target
    print("Set target")
    stage.SetEditTarget(live_layer)

    #initialize_device_prim(live_layer, iot_topic)

    # place the cube on the conveyor
    #global live_cube
    #live_cube = LiveCube(stage)
    #live_cube.scale(Gf.Vec3f(0.5))
    #live_cube.translate(Gf.Vec3f(100.0, -30.0, 195.0))

    omni.client.live_process()
    return stage, live_layer

def write_to_live(live_layer, iot_topic, msg_content):
    # First split the topic and extract
    payload = json.loads(msg_content)
    segments = iot_topic.split("/")

    print( payload)

    global live_cube
    if segments[2] == "place":
        # Create the cube
        live_cube = LiveCube(stage)
    elif segments[2] == "remove":
        stage.RemovePrim("/World/cube")
    elif segments[2] == "translate":
        live_cube.translate(Gf.Vec3f(payload["X"], payload["Y"], payload["Z"]))

    omni.client.live_process()

# connect to mqtt broker
def connect_mqtt(iot_topic):
    topic = f"iot/{iot_topic}"

    # called when a message arrives
    def on_message(client, userdata, msg):
        msg_content = msg.payload.decode()
        print(f"Received `{msg_content}` from `{msg.topic}` topic")
        write_to_live(live_layer, msg.topic, msg_content)

    # called when connection to mqtt broker has been established
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            # connect to our topic
            print(f"Subscribing to topic: {topic}")
            client.subscribe(topic + "/#")
        else:
            print(f"Failed to connect, return code {rc}")

    # let us know when we've subscribed
    def on_subscribe(client, userdata, mid, granted_qos):
        print(f"subscribed {mid} {granted_qos}")

    # Set Connecting Client ID
    client = mqtt_client.Client(f"python-mqtt-{random.randint(0, 1000)}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.connect("localhost", 1883)
    client.loop_start()
    return client


def run(stage, live_layer, iot_topic):
    print("Connecting MQTT")

    mqtt_client = connect_mqtt(iot_topic)

    # play back the data in real-time
    #for next_time, group in grouped:
    while True:
        time.sleep(1)

    mqtt_client = None


if __name__ == "__main__":
    IOT_TOPIC = "HMI_Crimp"
    omni.client.initialize()
    omni.client.set_log_level(omni.client.LogLevel.DEBUG)
    omni.client.set_log_callback(log_handler)
    try:
        stage, live_layer = asyncio.run(initialize_async(IOT_TOPIC))
        run(stage, live_layer, IOT_TOPIC)
    except:
        print("---- LOG MESSAGES ---")
        print(*messages, sep="\n")
        print("----")
    finally:
        omni.client.shutdown()
