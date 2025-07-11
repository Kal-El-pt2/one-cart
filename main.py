import json
import webbrowser
import os

JSON_FILE = "products.json"
LINKS_KEY = "_links"

def show_current_view(node):
    subcategories = [k for k in node if k != LINKS_KEY]
    links = node.get(LINKS_KEY, [])

    if subcategories:
        print("📂 Subcategories:")
        for i, sub in enumerate(subcategories, 1):
            print(f"  [{i}] {sub}")

    if links:
        print("🔗 Links:")
        for i, item in enumerate(links, len(subcategories) + 1):
            if isinstance(item, list) and len(item) == 2:
                url, desc = item
            else:
                url, desc = item, ""

            display_text = desc if desc.strip() else url
            print(f"  [{i}] {display_text}")

    if not subcategories and not links:
        print("📭 Empty category")



def load_data():
    if not os.path.exists(JSON_FILE):
        return {}
    with open(JSON_FILE) as f:
        return json.load(f)

def save_data(data):
    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=2)

def resolve_path(data, path):
    ref = data
    for key in path:
        ref = ref.get(key, {})
    return ref


def main_loop(data):
    path = []
    print("🛒 Product Link Manager (infinite nesting enabled)")
    print("Commands: list, open <x>, goto <x>, add <url>, edit <n> <url>, remove <n>, sub <name>, back, exit\n")

    while True:
        try:
            node = resolve_path(data, path)
            prompt = f"{'/'.join(path) or 'root'}> "
            cmd = input(prompt).strip()
        except KeyboardInterrupt:
            print("\n👋 Exiting.")
            break

        if cmd in {"exit", "quit"}:
            print("👋 Goodbye!")
            break

        if cmd == "list":
            show_current_view(node)

        elif cmd == "back":
            if path:
                path.pop()
            else:
                print("❌ Already at the root level.")

        elif cmd.startswith("open "):
            try:
                idx = int(cmd.split()[1]) - 1
                subcats = [k for k in node if k != LINKS_KEY]
                if idx < 0 or idx >= len(subcats):
                    print("❌ Invalid subcategory number.")
                    continue
                path.append(subcats[idx])
            except:
                print("❌ Usage: open <subcategory_number>")

        elif cmd.startswith("goto "):
            arg = cmd[5:].strip()
            links = node.get(LINKS_KEY, [])
            offset = len([k for k in node if k != LINKS_KEY])

            if arg == "all":
                if not links:
                    print("📭 No links to open.")
                else:
                    print(f"🌐 Opening all {len(links)} links...")
                    for item in links:
                        url = item[0] if isinstance(item, list) else item
                        webbrowser.open_new_tab(url)

            elif arg.startswith("range "):
                try:
                    range_str = arg[6:].strip()
                    start_str, end_str = range_str.split("-")
                    start = int(start_str) - 1 - offset
                    end = int(end_str) - offset
                    if start < 0 or end > len(links) or start >= end:
                        print("❌ Invalid range.")
                        return
                    print(f"🌐 Opening links {start+1+offset} to {end+offset}...")
                    for item in links[start:end]:
                        url = item[0] if isinstance(item, list) else item
                        webbrowser.open_new_tab(url)
                except:
                    print("❌ Usage: goto range <start>-<end>")

            else:
                try:
                    idx = int(arg) - 1 - offset
                    if idx < 0 or idx >= len(links):
                        print("❌ Invalid link number.")
                        return
                    item = links[idx]
                    url = item[0] if isinstance(item, list) else item
                    print(f"🌐 Opening: {url}")
                    webbrowser.open_new_tab(url)
                except:
                    print("❌ Usage: goto <link_number>, goto all, or goto range x-y")


        elif cmd.startswith("add "):
            try:
                parts = cmd[4:].strip().split(maxsplit=1)
                url = parts[0]
                desc = parts[1] if len(parts) > 1 else ""
                links = node.setdefault(LINKS_KEY, [])
                links.append([url, desc])
                save_data(data)
                print(f"✅ Added: {url}  →  \"{desc}\"")
            except:
                print("❌ Usage: add <url> <optional description>")


        elif cmd.startswith("edit "):
            parts = cmd.split(maxsplit=3)
            if len(parts) < 3:
                print("❌ Usage: edit <link_number> <new_url> <new_desc>")
                continue
            try:
                idx = int(parts[1]) - 1 - len([k for k in node if k != LINKS_KEY])
                new_url = parts[2]
                new_desc = parts[3] if len(parts) > 3 else ""
                links = node.get(LINKS_KEY, [])
                if idx < 0 or idx >= len(links):
                    print("❌ Invalid link number.")
                    continue
                old = links[idx]
                links[idx] = [new_url, new_desc]
                save_data(data)
                print(f"✏️ Replaced [{idx+1}] {old[0]} → {new_url}  \"{new_desc}\"")
            except:
                print("❌ Usage: edit <link_number> <new_url> <new_desc>")


        elif cmd.startswith("remove "):
            try:
                idx = int(cmd.split()[1]) - 1 - len([k for k in node if k != LINKS_KEY])
                links = node.get(LINKS_KEY, [])
                if idx < 0 or idx >= len(links):
                    print("❌ Invalid link number.")
                    continue
                removed = links.pop(idx)
                save_data(data)
                print(f"🗑️ Removed: {removed[0]}")
            except:
                print("❌ Usage: remove <link_number>")


        elif cmd.startswith("sub "):
            name = cmd[4:].strip()
            if not name:
                print("❌ Usage: sub <subcategory_name>")
                continue
            if name in node:
                print("⚠️ Subcategory already exists.")
            else:
                node[name] = {}
                save_data(data)
                print(f"✅ Created subcategory: '{name}'")

        elif cmd.startswith("new "):
            if path:
                print("❌ Use 'sub <name>' inside categories.")
                continue
            name = cmd[4:].strip()
            if not name:
                print("❌ Usage: new <category_name>")
                continue
            if name in data:
                print("⚠️ Category already exists.")
                continue
            data[name] = {}
            save_data(data)
            print(f"✅ Created new top-level category: '{name}'")
            
        
        elif cmd.startswith("delcat "):
            try:
                idx = int(cmd.split()[1]) - 1
                subcats = [k for k in node if k != LINKS_KEY]
                if idx < 0 or idx >= len(subcats):
                    print("❌ Invalid category number.")
                    continue
                target = subcats[idx]
                confirm = input(f"⚠️ Are you sure you want to delete '{target}' and all its contents? (y/N): ").strip().lower()
                if confirm == "y":
                    del node[target]
                    save_data(data)
                    print(f"🗑️ Deleted category '{target}'")
                else:
                    print("❌ Cancelled.")
            except:
                print("❌ Usage: delcat <category_number>")
                
        elif cmd.startswith("rename "):
            parts = cmd.split(maxsplit=2)
            if len(parts) != 3:
                print("❌ Usage: rename <category_number> <new_name>")
                continue
            try:
                idx = int(parts[1]) - 1
                new_name = parts[2].strip()
                subcats = [k for k in node if k != LINKS_KEY]
                if idx < 0 or idx >= len(subcats):
                    print("❌ Invalid category number.")
                    continue
                old_name = subcats[idx]
                if new_name in node:
                    print("⚠️ A category with that name already exists.")
                    continue
                node[new_name] = node.pop(old_name)
                save_data(data)
                print(f"✏️ Renamed '{old_name}' → '{new_name}'")
            
            except:
                print("❌ Invalid input. Usage: rename <category_number> <new_name>")


        else:
            print("❓ Unknown command. Try: list, open <x>, sub <name>, add <url>, goto <x>, edit <n> <url>, remove <n>, back, exit")

if __name__ == "__main__":
    data = load_data()
    print("🛒 Product Link Manager Ready!")
    print("""
    📘 Available Commands:

    📁 Category Navigation:
    list                   → List all categories or contents of current category
    open <x>               → Open category number x
    back                   → Go back to parent category
    new <name>             → Create a new category or subcategory
    rename <x> <new_name>  → Rename category or subcategory
    delete <x>             → Delete category or subcategory

    🔗 Link Management:
    add <url> <desc>       → Add a new link with optional description
    edit <x> <url> <desc>  → Edit an existing link (url and description)
    remove <x>             → Remove link number x
    goto <x>               → Open link number x
    goto all               → Open all links in current category
    goto range x-y         → Open link numbers x to y (inclusive)

    ❓ Other:
    exit / quit            → Exit the application
    """)

    main_loop(data)

    