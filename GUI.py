from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QListWidget, QLineEdit, QHBoxLayout, QSpinBox, QComboBox, QGroupBox, QPushButton, QListWidgetItem, QMessageBox, QTextEdit, QSizePolicy
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtCore
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
    
# ThreadItemWidget class
class ThreadItemWidget(QWidget):
    def __init__(self, relation_description, recipient, user_name, model, words_per_minute, conversation_context, stop_callback, double_click_callback, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.double_click_callback = double_click_callback

        # Basic thread information
        self.basic_info = f"Currently chatting with your {relation_description} {recipient} as {user_name}."
        self.label = QLabel(self.basic_info)
        self.layout.addWidget(self.label)

        # Detailed information
        self.detailed_info = (recipient, relation_description, user_name, conversation_context, words_per_minute, model)

        self.layout.addStretch(1)  # Add stretch to push buttons to the right

        # Stop button
        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(stop_callback)
        self.layout.addWidget(self.stop_button)

    def get_detailed_info(self):
        # Unpack the detailed information
        recipient, relation_description, user_name, conversation_context, words_per_minute, model = self.detailed_info
        
        # Use HTML to format the labels as bold
        detailed_info = (
            f"<b>Your name:</b> {user_name}<br>"
            f"<b>Recipient name:</b> {recipient}<br>"
            f"<b>Relationship:</b> {relation_description}<br>"
            f"<b>Conversation context:</b> {conversation_context}<br>"
            f"<b>Response Speed (WPM):</b> {words_per_minute}<br>"
            f"<b>GPT Model:</b> {model}"
        ) 
        return detailed_info

    def mouseDoubleClickEvent(self, event):
        # Signal to show detailed information
        self.double_click_callback(self)

class EmittingStream(QtCore.QObject):
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))

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

        self.current_output_buffer = None
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_console_output_area)
        self.update_timer.start(1000)  # Update every 1000 milliseconds (1 second)

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

        # Connect the currentRowChanged signal to a lambda that calls contact_selected
        contact_list.currentRowChanged.connect(
            lambda row: self.contact_selected(contact_list.item(row), tab_name)
        )

        layout.addWidget(search_box)
        layout.addWidget(contact_list)

        return contact_list_group

    def filter_contacts(self, text, contact_list):
        contact_list.clear()
        filtered_contacts = [name for name in self.contacts if text.lower() in name.lower()]
        contact_list.addItems(filtered_contacts)

    def contact_selected(self, item, tab_name):
        if item is not None:
            contact_name = item.text()
            self.contact_info[tab_name] = (contact_name, self.contacts[contact_name])


    def tab1_layout(self):
        main_layout = QHBoxLayout()
        left_side_layout = QVBoxLayout()
        
        name_group = QGroupBox("Your Name")
        name_layout = QVBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your name")
        name_layout.addWidget(self.name_input)
        name_group.setLayout(name_layout)
        left_side_layout.addWidget(name_group)

        contact_list_group = self.create_contact_list("tab1")
        left_side_layout.addWidget(contact_list_group)

        main_layout.addLayout(left_side_layout, 1)

        self.right_side_layout = QVBoxLayout()
        
        inputs_layout = QHBoxLayout()
        
        description_group = QGroupBox("Relation to Contact")
        description_layout = QVBoxLayout()
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("e.g. Sister, Cousin, etc.")
        description_layout.addWidget(self.description_input)
        description_group.setLayout(description_layout)
        inputs_layout.addWidget(description_group)

        wpm_group = QGroupBox("Response Speed (WPM)")
        wpm_group.setFixedWidth(140)
        wpm_layout = QVBoxLayout()
        self.wpm_input = QSpinBox()
        self.wpm_input.setRange(10, 200)
        self.wpm_input.setValue(80)
        wpm_layout.addWidget(self.wpm_input)
        wpm_group.setLayout(wpm_layout)
        inputs_layout.addWidget(wpm_group)

        model_group = QGroupBox("GPT Model")
        model_layout = QVBoxLayout()
        self.model_selection = QComboBox()
        self.model_selection.addItems(["gpt-4-1106-preview", "gpt-4-vision-preview", "gpt-4", "gpt-4-32k", "gpt-4-0613", "gpt-4-32k-0613", "gpt-3.5-turbo-1106", "gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-3.5-turbo-instruct"])
        model_layout.addWidget(self.model_selection)
        model_group.setLayout(model_layout)
        inputs_layout.addWidget(model_group)

        self.right_side_layout.addLayout(inputs_layout)

        context_group = QGroupBox("Context")
        context_layout = QVBoxLayout()
        self.context_input = QTextEdit()
        self.context_input.setPlaceholderText("Add any context you'd like to provide to the AI here. (optional)")
        self.context_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.context_input.setFixedHeight(100)
        context_layout.addWidget(self.context_input)
        context_group.setLayout(context_layout)
        self.right_side_layout.addWidget(context_group)

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self.run_AI_conversation)
        self.right_side_layout.addWidget(self.submit_button)

        self.thread_list_widget = QListWidget()
        self.right_side_layout.addWidget(self.thread_list_widget)

        self.return_to_thread_list_button = QPushButton("Return to Active Conversations")
        self.return_to_thread_list_button.clicked.connect(self.return_to_thread_list)
        self.return_to_thread_list_button.hide()
        self.right_side_layout.addWidget(self.return_to_thread_list_button)

        self.detailed_text_area = QTextEdit(self)
        self.detailed_text_area.setReadOnly(True)
        self.detailed_text_area.setFixedHeight(110)
        self.detailed_text_area.hide()
        self.right_side_layout.addWidget(self.detailed_text_area)

        self.console_output_label = QLabel("Console Output", self)
        self.console_output_label.hide()
        self.right_side_layout.addWidget(self.console_output_label)

        self.console_output_area = QTextEdit(self)
        self.console_output_area.setReadOnly(True)
        self.console_output_area.hide()
        self.right_side_layout.addWidget(self.console_output_area)

        main_layout.addLayout(self.right_side_layout, 3)
        self.tab1.setLayout(main_layout)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.run_AI_conversation()
        super(App, self).keyPressEvent(event)

    def run_AI_conversation(self):
        self.user_name = self.name_input.text()
        self.relation_description = self.description_input.text()
        self.words_per_minute = self.wpm_input.value()
        self.selected_model = self.model_selection.currentText()
        self.conversation_context = self.context_input.toPlainText()
        if self.conversation_context == "":
            self.conversation_context = None
        target_name = self.contact_info['tab1'][0]


        if not target_name:
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
            "words_per_minute": self.words_per_minute,
            "conversation_context": self.conversation_context
        }
        stop_flag = threading.Event()
        output_buffer = []
        thread = threading.Thread(target=self.ai_conversation, args=(stop_flag, output_buffer))
        thread.daemon = True
        thread.start()
        thread_info['output_buffer'] = output_buffer
        self.running_threads.append((thread, stop_flag, thread_info))
        self.update_thread_list()

    def ai_conversation(self, stop_flag, output_buffer):
        # Call the modified converse_with_AI function with the stop flag
        converse_with_AI(self.contact_info['tab1'][1], self.contact_info['tab1'][0], self.user_name, self.relation_description, self.words_per_minute, self.conversation_context, self.selected_model, stop_flag, output_buffer)

    def stop_conversation(self, thread_index):
        if 0 <= thread_index < len(self.running_threads):
            # Correct the unpacking to match the new structure of the tuples
            _, stop_flag, _ = self.running_threads[thread_index]  # Adding an extra underscore for the thread info
            stop_flag.set()  # Trigger the stop flag
            self.current_output_buffer = None
            self.running_threads.pop(thread_index)  # Remove the stopped thread
            self.update_thread_list()  # Update the GUI immediately

    def show_detailed_info(self, thread_widget):
        # Find the QListWidgetItem associated with the ThreadItemWidget
        thread_index = -1
        for i in range(self.thread_list_widget.count()):
            item = self.thread_list_widget.item(i)
            if self.thread_list_widget.itemWidget(item) == thread_widget:
                thread_index = i
                break

        if thread_index == -1:
            # Handle the case where the thread widget is not found
            QMessageBox.warning(self, "Error", "Thread not found.")
            return

        self.thread_list_widget.hide()
        self.submit_button.hide()

        self.return_to_thread_list_button.show()

        # Set the detailed information in the text area and show it
        self.detailed_text_area.setHtml(thread_widget.get_detailed_info())
        self.detailed_text_area.show()

        _, _, thread_info = self.running_threads[thread_index]
        self.current_output_buffer = thread_info['output_buffer']
        self.update_console_output_area()

        self.console_output_label.show()
        self.console_output_area.show()

    def update_console_output_area(self):
        # Save the scrollbar position
        scrollbar = self.console_output_area.verticalScrollBar()
        scrollbar_position = scrollbar.value()

        if self.current_output_buffer:
            self.console_output_area.setPlainText('\n'.join(self.current_output_buffer))

        # Restore the scrollbar position
        scrollbar.setValue(scrollbar_position)

    def return_to_thread_list(self):
        # Hide the detailed text area
        self.return_to_thread_list_button.hide()
        self.detailed_text_area.hide()
        self.console_output_label.hide()
        self.console_output_area.hide()

        self.thread_list_widget.show()
        self.submit_button.show()

    def update_thread_list(self):
        self.thread_list_widget.clear()
        for i, (thread, _, thread_info) in enumerate(self.running_threads):
            if thread.is_alive():
                item = QListWidgetItem(self.thread_list_widget)
                relevant_thread_info = {k: v for k, v in list(thread_info.items())[:-1]}
                widget = ThreadItemWidget(**relevant_thread_info, stop_callback=lambda _, i=i: self.stop_conversation(i), double_click_callback=self.show_detailed_info, parent=self.thread_list_widget)               
                item.setSizeHint(widget.sizeHint())
                self.thread_list_widget.addItem(item)
                self.thread_list_widget.setItemWidget(item, widget)

    def tab2_layout(self):
        main_layout = QHBoxLayout()

        # Left side layout
        left_side_layout = QVBoxLayout()

        # Contact List
        contact_list_group = self.create_contact_list("tab2 ")
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
    