import json
import webbrowser
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich.console import Group
import pyperclip
import keyboard
import threading
import time

# Platform-specific imports
if os.name == 'posix':
    import termios
    import tty
elif os.name == 'nt':
    import msvcrt

JSON_FILE = "products.json"
LINKS_KEY = "_links"

class ProductLinkManagerTUI:
    def __init__(self):
        self.console = Console()
        self.data = self.load_data()
        self.path = []
        self.current_selection = 0
        self.scroll_offset = 0
        self.running = True
        self.status_message = ""
        self.status_time = 0
        self.mode = "browse"
        self.add_inputs = ["", ""]
        self.add_input_index = 0
        self.old_terminal_settings = None
        
    def setup_terminal(self):
        """Setup terminal to prevent echo and enable raw input"""
        if os.name == 'posix':  # Unix/Linux/Mac
            try:
                self.old_terminal_settings = termios.tcgetattr(sys.stdin)
                tty.setraw(sys.stdin.fileno())
            except:
                pass
        elif os.name == 'nt':  # Windows
            # On Windows, we'll rely on keyboard suppress parameter
            pass
        
    def restore_terminal(self):
        """Restore terminal settings"""
        if os.name == 'posix' and self.old_terminal_settings:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_terminal_settings)
            except:
                pass
        elif os.name == 'nt':  # Windows
            # Clear any pending input
            try:
                while msvcrt.kbhit():
                    msvcrt.getch()
            except:
                pass
    
    def load_data(self):
        if not os.path.exists(JSON_FILE):
            return {}
        with open(JSON_FILE) as f:
            return json.load(f)
    
    def save_data(self):
        with open(JSON_FILE, "w") as f:
            json.dump(self.data, f, indent=2)
    
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
    
    def create_display(self):
        # Header
        header_content = Group(
            Align.center(Text("🛒 Product Link Manager (TUI)", style="bold cyan")),
            Text(f"📂 {'/'.join(self.path) if self.path else 'root'}", style="blue")
        )
        header = Panel(
            header_content,
            title="Product Manager",
            border_style="cyan"
        )

        # Items table
        items = self.get_current_items()

        if not items:
            content_text = Text("📭 No items in this category", style="dim")
            content = Panel(
                Align.center(content_text),
                title="Items (0 total)",
                border_style="white"
            )
        else:
            items_display = []
            visible_height = 15
            start_index = max(0, self.current_selection - visible_height // 2)
            end_index = min(len(items), start_index + visible_height)

            for i in range(start_index, end_index):
                item = items[i]
                if item[0] == "category":
                    prefix = "📁"
                    text = item[1]
                    style = "green"
                else:
                    prefix = "🔗"
                    text = item[1]
                    style = "yellow"

                if len(text) > 60:
                    text = text[:57] + "..."

                if i == self.current_selection and self.mode == "browse":
                    display_text = Text(f"► {prefix} {text}", style="bold white on blue")
                else:
                    display_text = Text(f"  {prefix} {text}", style=style)

                items_display.append(display_text)

            content = Panel(
                Group(*items_display),
                title=f"Items ({len(items)} total)",
                border_style="white"
            )

        # Prepare main display parts
        display_parts = [header, content]

        # If in adding mode, render input fields
        if self.mode == "adding":
            input_panels = []
            labels = ["URL", "Description"]
            for i, val in enumerate(self.add_inputs):
                is_active = i == self.add_input_index
                style = "bold white on blue" if is_active else "white"
                # Show cursor for active field
                display_val = val + "█" if is_active else val
                panel = Panel(
                    Text(f"{labels[i]}: {display_val}", style=style),
                    border_style="cyan"
                )
                input_panels.append(panel)

            add_instructions = Text("↑↓ to switch | Tab to confirm | ESC to cancel | Ctrl+V to paste", style="cyan")
            input_panels.append(Panel(Align.center(add_instructions), border_style="cyan"))

            display_parts.extend(input_panels)

        # Footer with controls
        controls_text = Text()
        controls_text.append("↑↓: Navigate  ", style="cyan")
        controls_text.append("Enter: Select  ", style="cyan")
        controls_text.append("B: Back  ", style="cyan")
        controls_text.append("A: Add  ", style="cyan")
        controls_text.append("D: Delete  ", style="cyan")
        controls_text.append("N: New Category  ", style="cyan")
        controls_text.append("Q: Quit", style="cyan")

        footer = Panel(
            Align.center(controls_text),
            title="Controls",
            border_style="cyan"
        )

        # Status message if active
        if self.status_message and time.time() - self.status_time < 3:
            status = Panel(
                Align.center(Text(self.status_message, style="bold green")),
                border_style="green"
            )
            display_parts.append(status)

        # Add footer
        display_parts.append(footer)

        return Group(*display_parts)

    
    def show_status(self, message):
        self.status_message = message
        self.status_time = time.time()
    
    def handle_input(self):
        while self.running:
            try:
                # Use keyboard.read_event with suppress to prevent terminal echo
                event = keyboard.read_event(suppress=True)
                if event.event_type == keyboard.KEY_DOWN:
                    if self.mode == "browse":
                        self.handle_browse_input(event)
                    elif self.mode == "adding":
                        self.handle_adding_input(event)
            except Exception:
                continue
            
    
    def handle_browse_input(self, event):
        if event.name == 'up':
            self.current_selection = max(0, self.current_selection - 1)
        elif event.name == 'down':
            items = self.get_current_items()
            if items:
                self.current_selection = min(len(items) - 1, self.current_selection + 1)
        elif event.name == 'enter':
            self.handle_enter()
        elif event.name == 'b':
            self.handle_back()
        elif event.name == 'a':
            self.mode = "adding"
            self.add_inputs = ["", ""]
            self.add_input_index = 0
        elif event.name == 'd':
            self.handle_delete()
        elif event.name == 'n':
            self.handle_new_category()
        elif event.name == 'q':
            self.running = False

    def handle_adding_input(self, event):
        if event.name == 'up':
            self.add_input_index = max(0, self.add_input_index - 1)
        elif event.name == 'down':
            self.add_input_index = min(1, self.add_input_index + 1)
        elif event.name == 'esc':
            self.mode = "browse"
            self.show_status("❌ Add cancelled")
        elif event.name == 'v' and keyboard.is_pressed('ctrl'):
            try:
                paste_text = pyperclip.paste()
                self.add_inputs[self.add_input_index] += paste_text
            except:
                self.show_status("❌ Paste failed")
        elif event.name == 'tab':
            # On Tab, if URL is empty, do nothing
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
        else:
            # Handle text input
            if len(event.name) == 1 and event.name.isprintable():
                self.add_inputs[self.add_input_index] += event.name
            elif event.name == 'space':
                self.add_inputs[self.add_input_index] += ' '
            elif event.name == 'backspace':
                self.add_inputs[self.add_input_index] = self.add_inputs[self.add_input_index][:-1]
            elif event.name in [':', '.', '/', '-', '_', '=', '?', '&', '%']:
                self.add_inputs[self.add_input_index] += event.name
                
        
    
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
                webbrowser.open_new_tab(url)
                self.show_status(f"🌐 Opened: {url}")
    
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
        
        # Temporarily restore terminal for input
        if os.name == 'posix':
            self.restore_terminal()
        
        # Pause the display
        self.running = False
        time.sleep(0.1)
        
        self.console.clear()
        
        try:
            if item[0] == "category":
                if Confirm.ask(f"Delete category '{item[1]}' and all its contents?"):
                    node = self.resolve_path(self.path)
                    del node[item[1]]
                    self.save_data()
                    self.show_status(f"🗑️ Deleted category '{item[1]}'")
                    # Adjust selection
                    new_items = self.get_current_items()
                    if self.current_selection >= len(new_items):
                        self.current_selection = max(0, len(new_items) - 1)
                else:
                    self.show_status("❌ Cancelled")
            else:
                if Confirm.ask(f"Delete link '{item[1]}'?"):
                    node = self.resolve_path(self.path)
                    links = node.get(LINKS_KEY, [])
                    # Find the link index
                    link_index = self.current_selection - len([k for k in node if k != LINKS_KEY])
                    if 0 <= link_index < len(links):
                        links.pop(link_index)
                        self.save_data()
                        self.show_status(f"🗑️ Deleted link")
                        # Adjust selection
                        new_items = self.get_current_items()
                        if self.current_selection >= len(new_items):
                            self.current_selection = max(0, len(new_items) - 1)
                else:
                    self.show_status("❌ Cancelled")
        except KeyboardInterrupt:
            self.show_status("❌ Cancelled")
        finally:
            if os.name == 'posix':
                self.setup_terminal()
            self.running = True
            self.start_display()
    
    def handle_new_category(self):
        # Temporarily restore terminal for input
        if os.name == 'posix':
            self.restore_terminal()
        
        # Pause the display
        self.running = False
        time.sleep(0.1)
        
        self.console.clear()
        self.console.print("📁 Creating new category...\n")
        
        try:
            name = Prompt.ask("Enter category name")
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
        except KeyboardInterrupt:
            self.show_status("❌ Cancelled")
        finally:
            if os.name == 'posix':
                self.setup_terminal()
            self.running = True
            self.start_display()
    
    def start_display(self):
        # Start input handler in a separate thread
        input_thread = threading.Thread(target=self.handle_input, daemon=True)
        input_thread.start()
        
        with Live(self.create_display(), refresh_per_second=4, console=self.console) as live:
            try:
                while self.running:
                    live.update(self.create_display())
                    time.sleep(0.1)
            except KeyboardInterrupt:
                self.running = False
    
    def run(self):
        self.console.print("[bold green]🛒 Product Link Manager Starting...[/bold green]")
        self.console.print("[yellow]Press Q to quit, use arrow keys to navigate[/yellow]\n")
        time.sleep(1)
        
        # Setup terminal to prevent echo
        self.setup_terminal()
        
        try:
            self.start_display()
        finally:
            # Always restore terminal settings
            self.restore_terminal()
        
        self.console.print("\n[bold green]👋 Goodbye![/bold green]")

def main():
    try:
        app = ProductLinkManagerTUI()
        app.run()
    except Exception as e:
        console = Console()
        console.print(f"[bold red]❌ Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()