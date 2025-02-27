from pickle import FALSE
from socketserver import ThreadingUnixDatagramServer
from sre_constants import IN
from traceback import print_exc
import requests
import geopy.distance
import time
import sys
from gps import *
from time import sleep
import RPi.GPIO as GPIO
from gpiozero import Buzzer
from datetime import datetime
import os
from gtts import gTTS
from io import BytesIO
import traceback
from datetime import date


from time import *
import time
import threading
 


import numpy
import math

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#This code is released under the terms of the unlicense: https://unlicense.org/
#Author github.com/lexfp

# Disclaimer: This code is not pretty. It is written like a script since that is what it is. 
#DUMP1090_URL = 'http://127.0.0.1/dump1090-fa/data/aircraft.json'
DUMP1090_URL = 'http://127.0.0.1/tar1090/data/aircraft.json'
UNKNOWN = 'Unknown'
LATITUDE = 'lat'
LONGTITUDE = 'lon'
BUZZER_PIN = 17
# seconds between each check
INTERVAL_SECONDS = 3
# set this to false if you don't want a long beep on initial gps lock
initialGPSLockBeep=True 
# I keep this value large so I know the app is running since it will always beep once.
# you can set the value lower to have a quieter system and a 3rd perimeter
OUTER_PERIMETER_ALARM_MILES = 2.0
# middle perimeter trigger sets of 2 beeps
MIDDLE_PERIMETER_ALARM_MILES = 1.5
# inner perimeter trigger sets of 3 beeps
INNER_PERIMETER_ALARM_MILES = 1
# upper limit of altitude at which you want to monitor aircraft
ALTITUDE_ALARM_FEET = 2000.0
running = True
#gpsd = gps(mode=WATCH_ENABLE | WATCH_NEWSTYLE)
#print('latitude\tlongitude\ttime utc\t\t\taltitude\tepv\tept\tspeed\tclimb') # '\t' = TAB to try and output the data in columns.

buzzer = Buzzer(BUZZER_PIN)
lastKnownLat=UNKNOWN
lastKnownLon=UNKNOWN

DEFAULTLAT  = 33.635029
DEFAULTLON = -117.842218

GPS_lock=False

m_iteration_number=0

USE_BUZZER=True
TTS=True

NUM_GPS_TRIES_UNTIL_DEFAULT=10

# the number of iterations we should try to reuse the last known position 
# set this to -1 if you plan on relocating the unit to a location with poor GPS 
# reception once initial position is established and you don't plan on moving around
# then it will never need the GPS coordinates again if they are not available
LAST_KNOWN_POSITION_REUSE_TIMES = -1
lastKnownPosReuse=0
failedGPSTries=0

# internet status
internet_is_connected = False

# GPS thread
gpsdthread = None #seting the global variable

