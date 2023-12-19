import sqlite3
import subprocess
import time
import os
import re

DB_PATH = "/Users/joshrizika/Library/Messages/chat.db"
CHECK_INTERVAL = 5

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
    
# function: gets the id of the last message in the database
# parameters: none
# returns: id of last message
def get_last_message_id():
    conn = sqlite3.connect(DB_PATH) #connect to database
    cursor = conn.cursor() #create cursor
    cursor.execute("SELECT ROWID FROM message ORDER BY ROWID DESC LIMIT 1") #get id of last message
    last_row_id = cursor.fetchone()[0] #get id from cursor
    conn.close() #close connection
    return last_row_id #return id

# function: listen for messages from a specific contact and respond
# parameters: target_names - list of strings, phrase_and_response - list of tuples
# returns: nothing
def listen_and_respond(target_names, phrase_and_response):
    check_interval = 5 #check for new messages every 5 seconds
    target_numbers = [get_contact_number(name) for name in target_names] #get target numbers from names
    print("listening for messages from {}".format(target_numbers))
    last_id_checked = get_last_message_id() #get id of last message

    while True: #loop forever
        conn = sqlite3.connect(DB_PATH) #connect to database
        cursor = conn.cursor() #create cursor

        cursor.execute("""
            SELECT message.ROWID, message.text, handle.id 
            FROM message 
            INNER JOIN handle ON message.handle_id = handle.ROWID 
            WHERE message.ROWID > ? AND handle.id IN ({}) AND message.is_from_me = 0
            ORDER BY message.ROWID DESC
            """.format(','.join('?' * len(target_numbers))), [last_id_checked] + target_numbers) #get recent messages from target number

        messages = cursor.fetchall() #get messages from cursor
        conn.close() #close connection

        if len(messages) > 0: #if there are new messages
            print(messages)
            for row in messages: #for each message
                row_id, text, receiving_number = row #get row id, text, and receiving number
                print(row_id, text, receiving_number)

                for phrase, response_message in phrase_and_response: #for each phrase and response
                    if phrase.lower() in text.lower(): #if phrase is in text
                        escaped_response_message = response_message.replace('"', '\\"') #escape quotes in response message
                        os.system(f'osascript sendMessage.applescript "{receiving_number}" "{escaped_response_message}"') #send response message
                        last_id_checked = row_id #update last id checked
                        break  

        time.sleep(check_interval) #sleep for check interval

if __name__ == "__main__":
    recipients = ["Adam Rizika", "Billy Hunt"]
    phrase_and_response = [("Hey", "Hey There!"), ("How are you", "I'm good, how are you?")]
    listen_and_respond(recipients, phrase_and_response)
    