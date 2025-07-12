import json
import webbrowser
import os
import sys
import curses
import threading
import time
import pyperclip
import re

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
        self.category_input = ""
        self.category_cursor_pos = 0
        
        curses.curs_set(0) 
        self.stdscr.clear()
        
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)      
        curses.init_pair(2, curses.COLOR_GREEN, -1)     
        curses.init_pair(3, curses.COLOR_YELLOW, -1)    
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE) 
        curses.init_pair(5, curses.COLOR_RED, -1)       
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)   
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_RED)   
        
        self.edit_inputs = ["", ""] 
        self.edit_input_index = 0
        self.edit_category_input = ""
        self.edit_category_cursor_pos = 0
        self.edit_original_name = ""
        
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
        
        for sub in subcategories:
            items.append(("category", sub))
        

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
    
    def validate_category_name(self, name):
        if not name:
            return None, "Category name cannot be empty"
        
        name = name.strip()
        
        if not name:
            return None, "Category name cannot be empty"
        
        if re.search(r'[<>:"/\\|?*]', name):
            return None, "Category name contains invalid characters"
        
        if len(name) > 50:
            return None, "Category name too long (max 50 characters)"
        
        if name == LINKS_KEY:
            return None, f"'{LINKS_KEY}' is a reserved name"
        
        return name, None
    
    def paste_from_clipboard(self):
        try:
            paste_text = pyperclip.paste()
            if paste_text:
                paste_text = paste_text.strip().replace('\n', ' ').replace('\r', ' ')
                while '  ' in paste_text:
                    paste_text = paste_text.replace('  ', ' ')
                
                if self.mode == "adding":
                    if self.add_input_index == 0 and (paste_text.startswith('http://') or paste_text.startswith('https://')):
                        self.add_inputs[self.add_input_index] = paste_text
                        self.show_status(f"📋 Pasted URL: {paste_text[:50]}{'...' if len(paste_text) > 50 else ''}")
                    else:
                        self.add_inputs[self.add_input_index] += paste_text
                        self.show_status(f"📋 Pasted: {paste_text[:30]}{'...' if len(paste_text) > 30 else ''}")
                elif self.mode == "new_category":
                    cleaned_text = re.sub(r'[<>:"/\\|?*]', '', paste_text)
                    if len(self.category_input + cleaned_text) <= 50:
                        self.category_input += cleaned_text
                        self.category_cursor_pos = len(self.category_input)
                        self.show_status(f"📋 Pasted (cleaned): {cleaned_text[:30]}{'...' if len(cleaned_text) > 30 else ''}")
                    else:
                        self.show_status("❌ Paste would exceed character limit")
            else:
                self.show_status("📋 Clipboard is empty")
        except Exception as e:
            self.show_status(f"❌ Paste failed: {str(e)}")
    
    def safe_addstr(self, y, x, text, attr=0):
        try:
            if y < self.height - 1 and x < self.width - 1:

                max_len = self.width - x - 1
                if len(text) > max_len:
                    text = text[:max_len-3] + "..."
                self.stdscr.addstr(y, x, text, attr)
        except curses.error:
            pass 
    
    def draw_box(self, y, x, height, width, title=""):
        try:
            self.stdscr.addch(y, x, curses.ACS_ULCORNER)
            self.stdscr.addch(y, x + width - 1, curses.ACS_URCORNER)
            self.stdscr.addch(y + height - 1, x, curses.ACS_LLCORNER)
            self.stdscr.addch(y + height - 1, x + width - 1, curses.ACS_LRCORNER)
            
            for i in range(1, width - 1):
                self.stdscr.addch(y, x + i, curses.ACS_HLINE)
                self.stdscr.addch(y + height - 1, x + i, curses.ACS_HLINE)
            
            for i in range(1, height - 1):
                self.stdscr.addch(y + i, x, curses.ACS_VLINE)
                self.stdscr.addch(y + i, x + width - 1, curses.ACS_VLINE)
            
            if title:
                title_text = f"[ {title} ]"
                title_x = x + (width - len(title_text)) // 2
                if title_x > x:
                    self.safe_addstr(y, title_x, title_text, curses.color_pair(1))
        except curses.error:
            pass
    
    def draw_display(self):
        self.stdscr.clear()
        
        header_y = 0
        header_height = 4
        self.draw_box(header_y, 0, header_height, self.width, "Product Link Manager")
        
        title_text = "🛒 Product Link Manager (TUI)"
        self.safe_addstr(header_y + 1, (self.width - len(title_text)) // 2, title_text, curses.color_pair(1) | curses.A_BOLD)
        
        path_text = f"📂 {'/'.join(self.path) if self.path else 'root'}"
        self.safe_addstr(header_y + 2, 2, path_text, curses.color_pair(1))
        

        items_y = header_height
        items_height = self.height - 8  
        if self.mode == "adding":
            items_height -= 6  
        elif self.mode == "new_category":
            items_height -= 8  
        elif self.mode == "edit_link":
            items_height -= 8  
        elif self.mode == "edit_category":
            items_height -= 8  
        
        items = self.get_current_items()
        
        if not items:
            self.draw_box(items_y, 0, items_height, self.width, "Items (0 total)")
            no_items_text = "📭 No items in this category"
            self.safe_addstr(items_y + items_height // 2, (self.width - len(no_items_text)) // 2, no_items_text, curses.color_pair(3))
        else:
            self.draw_box(items_y, 0, items_height, self.width, f"Items ({len(items)} total)")
            
            visible_height = items_height - 2  
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
                
                max_text_len = self.width - 8
                if len(text) > max_text_len:
                    text = text[:max_text_len-3] + "..."
                
                display_text = f"{prefix} {text}"
                
                if i == self.current_selection and self.mode == "browse":
                    self.safe_addstr(y_pos, 1, "►", curses.color_pair(4) | curses.A_BOLD)
                    self.safe_addstr(y_pos, 3, display_text, curses.color_pair(4) | curses.A_BOLD)
                else:
                    self.safe_addstr(y_pos, 3, display_text, color)
        
        if self.mode == "adding":
            input_y = items_y + items_height
            input_height = 6
            
            self.draw_box(input_y, 0, input_height, self.width, "Add New Link")
            
            labels = ["URL", "Description"]
            for i, (label, val) in enumerate(zip(labels, self.add_inputs)):
                y_pos = input_y + 1 + i * 2
                is_active = i == self.add_input_index
                
                self.safe_addstr(y_pos, 2, f"{label}:", curses.color_pair(1))
                
                input_text = val
                if is_active:
                    input_text += "█"
                    attr = curses.color_pair(4) | curses.A_BOLD
                else:
                    attr = curses.A_NORMAL
                
                max_input_len = self.width - len(label) - 6
                if len(input_text) > max_input_len:
                    input_text = input_text[:max_input_len-3] + "..."
                
                self.safe_addstr(y_pos, len(label) + 4, input_text, attr)
            
            instructions = "↑↓:switch | Tab:save | Esc:cancel | Ctrl+V/P:paste"
            self.safe_addstr(input_y + input_height - 2, 2, instructions, curses.color_pair(1))
        
        elif self.mode == "new_category":
            input_y = items_y + items_height
            input_height = 8
            
            self.draw_box(input_y, 0, input_height, self.width, "Create New Category")
            
            self.safe_addstr(input_y + 1, 2, "Category Name:", curses.color_pair(1))
            
            display_input = self.category_input
            if len(display_input) < self.category_cursor_pos:
                display_input += " " * (self.category_cursor_pos - len(display_input))
            
            display_input = display_input[:self.category_cursor_pos] + "█" + display_input[self.category_cursor_pos:]
            
            max_input_len = self.width - 20
            if len(display_input) > max_input_len:
                display_input = display_input[:max_input_len-3] + "..."
            
            self.safe_addstr(input_y + 2, 4, display_input, curses.color_pair(4) | curses.A_BOLD)
            

            char_count = f"({len(self.category_input)}/50)"
            color = curses.color_pair(5) if len(self.category_input) > 45 else curses.color_pair(1)
            self.safe_addstr(input_y + 2, self.width - 12, char_count, color)
            
            if self.category_input:
                validated_name, error = self.validate_category_name(self.category_input)
                if error:
                    self.safe_addstr(input_y + 4, 2, f"❌ {error}", curses.color_pair(5))
                else:
                    node = self.resolve_path(self.path)
                    if validated_name in node:
                        self.safe_addstr(input_y + 4, 2, "⚠️ Category already exists", curses.color_pair(7))
                    else:
                        self.safe_addstr(input_y + 4, 2, f"✅ Will create: '{validated_name}'", curses.color_pair(2))
            
            instructions1 = "Enter:create | Esc:cancel | Ctrl+V/P:paste"
            instructions2 = "Backspace:delete | ←→:move cursor"
            self.safe_addstr(input_y + 5, 2, instructions1, curses.color_pair(1))
            self.safe_addstr(input_y + 6, 2, instructions2, curses.color_pair(1))

        elif self.mode == "edit_link":
            input_y = items_y + items_height
            input_height = 8  
            
            self.draw_box(input_y, 0, input_height, self.width, "Edit Link")
            
            labels = ["URL", "Description"]
            
            for i, (label, val) in enumerate(zip(labels, self.edit_inputs)):
                y_pos = input_y + 1 + i * 2  
                is_active = i == self.edit_input_index
                
                self.safe_addstr(y_pos, 2, f"{label}:", curses.color_pair(1))
                
                max_input_len = self.width - 6  
                
                if not hasattr(self, 'edit_input_scroll_offset'):
                    self.edit_input_scroll_offset = [0, 0]  # One for each field
                
                if len(self.edit_input_scroll_offset) <= i:
                    self.edit_input_scroll_offset.extend([0] * (i + 1 - len(self.edit_input_scroll_offset)))
                
                if not hasattr(self, 'edit_input_cursor_pos'):
                    self.edit_input_cursor_pos = [len(self.edit_inputs[0]), len(self.edit_inputs[1])]
                

                if len(self.edit_input_cursor_pos) <= i:
                    self.edit_input_cursor_pos.extend([len(val) for val in self.edit_inputs[i:]])
                

                self.edit_input_cursor_pos[i] = min(len(val), max(0, self.edit_input_cursor_pos[i]))
                
                cursor_pos = self.edit_input_cursor_pos[i]
                scroll_offset = self.edit_input_scroll_offset[i]
                

                if cursor_pos < scroll_offset:
                    self.edit_input_scroll_offset[i] = cursor_pos
                elif cursor_pos >= scroll_offset + max_input_len - 1:  
                    self.edit_input_scroll_offset[i] = cursor_pos - max_input_len + 2
                
                self.edit_input_scroll_offset[i] = max(0, self.edit_input_scroll_offset[i])
                
                scroll_offset = self.edit_input_scroll_offset[i]
                visible_text = val[scroll_offset:scroll_offset + max_input_len - 1]
                
                if is_active:
                    cursor_in_visible = cursor_pos - scroll_offset
                    if 0 <= cursor_in_visible < len(visible_text):
                        visible_text = visible_text[:cursor_in_visible] + "█" + visible_text[cursor_in_visible:]
                    elif cursor_in_visible == len(visible_text):
                        visible_text += "█"
                    attr = curses.color_pair(4) | curses.A_BOLD
                else:
                    attr = curses.A_NORMAL
                
                left_indicator = "◀" if scroll_offset > 0 else " "
                right_indicator = "▶" if scroll_offset + max_input_len - 1 < len(val) else " "
                
                display_line = left_indicator + visible_text + right_indicator
                if len(display_line) > max_input_len:
                    display_line = display_line[:max_input_len]
                
                self.safe_addstr(y_pos + 1, 3, display_line, attr)
            
            instructions = "↑↓:switch | Tab:save | Esc:cancel | ←→:scroll | Ctrl+V/P:paste"
            self.safe_addstr(input_y + input_height - 2, 2, instructions, curses.color_pair(1))

        elif self.mode == "edit_category":
            input_y = items_y + items_height
            input_height = 8
            
            self.draw_box(input_y, 0, input_height, self.width, "Edit Category")
            
            self.safe_addstr(input_y + 1, 2, "Category Name:", curses.color_pair(1))
            
            max_input_len = self.width - 20
            
            if not hasattr(self, 'edit_category_scroll_offset'):
                self.edit_category_scroll_offset = 0
            
            cursor_pos = self.edit_category_cursor_pos
            scroll_offset = self.edit_category_scroll_offset
            
            if cursor_pos < scroll_offset:
                self.edit_category_scroll_offset = cursor_pos
            elif cursor_pos >= scroll_offset + max_input_len - 1:
                self.edit_category_scroll_offset = cursor_pos - max_input_len + 2
            
            self.edit_category_scroll_offset = max(0, self.edit_category_scroll_offset)
            
            scroll_offset = self.edit_category_scroll_offset
            visible_text = self.edit_category_input[scroll_offset:scroll_offset + max_input_len - 1]
            
            cursor_in_visible = cursor_pos - scroll_offset
            if 0 <= cursor_in_visible < len(visible_text):
                visible_text = visible_text[:cursor_in_visible] + "█" + visible_text[cursor_in_visible:]
            elif cursor_in_visible == len(visible_text):
                visible_text += "█"
            
            left_indicator = "◀" if scroll_offset > 0 else " "
            right_indicator = "▶" if scroll_offset + max_input_len - 1 < len(self.edit_category_input) else " "
            
            display_line = left_indicator + visible_text + right_indicator
            if len(display_line) > max_input_len:
                display_line = display_line[:max_input_len]
            
            self.safe_addstr(input_y + 2, 3, display_line, curses.color_pair(4) | curses.A_BOLD)
            
            char_count = f"({len(self.edit_category_input)}/50)"
            color = curses.color_pair(5) if len(self.edit_category_input) > 45 else curses.color_pair(1)
            self.safe_addstr(input_y + 2, self.width - 12, char_count, color)
            
            if self.edit_category_input:
                validated_name, error = self.validate_category_name(self.edit_category_input)
                if error:
                    self.safe_addstr(input_y + 4, 2, f"❌ {error}", curses.color_pair(5))
                else:
                    if validated_name == self.edit_original_name:
                        self.safe_addstr(input_y + 4, 2, "ℹ️ No changes made", curses.color_pair(1))
                    else:
                        node = self.resolve_path(self.path)
                        if validated_name in node:
                            self.safe_addstr(input_y + 4, 2, "⚠️ Category already exists", curses.color_pair(7))
                        else:
                            self.safe_addstr(input_y + 4, 2, f"✅ Will rename to: '{validated_name}'", curses.color_pair(2))
            
            instructions1 = "Enter:save | Esc:cancel | ←→:scroll | Ctrl+V/P:paste"
            instructions2 = "Backspace:delete | Home/End:move cursor"
            self.safe_addstr(input_y + 5, 2, instructions1, curses.color_pair(1))
            self.safe_addstr(input_y + 6, 2, instructions2, curses.color_pair(1))

        if self.mode == "browse":
            footer_y = self.height - 4
            footer_height = 3
            self.draw_box(footer_y, 0, footer_height, self.width, "Controls")
            
            controls = "↑↓:Navigate | Enter:Select | B:Back | A:Add | E:Edit | D:Delete | N:New Category | Q:Quit"
            if len(controls) > self.width - 4:
                controls1 = "↑↓:Navigate | Enter:Select | B:Back | A:Add | E:Edit"
                controls2 = "D:Delete | N:New Category | Q:Quit"
                self.safe_addstr(footer_y + 1, 2, controls1, curses.color_pair(1))
                self.safe_addstr(footer_y + 2, 2, controls2, curses.color_pair(1))
            else:
                self.safe_addstr(footer_y + 1, 2, controls, curses.color_pair(1))
        
        if self.status_message and time.time() - self.status_time < 3:
            status_y = self.height - 1
            self.safe_addstr(status_y, 0, " " * (self.width - 1), curses.color_pair(6))  # Clear line
            self.safe_addstr(status_y, 2, self.status_message[:self.width-4], curses.color_pair(6) | curses.A_BOLD)
        
        self.stdscr.refresh()


    def move_edit_cursor_left(self):
        if self.mode == "edit_link":
            field_index = self.edit_input_index
            if self.edit_input_cursor_pos[field_index] > 0:
                self.edit_input_cursor_pos[field_index] -= 1
        elif self.mode == "edit_category":
            if self.edit_category_cursor_pos > 0:
                self.edit_category_cursor_pos -= 1

    def move_edit_cursor_right(self):
        if self.mode == "edit_link":
            field_index = self.edit_input_index
            if self.edit_input_cursor_pos[field_index] < len(self.edit_inputs[field_index]):
                self.edit_input_cursor_pos[field_index] += 1
        elif self.mode == "edit_category":
            if self.edit_category_cursor_pos < len(self.edit_category_input):
                self.edit_category_cursor_pos += 1

    def move_edit_cursor_home(self):
        if self.mode == "edit_link":
            field_index = self.edit_input_index
            self.edit_input_cursor_pos[field_index] = 0
        elif self.mode == "edit_category":
            self.edit_category_cursor_pos = 0

    def move_edit_cursor_end(self):
        if self.mode == "edit_link":
            field_index = self.edit_input_index
            self.edit_input_cursor_pos[field_index] = len(self.edit_inputs[field_index])
        elif self.mode == "edit_category":
            self.edit_category_cursor_pos = len(self.edit_category_input)

    def insert_char_at_cursor(self, char):
        if self.mode == "edit_link":
            field_index = self.edit_input_index
            cursor_pos = self.edit_input_cursor_pos[field_index]
            self.edit_inputs[field_index] = (
                self.edit_inputs[field_index][:cursor_pos] + 
                char + 
                self.edit_inputs[field_index][cursor_pos:]
            )
            self.edit_input_cursor_pos[field_index] += 1
        elif self.mode == "edit_category":
            cursor_pos = self.edit_category_cursor_pos
            self.edit_category_input = (
                self.edit_category_input[:cursor_pos] + 
                char + 
                self.edit_category_input[cursor_pos:]
            )
            self.edit_category_cursor_pos += 1

    def delete_char_at_cursor(self):
        if self.mode == "edit_link":
            field_index = self.edit_input_index
            cursor_pos = self.edit_input_cursor_pos[field_index]
            if cursor_pos > 0:
                self.edit_inputs[field_index] = (
                    self.edit_inputs[field_index][:cursor_pos-1] + 
                    self.edit_inputs[field_index][cursor_pos:]
                )
                self.edit_input_cursor_pos[field_index] -= 1
        elif self.mode == "edit_category":
            cursor_pos = self.edit_category_cursor_pos
            if cursor_pos > 0:
                self.edit_category_input = (
                    self.edit_category_input[:cursor_pos-1] + 
                    self.edit_category_input[cursor_pos:]
                )
                self.edit_category_cursor_pos -= 1
        
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
        elif key == ord('e') or key == ord('E'):
            self.handle_edit()
        elif key == ord('a') or key == ord('A'):
            self.mode = "adding"
            self.add_inputs = ["", ""]
            self.add_input_index = 0
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
            self.mode = "new_category"
            self.category_input = ""
            self.category_cursor_pos = 0
            self.show_status("📁 Enter new category name")
        elif key == ord('q') or key == ord('Q'):
            self.running = False
    
    def handle_adding_input(self, key):
        if key == curses.KEY_UP:
            self.add_input_index = max(0, self.add_input_index - 1)
        elif key == curses.KEY_DOWN:
            self.add_input_index = min(1, self.add_input_index + 1)
        elif key == 27:  
            self.mode = "browse"
            self.show_status("❌ Add cancelled")
        elif key == 22:  
            self.paste_from_clipboard()
        elif key == ord('\t'): 
            if not self.add_inputs[0].strip():
                self.show_status("❌ URL cannot be empty")
            else:
                node = self.resolve_path(self.path)
                links = node.setdefault(LINKS_KEY, [])
                links.append([self.add_inputs[0], self.add_inputs[1]])
                self.save_data()
                self.show_status(f"✅ Added: {self.add_inputs[0]}")
                self.mode = "browse"
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self.add_inputs[self.add_input_index]:
                self.add_inputs[self.add_input_index] = self.add_inputs[self.add_input_index][:-1]
        elif 32 <= key <= 126: 
            self.add_inputs[self.add_input_index] += chr(key)
            
            
    def handle_edit(self):
        items = self.get_current_items()
        if not items or self.current_selection >= len(items):
            self.show_status("❌ No item to edit")
            return
        
        item = items[self.current_selection]
        
        if item[0] == "category":
            self.mode = "edit_category"
            self.edit_category_input = item[1]
            self.edit_original_name = item[1]
            self.edit_category_cursor_pos = len(self.edit_category_input)
            self.show_status(f"✏️ Editing category: {item[1]}")
        else:
            self.mode = "edit_link"
            link_data = item[2]
            if isinstance(link_data, list) and len(link_data) == 2:
                self.edit_inputs[0] = link_data[0]
                self.edit_inputs[1] = link_data[1]
            else:
                self.edit_inputs[0] = link_data
                self.edit_inputs[1] = ""
            self.edit_input_index = 0
            self.show_status(f"✏️ Editing link: {item[1]}")
    
    def handle_new_category_input(self, key):
        if key == 27:
            self.mode = "browse"
            self.show_status("❌ Category creation cancelled")
        elif key == ord('\n') or key == curses.KEY_ENTER:
            validated_name, error = self.validate_category_name(self.category_input)
            if error:
                self.show_status(f"❌ {error}")
                return
            
            node = self.resolve_path(self.path)
            if validated_name in node:
                self.show_status("⚠️ Category already exists")
                return
            
            node[validated_name] = {}
            self.save_data()
            self.show_status(f"✅ Created category: '{validated_name}'")
            self.mode = "browse"
            
            items = self.get_current_items()
            for i, item in enumerate(items):
                if item[0] == "category" and item[1] == validated_name:
                    self.current_selection = i
                    break
        elif key == ord('p') or key == ord('P'):
            self.paste_from_clipboard()
        elif key == 22:  
            self.paste_from_clipboard()
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self.category_cursor_pos > 0:
                self.category_input = self.category_input[:self.category_cursor_pos-1] + self.category_input[self.category_cursor_pos:]
                self.category_cursor_pos -= 1
        elif key == curses.KEY_LEFT:
            self.category_cursor_pos = max(0, self.category_cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            self.category_cursor_pos = min(len(self.category_input), self.category_cursor_pos + 1)
        elif key == curses.KEY_HOME:
            self.category_cursor_pos = 0
        elif key == curses.KEY_END:
            self.category_cursor_pos = len(self.category_input)
        elif 32 <= key <= 126:
            if len(self.category_input) < 50:
                char = chr(key)
                if not re.search(r'[<>:"/\\|?*]', char):
                    self.category_input = self.category_input[:self.category_cursor_pos] + char + self.category_input[self.category_cursor_pos:]
                    self.category_cursor_pos += 1
                else:
                    self.show_status("❌ Invalid character (not allowed: < > : \" / \\ | ? *)")
            else:
                self.show_status("❌ Maximum length reached (50 characters)")
                
    def handle_edit_link_input(self, key):
        if key == curses.KEY_UP:
            self.edit_input_index = max(0, self.edit_input_index - 1)
        elif key == curses.KEY_DOWN:
            self.edit_input_index = min(1, self.edit_input_index + 1)
        elif key == 27:  
            self.mode = "browse"
            self.show_status("❌ Edit cancelled")
        elif key == 22:  
            self.paste_from_clipboard_edit()
        elif key == ord('\t'):
            if not self.edit_inputs[0].strip():
                self.show_status("❌ URL cannot be empty")
            else:
                node = self.resolve_path(self.path)
                links = node.get(LINKS_KEY, [])
                
                num_categories = len([k for k in node if k != LINKS_KEY])
                link_index = self.current_selection - num_categories
                
                if 0 <= link_index < len(links):
                    links[link_index] = [self.edit_inputs[0], self.edit_inputs[1]]
                    self.save_data()
                    self.show_status(f"✅ Updated link: {self.edit_inputs[0]}")
                    self.mode = "browse"
                else:
                    self.show_status("❌ Invalid link index")
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self.edit_inputs[self.edit_input_index]:
                self.edit_inputs[self.edit_input_index] = self.edit_inputs[self.edit_input_index][:-1]
        elif 32 <= key <= 126:
            self.edit_inputs[self.edit_input_index] += chr(key)

    def handle_edit_category_input(self, key):
        if key == 27:
            self.mode = "browse"
            self.show_status("❌ Edit cancelled")
        elif key == ord('\n') or key == curses.KEY_ENTER:

            validated_name, error = self.validate_category_name(self.edit_category_input)
            if error:
                self.show_status(f"❌ {error}")
                return
            
            if validated_name == self.edit_original_name:
                self.show_status("❌ No changes made")
                self.mode = "browse"
                return
            
            node = self.resolve_path(self.path)
            if validated_name in node:
                self.show_status("⚠️ Category name already exists")
                return
            
            if self.edit_original_name in node:
                node[validated_name] = node.pop(self.edit_original_name)
                self.save_data()
                self.show_status(f"✅ Renamed category: '{self.edit_original_name}' → '{validated_name}'")
                self.mode = "browse"
                
                items = self.get_current_items()
                for i, item in enumerate(items):
                    if item[0] == "category" and item[1] == validated_name:
                        self.current_selection = i
                        break
            else:
                self.show_status("❌ Original category not found")
        elif key == ord('p') or key == ord('P'):
            self.paste_from_clipboard_edit()
        elif key == 22:  
            self.paste_from_clipboard_edit()
        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
            if self.edit_category_cursor_pos > 0:
                self.edit_category_input = self.edit_category_input[:self.edit_category_cursor_pos-1] + self.edit_category_input[self.edit_category_cursor_pos:]
                self.edit_category_cursor_pos -= 1
        elif key == curses.KEY_LEFT:
            self.edit_category_cursor_pos = max(0, self.edit_category_cursor_pos - 1)
        elif key == curses.KEY_RIGHT:
            self.edit_category_cursor_pos = min(len(self.edit_category_input), self.edit_category_cursor_pos + 1)
        elif key == curses.KEY_HOME:
            self.edit_category_cursor_pos = 0
        elif key == curses.KEY_END:
            self.edit_category_cursor_pos = len(self.edit_category_input)
        elif 32 <= key <= 126:
            if len(self.edit_category_input) < 50:
                char = chr(key)
                if not re.search(r'[<>:"/\\|?*]', char):
                    self.edit_category_input = self.edit_category_input[:self.edit_category_cursor_pos] + char + self.edit_category_input[self.edit_category_cursor_pos:]
                    self.edit_category_cursor_pos += 1
                else:
                    self.show_status("❌ Invalid character (not allowed: < > : \" / \\ | ? *)")
            else:
                self.show_status("❌ Maximum length reached (50 characters)")

    def paste_from_clipboard_edit(self):
        try:
            paste_text = pyperclip.paste()
            if paste_text:
                paste_text = paste_text.strip().replace('\n', ' ').replace('\r', ' ')
                while '  ' in paste_text:
                    paste_text = paste_text.replace('  ', ' ')
                
                if self.mode == "edit_link":
                    if self.edit_input_index == 0 and (paste_text.startswith('http://') or paste_text.startswith('https://')):
                        self.edit_inputs[self.edit_input_index] = paste_text
                        self.show_status(f"📋 Pasted URL: {paste_text[:50]}{'...' if len(paste_text) > 50 else ''}")
                    else:
                        self.edit_inputs[self.edit_input_index] += paste_text
                        self.show_status(f"📋 Pasted: {paste_text[:30]}{'...' if len(paste_text) > 30 else ''}")
                elif self.mode == "edit_category":
                    cleaned_text = re.sub(r'[<>:"/\\|?*]', '', paste_text)
                    if len(self.edit_category_input + cleaned_text) <= 50:
                        self.edit_category_input += cleaned_text
                        self.edit_category_cursor_pos = len(self.edit_category_input)
                        self.show_status(f"📋 Pasted (cleaned): {cleaned_text[:30]}{'...' if len(cleaned_text) > 30 else ''}")
                    else:
                        self.show_status("❌ Paste would exceed character limit")
            else:
                self.show_status("📋 Clipboard is empty")
        except Exception as e:
            self.show_status(f"❌ Paste failed: {str(e)}")
    
    def handle_enter(self):
        items = self.get_current_items()
        if items and self.current_selection < len(items):
            item = items[self.current_selection]
            if item[0] == "category":

                self.path.append(item[1])
                self.current_selection = 0
                self.show_status(f"Entered category: {item[1]}")
            else:
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

        self.stdscr.clear()
        if item[0] == "category":
            confirm_text = f"Delete category '{item[1]}' and all its contents? (y/n)"
        else:
            confirm_text = f"Delete link '{item[1]}'? (y/n)"

        self.safe_addstr(self.height // 2, (self.width - len(confirm_text)) // 2, confirm_text, curses.color_pair(5) | curses.A_BOLD)
        self.stdscr.refresh()

        self.stdscr.timeout(-1)  
        key = self.stdscr.getch()
        self.stdscr.timeout(100)  
        
        if key == ord('y') or key == ord('Y'):
            node = self.resolve_path(self.path)
            if item[0] == "category":
                if item[1] in node:
                    del node[item[1]]
                    self.save_data()
                    self.show_status(f"🗑️ Deleted category '{item[1]}'")
                else:
                    self.show_status("❌ Category not found")
            else:
                links = node.get(LINKS_KEY, [])
                if not links:
                    self.show_status("❌ No links to delete")
                    return
                
                num_categories = len([k for k in node if k != LINKS_KEY])
                link_index = self.current_selection - num_categories
                
                if 0 <= link_index < len(links):
                    removed = links.pop(link_index)
                    self.save_data()
                    removed_url = removed[0] if isinstance(removed, list) else removed
                    self.show_status(f"🗑️ Removed: {removed_url}")
                else:
                    self.show_status("❌ Invalid link index")

            new_items = self.get_current_items()
            if self.current_selection >= len(new_items):
                self.current_selection = max(0, len(new_items) - 1)
        else:
            self.show_status("❌ Delete cancelled")
            
            
    def run(self):
        self.stdscr.timeout(100) 
        
        while self.running:
            self.draw_display()
          
            try:
                key = self.stdscr.getch()
                if key != -1:  
                    if self.mode == "browse":
                        self.handle_browse_input(key)
                    elif self.mode == "adding":
                        self.handle_adding_input(key)
                    elif self.mode == "new_category":
                        self.handle_new_category_input(key)
                    elif self.mode == "edit_link":
                        self.handle_edit_link_input(key)
                    elif self.mode == "edit_category":
                        self.handle_edit_category_input(key)
            except:
                pass
            
          
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