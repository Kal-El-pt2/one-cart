import json
import webbrowser
import os
import sys
from typing import Dict, List, Any, Tuple, Optional
import keyboard
import threading
import time

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.layout import Layout
    from rich.live import Live
    from rich.prompt import Prompt, Confirm
    from rich.align import Align
    from rich import box
except ImportError:
    print("Please install required dependencies:")
    print("pip install rich keyboard")
    sys.exit(1)

JSON_FILE = "products.json"
LINKS_KEY = "_links"

class ProductLinkManagerTUI:
    def __init__(self):
        self.console = Console()
        self.data = self.load_data()
        self.path = []
        self.current_selection = 0
        self.scroll_offset = 0
        self.status_message = ""
        self.running = True
        self.refresh_needed = True
        
    def load_data(self) -> Dict:
        if not os.path.exists(JSON_FILE):
            return {}
        with open(JSON_FILE) as f:
            return json.load(f)
    
    def save_data(self):
        with open(JSON_FILE, "w") as f:
            json.dump(self.data, f, indent=2)
    
    def resolve_path(self, path: List[str]) -> Dict:
        ref = self.data
        for key in path:
            ref = ref.get(key, {})
        return ref
    
    def get_current_items(self) -> Tuple[List[str], List]:
        node = self.resolve_path(self.path)
        subcategories = [k for k in node if k != LINKS_KEY]
        links = node.get(LINKS_KEY, [])
        return subcategories, links
    
    def create_header(self) -> Panel:
        path_str = "/" + "/".join(self.path) if self.path else "/root"
        header_text = Text()
        header_text.append("🛒 Product Link Manager", style="bold cyan")
        header_text.append("\n")
        header_text.append(f"📁 Current Path: {path_str}", style="blue")
        
        return Panel(
            header_text,
            box=box.ROUNDED,
            title="[bold green]Navigation[/bold green]",
            border_style="cyan"
        )
    
    def create_items_table(self) -> Table:
        subcategories, links = self.get_current_items()
        
        table = Table(
            title="📋 Items",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        
        table.add_column("", width=3, justify="center")
        table.add_column("Type", width=8)
        table.add_column("Name/URL", min_width=30)
        table.add_column("Description", min_width=20)
        
        all_items = []
        
        # Add subcategories
        for i, sub in enumerate(subcategories):
            all_items.append(("category", sub, "", i))
        
        # Add links
        for i, item in enumerate(links):
            if isinstance(item, list) and len(item) >= 2:
                url, desc = item[0], item[1]
            else:
                url, desc = (item, "") if isinstance(item, str) else (item[0], "")
            all_items.append(("link", url, desc, i))
        
        if not all_items:
            table.add_row("", "📭", "No items", "Empty category")
            return table
        
        # Calculate visible range
        max_visible = 15  # Show max 15 items at once
        start_idx = self.scroll_offset
        end_idx = min(len(all_items), start_idx + max_visible)
        
        for i in range(start_idx, end_idx):
            item_type, name, desc, original_idx = all_items[i]
            
            # Selection indicator
            indicator = "👉" if i == self.current_selection else "  "
            
            # Type and styling
            if item_type == "category":
                type_icon = "📂"
                name_style = "bold green"
                desc_style = "dim"
            else:
                type_icon = "🔗"
                name_style = "yellow"
                desc_style = "cyan"
            
            # Highlight selected row
            if i == self.current_selection:
                name_style = f"reverse {name_style}"
                desc_style = f"reverse {desc_style}"
            
            # Truncate long text
            if len(name) > 40:
                name = name[:37] + "..."
            if len(desc) > 30:
                desc = desc[:27] + "..."
            
            table.add_row(
                indicator,
                type_icon,
                Text(name, style=name_style),
                Text(desc, style=desc_style)
            )
        
        # Show scroll info if needed
        if len(all_items) > max_visible:
            scroll_info = f"Showing {start_idx + 1}-{end_idx} of {len(all_items)}"
            table.caption = scroll_info
        
        return table
    
    def create_help_panel(self) -> Panel:
        help_text = Text()
        help_text.append("🎮 Controls:\n", style="bold yellow")
        help_text.append("↑↓ Navigate   ", style="green")
        help_text.append("Enter Open    ", style="green")
        help_text.append("Space Goto    ", style="green")
        help_text.append("B Back\n", style="green")
        help_text.append("A Add URL     ", style="blue")
        help_text.append("C Category    ", style="blue")
        help_text.append("E Edit        ", style="blue")
        help_text.append("D Delete\n", style="blue")
        help_text.append("G Open All    ", style="magenta")
        help_text.append("R Refresh     ", style="magenta")
        help_text.append("Q Quit        ", style="red")
        
        return Panel(
            help_text,
            box=box.ROUNDED,
            title="[bold yellow]Help[/bold yellow]",
            border_style="yellow"
        )
    
    def create_status_panel(self) -> Panel:
        if self.status_message:
            status_text = Text(self.status_message, style="bold green")
        else:
            status_text = Text("Ready", style="dim")
        
        return Panel(
            status_text,
            box=box.ROUNDED,
            title="[bold blue]Status[/bold blue]",
            border_style="blue"
        )
    
    def create_layout(self) -> Layout:
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=8)
        )
        
        layout["body"].split_row(
            Layout(name="main", ratio=2),
            Layout(name="sidebar", size=30)
        )
        
        layout["footer"].split_row(
            Layout(name="help", ratio=1),
            Layout(name="status", size=20)
        )
        
        # Fill the layout
        layout["header"].update(self.create_header())
        layout["main"].update(self.create_items_table())
        layout["sidebar"].update(Panel("", title="Info", border_style="dim"))
        layout["help"].update(self.create_help_panel())
        layout["status"].update(self.create_status_panel())
        
        return layout
    
    def handle_navigation(self, key):
        subcategories, links = self.get_current_items()
        total_items = len(subcategories) + len(links)
        
        if total_items == 0:
            return
        
        if key == "up":
            self.current_selection = max(0, self.current_selection - 1)
        elif key == "down":
            self.current_selection = min(total_items - 1, self.current_selection + 1)
        
        # Update scroll offset
        max_visible = 15
        if self.current_selection < self.scroll_offset:
            self.scroll_offset = self.current_selection
        elif self.current_selection >= self.scroll_offset + max_visible:
            self.scroll_offset = self.current_selection - max_visible + 1
        
        self.refresh_needed = True
    
    def enter_selected(self):
        subcategories, links = self.get_current_items()
        total_items = len(subcategories) + len(links)
        
        if total_items == 0:
            self.status_message = "No items to select"
            return
        
        if self.current_selection < len(subcategories):
            # Enter subcategory
            selected_category = subcategories[self.current_selection]
            self.path.append(selected_category)
            self.current_selection = 0
            self.scroll_offset = 0
            self.status_message = f"Entered category: {selected_category}"
        else:
            # Open link
            self.goto_selected()
        
        self.refresh_needed = True
    
    def goto_selected(self):
        subcategories, links = self.get_current_items()
        
        if self.current_selection >= len(subcategories):
            link_index = self.current_selection - len(subcategories)
            if link_index < len(links):
                item = links[link_index]
                url = item[0] if isinstance(item, list) else item
                try:
                    webbrowser.open_new_tab(url)
                    self.status_message = f"Opened: {url}"
                except Exception as e:
                    self.status_message = f"Error opening URL: {str(e)}"
                self.refresh_needed = True
    
    def goto_all(self):
        _, links = self.get_current_items()
        if not links:
            self.status_message = "No links to open"
            self.refresh_needed = True
            return
        
        try:
            for item in links:
                url = item[0] if isinstance(item, list) else item
                webbrowser.open_new_tab(url)
            self.status_message = f"Opened {len(links)} links"
        except Exception as e:
            self.status_message = f"Error opening links: {str(e)}"
        self.refresh_needed = True
    
    def add_url(self):
        try:
            url = Prompt.ask("\n🔗 Enter URL")
            if not url.strip():
                self.status_message = "URL cannot be empty"
                return
            
            desc = Prompt.ask("📝 Enter description (optional)", default="")
            
            node = self.resolve_path(self.path)
            links = node.setdefault(LINKS_KEY, [])
            links.append([url, desc])
            self.save_data()
            
            self.status_message = f"Added: {url}"
            self.refresh_needed = True
        except (KeyboardInterrupt, EOFError):
            self.status_message = "Cancelled"
            self.refresh_needed = True
    
    def add_category(self):
        try:
            name = Prompt.ask("\n📂 Enter category name")
            if not name.strip():
                self.status_message = "Category name cannot be empty"
                return
            
            node = self.resolve_path(self.path)
            
            if name in node:
                self.status_message = "Category already exists"
                return
            
            node[name] = {}
            self.save_data()
            
            self.status_message = f"Created category: {name}"
            self.refresh_needed = True
        except (KeyboardInterrupt, EOFError):
            self.status_message = "Cancelled"
            self.refresh_needed = True
    
    def edit_selected(self):
        subcategories, links = self.get_current_items()
        
        if self.current_selection >= len(subcategories):
            link_index = self.current_selection - len(subcategories)
            if link_index < len(links):
                item = links[link_index]
                current_url = item[0] if isinstance(item, list) else item
                current_desc = item[1] if isinstance(item, list) and len(item) > 1 else ""
                
                try:
                    new_url = Prompt.ask(f"\n🔗 Edit URL", default=current_url)
                    new_desc = Prompt.ask("📝 Edit description", default=current_desc)
                    
                    node = self.resolve_path(self.path)
                    links = node.get(LINKS_KEY, [])
                    links[link_index] = [new_url, new_desc]
                    self.save_data()
                    
                    self.status_message = f"Updated: {new_url}"
                    self.refresh_needed = True
                except (KeyboardInterrupt, EOFError):
                    self.status_message = "Cancelled"
                    self.refresh_needed = True
        else:
            self.status_message = "Cannot edit categories"
            self.refresh_needed = True
    
    def delete_selected(self):
        subcategories, links = self.get_current_items()
        
        if self.current_selection < len(subcategories):
            # Delete category
            category_name = subcategories[self.current_selection]
            try:
                if Confirm.ask(f"\n⚠️ Delete category '{category_name}' and all contents?"):
                    node = self.resolve_path(self.path)
                    del node[category_name]
                    self.save_data()
                    self.status_message = f"Deleted category: {category_name}"
                    
                    # Adjust selection
                    subcategories, _ = self.get_current_items()
                    if self.current_selection >= len(subcategories):
                        self.current_selection = max(0, len(subcategories) - 1)
                else:
                    self.status_message = "Cancelled"
            except (KeyboardInterrupt, EOFError):
                self.status_message = "Cancelled"
        else:
            # Delete link
            link_index = self.current_selection - len(subcategories)
            if link_index < len(links):
                item = links[link_index]
                url = item[0] if isinstance(item, list) else item
                try:
                    if Confirm.ask(f"\n⚠️ Delete link '{url}'?"):
                        node = self.resolve_path(self.path)
                        links = node.get(LINKS_KEY, [])
                        links.pop(link_index)
                        self.save_data()
                        self.status_message = f"Deleted: {url}"
                        
                        # Adjust selection
                        subcategories, updated_links = self.get_current_items()
                        total_items = len(subcategories) + len(updated_links)
                        if self.current_selection >= total_items:
                            self.current_selection = max(0, total_items - 1)
                    else:
                        self.status_message = "Cancelled"
                except (KeyboardInterrupt, EOFError):
                    self.status_message = "Cancelled"
        
        self.refresh_needed = True
    
    def go_back(self):
        if self.path:
            self.path.pop()
            self.current_selection = 0
            self.scroll_offset = 0
            self.status_message = "Moved back"
        else:
            self.status_message = "Already at root"
        self.refresh_needed = True
    
    def setup_keyboard_handler(self):
        def on_key_event(e):
            if not self.running:
                return
            
            if e.event_type == keyboard.KEY_DOWN:
                if e.name == 'up':
                    self.handle_navigation('up')
                elif e.name == 'down':
                    self.handle_navigation('down')
                elif e.name == 'enter':
                    self.enter_selected()
                elif e.name == 'space':
                    self.goto_selected()
                elif e.name == 'b':
                    self.go_back()
                elif e.name == 'a':
                    self.add_url()
                elif e.name == 'c':
                    self.add_category()
                elif e.name == 'e':
                    self.edit_selected()
                elif e.name == 'd':
                    self.delete_selected()
                elif e.name == 'g':
                    self.goto_all()
                elif e.name == 'r':
                    self.refresh_needed = True
                elif e.name == 'q':
                    self.running = False
                elif e.name == 'esc':
                    self.running = False
        
        keyboard.hook(on_key_event)
    
    def run(self):
        self.console.clear()
        self.console.print("[bold green]🛒 Product Link Manager TUI[/bold green]")
        self.console.print("[yellow]Loading...[/yellow]")
        
        self.setup_keyboard_handler()
        
        try:
            with Live(self.create_layout(), refresh_per_second=4, screen=True) as live:
                while self.running:
                    if self.refresh_needed:
                        live.update(self.create_layout())
                        self.refresh_needed = False
                    
                    time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            keyboard.unhook_all()
            self.console.clear()
            self.console.print("[bold green]👋 Thanks for using Product Link Manager![/bold green]")

def main():
    try:
        app = ProductLinkManagerTUI()
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have installed the required dependencies:")
        print("pip install rich keyboard")

if __name__ == "__main__":
    main()