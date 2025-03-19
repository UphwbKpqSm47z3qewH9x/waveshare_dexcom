import sys
import os
import time
from datetime import datetime
import logging

# Add the Waveshare EPD library to the system path
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)
else:
    print("Error: Cannot find Waveshare EPD library.  Please make sure the library files are in a directory named 'lib' in the same directory as this script.")
    sys.exit(1)

from waveshare_epd import epd2in13_V2  # Import the specific EPD driver

# Import dexcomCalls
try:
    from dexcomCalls import get_dexcom_reading  # Import the function
except ImportError:
    print("Error: Cannot find dexcomCalls.py.  Please make sure it is in the same directory as this script, or in the PYTHONPATH.")
    sys.exit(1)

from PIL import Image, ImageDraw, ImageFont

# Configuration
DEBUG = True  # Set to False for production
# NIGHTSCOUT_URL = "YOUR_NIGHTSCOUT_URL"  # Replace with your Nightscout URL # Not used with direct Dexcom
# NIGHTSCOUT_API_SECRET = "YOUR_API_SECRET" # Replace with your Nightscout API secret, if required # Not used with direct Dexcom
DEXCOM_USERNAME = "deculpep"  # Replace with your Dexcom username
DEXCOM_PASSWORD = "d7tAV4q7b7iG8wTpHJBm"  # Replace with your Dexcom password
LOCATION = "Home"  # Or any identifier you want
SLEEP_DURATION = 300  # Time between updates in seconds (e.g., 300 for 5 minutes)
FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'  # Path to a font on your system

# Logging setup
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)



def get_battery_level():
    """
    Gets the battery level.  This is a placeholder.
    In a real implementation, you would need to read this from a sensor
    connected to your Raspberry Pi.
    """
    import random
    return random.randint(0, 100)  # Placeholder

def get_trend_arrow(trend):
    """
    Determines the trend arrow based on the Dexcom trend value.
    See https://developer.dexcom.com/trend-values for values
    """
    if trend == 1:
        return '↑↑'  # Rapid rise
    elif trend == 2:
        return '↑'   # Rise
    elif trend == 3:
        return '↗' # rise slightly
    elif trend == 4:
        return '→'   # Steady
    elif trend == 5:
        return '↘'  # fall slightly
    elif trend == 6:
        return '↓'   # Fall
    elif trend == 7:
        return '↓↓'  # Rapid fall
    else:
        return '?'   # Unknown

def main():
    """
    Main function to fetch data, update display, and handle errors.
    """
    epd = None
    try:
        logger.info("Initializing E-Paper display...")
        epd = epd2in13_V2.EPD()
        epd.init()
        epd.Clear(0xFF)

        # Create a font object
        font = ImageFont.truetype(FONT_PATH, 24)
        font_large = ImageFont.truetype(FONT_PATH, 48)

        logger.info("Starting Dexcom E-Paper display loop...")
        while True:
            start_time = time.time()
            try:
                # Get data from Dexcom
                dexcom_data = get_dexcom_reading(DEXCOM_USERNAME, DEXCOM_PASSWORD) # Use the function
                battery_level = get_battery_level()

                if dexcom_data:
                    glucose_value = dexcom_data.get('glucose')
                    trend_value = dexcom_data.get('trend')
                    trend_arrow = get_trend_arrow(trend_value)
                    last_updated = dexcom_data.get('datetime').strftime('%H:%M') # Format the datetime object
                    logger.info(f"Glucose: {glucose_value}, Trend: {trend_arrow}, Last Updated: {last_updated}, Battery: {battery_level}")

                    # Create a new image
                    image = Image.new('1', (epd.width, epd.height), 255)
                    draw = ImageDraw.Draw(image)

                    # Draw the glucose value
                    glucose_text = str(glucose_value) if glucose_value is not None else "---"
                    glucose_width, glucose_height = font_large.getsize(glucose_text)
                    x_center = epd.width // 2
                    y_center = epd.height // 2 - 10
                    glucose_x = x_center - glucose_width // 2
                    glucose_y = y_center - glucose_height // 2
                    draw.text((glucose_x, glucose_y), glucose_text, font=font_large, fill=0)

                    # Draw the trend arrow
                    trend_x = glucose_x + glucose_width + 10
                    trend_y = glucose_y + (glucose_height - font.getsize(trend_arrow)[1]) // 2
                    draw.text((trend_x, trend_y), trend_arrow, font=font, fill=0)

                    # Draw "Last Updated" and time
                    updated_text = f"Last Updated: {last_updated}"
                    updated_width, updated_height = font.getsize(updated_text)
                    updated_x = x_center - updated_width // 2
                    updated_y = y_center + glucose_height // 2 + 5
                    draw.text((updated_x, updated_y), updated_text, font=font, fill=0)

                    # Draw battery level
                    battery_text = f"Battery: {battery_level}%"
                    battery_width, battery_height = font.getsize(battery_text)
                    battery_x = x_center - battery_width // 2
                    battery_y = epd.height - battery_height - 5
                    draw.text((battery_x, battery_y), battery_text, font=font, fill=0)

                    # Display the image
                    epd.display(epd.getbuffer(image))
                    epd.sleep()

                else:
                    logger.warning("No data received from Dexcom. Displaying error message.")
                    image = Image.new('1', (epd.width, epd.height), 255)
                    draw = ImageDraw.Draw(image)
                    draw.text((10, 50), "Error: No data from\nDexcom", font=font, fill=0)
                    draw.text((10, 100), "Check connection\nand credentials.", font=font, fill=0)
                    epd.display(epd.getbuffer(image))
                    epd.sleep()

            except Exception as e:
                logger.exception(f"An error occurred: {e}")
                if epd:
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
            sleep_time = max(0, SLEEP_DURATION - loop_duration)
            logger.info(f"Sleeping for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("Exiting program. Cleaning up...")
        if epd:
            epd.init()
            epd.Clear(0xFF)
            epd.sleep()
            epd.module_exit()
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
