import os
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog
from datetime import datetime
import json
from gpt import GPT, list_openai_models
from claude import Claude, list_anthropic_models

openai_models = list_openai_models()
anthropic_models = list_anthropic_models()

#from time import sleep
#while not os.environ.get('DISPLAY'):
#    sleep(5) # sleep until display is ready

current_filepath = None

def clear_text_and_reset_path():
    global current_filepath
    text_area.delete('1.0', tk.END)
    current_filepath = None

# Function to initialize or update JSON file
def update_json_file(file_path, user_text, assistant_text):
    data = {
        'chat_creation': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'message_history': []
    }
    
    # Load existing data if file exists
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)

    # Append new messages
    data['message_history'].append({'role': 'user', 'content': user_text})
    data['message_history'].append({'role': 'assistant', 'content': assistant_text})
    
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Function to load text from a JSON file into the text area
def load_text_json(filename):
    global current_filepath
    global selected_model
    current_filepath = filename
    with open(filename, 'r') as file:
        data = json.load(file)

    text_area.delete('1.0', tk.END)
    for message in data['message_history']:
        # if message['role'] == "assist"
        text_area.insert(tk.END, f"  {message['role'].upper()}: {message['content']}\n\n\n")

def append_text_json():
    global current_filepath
    global selected_model

    text = input_box.get()
    if text:
        if not current_filepath:
            # current_filepath = os.path.join(directory, datetime.now().strftime("%Y%m%d%H%M%S") + ".json")
            m = GPT(system_message='You create 1-5 word summaries of a prompt serving as the name for the conversation. Name should include only characters normally allowed in filenames.')
            chat_name = m.prompt(f'Given the users prompt below, provide a short name, no more than 5 words, for the conversation (based on the prompt) to help remind the user of the subject matter. Do not surround your name in quotes, or apply any other formatting.  Only include the name.\n\nPrompt: {text}\n\nName: ')
            current_filepath = os.path.join(directory, chat_name.split('"')[0] + ".json")
            message_history=[]
        else:
            with open(current_filepath, 'r') as file:
                chat = json.load(file)
                message_history=chat['message_history']

        # Print every other letter of the user's message
        # modified_text = text[::2]
        if selected_model in anthropic_models.keys():
            m = Claude(model=anthropic_models[selected_model], injected_messages=message_history)
        elif selected_model in openai_models.keys():
            m = GPT(model=openai_models[selected_model], injected_messages=message_history)
        else:
            print(f"Unrecognized model: {selected_model}")
        response = m.prompt(text)

        update_json_file(current_filepath, text, response)
        load_text_json(current_filepath)

        populate_files_json(directory, file_frame)
    input_box.delete(0, tk.END)

# Function to delete a file
def delete_file(file):
    result = messagebox.askokcancel("Confirm Deletion", "Are you sure you want to delete this file?")
    if result:
        os.remove(file)
        populate_files_json(directory, file_frame)

# Function to rename a file
def rename_file(old_file_path):
    new_file_name = simpledialog.askstring("Rename File", "Enter new filename:", initialvalue=os.path.basename(old_file_path).split('.')[0])
    if new_file_name and new_file_name != os.path.basename(old_file_path).split('.')[0]:
        new_file_path = os.path.join(directory, new_file_name + ".json")
        if not os.path.exists(new_file_path):
            os.rename(old_file_path, new_file_path)
            populate_files_json(directory, file_frame)
        else:
            messagebox.showerror("Error", "File with this name already exists.")
    elif new_file_name:
        messagebox.showinfo("No Change", "Filename is the same as before.")

# Function to populate the file frame with buttons for each text file
def populate_files_json(directory, file_frame):
    # Clear files
    for widget in file_frame.winfo_children():
        widget.destroy()
    
    # fullscreen button
    #flsc_button = tk.Button(file_frame, text='fullscreen', command=set_full_screen)
    #flsc_button.pack(side=tk.TOP)

    files = [f for f in os.listdir(directory) if f.endswith('.json')]
    sorted_files = sorted(files, key=lambda x: os.path.getmtime(os.path.join(directory, x)), reverse=True)

    for file in sorted_files:
        file_path = os.path.join(directory, file)
        file_frame_row = tk.Frame(file_frame)
        file_frame_row.pack(fill='x', expand=False)

        btn = tk.Button(file_frame_row, text=file.split('.')[0], command=lambda f=file_path: load_text_json(f))
        btn.pack(side=tk.LEFT, fill='x', expand=False)

        rename_btn = tk.Button(file_frame_row, text='..', command=lambda f=file_path: rename_file(f)) #✏️
        rename_btn.pack(side=tk.RIGHT)

        del_btn = tk.Button(file_frame_row, text='-', command=lambda f=file_path: delete_file(f))
        del_btn.pack(side=tk.RIGHT)

