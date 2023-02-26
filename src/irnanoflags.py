from nanoleafapi import Nanoleaf
import irsdk
from threading import Thread
import logging
import time
from enum import Enum
import configparser
import re

SCRIPTNAME = "iRNanoFlags"
flags = ""

# initate everything we need for thread safe logging to stdout
logger = logging.getLogger(SCRIPTNAME)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# add formatter to ch
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.info("---------------------------------------------")
logger.info("%s" % (SCRIPTNAME, ))
logger.info("---------------------------------------------")

class IRacingMemoryFlagType(Enum):
    # global flags
    checkered = 0x0001
    white = 0x0002
    green = 0x0004
    yellow = 0x0008
    red = 0x0010
    blue = 0x0020
    debris = 0x0040
    crossed = 0x0080
    yellow_waving = 0x0100
    one_lap_to_green = 0x0200
    green_held = 0x0400
    ten_to_go = 0x0800
    five_to_go = 0x1000
    random_waving = 0x2000
    caution = 0x4000
    caution_waving = 0x8000

    # drivers black flags
    black = 0x010000
    disqualify = 0x020000
    servicible = 0x040000  # car is allowed service (not a flag)
    furled = 0x080000
    repair = 0x100000

    # start lights
    #start_hidden = 0x10000000
    #start_ready = 0x20000000
    #start_set = 0x40000000
    #start_go = 0x80000000


class IRacingGUIFlagType(Enum):
    IRACING_NO_FLAG = 0
    IRACING_BLUE_FLAG = 1
    IRACING_MEATBALL_FLAG = 2
    IRACING_BLACK_FLAG = 3
    IRACING_YELLOW_FLAG = 4
    IRACING_GREEN_FLAG = 5
    IRACING_WHITE_FLAG = 6
    IRACING_CHEQUERED_FLAG = 7
    IRACING_RED_FLAG = 8


# this is our State class, with some helpful variables
class State:

    def __init__(self):
        self.reset()

    def reset(self):
        # set all members to their initial value
        self.ir_connected = False
        self.last_car_setup_tick = -1
        self.CURRENT_FLAG = 0x0004
        self.CURRENT_EFFECT = ""
        self.DEFAULT_EFFECT = ""
        self.SET_NANOLEAF = "BLUB"


# here we check if we are connected to iracing
# so we can retrieve some data
def check_iracing():
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False
        # don't forget to reset your State variables
        state.last_car_setup_tick = -1
        # we are shutting down ir library (clearing all internal variables)
        ir.shutdown()
        logger.info('iRacing - irsdk disconnected')
    elif not state.ir_connected and ir.startup() and ir.is_initialized and ir.is_connected:
        state.ir_connected = True
        logger.info('iRacing - irsdk connected')
        # set state nanoleaf default effect
        state.SET_NANOLEAF = config["EFFECTS"]["default"]
        if ir['WeekendInfo']:
            tracklength = ir["WeekendInfo"]["TrackLength"]
            try:
                tracklength_km = re.search('([\d\.]+?)\ km.*$', tracklength).group(1)
            except AttributeError:
                tracklength_km = ''
            state.track_length = float(tracklength_km) * 1000
            logger.info('iRacing - The next events Category: %s'
                  % (ir['WeekendInfo']['Category'], ))
            logger.info("iRacing - Track: %s, %s, %s"
                  % (ir['WeekendInfo']['TrackDisplayName'],
                  ir['WeekendInfo']['TrackCity'],
                  ir['WeekendInfo']['TrackCountry']))

def nanoWorker(r, stop):
    logger.info("Nanoleaf - Thread starts")
    nl = Nanoleaf(config["NANOLEAF"]["nanoleaf_ip"])
    nl.power_on()
    current_effect = ""
    known_effects = nl.list_effects()
    while not stop():
        current_effect = nl.get_current_effect()
        if state.SET_NANOLEAF:
            if not current_effect == state.SET_NANOLEAF:
                if state.SET_NANOLEAF in known_effects:
                    nl.set_effect(state.SET_NANOLEAF)
                    time.sleep(int(config["NANOLEAF"]["max_duration"]))
                    nl.set_effect(config["EFFECTS"]["default"])
                    state.SET_NANOLEAF = "DONE"

        time.sleep(1)
    logger.info("Nanoleaf - Thread ends")


def irtcprMain(r, stop):
    memory_flags = []
    logger.info("Main - Thread starts")
    while not stop():
        if not state.ir_connected:
            try:
                ir.startup()
            except Exception as e:
                logger.critical("cannot startup IRSDK: %s" % (e,))
                exit(1)
        try:
            check_iracing()
        except Exception as e:
            logger.critical("iRacingWorker - Exception while checking iracing: %s" % (e,))

        if state.ir_connected:
            session_flag = ir['SessionFlags']
            if session_flag:
                for flag in IRacingMemoryFlagType:
                    if IRacingMemoryFlagType(flag).value & session_flag == IRacingMemoryFlagType(flag).value:
                        memory_flags.append(flag)

                        if IRacingMemoryFlagType.blue in memory_flags:
                            logger.info("blue flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["blue"]
                        if IRacingMemoryFlagType.repair in memory_flags:
                            logger.info("meatball flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["meatball"]
                        if IRacingMemoryFlagType.black in memory_flags:
                            logger.info("black flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["black"]
                        if IRacingMemoryFlagType.yellow in memory_flags or IRacingMemoryFlagType.yellow_waving in memory_flags:
                            logger.info("yellow flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["yellow"]
                        if IRacingMemoryFlagType.caution in memory_flags or IRacingMemoryFlagType.yellow_waving in memory_flags:
                            logger.info("caution flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["caution"]
                        if IRacingMemoryFlagType.caution_waving in memory_flags or IRacingMemoryFlagType.yellow_waving in memory_flags:
                            logger.info("caution_waving flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["caution_waving"]
                        if IRacingMemoryFlagType.green in memory_flags:
                            logger.info("green flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["green"]
                        if IRacingMemoryFlagType.white in memory_flags:
                            logger.info("white flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["white"]
                        if IRacingMemoryFlagType.checkered in memory_flags:
                            logger.info("checkered flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["checkered"]
                        if IRacingMemoryFlagType.red in memory_flags:
                            logger.info("red flag")
                            state.SET_NANOLEAF = config["EFFECTS"]["red"]
                memory_flags = []

        time.sleep(1)
    logger.info("Main - Thread ends")

# read config
config = configparser.ConfigParser()
config.read("irnanoflags.ini")

try:
    nano = Nanoleaf(config["NANOLEAF"]["nanoleaf_ip"])
except Exception as ne:
    logger.critical("cannot connect to your nanoleaf.")
    logger.critical("check ip in ini file and repair your nanoleaf")
    logger.critical("(hold power button 5-7 seconds and restart this tool)")
    exit(1)

try:
    ir = irsdk.IRSDK(parse_yaml_async=True)
except Exception as e:
    logger.critical("cannot initialize IRSDK: %s" % (e,))

# initialize our State class
state = State()
# state.reset()

stop_main_thread = False

# first we need to open the main thread, which will
# check if we can connect to the iracing api
irtcprMainThread = Thread(target=irtcprMain, args=(flags, lambda: stop_main_thread, ))
nanoLeafThread = Thread(target=nanoWorker, args=(flags, lambda: stop_main_thread, ))
irtcprMainThread.start()
nanoLeafThread.start()
input("any key to end\n")
stop_main_thread = True

irtcprMainThread.join()
nanoLeafThread.join()
