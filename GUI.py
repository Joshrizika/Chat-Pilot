from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QListWidget, QLineEdit, QHBoxLayout, QSpinBox, QComboBox, QGroupBox, QPushButton, QListWidgetItem, QMessageBox
from PyQt5.QtCore import Qt
import sys
import subprocess
import json
from automateAIResponse import converse_with_AI
import threading


def compile_swift_script(swift_file, executable_name):
    try:
        subprocess.run(['swiftc', '-o', executable_name, swift_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during Swift compilation: {e}")
        return False
    return True

def get_contacts():
    contacts_filename = 'ContactsFile'
    compile_swift_script('FetchContacts.swift', contacts_filename)

    try:
        result = subprocess.run([f'./{contacts_filename}'], capture_output=True, text=True, check=True)
        contacts_json = result.stdout
        sorted_contacts = dict(sorted(json.loads(contacts_json).items(), key=lambda x: x[0]))
        return sorted_contacts
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None

class ThreadItemWidget(QWidget):
    def __init__(self, relation_description, recipient, user_name, model, words_per_minute, stop_callback, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        # Format and set the thread information
        thread_info = f"Currently chatting with your {relation_description} {recipient} as {user_name}. \nThis chat uses {model} and responds at {words_per_minute} words per minute."
        self.label = QLabel(thread_info)
        layout.addWidget(self.label)

        # Stop button
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(stop_callback)
        layout.addStretch(1)
        layout.addWidget(self.stop_button)

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chat Pilot")
        self.setGeometry(100, 100, 900, 600)

        self.contacts = get_contacts() or {}
        self.contact_info = {"tab1": (None, None), "tab2": (None, None)}

        self.tabWidget = QTabWidget()

        self.tab1 = QWidget()
        self.tab2 = QWidget()

        self.tabWidget.addTab(self.tab1, "AI Conversation")
        self.tabWidget.addTab(self.tab2, "Repeat Message")

        self.tab1_layout()
        self.tab2_layout()

        self.setCentralWidget(self.tabWidget)

        self.running_threads = []

    def create_contact_list(self, tab_name):
        # Create a group box for the contact list and search box
        contact_list_group = QGroupBox("Contacts")
        layout = QVBoxLayout(contact_list_group)

        search_box = QLineEdit()
        search_box.setPlaceholderText("Search contacts...")

        # Connect the textChanged signal of the search box to the filter_contacts method
        search_box.textChanged.connect(lambda text: self.filter_contacts(text, contact_list))

        contact_list = QListWidget()
        contact_list.addItems(sorted(self.contacts.keys()))
        contact_list.itemClicked.connect(lambda item: self.contact_selected(item, tab_name))

        layout.addWidget(search_box)
        layout.addWidget(contact_list)

        return contact_list_group


    def filter_contacts(self, text, contact_list):
        contact_list.clear()
        filtered_contacts = [name for name in self.contacts if text.lower() in name.lower()]
        contact_list.addItems(filtered_contacts)

    def contact_selected(self, item, tab_name):
        contact_name = item.text()
        self.contact_info[tab_name] = (contact_name, self.contacts[contact_name])
        print(f"Selected number for {tab_name}: {self.contact_info[tab_name][1]}")
        print(f"Selected name for {tab_name}: {self.contact_info[tab_name][0]}")

    def tab1_layout(self):
        main_layout = QHBoxLayout()

        # Left side layout
        left_side_layout = QVBoxLayout()

        # GroupBox for 'Your Name' Input
        name_group = QGroupBox("Your Name")
        name_layout = QVBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your name")
        name_layout.addWidget(self.name_input)
        name_group.setLayout(name_layout)
        left_side_layout.addWidget(name_group)

        # Contact List
        contact_list_group = self.create_contact_list("tab1")
        left_side_layout.addWidget(contact_list_group)

        # Add left side layout to main layout
        main_layout.addLayout(left_side_layout, 1)

        # Right side - Vertical Layout for Grouped Inputs and Thread List
        right_side_layout = QVBoxLayout()

        # Horizontal Layout for Grouped Inputs
        inputs_layout = QHBoxLayout()

        # GroupBox for Description Input
        description_group = QGroupBox("Relation to Contact")
        description_layout = QVBoxLayout()
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("e.g. Sister, Cousin, etc.")
        description_layout.addWidget(self.description_input)
        description_group.setLayout(description_layout)
        inputs_layout.addWidget(description_group)

        # GroupBox for Words Per Minute Input
        wpm_group = QGroupBox("Words Per Minute")
        wpm_layout = QVBoxLayout()
        self.wpm_input = QSpinBox()
        self.wpm_input.setRange(10, 200)
        self.wpm_input.setValue(80)
        wpm_layout.addWidget(self.wpm_input)
        wpm_group.setLayout(wpm_layout)
        inputs_layout.addWidget(wpm_group)

        # GroupBox for GPT Model Selection
        model_group = QGroupBox("GPT Model")
        model_layout = QVBoxLayout()
        self.model_selection = QComboBox()
        self.model_selection.addItems(["gpt-4-1106-preview", "gpt-4-vision-preview", "gpt-4", "gpt-4-32k", "gpt-4-0613", "gpt-4-32k-0613", "gpt-3.5-turbo-1106", "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-instruct"])
        model_layout.addWidget(self.model_selection)
        model_group.setLayout(model_layout)
        inputs_layout.addWidget(model_group)

        # Add the inputs layout to the right side layout
        right_side_layout.addLayout(inputs_layout)

        # Add Submit Button
        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.run_AI_conversation)
        right_side_layout.addWidget(self.submit_button)

        # Add QListWidget to display threads
        self.thread_list_widget = QListWidget()
        right_side_layout.addWidget(self.thread_list_widget)

        # Add the right side layout to the main layout with stretch factor
        main_layout.addLayout(right_side_layout, 3)

        self.tab1.setLayout(main_layout)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.run_AI_conversation()
        super(App, self).keyPressEvent(event)

    def run_AI_conversation(self):
        self.relation_description = self.description_input.text()
        self.words_per_minute = self.wpm_input.value()
        self.selected_model = self.model_selection.currentText()
        self.user_name = self.name_input.text()
        target_name = self.contact_info['tab1'][0]

        if not self.contact_info['tab1'][0]:
            QMessageBox.warning(self, "Error", "Please select a recipient.")
            return

        if not self.user_name:
            QMessageBox.warning(self, "Error", "Please enter your name.")
            return
        
        if not self.relation_description:
            QMessageBox.warning(self, "Error", "Please enter your relation to the recipient.")
            return

        # Check if a thread to the same person is already running
        for thread, _, thread_info in self.running_threads:
            if thread.is_alive() and thread_info['recipient'] == target_name:
                QMessageBox.warning(self, "Error", f"A conversation with {thread_info['recipient']} is already in progress. Please choose a different contact.")
                return  # Exit without starting a new thread

        # If no other thread is found, proceed to start a new conversation
        thread_info = {
            "relation_description": self.relation_description,
            "recipient": target_name,
            "user_name": self.user_name,
            "model": self.selected_model,
            "words_per_minute": self.words_per_minute
        }
        stop_flag = threading.Event()
        thread = threading.Thread(target=self.ai_conversation, args=(stop_flag,))
        thread.daemon = True
        thread.start()
        self.running_threads.append((thread, stop_flag, thread_info))
        self.update_thread_list()

    def ai_conversation(self, stop_flag):
        # Call the modified converse_with_AI function with the stop flag
        converse_with_AI(self.contact_info['tab1'][1], self.contact_info['tab1'][0], self.user_name, self.relation_description, self.words_per_minute, self.selected_model, stop_flag)

    def stop_conversation(self, thread_index):
        if 0 <= thread_index < len(self.running_threads):
            # Correct the unpacking to match the new structure of the tuples
            _, stop_flag, _ = self.running_threads[thread_index]  # Adding an extra underscore for the thread info
            stop_flag.set()  # Trigger the stop flag
            self.running_threads.pop(thread_index)  # Remove the stopped thread
            print(f"Stopping thread {thread_index+1}")
            self.update_thread_list()  # Update the GUI immediately

    def update_thread_list(self):
        self.thread_list_widget.clear()
        for i, (thread, _, thread_info) in enumerate(self.running_threads):
            if thread.is_alive():
                item = QListWidgetItem(self.thread_list_widget)
                widget = ThreadItemWidget(**thread_info, stop_callback=lambda: self.stop_conversation(i), parent=self.thread_list_widget)
                item.setSizeHint(widget.sizeHint())
                self.thread_list_widget.addItem(item)
                self.thread_list_widget.setItemWidget(item, widget)
    
    # def tab_layout(self, tab_name):
    #     layout = QHBoxLayout()
    #     contact_list_layout = self.create_contact_list(tab_name)
    #     layout.addLayout(contact_list_layout, 1)  # Adjust the proportion as needed
    #     layout.addWidget(QLabel(f"Content of {tab_name.capitalize()}"), 3)  # Adjust the proportion as needed
    #     return layout
    
    def tab2_layout(self):
        main_layout = QHBoxLayout()

        # Left side layout
        left_side_layout = QVBoxLayout()

        # Contact List
        contact_list_group = self.create_contact_list("tab1")
        left_side_layout.addWidget(contact_list_group)

        # Add left side layout to main layout
        main_layout.addLayout(left_side_layout, 1)

        self.tab2.setLayout(main_layout)
    
def main():
    app = QApplication(sys.argv)
    gui = App()
    gui.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
    