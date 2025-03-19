import dexcomCalls
import matplotLibActions
#
#from PIL import Image, ImageFont, ImageDraw
#
#from font_intuitive import Intuitive

#from inky import InkyPHAT, InkyWHAT
#from waveshare_epd import epd2in13_V3
#    epd = epd2in13_V3.EPD()
#    logging.info("init and Clear")
#    epd.init()
#    epd.Clear(0xFF)
#from config import matplotImagePath, inkyPhatColour, inkyPhatLastImageShown, saveLastImageShown
#
#def displayText(text, position, size, offsetx, offsety):
   # Put title text on Pi
#   draw = ImageDraw.Draw(img)
#   font = ImageFont.truetype(Intuitive, size)
#   w, h = font.getsize(text)
#    x = 0
#    y = offsety
#    if position == "centered":
#        x = (inky_display.WIDTH / 2) - (w / 2)
#
#    if position == "right":
#        x = inky_display.WIDTH - w - offsetx
#
#    draw.text((x, y), text, inky_display.BLACK, font)
#    return w, h
#
#
sgvs, dates, delta = dexcomCalls.getDataFromNightscout()
#
matplotLibActions.createSGVPlot(sgvs, dates)
#
# Setup objects
#inky_display = InkyPHAT(inkyPhatColour)
#img = Image.open(matplotImagePath)
#img = img.convert('L')
#img = img.point(lambda x: 255 if x < 240 else 0, '1')
#img = img.resize((inky_display.WIDTH, inky_display.HEIGHT))
#
#if delta > 0:
#    deltaStr = "+%d" % delta
#else:
#    deltaStr = "%d" % delta
#
#w, hdelta = displayText(deltaStr, "right", 20, 0, 0)
#wmg, hmgdl = displayText("mg/dl", "right", 10, 0, hdelta)
#wsgv, h = displayText(str(sgvs[-1]), "right", 32, wmg + 2, 0)
#displayText(dates[-1], "right", 12, 0, hdelta + hmgdl)
import sys
import os
import time
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
import logging

# Add the Waveshare EPD library to the system path
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
else:
    print("Error: Cannot find Waveshare EPD library.  Please make sure the library files are in a directory named 'lib' in the same directory as this script.")
    sys.exit(1)

from waveshare_epd import epd2in13_V2  # Import the specific EPD driver

# Configuration
DEBUG = True  # Set to False for production
#NIGHTSCOUT_URL = "YOUR_NIGHTSCOUT_URL"  # Replace with your Nightscout URL, include https://
#NIGHTSCOUT_API_SECRET = "YOUR_API_SECRET" # Replace with your Nightscout API secret, if required
LOCATION = "Home"  # Or any identifier you want
SLEEP_DURATION = 300  # Time between updates in seconds (e.g., 300 for 5 minutes)
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' # Path to a font on your system

# Logging setup
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_nightscout_data():
    """
    Fetches the latest blood glucose data from Nightscout.
    Handles errors and returns None if data retrieval fails.
    """
    try:
        headers = {}
        if NIGHTSCOUT_API_SECRET:
            headers['api-secret'] = NIGHTSCOUT_API_SECRET
        url = f"{NIGHTSCOUT_URL}/api/v1/entries.json?count=1"
        response = requests.get(url, headers=headers, timeout=10)  # Added timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        if not data:
            logger.warning("Nightscout returned empty data.")
            return None
        return data[0]  # Return only the latest entry

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Nightscout: {e}")
        return None
    except (ValueError, KeyError, IndexError) as e:
        logger.error(f"Error parsing data from Nightscout: {e}")
        return None

def get_battery_level():
    """
    Gets the battery level.  This is a placeholder.
    In a real implementation, you would need to read this from a sensor
    connected to your Raspberry Pi (if you have one).
    For example, you might use a library to read from an ADC.
    """
    #  Replace this with code to read the actual battery level.
    #  This is just a placeholder that returns a random value.
    #  For example, if you had a sensor connected to ADC channel 0:
    #  import spidev
    #  spi = spidev.SpiDev()
    #  spi.open(0, 0)
    #  spi.max_speed_hz = 1000000
    #  def read_adc(channel):
    #      if channel < 0 or channel > 7:
    #          return -1
    #      spi_msg = [0x01, (0x08 + channel) << 4, 0x00]
    #      reply = spi.xfer2(spi_msg)
    #      return ((reply[1] & 0x03) << 8) | reply[2]
    #  adc_value = read_adc(0)
    #  battery_level = adc_value / 1023 * 100 # convert
    import random
    return random.randint(0, 100)  # Placeholder: returns a random percentage

def get_trend_arrow(change):
    """
    Determines the trend arrow based on the change in glucose value.
    """
    if change > 2:
        return '↑↑'  # Rapid rise
    elif change > 0.5:
        return '↑'   # Rise
    elif change < -2:
        return '↓↓'  # Rapid fall
    elif change < -0.5:
        return '↓'   # Fall
    else:
        return '→'   # Steady

