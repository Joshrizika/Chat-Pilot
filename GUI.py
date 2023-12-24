from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QListWidget, QLineEdit, QHBoxLayout, QSpinBox, QComboBox, QGroupBox, QPushButton, QListWidgetItem, QMessageBox, QTextEdit, QSizePolicy
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtCore
import sys
import subprocess
import json
from automateAIResponse import converse_with_AI
import threading

# function: compile swift script that fetches contacts
# parameters: swift_file - string, executable_name - string
# returns: success - boolean
def compile_swift_script(swift_file, executable_name):
    try:
        subprocess.run(['swiftc', '-o', executable_name, swift_file], check=True) #compile swift script
    except subprocess.CalledProcessError as e: #if error occurs during compilation
        print(f"Error during Swift compilation: {e}") #print error
        return False
    return True

# function: get contacts from contacts file
# parameters: none
# returns: contacts - dictionary
def get_contacts(): 
    contacts_filename = 'ContactsFile' #name of storage file
    compile_swift_script('FetchContacts.swift', contacts_filename) #compile swift script to fetch contacts
    try:
        result = subprocess.run([f'./{contacts_filename}'], capture_output=True, text=True, check=True) #get contacts from local file
        contacts_json = result.stdout #get contacts from result stdout
        sorted_contacts = dict(sorted(json.loads(contacts_json).items(), key=lambda x: x[0])) #sort contacts alphabetically
        return sorted_contacts
    except subprocess.CalledProcessError as e: #if error occurs during execution
        print(f"Error: {e}") #print error
        return None
    
# class - widget for each thread in the list
class ThreadItemWidget(QWidget):
    # function: constructor
    # parameters: relation_description - string, recipient - string, user_name - string, model - string, words_per_minute - int, conversation_context - string, stop_callback - function, double_click_callback - function, parent - QWidget
    # returns: nothing
    def __init__(self, relation_description, recipient, user_name, model, words_per_minute, conversation_context, stop_callback, double_click_callback, parent=None): 
        super().__init__(parent)
        self.layout = QHBoxLayout(self) #create horizontal layout
        self.double_click_callback = double_click_callback #set double click callback

        self.basic_info = f"Currently chatting with your {relation_description} {recipient} as {user_name}." #set basic info string
        self.label = QLabel(self.basic_info) #create label with basic info
        self.layout.addWidget(self.label) #add label to layout

        self.detailed_info = (recipient, relation_description, user_name, conversation_context, words_per_minute, model) #set detailed info tuple

        self.layout.addStretch(1) #add stretch to push buttons to the right

        self.stop_button = QPushButton("Stop", self) #create stop button
        self.stop_button.clicked.connect(stop_callback) #connect stop button to stop callback
        self.layout.addWidget(self.stop_button) #add stop button to layout

    # function: get detailed information
    # parameters: self - ThreadItemWidget
    # returns: detailed_info - string
    def get_detailed_info(self):
        recipient, relation_description, user_name, conversation_context, words_per_minute, model = self.detailed_info #unpack detailed info tuple
        
        detailed_info = ( #set detailed info string as html
            f"<b>Your name:</b> {user_name}<br>"
            f"<b>Recipient name:</b> {recipient}<br>"
            f"<b>Relationship:</b> {relation_description}<br>"
            f"<b>Conversation context:</b> {conversation_context}<br>"
            f"<b>Response Speed (WPM):</b> {words_per_minute}<br>"
            f"<b>GPT Model:</b> {model}"
        ) 
        return detailed_info

    # function: mouse double click event handler
    # parameters: self - ThreadItemWidget, event - QMouseEvent
    # returns: nothing
    def mouseDoubleClickEvent(self, event):
        self.double_click_callback(self) #call double click callback to show detailed info

# class - emitting stream for console output
class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str) #create signal

    # function: write text to console
    # parameters: self - EmittingStream, text - string
    # returns: nothing
    def write(self, text): 
        self.textWritten.emit(str(text)) #emit signal

