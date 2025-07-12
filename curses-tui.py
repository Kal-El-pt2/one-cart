import json
import webbrowser
import os
import sys
import curses
import threading
import time
import pyperclip

# Try to import windows-curses on Windows
try:
    import curses
except ImportError:
    try:
        import windows_curses as curses
    except ImportError:
        print("Please install windows-curses: pip install windows-curses")
        sys.exit(1)

JSON_FILE = "products.json"
LINKS_KEY = "_links"

class ProductLinkManagerTUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.data = self.load_data()
        self.path = []
        self.current_selection = 0
        self.running = True
        self.status_message = ""
        self.status_time = 0
        self.mode = "browse"
        self.add_inputs = ["", ""]
        self.add_input_index = 0
        self.scroll_offset = 0
        
        # Initialize curses
        curses.curs_set(0)  # Hide cursor
        self.stdscr.clear()
        
        # Initialize colors
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)      # Header
        curses.init_pair(2, curses.COLOR_GREEN, -1)     # Categories
        curses.init_pair(3, curses.COLOR_YELLOW, -1)    # Links
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Selected
        curses.init_pair(5, curses.COLOR_RED, -1)       # Error
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)   # Status
        
        # Get terminal dimensions
        self.height, self.width = self.stdscr.getmaxyx()
        
    def load_data(self):
        if not os.path.exists(JSON_FILE):
            return {}
        try:
            with open(JSON_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def save_data(self):
        try:
            with open(JSON_FILE, "w", encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.show_status(f"❌ Save failed: {str(e)}")
    
    def resolve_path(self, path):
        ref = self.data
        for key in path:
            ref = ref.get(key, {})
        return ref
    
    def get_current_items(self):
        node = self.resolve_path(self.path)
        subcategories = [k for k in node if k != LINKS_KEY]
        links = node.get(LINKS_KEY, [])
        
        items = []
        
        # Add subcategories
        for sub in subcategories:
            items.append(("category", sub))
        
        # Add links
        for link in links:
            if isinstance(link, list) and len(link) == 2:
                url, desc = link
                display_text = desc if desc.strip() else url
            else:
                display_text = link
            items.append(("link", display_text, link))
        
        return items
    
    def show_status(self, message):
        self.status_message = message
        self.status_time = time.time()
    
    def paste_from_clipboard(self):
        """Paste text from clipboard to current input field"""
        try:
            paste_text = pyperclip.paste()
            if paste_text:
                # Clean up the pasted text (remove newlines, extra spaces)
                paste_text = paste_text.strip().replace('\n', ' ').replace('\r', ' ')
                while '  ' in paste_text:  # Remove multiple spaces
                    paste_text = paste_text.replace('  ', ' ')
                
                # If pasting into URL field and it looks like a URL, replace entirely
                if self.add_input_index == 0 and (paste_text.startswith('http://') or paste_text.startswith('https://')):
                    self.add_inputs[self.add_input_index] = paste_text
                    self.show_status(f"📋 Pasted URL: {paste_text[:50]}{'...' if len(paste_text) > 50 else ''}")
                else:
                    # Otherwise append to current text
                    self.add_inputs[self.add_input_index] += paste_text
                    self.show_status(f"📋 Pasted: {paste_text[:30]}{'...' if len(paste_text) > 30 else ''}")
            else:
                self.show_status("📋 Clipboard is empty")
        except Exception as e:
            self.show_status(f"❌ Paste failed: {str(e)}")
    
    def safe_addstr(self, y, x, text, attr=0):
        """Safely add string to screen, handling out-of-bounds"""
        try:
            if y < self.height - 1 and x < self.width - 1:
                # Truncate text if it would go off screen
                max_len = self.width - x - 1
                if len(text) > max_len:
                    text = text[:max_len-3] + "..."
                self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass  # Ignore curses errors for positioning
    
    def draw_box(self, y, x, height, width, title=""):
        """Draw a box with optional title"""
        try:
            # Draw corners
            self.stdscr.addch(y, x, curses.ACS_ULCORNER)
            self.stdscr.addch(y, x + width - 1, curses.ACS_URCORNER)
            self.stdscr.addch(y + height - 1, x, curses.ACS_LLCORNER)
            self.stdscr.addch(y + height - 1, x + width - 1, curses.ACS_LRCORNER)
            
            # Draw horizontal lines
            for i in range(1, width - 1):
                self.stdscr.addch(y, x + i, curses.ACS_HLINE)
                self.stdscr.addch(y + height - 1, x + i, curses.ACS_HLINE)
            
            # Draw vertical lines
            for i in range(1, height - 1):
                self.stdscr.addch(y + i, x, curses.ACS_VLINE)
                self.stdscr.addch(y + i, x + width - 1, curses.ACS_VLINE)
            
            # Add title if provided
            if title:
                title_text = f"[ {title} ]"
                title_x = x + (width - len(title_text)) // 2
                if title_x > x:
                    self.safe_addstr(y, title_x, title_text, curses.color_pair(1))
        except curses.error:
            pass
    
    def draw_display(self):
        """Draw the entire display"""
        self.stdscr.clear()
        
        # Header
        header_y = 0
        header_height = 4
        self.draw_box(header_y, 0, header_height, self.width, "Product Link Manager")
        
        title_text = "🛒 Product Link Manager (TUI)"
        self.safe_addstr(header_y + 1, (self.width - len(title_text)) // 2, title_text, curses.color_pair(1) | curses.A_BOLD)
        
        path_text = f"📂 {'/'.join(self.path) if self.path else 'root'}"
        self.safe_addstr(header_y + 2, 2, path_text, curses.color_pair(1))
        
        # Items area
        items_y = header_height
        items_height = self.height - 8  # Leave room for footer and status
        if self.mode == "adding":
            items_height -= 6  # Make room for input fields
        
        items = self.get_current_items()
        
        if not items:
            self.draw_box(items_y, 0, items_height, self.width, "Items (0 total)")
            no_items_text = "📭 No items in this category"
            self.safe_addstr(items_y + items_height // 2, (self.width - len(no_items_text)) // 2, no_items_text, curses.color_pair(3))
        else:
            self.draw_box(items_y, 0, items_height, self.width, f"Items ({len(items)} total)")
            
            # Calculate visible items
            visible_height = items_height - 2  # Account for box borders
            start_index = max(0, self.current_selection - visible_height // 2)
            end_index = min(len(items), start_index + visible_height)
            
            for i in range(start_index, end_index):
                item = items[i]
                y_pos = items_y + 1 + (i - start_index)
                
                if item[0] == "category":
                    prefix = "📁"
                    text = item[1]
                    color = curses.color_pair(2)
                else:
                    prefix = "🔗"
                    text = item[1]
                    color = curses.color_pair(3)
                
                # Truncate text if too long
                max_text_len = self.width - 8  # Account for prefix and padding
                if len(text) > max_text_len:
                    text = text[:max_text_len-3] + "..."
                
                display_text = f"{prefix} {text}"
                
                if i == self.current_selection and self.mode == "browse":
                    # Highlight selected item
                    self.safe_addstr(y_pos, 1, "►", curses.color_pair(4) | curses.A_BOLD)
                    self.safe_addstr(y_pos, 3, display_text, curses.color_pair(4) | curses.A_BOLD)
                else:
                    self.safe_addstr(y_pos, 3, display_text, color)
        
        # Input fields (if in adding mode)
        if self.mode == "adding":
            input_y = items_y + items_height
            input_height = 6
            
            self.draw_box(input_y, 0, input_height, self.width, "Add New Link")
            
            labels = ["URL", "Description"]
            for i, (label, val) in enumerate(zip(labels, self.add_inputs)):
                y_pos = input_y + 1 + i * 2
                is_active = i == self.add_input_index
                
                # Label
                self.safe_addstr(y_pos, 2, f"{label}:", curses.color_pair(1))
                
                # Input field
                input_text = val
                if is_active:
                    input_text += "█"  # Cursor
                    attr = curses.color_pair(4) | curses.A_BOLD
                else:
                    attr = curses.A_NORMAL
                
                # Truncate input if too long
                max_input_len = self.width - len(label) - 6
                if len(input_text) > max_input_len:
                    input_text = input_text[:max_input_len-3] + "..."
                
                self.safe_addstr(y_pos, len(label) + 4, input_text, attr)
            
            # Instructions
            instructions = "↑↓:switch | Tab:save | Esc:cancel | Ctrl+V/P:paste"
            self.safe_addstr(input_y + input_height - 2, 2, instructions, curses.color_pair(1))
        
        # Footer
        footer_y = self.height - 4
        footer_height = 3
        self.draw_box(footer_y, 0, footer_height, self.width, "Controls")
        
        controls = "↑↓:Navigate | Enter:Select | B:Back | A:Add | D:Delete | N:New Category | Q:Quit"
        # Split controls if too long
        if len(controls) > self.width - 4:
            controls1 = "↑↓:Navigate | Enter:Select | B:Back | A:Add"
            controls2 = "D:Delete | N:New Category | Q:Quit"
            self.safe_addstr(footer_y + 1, 2, controls1, curses.color_pair(1))
            self.safe_addstr(footer_y + 2, 2, controls2, curses.color_pair(1))
        else:
            self.safe_addstr(footer_y + 1, 2, controls, curses.color_pair(1))
        
        # Status message
        if self.status_message and time.time() - self.status_time < 3:
            status_y = self.height - 1
            self.safe_addstr(status_y, 0, " " * (self.width - 1), curses.color_pair(6))  # Clear line
            self.safe_addstr(status_y, 2, self.status_message[:self.width-4], curses.color_pair(6) | curses.A_BOLD)
        
        self.stdscr.refresh()
    
    def handle_browse_input(self, key):
        if key == curses.KEY_UP:
            self.current_selection = max(0, self.current_selection - 1)
        elif key == curses.KEY_DOWN:
            items = self.get_current_items()
            if items:
                self.current_selection = min(len(items) - 1, self.current_selection + 1)
        elif key == ord('\n') or key == curses.KEY_ENTER:
            self.handle_enter()
        elif key == ord('b') or key == ord('B'):
            self.handle_back()
        elif key == ord('a') or key == ord('A'):
            self.mode = "adding"
            self.add_inputs = ["", ""]
            self.add_input_index = 0
            # Auto-paste if clipboard contains a URL
            try:
                clipboard_content = pyperclip.paste()
                if clipboard_content and (clipboard_content.startswith('http://') or clipboard_content.startswith('https://')):
                    self.add_inputs[0] = clipboard_content.strip()
                    self.show_status("📋 Auto-pasted URL from clipboard")
            except:
                pass
        elif key == ord('d') or key == ord('D'):
            self.handle_delete()
        elif key == ord('n') or key == ord('N'):
            self.handle_new_category()
        elif key == ord('q') or key == ord('Q'):
            self.running = False
    
    def handle_adding_input(self, key):
        if key == curses.KEY_UP:
            self.add_input_index = max(0, self.add_input_index - 1)
        elif key == curses.KEY_DOWN:
            self.add_input_index = min(1, self.add_input_index + 1)
        elif key == 27:  # ESC
            self.mode = "browse"
            self.show_status("❌ Add cancelled")
        elif key == ord('p') or key == ord('P'):
            self.paste_from_clipboard()
        elif key == 22:  # Ctrl+V
            self.paste_from_clipboard()
        elif key == ord('\t'):  # Tab
            if not self.add_inputs[0].strip():
                self.show_status("❌ URL cannot be empty")
            else:
                # Save the new link
                node = self.resolve_path(self.path)
                links = node.setdefault(LINKS_KEY, [])
                links.append([self.add_inputs[0], self.add_inputs[1]])
                self.save_data()
                self.show_status(f"✅ Added: {self.add_inputs[0]}")
                self.mode = "browse"
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self.add_inputs[self.add_input_index]:
                self.add_inputs[self.add_input_index] = self.add_inputs[self.add_input_index][:-1]
        elif 32 <= key <= 126:  # Printable ASCII
            self.add_inputs[self.add_input_index] += chr(key)
    
    def handle_enter(self):
        items = self.get_current_items()
        if items and self.current_selection < len(items):
            item = items[self.current_selection]
            if item[0] == "category":
                # Navigate to category
                self.path.append(item[1])
                self.current_selection = 0
                self.show_status(f"Entered category: {item[1]}")
            else:
                # Open link
                link_data = item[2]
                url = link_data[0] if isinstance(link_data, list) else link_data
                try:
                    webbrowser.open_new_tab(url)
                    self.show_status(f"🌐 Opened: {url}")
                except:
                    self.show_status(f"❌ Failed to open: {url}")
    
    def handle_back(self):
        if self.path:
            category = self.path.pop()
            self.current_selection = 0
            self.show_status(f"Left category: {category}")
        else:
            self.show_status("❌ Already at root")
    
    def handle_delete(self):
        items = self.get_current_items()
        if not items or self.current_selection >= len(items):
            self.show_status("❌ No item to delete")
            return
        
        item = items[self.current_selection]
        
        # Simple confirmation - show message and wait for y/n
        self.stdscr.clear()
        if item[0] == "category":
            confirm_text = f"Delete category '{item[1]}' and all its contents? (y/n)"
        else:
            confirm_text = f"Delete link '{item[1]}'? (y/n)"
        
        self.safe_addstr(self.height // 2, (self.width - len(confirm_text)) // 2, confirm_text, curses.color_pair(5) | curses.A_BOLD)
        self.stdscr.refresh()
        
        key = self.stdscr.getch()
        if key == ord('y') or key == ord('Y'):
            if item[0] == "category":
                node = self.resolve_path(self.path)
                del node[item[1]]
                self.save_data()
                self.show_status(f"🗑️ Deleted category '{item[1]}'")
            else:
                node = self.resolve_path(self.path)
                links = node.get(LINKS_KEY, [])
                # Find the link index
                link_index = self.current_selection - len([k for k in node if k != LINKS_KEY])
                if 0 <= link_index < len(links):
                    links.pop(link_index)
                    self.save_data()
                    self.show_status("🗑️ Deleted link")
            
            # Adjust selection
            new_items = self.get_current_items()
            if self.current_selection >= len(new_items):
                self.current_selection = max(0, len(new_items) - 1)
        else:
            self.show_status("❌ Cancelled")
    
    def handle_new_category(self):
        # Simple input for new category name
        self.stdscr.clear()
        prompt = "Enter category name: "
        self.safe_addstr(self.height // 2, (self.width - len(prompt)) // 2 - 10, prompt, curses.color_pair(1))
        self.stdscr.refresh()
        
        # Enable cursor and echo for input
        curses.curs_set(1)
        curses.echo()
        
        try:
            # Get input
            input_y = self.height // 2
            input_x = (self.width - len(prompt)) // 2 - 10 + len(prompt)
            self.stdscr.move(input_y, input_x)
            name = self.stdscr.getstr(input_y, input_x, 50).decode('utf-8')
            
            if name:
                node = self.resolve_path(self.path)
                if name in node:
                    self.show_status("⚠️ Category already exists")
                else:
                    node[name] = {}
                    self.save_data()
                    self.show_status(f"✅ Created category: '{name}'")
            else:
                self.show_status("❌ No name provided")
        except:
            self.show_status("❌ Cancelled")
        finally:
            # Restore cursor and echo settings
            curses.curs_set(0)
            curses.noecho()
    
    def run(self):
        """Main run loop"""
        self.stdscr.timeout(100)  # Non-blocking input with 100ms timeout
        
        while self.running:
            # Update display
            self.draw_display()
            
            # Handle input
            try:
                key = self.stdscr.getch()
                if key != -1:  # Key was pressed
                    if self.mode == "browse":
                        self.handle_browse_input(key)
                    elif self.mode == "adding":
                        self.handle_adding_input(key)
            except:
                pass
            
            # Small delay to prevent high CPU usage
            time.sleep(0.01)

def main():
    def run_app(stdscr):
        app = ProductLinkManagerTUI(stdscr)
        app.run()
    
    try:
        curses.wrapper(run_app)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()