class GpsPoller(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global gpsdthread #bring it in scope
    gpsdthread = gps(mode=WATCH_ENABLE) #starting the stream of info
    self.current_value = None
    self.running = True #setting the thread running to true
 
  def run(self):
    global gpsdthread
    while gpsp.running:
      gpsdthread.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer
      sleep(0.1)

def getPositionData(gps):
    nx = gpsd.next()
    # For a list of all supported classes and fields refer to:
    # https://gpsd.gitlab.io/gpsd/gpsd_json.html
    global lastKnownLat
    global lastKnownLon
    global lastKnownPosReuse
    if nx['class'] == 'TPV':
        lastKnownLat = getattr(nx, LATITUDE, UNKNOWN)
        lastKnownLon = getattr(nx, LONGTITUDE, UNKNOWN)
        lastKnownPosReuse=0 #reset counter since we refreshed coords
        #print "Your position: lon = " + str(longitude) + ", lat = " + str(latitude)
        return (lastKnownLat, lastKnownLon)
    else:
        #print "NON TPV gps class encountered: "+nx['class']
        if LAST_KNOWN_POSITION_REUSE_TIMES < 0:
            return (lastKnownLat, lastKnownLon)
        elif lastKnownPosReuse < LAST_KNOWN_POSITION_REUSE_TIMES:
            lastKnownPosReuse += 1
            return (lastKnownLat, lastKnownLon)
        else:
    	    return(UNKNOWN,UNKNOWN)

def getPositionDataUsingThread():
    ##print('getPositionDataUsingThread called')
    global lastKnownLat
    global lastKnownLon
    global lastKnownPosReuse  
    global gpsdthread
    # print(gpsdthread.fix.mode, gpsdthread.fix.latitude , gpsdthread.fix.longitude, datetime.now())
    if gpsdthread.fix.mode == 3: # fix
        ##print('fix mode = 3')
        lastKnownPosReuse=0 #reset counter since we refreshed coords
        lastKnownLat=gpsdthread.fix.latitude
        lastKnownLon=gpsdthread.fix.longitude
        ##print('getPositionDataUsingThread returning mode 3')
        return (lastKnownLat, lastKnownLon)
    else: #  no fix
        ##print('fix mode != 3')
        if LAST_KNOWN_POSITION_REUSE_TIMES < 0:
            ##print('getPositionDataUsingThread returning no fix a')
            return (lastKnownLat, lastKnownLon)
        elif lastKnownPosReuse < LAST_KNOWN_POSITION_REUSE_TIMES:
            ##print('LAST_KNOWN_POSITION_REUSE_TIMES < 0:')
            lastKnownPosReuse += 1
            ##print('getPositionDataUsingThread returning no fix b')
            return (lastKnownLat, lastKnownLon)
        else:
            ##print('LAST_KNOWN_POSITION_REUSE_TIMES < 0:')
            return(UNKNOWN,UNKNOWN)


# def getPositionDataFromThread(gps):
#     nx = gpsd.next()
#     # For a list of all supported classes and fields refer to:
#     # https://gpsd.gitlab.io/gpsd/gpsd_json.html
#     global lastKnownLat
#     global lastKnownLon
#     global lastKnownPosReuse
#     if nx['class'] == 'TPV':
#         lastKnownLat = getattr(nx, LATITUDE, UNKNOWN)
#         lastKnownLon = getattr(nx, LONGTITUDE, UNKNOWN)
#         lastKnownPosReuse=0 #reset counter since we refreshed coords
#         #print "Your position: lon = " + str(longitude) + ", lat = " + str(latitude)
#         return (lastKnownLat, lastKnownLon)
#     else:
#         #print "NON TPV gps class encountered: "+nx['class']
#         if LAST_KNOWN_POSITION_REUSE_TIMES < 0:
#             return (lastKnownLat, lastKnownLon)
#         elif lastKnownPosReuse < LAST_KNOWN_POSITION_REUSE_TIMES:
#             lastKnownPosReuse += 1
#             return (lastKnownLat, lastKnownLon)
#         else:
    	    # return(UNKNOWN,UNKNOWN)

def buzz(wait=0.1):
    if USE_BUZZER == True:
        buzzer.on()
        sleep(wait)
        buzzer.off()
    else:
        sleep(wait)
    
    
    sleep(0.2)

def checkRadar():
    global failedGPSTries
    global gpsd
    global GPS_lock
    global initialGPSLockBeep

    #homecoords = getPositionData(gpsd)
    homecoords = getPositionDataUsingThread()
    #x = datetime.now()
    #print(x)
    #print("time= ",datetime.datetime.now())
    ##print('getPositionDataUsingThread returned')
    
    ##print(datetime.now(), homecoords)
    ##print('checking if coords make sense')
    if not ((homecoords[0] == UNKNOWN) or (homecoords[1] == UNKNOWN)): # we have a good gps lock!
        failedGPSTries = 0
        GPS_lock=True
    if (homecoords[0] == UNKNOWN) or (homecoords[1] == UNKNOWN):
        GPS_lock=False
        print("Cannot determine GPS position yet...try #"+str(failedGPSTries))
        #sleep(1)
        failedGPSTries += 1
        if failedGPSTries < NUM_GPS_TRIES_UNTIL_DEFAULT:
            return # keep trying up to 10ish tries
        if failedGPSTries == NUM_GPS_TRIES_UNTIL_DEFAULT: # inform user no lock, using default lat/lon
            text_to_say_about_no_gps='No GPS lock. Using default position.'
            tts_depending_on_internet(text_to_say_about_no_gps)
            initialGPSLockBeep == True
        if failedGPSTries >= NUM_GPS_TRIES_UNTIL_DEFAULT: # lots of tries, go for default
            homecoords=(DEFAULTLAT, DEFAULTLON)
    ##print('did check if coords make sense')

    if initialGPSLockBeep == True and GPS_lock == True:
        initialGPSLockBeep=False
        print("GPS LOCK: ", homecoords, datetime.now())
        buzz(1)
        buzz(1)
        #print 'gps lock, calling tts'
        tts_depending_on_internet("GPS Lock.")
        #print 'called tts'
        sleep(2)
    r = requests.get(DUMP1090_URL)
    ##print('getting airplane data')
    try:
        airplanes = r.json()
    except:
        print('Error while getting airplane data')
        return
    ##print('got airplane data, checking alarm conditions')
    outerAlarmTriggered = False
    middleAlarmTriggered = False
    innerAlarmTriggered = False
    ##print('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX')
    #print(airplanes)
    ##print('YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY')
    
    for airplane in airplanes['aircraft']:
        try:
            m_alt_data_is_valid=False
            m_lat_lon_data_is_valid=False
            m_category_data_is_valid=False
            m_aircraft_is_a_helicopter=False
            ##print('+++++++++++++++++++++')
            #print('airplane.keys()=')
            #print(airplane.keys())
            ##print('---------------------')
            ##print('checking alt_baro')
            if 'category' in airplane.keys():
                m_type_data_is_valid=True
                #print('Category = ',airplane["category"])
                if airplane["category"]=="A7":
                    m_aircraft_is_a_helicopter=True
                    



            if 'alt_baro' in airplane.keys():
                altitude = airplane["alt_baro"]
                ##print('altitude =', altitude)
                ##print('type(altitude) = ',type(altitude))
                if altitude!='ground':
                    m_alt_data_is_valid=True

            ##print('checking LATITUDE')
            if LATITUDE in airplane.keys():
                planecoords = (airplane[LATITUDE], airplane[LONGTITUDE])
                m_lat_lon_data_is_valid=True
            # altitude = int(airplane["alt_baro"])
            # planecoords = (airplane[LATITUDE], airplane[LONGTITUDE])
            #print(altitude,planecoords)
            ##print('if valid...')
            ##print(m_alt_data_is_valid,m_lat_lon_data_is_valid)
            if m_alt_data_is_valid==True and m_lat_lon_data_is_valid==True:
                ##print('valid')
                distanceToPlane = geopy.distance.geodesic(homecoords, planecoords).miles
                bearing_to_plane=get_bearing(homecoords[0], homecoords[1], airplane[LATITUDE], airplane[LONGTITUDE])
                # print('Alt = ',altitude,' lat/lon = ',planecoords,'dist =  ',distanceToPlane, 'mi. bearing = ',bearing_to_plane)
                #print('Alt = ',altitude,' lat/lon = ',planecoords,'dist =   %.0f' % distanceToPlane, 'mi. bearing = %.0f' % bearing_to_plane)
                #print(altitude,planecoords)
                if altitude < ALTITUDE_ALARM_FEET:
                    if distanceToPlane < INNER_PERIMETER_ALARM_MILES:
                        innerAlarmTriggered = True
                        #print 'Inner alarm triggered by '+airplane['flight']+' at '+str(datetime.now())+' with distance '+str(distanceToPlane)+ 'at bearing' + str(bearing_to_plane) + 'degrees.'
                        auralreport(distanceToPlane,altitude,bearing_to_plane,m_aircraft_is_a_helicopter)
                    elif distanceToPlane < MIDDLE_PERIMETER_ALARM_MILES:
                        middleAlarmTriggered = True
                        #print 'Middle alarm triggered by '+airplane['flight']+' at '+str(datetime.now())+' with distance '+str(distanceToPlane)+ 'at bearing' + str(bearing_to_plane) + 'degrees.'
                        auralreport(distanceToPlane,altitude,bearing_to_plane,m_aircraft_is_a_helicopter)
                    elif distanceToPlane < OUTER_PERIMETER_ALARM_MILES:
                        outerAlarmTriggered = True
                        auralreport(distanceToPlane,altitude,bearing_to_plane,m_aircraft_is_a_helicopter)
                        #print 'Outer alarm triggered by '+airplane['flight']+' at '+str(datetime.now())+' with distance '+str(distanceToPlane)+ 'at bearing' + str(bearing_to_plane) + 'degrees.'   
        except KeyError:
            print('Error checking airplane conditions:')
            print(KeyError)
            pass
    #print('did check alarm conditions, buzzing if needed')
    if innerAlarmTriggered:
        buzz(1)
        buzz(1)
        buzz(1)
    elif middleAlarmTriggered:
        buzz(1)
        buzz(1)
    elif outerAlarmTriggered:
        buzz(1)
    #print('done with check radar, returning...')


def testgps(): # from: https://ozzmaker.com/using-python-with-a-gps-receiver-on-a-raspberry-pi/
    report = gpsd.next() #
    if report['class'] == 'TPV':
        print(getattr(report,'lat',0.0),"\t",)
        print(getattr(report,'lon',0.0),"\t",)
        print(getattr(report,'time',''),"\t",)
        print(getattr(report,'alt','nan'),"\t\t",)
        print(getattr(report,'epv','nan'),"\t",)
        print(getattr(report,'ept','nan'),"\t",)
        print(getattr(report,'speed','nan'),"\t",)
        print(getattr(report,'climb','nan'),"\t")
    return

def auralreport(m_distance,m_alt,m_bearing,m_is_this_a_helicopter):
    #buzz(0.5)
    distance_string = "{:.1f}".format(m_distance)
    m_bearing_string = "{:.0f}".format(m_bearing)
   
    deltadegrees=22.5
    if(m_bearing<deltadegrees):
        m_direction_text='north'
    elif((m_bearing>=(45-deltadegrees))) and (m_bearing<(45+deltadegrees)):
        m_direction_text='northeast'
    elif((m_bearing>=(90-deltadegrees))) and (m_bearing<(90+deltadegrees)):
        m_direction_text='east'
    elif((m_bearing>=(135-deltadegrees))) and (m_bearing<(135+deltadegrees)):
        m_direction_text='southeast'
    elif((m_bearing>=(180-deltadegrees))) and (m_bearing<(180+deltadegrees)):
        m_direction_text='south'
    elif((m_bearing>=(225-deltadegrees))) and (m_bearing<(225+deltadegrees)):
        m_direction_text='southwest'
    elif((m_bearing>=(270-deltadegrees))) and (m_bearing<(270+deltadegrees)):
        m_direction_text='west'
    elif((m_bearing>=(315-deltadegrees))) and (m_bearing<(315+deltadegrees)):
        m_direction_text='northwest'
    elif(m_bearing>=(360-deltadegrees)):
        m_direction_text='north'
    
    #texttosay='Attention: Aircraft detected with to the '+ m_direction_text+ ' with altitude '+str(m_alt) +' feet, at '+  distance_string + ' miles. At bearing '+m_bearing_string +" degrees."
    m_kind_string=""
    if m_is_this_a_helicopter==False:
        m_kind_string="Aircraft "
    else:
        m_kind_string="Helicopter "
    if GPS_lock==True:
        texttosay=m_kind_string +' detected ' + distance_string + ' miles to the ' + m_direction_text+ ' at altitude '+str(m_alt) +' feet.'
    else:
        texttosay=m_kind_string +' detected ' + distance_string + ' miles to the ' + m_direction_text+ 'of default position at altitude '+str(m_alt) +' feet.'
        print('**********************')
    print(datetime.now(), texttosay)
    tts_depending_on_internet(texttosay)

def tts_depending_on_internet(m_text_to_say):
    if TTS == True:    
        if (internet_is_connected==True):
            print('calling gtts')
            tts_google(m_text_to_say)
            print('did call gtts')
        else: 
            print('calling festival')
            tts_festival(m_text_to_say)
            print ('did call festival')
    else:
        return

def tts_festival(m_text_to_say):
    systemcommandtosend='echo "'+m_text_to_say+'"| festival --tts '
    os.system(systemcommandtosend)   
    
def tts_google(m_text_to_say):
    # see xyz
    # for not using file see :
    # https://gtts.readthedocs.io/en/latest/module.html#playing-sound-directly
    language = 'en'
    #myobj = gTTS(text=m_text_to_say, lang=language,  slow=False) # standard
    #myobj = gTTS(text=m_text_to_say, lang=language, tld='ie', slow=False) # Irish
    #myobj = gTTS(text=m_text_to_say, lang=language, tld='co.uk', slow=False) # UK
    #print 'google tts starting'
    try:
        myobj = gTTS(text=m_text_to_say, lang=language, tld='com.au', slow=False) # Australian
    except:
        speed(0.1)
        pass
    #print 'google tts started'
    try:
        myobj.save("/home/pi/fpvradar/tts.mp3")
    except:
        sleep(0.1)
        pass
    #print 'mp3 saved'
    os.system("mpg321 /home/pi/fpvradar/tts.mp3  >  /dev/null 2>&1")
    #print 'mp3 played'
    #mp3_fp = BytesIO()
    #tts = gTTS('hello', lang='en')
    #tts.write_to_fp(mp3_fp)

def get_bearing(lat1, long1, lat2, long2):
    # from https://stackoverflow.com/questions/54873868/python-calculate-bearing-between-two-lat-long
    # see also:
    # from https://www.movable-type.co.uk/scripts/latlong.html
    # https://pypi.org/project/pyproj/

    dLon = (long2 - long1)
    x = math.cos(math.radians(lat2)) * math.sin(math.radians(dLon))
    y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(math.radians(dLon))
    brng = numpy.arctan2(x,y)
    brng = numpy.degrees(brng) + 360
    if(brng<0):
        brng=brng+360
    if(brng>360):
        brng=brng-360
    return brng


def check_internet():
    #os.seteuid(pi)
    #os.system('whoami')
    # from: https://betterprogramming.pub/how-to-check-the-users-internet-connection-in-python-224e32d870c8
    url='http://google.com'
    timeout=INTERVAL_SECONDS
    #sleep(10)
    try:
        r = requests.head(url, timeout=timeout)
        #print 'Internet is CONNECTED.'
        #sleep(INTERVAL_SECONDS)
        return True
    except requests.ConnectionError as ex:
        #print 'Internet is NOT CONNECTED.'
        print(ex)
        return False
    return False

try:
    print('-------------------------------------------------------------')
    print("Application started!")

    print('-------------------------------------------------------------')
    print("Launching GPS thread")
    gpsp = GpsPoller() # create the thread
    gpsp.start() # start it up
    print("GPS thread launched!")
    print('-------------------------------------------------------------')

    ##internet_is_connected=check_internet()
    

    while running:
        print('#################################################################')
        print('m_iteration_number = ',m_iteration_number)
        m_iteration_number=m_iteration_number+1
        ##print('calling checkradar')
        checkRadar()
        ##print('called checkradar')
        #checkRadartest()
        #nx = gpsd.next()
        #testgps()
        sys.stdout.flush()
        #print(gpsdthread.fix.mode, gpsdthread.fix.latitude , gpsdthread.fix.longitude, datetime.now())
        #time.sleep(INTERVAL_SECONDS)
        ##print('calling internet_is_connected')
        sys.stdout.flush()
        internet_is_connected= check_internet()
        ##print('called internet_is_connected')
        ##print('waiting')
        sys.stdout.flush()
        sleep(INTERVAL_SECONDS)
        ##print('done waiting')
        print('----------------------------------------------------------------')
        sys.stdout.flush()


except (ValueError):
	#sometimes we get errors parsing json
    print('some error:')
    print(ValueError)
    pass

except (KeyboardInterrupt):
    running = False
    print("Applications closed!")

except:
    print("Caught generic exception - continuing")
    print("Initializing new GPS object...")
    # gpsd = gps(mode=WATCH_ENABLE | WATCH_NEWSTYLE)
    # # https://stackoverflow.com/questions/1483429/how-to-print-an-exception-in-python
    traceback.print_exc()
    sys.stdout.flush()
    # GPS_lock=False
    # initialGPSLockBeep=True
    pass