# class - custom line edit for search box
class CustomLineEdit(QLineEdit):
    # function: constructor
    # parameters: contact_list - QListWidget, *args, **kwargs
    # returns: nothing
    def __init__(self, contact_list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.contact_list = contact_list #set contact list

    # function: key press event handler
    # parameters: self - CustomLineEdit, event - QKeyEvent
    # returns: nothing
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down: #if down arrow key is pressed
            if self.contact_list.count() > 0: #if contact list is not empty
                self.contact_list.setFocus() #set focus to contact list
                self.contact_list.setCurrentRow(0) #set current row to 0
        else: 
            super().keyPressEvent(event) #call super key press event handler

# class - custom list widget for contact list
class CustomListWidget(QListWidget):
    # function: constructor
    # parameters: search_box - CustomLineEdit, *args, **kwargs
    # returns: nothing
    def __init__(self, search_box, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_box = search_box #set search box

    # function: key press event handler
    # parameters: self - CustomListWidget, event - QKeyEvent
    # returns: nothing
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up and self.currentRow() == 0: #if up arrow key is pressed and current row is 0
            self.search_box.setFocus() #set focus to search box
        else:
            super().keyPressEvent(event) #call super key press event handler


# class - Graphical User Interface
class App(QMainWindow):
    # function: constructor
    # parameters: self - App
    # returns: nothing
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Pilot") #set title
        self.setGeometry(100, 100, 900, 600) #set window size and location

        self.contacts = get_contacts() or {} #get the contacts from the contacts file
        self.contact_info = (None, None) #set contact info to None

        self.main_widget = QWidget() #create horizontal layout

        self.create_layout() #create layout

        self.setCentralWidget(self.main_widget) #set main widget as central widget

        self.running_threads = [] #initialize list of tuples containing the thread, stop flag, and thread info

        self.current_output_buffer = None #initialize the current output buffer to None
        self.update_timer = QTimer(self) #create a timer to update the console output area
        self.update_timer.timeout.connect(self.update_console_output_area) #connect the timeout signal to the update_console_output_area method
        self.update_timer.start(1000)  #update every 1000 milliseconds (1 second)

    # function: create contact list
    # parameters: self - App
    # returns: contact_list_group - QGroupBox
    def create_contact_list(self):
        contact_list_group = QGroupBox("Contacts") #create group box for contact list
        layout = QVBoxLayout(contact_list_group) #create vertical layout for group box

        contact_list = CustomListWidget(None) #create list widget for contact list
        search_box = CustomLineEdit(contact_list) #create line edit for search box

        search_box.setPlaceholderText("Search contacts...") #set placeholder text for search box
        search_box.textChanged.connect(lambda text: self.filter_contacts(text, contact_list)) #connect text changed signal to filter_contacts

        contact_list.search_box = search_box  # Set reference to search box in the list widget
        contact_list.addItems(sorted(self.contacts.keys())) #add contacts to contact list

        contact_list.currentRowChanged.connect( #connect current row changed signal to contact_selected
            lambda row: self.contact_selected(contact_list.item(row)) #call contact_selected in lambda function
        )

        layout.addWidget(search_box) #add search box to layout
        layout.addWidget(contact_list) #add contact list to layout

        return contact_list_group

    # function: filter contacts
    # parameters: self - App, text - string, contact_list - QListWidget
    # returns: nothing
    def filter_contacts(self, text, contact_list):
        contact_list.clear() #clear contact list
        filtered_contacts = [name for name in self.contacts if text.lower() in name.lower()] #get filtered contacts
        contact_list.addItems(filtered_contacts) #add filtered contacts to contact list

    # function: get selected contact
    # parameters: self - App, item - QListWidgetItem
    # returns: nothing
    def contact_selected(self, item):
        if item: #if item is not None
            contact_name = item.text() #get contact name
            self.contact_info = (contact_name, self.contacts[contact_name]) #set contact info to contact name and contact number
    
    # function: set up layout
    # parameters: self - App
    # returns: nothing
    def create_layout(self):
        window_layout = QVBoxLayout() #create vertical layout

        # Title
        title = QLabel("Automated AI Conversations") #create title
        title.setAlignment(Qt.AlignCenter) #set alignment for title to center
        font = title.font() #get font for title
        font.setBold(True) #set font to bold
        font.setPointSize(20) #set font size to 20
        title.setFont(font) #set font for title
        window_layout.addWidget(title) #add title to window layout

        main_layout = QHBoxLayout() #create horizontal layout
        
        left_side_layout = QVBoxLayout() #create vertical layout for left side
        
        # User Name
        name_group = QGroupBox("Your Name") #create group box for name input
        name_layout = QVBoxLayout() #create vertical layout for group box
        self.name_input = QLineEdit() #create line edit for name input
        self.name_input.setPlaceholderText("Enter your name") #set placeholder text for name input
        name_layout.addWidget(self.name_input) #add name input to layout
        name_group.setLayout(name_layout) #set layout for group box
        left_side_layout.addWidget(name_group) #add group box to left side layout

        contact_list_group = self.create_contact_list() #create contact list group
        left_side_layout.addWidget(contact_list_group) #add contact list group to left side layout

        main_layout.addLayout(left_side_layout, 1) #add left side layout to main layout

        self.right_side_layout = QVBoxLayout() #create vertical layout for right side
        
        inputs_layout = QHBoxLayout() #create horizontal layout for inputs
        
        # Relation Description
        description_group = QGroupBox("Relation to Contact") #create group box for relation description input
        description_layout = QVBoxLayout() #create vertical layout for group box
        self.description_input = QLineEdit() #create line edit for relation description input
        self.description_input.setPlaceholderText("e.g. Sister, Cousin, etc.") #set placeholder text for relation description input
        description_layout.addWidget(self.description_input) #add relation description input to layout
        description_group.setLayout(description_layout) #set layout for group box
        inputs_layout.addWidget(description_group) #add group box to inputs layout

        # Words Per Minute
        wpm_group = QGroupBox("Response Speed (WPM)") #create group box for words per minute input
        wpm_group.setFixedWidth(140) #set fixed width for group box
        wpm_layout = QVBoxLayout() #create vertical layout for group box
        self.wpm_input = QSpinBox() #create spin box for words per minute input
        self.wpm_input.setRange(10, 200) #set range for words per minute input
        self.wpm_input.setValue(80) #set default value for words per minute input
        wpm_layout.addWidget(self.wpm_input) #add words per minute input to layout
        wpm_group.setLayout(wpm_layout) #set layout for group box
        inputs_layout.addWidget(wpm_group) #add group box to inputs layout

        # GPT Model
        model_group = QGroupBox("GPT Model") #create group box for GPT model selection
        model_layout = QVBoxLayout() #create vertical layout for group box
        self.model_selection = QComboBox() #create combo box for GPT model selection
        self.model_selection.addItems(["gpt-4-1106-preview", "gpt-4-vision-preview", "gpt-4", "gpt-4-32k", "gpt-3.5-turbo-1106", "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-instruct"]) #add GPT models to combo box
        model_layout.addWidget(self.model_selection) #add GPT model selection to layout
        model_group.setLayout(model_layout) #set layout for group box
        inputs_layout.addWidget(model_group) #add group box to inputs layout

        self.right_side_layout.addLayout(inputs_layout) #add inputs layout to right side layout

        # Context
        context_group = QGroupBox("Context") #create group box for context input
        context_layout = QVBoxLayout() #create vertical layout for group box
        self.context_input = QTextEdit() #create text edit for context input
        self.context_input.setPlaceholderText("Add any context you'd like to provide to the AI here. (optional)") #set placeholder text for context input
        self.context_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) #set size policy for context input
        self.context_input.setFixedHeight(100) #set fixed height for context input
        context_layout.addWidget(self.context_input) #add context input to layout
        context_group.setLayout(context_layout) #set layout for group box
        self.right_side_layout.addWidget(context_group) #add group box to right side layout

        # Submit Button
        self.submit_button = QPushButton("Submit") #create submit button
        self.submit_button.clicked.connect(self.run_AI_conversation) #connect submit button to run_AI_conversation
        self.right_side_layout.addWidget(self.submit_button) #add submit button to right side layout

        # Thread List
        self.thread_list_widget = QListWidget() #create list widget for thread list
        self.right_side_layout.addWidget(self.thread_list_widget) #add thread list widget to right side layout

        # Return to Thread List Button
        self.return_to_thread_list_button = QPushButton("Return to Active Conversations") #create return to thread list button
        self.return_to_thread_list_button.clicked.connect(self.return_to_thread_list) #connect return to thread list button to return_to_thread_list
        self.return_to_thread_list_button.hide() #hide return to thread list button
        self.right_side_layout.addWidget(self.return_to_thread_list_button) #add return to thread list button to right side layout

        # Detailed Info
        self.detailed_text_area = QTextEdit(self) #create text edit for detailed info
        self.detailed_text_area.setReadOnly(True) #set detailed info text edit to read only
        self.detailed_text_area.setFixedHeight(110) #set fixed height for detailed info text edit
        self.detailed_text_area.hide() #hide detailed info text edit
        self.right_side_layout.addWidget(self.detailed_text_area) #add detailed info text edit to right side layout

        # Console Output
        self.console_output_label = QLabel("Console Output", self) #create label for console output
        self.console_output_label.hide() #hide console output label
        self.right_side_layout.addWidget(self.console_output_label) #add console output label to right side layout

        self.console_output_area = QTextEdit(self) #create text edit for console output
        self.console_output_area.setReadOnly(True) #set console output text edit to read only
        self.console_output_area.hide() #hide console output text edit
        self.right_side_layout.addWidget(self.console_output_area) #add console output text edit to right side layout

        main_layout.addLayout(self.right_side_layout, 3) #add right side layout to main layout

        window_layout.addLayout(main_layout) #add main layout to window layout

        self.main_widget.setLayout(window_layout) #set main layout
    
    #function: enter key press event handler
    #parameters: self - App, event - QKeyEvent
    #returns: nothing
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter: #if enter key is pressed
            self.run_AI_conversation() #call run_AI_conversation
        super(App, self).keyPressEvent(event) #call super key press event handler

    # function: setup and run AI conversation
    # parameters: self - App
    # returns: nothing
    def run_AI_conversation(self):
        self.user_name = self.name_input.text() #get user name
        if not self.user_name: #if user name is empty
            QMessageBox.warning(self, "Error", "Please enter your name.") #show error message
            return
        
        self.relation_description = self.description_input.text() #get relation description
        if not self.relation_description: #if relation description is empty
            QMessageBox.warning(self, "Error", "Please enter your relation to the recipient.") #show error message
            return
        
        self.words_per_minute = self.wpm_input.value() #get words per minute
        self.selected_model = self.model_selection.currentText() #get GPT model
        self.conversation_context = self.context_input.toPlainText() #get conversation context
        if self.conversation_context == "": #if conversation context is empty
            self.conversation_context = None #set conversation context to None

        target_name = self.contact_info[0] #get target name
        if not target_name: #if target name is None
            QMessageBox.warning(self, "Error", "Please select a recipient.") #show error message
            return

        for thread, _, thread_info in self.running_threads: #for each thread in running threads
            if thread.is_alive() and thread_info['recipient'] == target_name: #if thread is alive and recipient is target name
                QMessageBox.warning(self, "Error", f"A conversation with {thread_info['recipient']} is already in progress. Please choose a different contact.") #show error message
                return 

        thread_info = { #set thread info dictionary
            "relation_description": self.relation_description,
            "recipient": target_name,
            "user_name": self.user_name,
            "model": self.selected_model,
            "words_per_minute": self.words_per_minute,
            "conversation_context": self.conversation_context
        }
        stop_flag = threading.Event() #create stop flag
        output_buffer = [] #create output buffer
        thread = threading.Thread(target=self.ai_conversation, args=(stop_flag, output_buffer)) #create thread
        thread.daemon = True #set thread to daemon
        thread.start() #start thread
        thread_info['output_buffer'] = output_buffer #add output buffer to thread info
        self.running_threads.append((thread, stop_flag, thread_info)) #add thread, stop flag, and thread info to running threads
        self.update_thread_list() #update thread list

    # function: begin AI conversation
    # parameters: self - App, stop_flag - threading.Event, output_buffer - list
    # returns: nothing
    def ai_conversation(self, stop_flag, output_buffer):
        converse_with_AI(self.contact_info[1], self.contact_info[0], self.user_name, self.relation_description, self.words_per_minute, self.conversation_context, self.selected_model, stop_flag, output_buffer) #call converse_with_AI

    # function: stop conversation
    # parameters: self - App, thread_index - int
    # returns: nothing
    def stop_conversation(self, thread_index):
        if 0 <= thread_index < len(self.running_threads): #check if the thread index is valid
            _, stop_flag, _ = self.running_threads[thread_index] #get the stop flag
            stop_flag.set()  #trigger the stop flag
            self.current_output_buffer = None #clear the output buffer
            self.running_threads.pop(thread_index) #remove the stopped thread
            self.update_thread_list() #update the GUI immediately

    # function: show detailed thread info
    # parameters: self - App, thread_widget - ThreadItemWidget
    # returns: nothing
    def show_detailed_info(self, thread_widget):
        thread_index = -1 #initialize thread index to -1
        for i in range(self.thread_list_widget.count()): #for each item in the thread list widget
            item = self.thread_list_widget.item(i) #get item
            if self.thread_list_widget.itemWidget(item) == thread_widget: #if item widget is thread widget
                thread_index = i #set thread index to i
                break

        if thread_index == -1: #if thread is not found
            QMessageBox.warning(self, "Error", "Thread not found.") #show error message
            return

        self.thread_list_widget.hide() #hide the thread list widget
        self.submit_button.hide() #hide the submit button

        self.return_to_thread_list_button.show() #show the return to thread list button

        self.detailed_text_area.setHtml(thread_widget.get_detailed_info()) #set the detailed text area to the detailed info
        self.detailed_text_area.show() #show the detailed text area

        _, _, thread_info = self.running_threads[thread_index] #get the thread info
        self.current_output_buffer = thread_info['output_buffer'] #set the current output buffer to the thread's output buffer
        self.update_console_output_area() #update the console output area

        self.console_output_label.show() #show the console output label
        self.console_output_area.show() #show the console output area

    # function: update console output area
    # parameters: self - App
    # returns: nothing
    def update_console_output_area(self):
        scrollbar = self.console_output_area.verticalScrollBar() #get the vertical scrollbar
        scrollbar_position = scrollbar.value() #get the scrollbar position

        if self.current_output_buffer: #if the current output buffer is not None
            self.console_output_area.setPlainText('\n'.join(self.current_output_buffer)) #set the console output area to the current output buffer

        scrollbar.setValue(scrollbar_position) #set the scrollbar position to the previous position

    # function: return to thread list
    # parameters: self - App
    # returns: nothing
    def return_to_thread_list(self):
        self.return_to_thread_list_button.hide() #hide the return to thread list button
        self.detailed_text_area.hide() #hide the detailed text area
        self.console_output_label.hide() #hide the console output label
        self.console_output_area.hide() #hide the console output area

        self.thread_list_widget.show() #show the thread list widget
        self.submit_button.show() #show the submit button

    # function: update thread list
    # parameters: self - App
    # returns: nothing
    def update_thread_list(self):
        self.thread_list_widget.clear() #clear the thread list widget
        for i, (thread, _, thread_info) in enumerate(self.running_threads): #for each thread in running threads
            if thread.is_alive(): #if thread is alive
                item = QListWidgetItem(self.thread_list_widget) #create list widget item
                relevant_thread_info = {k: v for k, v in list(thread_info.items())[:-1]} #get relevant thread info
                widget = ThreadItemWidget(**relevant_thread_info, stop_callback=lambda _, i=i: self.stop_conversation(i), double_click_callback=self.show_detailed_info, parent=self.thread_list_widget) #create thread item widget
                item.setSizeHint(widget.sizeHint()) #set size hint for item
                self.thread_list_widget.addItem(item) #add item to thread list widget
                self.thread_list_widget.setItemWidget(item, widget) #set widget for item
    
def main():
    app = QApplication(sys.argv) #create application
    gui = App() #create GUI
    gui.show() #show GUI
    sys.exit(app.exec_()) #exit application

if __name__ == '__main__':
    main()
    