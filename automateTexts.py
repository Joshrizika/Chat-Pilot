import os
import time
import subprocess
import re

# function: repeatedly send a message to a recipient
# parameters: recipient_name - string, message - string, interval - int, duration - int
# returns: nothing
def send_repeat_message(recipient_name, message, interval, duration):
    recipient_number = get_contact_number(recipient_name) #get recipient number
    start_time = time.time() #get start time
    end_time = start_time + duration #calculate end time
    while time.time() < end_time: #while current time is less than end time
        os.system("osascript sendMessage.applescript {} {}".format(recipient_number, message)) #send message
        time.sleep(interval) #sleep for interval

# function: gets contact number from contact name
# parameters: name - string
# returns: phone number
def get_contact_number(name):
    script = f'osascript getContactNumber.applescript "{name}"' #define applescript to get contact number
    process = subprocess.Popen(script, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) #run applescript
    output, error = process.communicate() #get output and error from applescript

    if process.returncode == 0: #if applescript ran successfully
        phone_number = output.decode('utf-8').strip() #get phone number from output
        filtered_number = re.sub(r"[^\d+]", "", phone_number) #filter out non-numeric characters
        return filtered_number #return filtered number
    else:
        raise Exception("Error: " + error.decode('utf-8')) #raise exception if applescript failed
    

if __name__ == "__main__":   
    message = "'Hi Vivi'"
    recipient_name = "Vivi Hunt"
    send_repeat_message(recipient_name, message, interval=1, duration=60)
