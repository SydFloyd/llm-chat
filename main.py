import os
import re
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox
import tkinter.simpledialog as simpledialog
from datetime import datetime
import json
from gpt import GPT, list_openai_models
from claude import Claude, list_anthropic_models

class ChatManager:
    """Manages chat data storage and retrieval"""
    
    def __init__(self, directory="texts"):
        self.directory = directory
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    def generate_filename(self, text):
        """Generate a filename from user text without API call"""
        # Extract first 5-10 words or 30 chars, whichever is shorter
        words = text.split()[:5]
        name = " ".join(words)
        if len(name) > 30:
            name = name[:30]
        
        # Sanitize the filename
        chat_name_sanitized = re.sub(r'[<>:"/\\|?*]', '', name).strip()
        if not chat_name_sanitized:
            # Fallback to timestamp if no valid name could be created
            chat_name_sanitized = datetime.now().strftime("%Y%m%d%H%M%S")
            
        return os.path.join(self.directory, chat_name_sanitized + ".json")
    
    def save_chat(self, filepath, model, user_text, assistant_text):
        """Save or update a chat file"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as file:
                data = json.load(file)
        else:    
            data = {
                'chat_creation': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'model': model,
                'message_history': []
            }

        # Append new messages
        data['message_history'].append({'role': 'user', 'content': user_text})
        data['message_history'].append({'role': 'assistant', 'content': assistant_text})
        
        with open(filepath, 'w') as file:
            json.dump(data, file, indent=4)
    
    def load_chat(self, filepath):
        """Load chat data from file"""
        with open(filepath, 'r') as file:
            return json.load(file)
    
    def get_message_history(self, filepath):
        """Get just the message history from a file"""
        if filepath and os.path.exists(filepath):
            data = self.load_chat(filepath)
            return data.get('message_history', [])
        return []
    
    def delete_chat(self, filepath):
        """Delete a chat file"""
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
            
    def rename_chat(self, old_path, new_name):
        """Rename a chat file"""
        if os.path.exists(old_path):
            new_path = os.path.join(self.directory, new_name + ".json")
            if not os.path.exists(new_path):
                os.rename(old_path, new_path)
                return new_path
        return None
    
    def list_chats(self):
        """List all chat files sorted by modification time"""
        files = [f for f in os.listdir(self.directory) if f.endswith('.json')]
        return sorted(files, key=lambda x: os.path.getmtime(os.path.join(self.directory, x)), reverse=True)


class ChatApp:
    """Main chat application class"""
    
    def __init__(self, root):
        self.root = root
        root.title("Chat Application")
        
        # Initialize models
        self.openai_models = list_openai_models()
        self.anthropic_models = list_anthropic_models()
        
        # Initialize chat manager
        self.chat_manager = ChatManager()
        
        # Set up state variables
        self.current_filepath = None
        self.selected_model = list(self.openai_models.keys())[0]
        
        # Create the UI
        self._create_ui()
        
        # Bind events
        self._bind_events()
        
        # Populate files
        self._populate_files()
    
    def _create_ui(self):
        """Create the user interface"""
        # Create frame containers
        self.file_frame_container = tk.Frame(self.root)
        self.viewport_frame = tk.Frame(self.root)
        self.input_frame = tk.Frame(self.root)
        self.dropdown_frame = tk.Frame(self.root)
        
        # Position frame containers in grid
        self.file_frame_container.grid(row=0, column=0, sticky="ns")
        self.viewport_frame.grid(row=0, column=1, sticky="nsew")
        self.input_frame.grid(row=1, column=1, sticky="ew")
        self.dropdown_frame.grid(row=1, column=0, sticky="ns")
        
        # Create scrollable file list area
        self._create_file_list()
        
        # Create chat display area
        self._create_chat_display()
        
        # Create input area
        self._create_input_area()
        
        # Create model selection area
        self._create_model_selection()
        
        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=0)
        self.root.grid_columnconfigure(1, weight=4)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
    
    def _create_file_list(self):
        """Create the scrollable file list area"""
        # Create canvas and scrollbar for file list
        self.file_canvas = tk.Canvas(self.file_frame_container)
        self.file_scrollbar = tk.Scrollbar(self.file_frame_container, orient="vertical", command=self.file_canvas.yview)
        
        # Configure canvas and scrollbar
        self.file_scrollbar.pack(side="right", fill="y")
        self.file_canvas.pack(side="left", fill="both", expand=True)
        self.file_canvas.configure(yscrollcommand=self.file_scrollbar.set)
        
        # Create frame for file buttons
        self.file_frame = tk.Frame(self.file_canvas)
        self.file_canvas.create_window((0, 0), window=self.file_frame, anchor="nw")
        
        # Configure canvas to update scrollregion when file_frame changes
        self.file_frame.bind("<Configure>", self._on_file_frame_configure)
    
    def _create_chat_display(self):
        """Create the chat display area"""
        # Create text area with scrollbar
        self.text_area = tk.Text(self.viewport_frame, wrap=tk.WORD)
        self.text_scrollbar = tk.Scrollbar(self.viewport_frame, command=self.text_area.yview)
        
        # Configure text area and scrollbar
        self.text_area['yscrollcommand'] = self.text_scrollbar.set
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.pack(expand=True, fill='both')
    
    def _create_input_area(self):
        """Create the input area"""
        # Create input box and send button
        self.input_box = tk.Entry(self.input_frame)
        self.send_button = tk.Button(self.input_frame, text='Send', command=self.send_message)
        
        # Configure input box and send button
        self.input_box.pack(side=tk.LEFT, expand=True, fill='x')
        self.send_button.pack(side=tk.RIGHT)
    
    def _create_model_selection(self):
        """Create the model selection area"""
        # Create model dropdown and new chat button
        model_options = list(self.openai_models.keys()) + list(self.anthropic_models.keys())
        self.model_dropdown = tk.ttk.Combobox(self.dropdown_frame, values=model_options)
        self.model_dropdown.set(self.selected_model)
        self.plus_button = tk.Button(self.dropdown_frame, text='+', command=self.new_chat)
        
        # Configure model dropdown and new chat button
        self.model_dropdown.pack(side=tk.LEFT)
        self.plus_button.pack(side=tk.RIGHT)
    
    def _bind_events(self):
        """Bind events to functions"""
        # Bind model selection
        self.model_dropdown.bind("<<ComboboxSelected>>", self._on_model_select)
        
        # Bind key commands
        self.root.bind('<Return>', lambda event: self.send_message())
        self.root.bind("<Control-n>", lambda event: self.new_chat())
        
        # Bind Ctrl+Backspace for deleting previous word
        self.text_area.bind("<Control-BackSpace>", self._delete_previous_word_textarea)
        self.input_box.bind("<Control-BackSpace>", self._delete_previous_word_input)
        
        # Alternative bindings for different platforms
        self.text_area.bind("<Control-h>", self._delete_previous_word_textarea)
        self.input_box.bind("<Control-h>", self._delete_previous_word_input)
    
    def new_chat(self):
        """Clear the chat area and reset the current filepath"""
        self.text_area.delete('1.0', tk.END)
        self.current_filepath = None
    
    def send_message(self):
        """Send the user message and get a response"""
        text = self.input_box.get()
        if not text:
            return
            
        # Create a new chat file if needed
        if self.current_filepath is None:
            self.current_filepath = self.chat_manager.generate_filename(text)
            message_history = []
        else:
            message_history = self.chat_manager.get_message_history(self.current_filepath)
        
        # Get response from appropriate model
        if self.selected_model in self.anthropic_models.keys():
            m = Claude(model=self.anthropic_models[self.selected_model], injected_messages=message_history)
        elif self.selected_model in self.openai_models.keys():
            m = GPT(model=self.openai_models[self.selected_model], injected_messages=message_history)
        else:
            print(f"Unrecognized model: {self.selected_model}")
            return
            
        response = m.prompt(text)
        
        # Save and display the chat
        self.chat_manager.save_chat(self.current_filepath, self.selected_model, text, response)
        self._display_chat(self.current_filepath)
        
        # Update the file list
        self._populate_files()
        
        # Clear the input box
        self.input_box.delete(0, tk.END)

    def _display_chat(self, filepath):
        """Display chat contents in the text area"""
        data = self.chat_manager.load_chat(filepath)
        
        self.text_area.delete('1.0', tk.END)
        for message in data['message_history']:
            speaker = "User" if message['role'] == "user" else data['model']
            self.text_area.insert(tk.END, f"  {speaker}: {message['content']}\n\n\n")
    
    def delete_chat(self, filepath):
        """Delete a chat file"""
        result = messagebox.askokcancel("Confirm Deletion", "Are you sure you want to delete this file?")
        if result:
            if self.chat_manager.delete_chat(filepath):
                if filepath == self.current_filepath:
                    self.new_chat()
                self._populate_files()
    
    def rename_chat(self, old_filepath):
        """Rename a chat file"""
        old_name = os.path.basename(old_filepath).split('.')[0]
        new_name = simpledialog.askstring("Rename File", "Enter new filename:", initialvalue=old_name)
        
        if not new_name:
            return
            
        if new_name == old_name:
            messagebox.showinfo("No Change", "Filename is the same as before.")
            return
            
        new_filepath = self.chat_manager.rename_chat(old_filepath, new_name)
        if new_filepath:
            if old_filepath == self.current_filepath:
                self.current_filepath = new_filepath
            self._populate_files()
        else:
            messagebox.showerror("Error", "File with this name already exists or couldn't be renamed.")
    
    def _populate_files(self):
        """Populate the file frame with buttons for each chat file"""
        # Clear existing files
        for widget in self.file_frame.winfo_children():
            widget.destroy()
        
        # Get list of chat files
        files = self.chat_manager.list_chats()
        
        # Create a button for each file
        for file in files:
            file_path = os.path.join(self.chat_manager.directory, file)
            
            # Create a row frame for this file
            file_frame_row = tk.Frame(self.file_frame)
            file_frame_row.pack(fill='x', expand=False)
            
            # Create buttons
            btn = tk.Button(file_frame_row, text=file.split('.')[0], 
                           command=lambda f=file_path: self._load_chat(f))
            btn.pack(side=tk.LEFT, fill='x', expand=True)
            
            rename_btn = tk.Button(file_frame_row, text='..', 
                                  command=lambda f=file_path: self.rename_chat(f))
            rename_btn.pack(side=tk.RIGHT)
            
            del_btn = tk.Button(file_frame_row, text='🗑', 
                               command=lambda f=file_path: self.delete_chat(f))
            del_btn.pack(side=tk.RIGHT)
    
    def _load_chat(self, filepath):
        """Load a chat from file and display it"""
        self.current_filepath = filepath
        self._display_chat(filepath)
    
    def _on_file_frame_configure(self, event):
        """Handle file frame configuration to update scrollbar"""
        self.file_canvas.configure(scrollregion=self.file_canvas.bbox("all"))
    
    def _on_model_select(self, event):
        """Handle model selection from dropdown"""
        self.selected_model = self.model_dropdown.get()
        self.new_chat()

    def _delete_previous_word_input(self, event):
        """Delete the previous word in the input box"""
        current_pos = self.input_box.index(tk.INSERT)
        text = self.input_box.get()
        
        # If at start of input, do nothing
        if current_pos == 0:
            return "break"
        
        # Get text from beginning to current position
        text_before = text[:current_pos]
        
        # Find the last word and any space before the cursor
        match = re.search(r'(\S+)(\s*)$', text_before)
        
        if match:
            # Word found, delete from the start of the word
            word = match.group(1)
            spaces = match.group(2)
            
            # If we're right after the word (no spaces), look for the previous word + spaces
            if not spaces and current_pos > len(word):
                remaining_text = text_before[:-len(word)]
                prev_match = re.search(r'(\S+)(\s+)$', remaining_text)
                if prev_match:
                    prev_word = prev_match.group(1)
                    prev_spaces = prev_match.group(2)
                    # Delete the previous word + its spaces
                    prev_start = current_pos - len(word) - len(prev_spaces) - len(prev_word)
                    self.input_box.delete(prev_start, current_pos - len(word))
                    return "break"
            
            # Delete the word (and its spaces if any)
            word_start = current_pos - len(word) - len(spaces)
            self.input_box.delete(word_start, current_pos)
        else:
            # If no match (rare case), just delete the last character
            self.input_box.delete(current_pos-1, current_pos)
        
        return "break"  # Prevent the default handling

    def _delete_previous_word_textarea(self, event):
        """Delete the previous word in the text area"""
        current_pos = self.text_area.index(tk.INSERT)
        # Get the line and column of current position
        line, col = map(int, current_pos.split('.'))
        
        # If at the beginning of a line and not the first line, move to end of previous line
        if col == 0 and line > 1:
            prev_line = line - 1
            prev_line_length = int(self.text_area.index(f"{prev_line}.end").split('.')[1])
            self.text_area.delete(f"{prev_line}.{prev_line_length}", current_pos)
            return "break"
        
        # If at beginning of first line, do nothing
        if col == 0 and line == 1:
            return "break"
        
        # Get text from beginning of line to current position
        line_text = self.text_area.get(f"{line}.0", current_pos)
        
        # Find the last word and any space before the cursor
        match = re.search(r'(\S+)(\s*)$', line_text)
        
        if match:
            word = match.group(1)
            spaces = match.group(2)
            
            # If we're right after the word (no spaces), look for the previous word + spaces
            if not spaces and col > len(word):
                remaining_text = line_text[:-len(word)]
                prev_match = re.search(r'(\S+)(\s+)$', remaining_text)
                if prev_match:
                    prev_word = prev_match.group(1)
                    prev_spaces = prev_match.group(2)
                    # Delete the previous word + its spaces
                    prev_start_col = col - len(word) - len(prev_spaces) - len(prev_word)
                    self.text_area.delete(f"{line}.{prev_start_col}", f"{line}.{col - len(word)}")
                    return "break"
            
            # Delete the word (and its spaces if any)
            word_start_col = col - len(word) - len(spaces)
            self.text_area.delete(f"{line}.{word_start_col}", current_pos)
        else:
            # If no match, delete from beginning of line
            self.text_area.delete(f"{line}.0", current_pos)
        
        return "break"  # Prevent the default handling


# Initialize the main application
if __name__ == "__main__":
    # Create the main Tkinter window
    root = tk.Tk()
    root.title("Chat Application")
    
    # Create the chat application
    app = ChatApp(root)
    
    # Optional fullscreen mode
    # root.attributes("-fullscreen", True)
    
    # Start the Tkinter event loop
    root.mainloop()