# Initialize the main Tkinter window
app = tk.Tk()
app.title("GPT")

# Create directory if it doesn't exist
directory = 'texts'  # Specify your directory here
if not os.path.exists(directory):
    os.makedirs(directory)


# Create a frame that will contain the canvas and scrollbar
file_frame_container = tk.Frame(app)
file_frame_container.grid(row=0, column=0, sticky="ns")

# Create the canvas and a vertical scrollbar attached to it
file_canvas = tk.Canvas(file_frame_container)
file_scrollbar = tk.Scrollbar(file_frame_container, orient="vertical", command=file_canvas.yview)

# Pack the scrollbar to the right of file_frame_container, fill Y
file_scrollbar.pack(side="right", fill="y")

# Pack the canvas into file_frame_container and fill in both directions. Expand=True allows it to fill the space
file_canvas.pack(side="left", fill="both", expand=True)

# Configure the canvas to respond to scrollbar movements
file_canvas.configure(yscrollcommand=file_scrollbar.set)

# Create a frame inside the canvas which will contain the files
file_frame = tk.Frame(file_canvas)

# Add the file_frame to the canvas
file_canvas.create_window((0, 0), window=file_frame, anchor="nw")

def on_file_frame_configure(event):
    # Update the scroll region to encompass the file_frame
    file_canvas.configure(scrollregion=file_canvas.bbox("all"))

# Bind the configure event of file_frame to on_file_frame_configure, so it gets updated when its size changes
file_frame.bind("<Configure>", on_file_frame_configure)


# Define and configure frames
# file_frame = tk.Frame(app)
viewport_frame = tk.Frame(app)
input_frame = tk.Frame(app)
dropdown_frame = tk.Frame(app)
# file_frame.grid(row=0, column=0, sticky="ns")
viewport_frame.grid(row=0, column=1, sticky="nsew")
input_frame.grid(row=1, column=1, sticky="ew")
dropdown_frame.grid(row=1, column=0, sticky="ns")

# Set up text area with scrollbar
text_area = tk.Text(viewport_frame, wrap=tk.WORD)
scrollbar = tk.Scrollbar(viewport_frame, command=text_area.yview)
text_area['yscrollcommand'] = scrollbar.set
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
text_area.pack(expand=True, fill='both')

# Function to handle model selection from the dropdown
def on_model_select(event):
    global selected_model
    selected_model = model_dropdown.get()

# Dropdown for model selection
selected_model = list(openai_models.keys())[0]
# model_options = ['gpt-4', 'gpt-4-turbo-preview', 'gpt-3.5-turbo', "claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
model_options = list(openai_models.keys()) + list(anthropic_models.keys())
model_dropdown = tk.ttk.Combobox(dropdown_frame, values=model_options)
model_dropdown.set(selected_model)
model_dropdown.pack(side=tk.LEFT)
model_dropdown.bind("<<ComboboxSelected>>", on_model_select)

# Input box and send button
input_box = tk.Entry(input_frame)
input_box.pack(side=tk.LEFT, expand=True, fill='x')
send_button = tk.Button(input_frame, text='Send', command=append_text_json)
send_button.pack(side=tk.RIGHT)
plus_button = tk.Button(dropdown_frame, text='+', command=clear_text_and_reset_path)
plus_button.pack(side=tk.RIGHT)
    
app.bind('<Return>', lambda event: append_text_json())
app.bind("<Control-n>", clear_text_and_reset_path())

# Adjust column weights for layout
app.grid_columnconfigure(0, weight=0)
app.grid_columnconfigure(1, weight=4)
app.grid_rowconfigure(0, weight=1)
app.grid_rowconfigure(1, weight=0)

# Populate the directory with file buttons
populate_files_json(directory, file_frame)

# app.attributes("-fullscreen", True)

# Start the Tkinter event loop
app.mainloop()