def main():
    """
    Main function to fetch data, update display, and handle errors.
    """
    epd = None  # Initialize epd outside the try block
    try:
        logger.info("Initializing E-Paper display...")
        epd = epd2in13_V2.EPD()  # Initialize the EPD object
        epd.init()  # Initialize the display
        epd.Clear(0xFF)  # Clear the display (white)

        # Create a font object
        font = ImageFont.truetype(FONT_PATH, 24)  # Larger font
        font_large = ImageFont.truetype(FONT_PATH, 48)  # Even larger font for glucose

        logger.info("Starting Nightscout E-Paper display loop...")
        while True:
            start_time = time.time() # start time to calculate the loop duration
            try:
                # Get data
                nightscout_data = get_nightscout_data()
                battery_level = get_battery_level()

                if nightscout_data:
                    glucose_value = nightscout_data.get('sgv')
                    # Calculate change.  Use sgv if available, otherwise, try 'delta'
                    change = nightscout_data.get('delta')
                    if change is None:
                         change = nightscout_data.get('change')

                    trend_arrow = get_trend_arrow(change) if change is not None else '?'
                    last_updated = datetime.fromtimestamp(nightscout_data.get('date') / 1000).strftime('%H:%M')
                    logger.info(f"Glucose: {glucose_value}, Trend: {trend_arrow}, Last Updated: {last_updated}, Battery: {battery_level}")


                    # Create a new image
                    image = Image.new('1', (epd.width, epd.height), 255)  # 255: white, 0: black
                    draw = ImageDraw.Draw(image)

                    # Draw the glucose value (larger font)
                    glucose_text = str(glucose_value) if glucose_value is not None else "---"
                    glucose_width, glucose_height = font_large.getsize(glucose_text)
                    x_center = epd.width // 2
                    y_center = epd.height // 2 - 10 # adjust vertical
                    glucose_x = x_center - glucose_width // 2
                    glucose_y = y_center - glucose_height // 2
                    draw.text((glucose_x, glucose_y), glucose_text, font=font_large, fill=0)

                    # Draw the trend arrow
                    trend_x = glucose_x + glucose_width + 10  # Position to the right of glucose
                    trend_y = glucose_y + (glucose_height - font.getsize(trend_arrow)[1]) // 2 # Vertically align
                    draw.text((trend_x, trend_y), trend_arrow, font=font, fill=0)

                    # Draw "Last Updated" and time
                    updated_text = f"Last Updated: {last_updated}"
                    updated_width, updated_height = font.getsize(updated_text)
                    updated_x = x_center - updated_width // 2
                    updated_y = y_center + glucose_height // 2 + 5 # Position below glucose
                    draw.text((updated_x, updated_y), updated_text, font=font, fill=0)

                    # Draw battery level
                    battery_text = f"Battery: {battery_level}%"
                    battery_width, battery_height = font.getsize(battery_text)
                    battery_x = x_center - battery_width // 2
                    battery_y = epd.height - battery_height - 5  # Bottom
                    draw.text((battery_x, battery_y), battery_text, font=font, fill=0)

                    # Display the image
                    epd.display(epd.getbuffer(image))
                    epd.sleep()

                else:
                    logger.warning("No data received from Nightscout. Displaying error message.")
                    image = Image.new('1', (epd.width, epd.height), 255)
                    draw = ImageDraw.Draw(image)
                    draw.text((10, 50), "Error: No data from\nNightscout", font=font, fill=0)
                    draw.text((10, 100), "Check connection\nand URL.", font=font, fill=0)
                    epd.display(epd.getbuffer(image))
                    epd.sleep()

            except Exception as e:
                logger.exception(f"An error occurred: {e}") # Log the full exception
                if epd: # Check if epd is initialized
                   epd.init()
                   epd.Clear(0xFF)
                   image = Image.new('1', (epd.width, epd.height), 255)
                   draw = ImageDraw.Draw(image)
                   draw.text((10, 50), "General Error.", font=font, fill=0)
                   draw.text((10, 100), "Check logs.", font=font, fill=0)
                   epd.display(epd.getbuffer(image))
                   epd.sleep()

            # Sleep and update
            end_time = time.time()
            loop_duration = end_time - start_time
            sleep_time = max(0, SLEEP_DURATION - loop_duration) # Ensure не negative sleep
            logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("Exiting program. Cleaning up...")
        if epd:
            epd.init()  # Initialize so we can clear the display.
            epd.Clear(0xFF)  # Clear the display
            epd.sleep()
            epd.module_exit() # Safe exit
        logger.info("Cleanup complete.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        if epd:
            epd.init()
            epd.Clear(0xFF)
            epd.sleep()
            epd.module_exit()
        sys.exit(1)

if __name__ == "__main__":
    main()

if saveLastImageShown:
    img.save(inkyPhatLastImageShown, "PNG")
inky_display.set_image(img)
inky_display.show()
