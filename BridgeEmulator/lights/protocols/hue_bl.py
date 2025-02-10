import asyncio
import logManager
import HueBLE
from bleak import BleakScanner
from HueBLE import HueBleLight
from functions.colors import convert_xy
logging = logManager.logger.get_logger(__name__)

async def connect(address):    
    device = await BleakScanner.find_device_by_address(address)
    return HueBLE.HueBleLight(device)

def set_light(light, data):
    address = light.protocol_cfg["ip"]
    with asyncio.Runner() as runner:
        bl_light = runner.run(connect(address))
        for key, value in data.items():
            if key == "on":
                runner.run(bl_light.set_power(value))
            if key == "bri":
                runner.run(bl_light.set_brightness(value))
            if key == "xy":
                color = convert_xy(value[0], value[1], light.state["bri"])
                runner.run(bl_light.set_colour_xy(color[0], color[1]))

def get_light_state(light):
    address = light.protocol_cfg["ip"]
    state = {"on": False}
    with asyncio.Runner() as runner:
        try:
            bl_light = runner.run(connect(address))
            state["on"] = runner.run(bl_light.poll_power_state())
            state["xy"] = runner.run(bl_light.poll_colour_xy())
            if bl_light.supports_colour_xy:
                state["colormode"] = "xy"
            elif bl_light.supports_colour_temp:
                state["colormode"] = "ct"
            elif bl_light.supports_brightness:
                state["bri"] = runner.run(bl_light.poll_brightness())
        except Exception as e:
            logging.warning(e)
            return { 'reachable': False }
    
    return state

async def discover_lights():
    bl_lights = [HueBleLight(l) for l in await HueBLE.discover_lights()]
    connected_lights = []
    for l in bl_lights:
        is_connected = await l.connect()
        if is_connected:
            await l.poll_manufacturer()
            await l.poll_model()
            await l.poll_light_name()
            logging.debug(f"Connected to {l.manufacturer}:{l.model}:{l.name}")
            connected_lights.append(l)
        else:
            logging.error(f"Unable to connect to {l.name}")

    return connected_lights
    

def discover(detectedLights):
    logging.debug("hue_bl: <discover> invoked!")
    try:
        lights = asyncio.run(discover_lights())

        if len(lights) > 0:
            logging.debug(f"Discovered {len(lights)} Hue bluetooth light(s).")
        for l in lights:
            detectedLights.append({"protocol": "hue_bl", "name": l.name, "modelid": l.model, "protocol_cfg": {"ip": l.address, "modelid": l.model, "id": l.address, "uniqueid": l.address}})        
    except Exception as e:
        logging.error("Error connecting to BLE light: %s", e)

    logging.debug(f"detected_lights: {detectedLights}")
