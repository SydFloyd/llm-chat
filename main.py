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
            chat_name_sanitized = "chat"
            
        # Add timestamp to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{chat_name_sanitized}_{timestamp}.json"
            
        return os.path.join(self.directory, filename)
    
    def save_chat(self, filepath, model, user_text, assistant_text):
        """Save or update a chat file"""
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as file:
                data = json.load(file)
                # Update the last modified timestamp
                data['last_modified'] = timestamp
        else:    
            data = {
                'chat_creation': timestamp,
                'last_modified': timestamp,
                'model': model,
                'message_history': []
            }

        # Append new messages with timestamps
        data['message_history'].append({
            'role': 'user', 
            'content': user_text,
            'timestamp': timestamp
        })
        data['message_history'].append({
            'role': 'assistant', 
            'content': assistant_text,
            'timestamp': timestamp
        })
        
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
            
    def get_display_name(self, filename):
        """Extract display name from filename by removing timestamp"""
        # Extract name without extension and timestamp
        name = os.path.basename(filename)
        if "_" in name:
            # Remove the timestamp part (assuming format name_timestamp.json)
            name = name.split("_")[0]
        else:
            # Remove extension if no timestamp
            name = os.path.splitext(name)[0]
        return name
        
    def rename_chat(self, old_path, new_name):
        """Rename a chat file while preserving timestamp"""
        if os.path.exists(old_path):
            # Extract the timestamp from old filename if it exists
            old_filename = os.path.basename(old_path)
            timestamp_part = ""
            
            if "_" in old_filename:
                # Get the timestamp part from the original filename
                parts = os.path.splitext(old_filename)[0].split("_")
                if len(parts) > 1:
                    timestamp_part = "_" + parts[1]
            
            # If no timestamp exists, add a new one to ensure uniqueness
            if not timestamp_part:
                timestamp_part = "_" + datetime.now().strftime("%Y%m%d%H%M%S")
                
            # Create new filename with sanitized name and original timestamp
            new_filename = re.sub(r'[<>:"/\\|?*]', '', new_name).strip() + timestamp_part + ".json"
            new_path = os.path.join(self.directory, new_filename)
            
            # If the exact path already exists, add additional uniqueness
            if os.path.exists(new_path) and new_path != old_path:
                extra_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                new_filename = re.sub(r'[<>:"/\\|?*]', '', new_name).strip() + "_" + extra_timestamp + ".json"
                new_path = os.path.join(self.directory, new_filename)
                
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
        
        # Set a reasonable default size
        root.geometry("1000x700")
        
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
        # Configure the main window grid
        self.root.grid_columnconfigure(1, weight=1)  # Make column 1 expandable
        self.root.grid_rowconfigure(0, weight=1)     # Make row 0 expandable
        
        # Create a PanedWindow oriented horizontally
        self.paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned_window.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Create frames for chat list and chat view
        self.file_frame_container = tk.Frame(self.paned_window, width=200, bg="lightgray")
        self.file_frame_container.pack_propagate(False)  # Prevent the frame from shrinking
        
        self.viewport_frame = tk.Frame(self.paned_window, bg="white")
        
        # Add the frames to the paned window with initial sizes
        self.paned_window.add(self.file_frame_container)
        self.paned_window.add(self.viewport_frame)
        
        # Create bottom row frames
        self.dropdown_frame = tk.Frame(self.root)
        self.dropdown_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        self.input_frame = tk.Frame(self.root)
        self.input_frame.grid(row=1, column=1, sticky="ew", padx=5, pady=5)
        
        # Create all UI components
        self._create_file_list()
        self._create_chat_display()
        self._create_input_area()
        self._create_model_selection()
    
    def _create_file_list(self):
        """Create the scrollable file list area"""
        # Create a label for the file list section
        file_label = tk.Label(self.file_frame_container, text="Chat History", bg="lightgray", font=("Arial", 10, "bold"))
        file_label.pack(side="top", fill="x", padx=5, pady=5)
        
        # Create canvas and scrollbar for file list
        self.file_canvas = tk.Canvas(self.file_frame_container, bg="lightgray", highlightthickness=0)
        self.file_scrollbar = tk.Scrollbar(self.file_frame_container, orient="vertical", command=self.file_canvas.yview)
        
        # Configure canvas and scrollbar
        self.file_scrollbar.pack(side="right", fill="y")
        self.file_canvas.pack(side="left", fill="both", expand=True)
        self.file_canvas.configure(yscrollcommand=self.file_scrollbar.set)
        
        # Create frame for file buttons
        self.file_frame = tk.Frame(self.file_canvas, bg="lightgray")
        self.file_canvas.create_window((0, 0), window=self.file_frame, anchor="nw", width=self.file_canvas.winfo_width())
        
        # Configure canvas to update scrollregion when file_frame changes
        self.file_frame.bind("<Configure>", self._on_file_frame_configure)
        
        # Make the canvas resize with its container
        self.file_frame_container.bind("<Configure>", self._on_file_container_configure)
    
    def _create_chat_display(self):
        """Create the chat display area"""
        # Create text area with scrollbar
        self.text_area = tk.Text(self.viewport_frame, wrap=tk.WORD, padx=10, pady=10)
        self.text_scrollbar = tk.Scrollbar(self.viewport_frame, command=self.text_area.yview)
        
        # Configure text area and scrollbar
        self.text_area['yscrollcommand'] = self.text_scrollbar.set
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.pack(expand=True, fill='both')
        
        # Set a nice base font
        base_font = ("Segoe UI", 10)
        self.text_area.configure(font=base_font)
        
        # No markdown formatting
        
        # Configure tags for user/assistant messages with better visual differentiation
        # Use only supported tag options (removing pady, padx, relief, borderwidth)
        self.text_area.tag_configure("user_header", 
                                    background="#e1f5fe", 
                                    font=(base_font[0], base_font[1], "bold"))
        
        self.text_area.tag_configure("assistant_header", 
                                    background="#e8f5e9", 
                                    font=(base_font[0], base_font[1], "bold"))
        
        self.text_area.tag_configure("user_content", 
                                    background="#f5f5f5",
                                    lmargin1=20,
                                    lmargin2=20)
        
        self.text_area.tag_configure("assistant_content", 
                                    background="#ffffff",
                                    lmargin1=20,
                                    lmargin2=20)
    
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
        self.text_area.config(state=tk.NORMAL)  # Ensure text area is editable
        
        for i, message in enumerate(data['message_history']):
            is_user = message['role'] == "user"
            speaker = "User" if is_user else data['model']
            header_tag = "user_header" if is_user else "assistant_header"
            content_tag = "user_content" if is_user else "assistant_content"
            
            # Add space between messages (but not before the first one)
            if i > 0:
                self.text_area.insert(tk.END, "\n\n")
            
            # Insert message header with background color (without timestamp to reduce clutter)
            self.text_area.insert(tk.END, f"  {speaker}:  \n\n", header_tag)
            
            # Insert message content with padding before and after
            # Add space before content for padding
            self.text_area.insert(tk.END, "  " + message['content'].replace("\n", "\n  ") + "\n", content_tag)
            
        # Scroll to the end to show the latest messages
        self.text_area.see(tk.END)
    
    # Markdown formatting removed
    
    # Markdown pattern tagging removed
    
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
        # Get display name without timestamp
        old_name = self.chat_manager.get_display_name(os.path.basename(old_filepath))
        new_name = simpledialog.askstring("Rename File", "Enter new filename:", initialvalue=old_name)
        
        if not new_name:
            return
            
        if new_name == old_name:
            messagebox.showinfo("No Change", "Filename is the same as before.")
            return
        
        # Our improved rename_chat will handle duplicates automatically    
        new_filepath = self.chat_manager.rename_chat(old_filepath, new_name)
        if new_filepath:
            if old_filepath == self.current_filepath:
                self.current_filepath = new_filepath
            self._populate_files()
        else:
            messagebox.showerror("Error", "Couldn't rename the file.")
    
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
            
            # Get display name (without timestamp)
            display_name = self.chat_manager.get_display_name(file)
            
            # Add tooltip with full timestamp by loading creation date from file
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    creation_date = data.get('chat_creation', '')
                    tooltip = f"Created: {creation_date}" if creation_date else file
            except (json.JSONDecodeError, FileNotFoundError):
                tooltip = file
            
            # Create a row frame for this file
            file_frame_row = tk.Frame(self.file_frame, bg="lightgray")
            file_frame_row.pack(fill='x', expand=False, padx=2, pady=2)
            
            # Create buttons
            btn = tk.Button(file_frame_row, text=display_name, 
                           command=lambda f=file_path: self._load_chat(f),
                           anchor="w", relief=tk.FLAT, bg="#e0e0e0")
            btn.pack(side=tk.LEFT, fill='x', expand=True)
            
            # Create tooltip functionality (hover text)
            self._create_tooltip(btn, tooltip)
            
            rename_btn = tk.Button(file_frame_row, text='..', 
                                  command=lambda f=file_path: self.rename_chat(f),
                                  relief=tk.FLAT, bg="#e0e0e0")
            rename_btn.pack(side=tk.RIGHT)
            
            del_btn = tk.Button(file_frame_row, text='🗑', 
                               command=lambda f=file_path: self.delete_chat(f),
                               relief=tk.FLAT, bg="#e0e0e0")
            del_btn.pack(side=tk.RIGHT)
            
        # Force update to recalculate scroll region
        self.file_frame.update_idletasks()
        self.file_canvas.configure(scrollregion=self.file_canvas.bbox("all"))
        
    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""
        def enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 20
            
            # Create a toplevel window
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tooltip, text=text, justify='left',
                           background="#ffffe0", relief="solid", borderwidth=1,
                           font=("Arial", "8", "normal"))
            label.pack(ipadx=1)
            
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
                
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    def _load_chat(self, filepath):
        """Load a chat from file and display it"""
        self.current_filepath = filepath
        self._display_chat(filepath)
    
    def _on_file_frame_configure(self, event):
        """Handle file frame configuration to update scrollbar"""
        self.file_canvas.configure(scrollregion=self.file_canvas.bbox("all"))
        
    def _on_file_container_configure(self, event):
        """Resize the canvas when the container changes size"""
        # Update the canvas size
        width = event.width - self.file_scrollbar.winfo_width()
        self.file_canvas.itemconfig(1, width=width)  # Update the window width
    
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
    
    # Set minimum and default window size
    root.minsize(800, 600)
    root.geometry("1000x700")
    
    # Create the chat application
    app = ChatApp(root)
    
    # Optional fullscreen mode
    # root.attributes("-fullscreen", True)
    
    # Start the Tkinter event loop
    root.mainloop()
