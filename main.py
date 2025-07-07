import json
import webbrowser
import os

JSON_FILE = "template.json"
LINKS_KEY = "_links"

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

def show_current_view(node):
    subcategories = [k for k in node if k != LINKS_KEY]
    links = node.get(LINKS_KEY, [])

    if subcategories:
        print("📂 Subcategories:")
        for i, sub in enumerate(subcategories, 1):
            print(f"  [{i}] {sub}")
    if links:
        print("🔗 Links:")
        for i, url in enumerate(links, len(subcategories) + 1):
            print(f"  [{i}] {url}")
    if not subcategories and not links:
        print("📭 Empty category")

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
                    for url in links:
                        webbrowser.open_new_tab(url)

            elif arg.startswith("range "):
                try:
                    range_str = arg[6:].strip()
                    start_str, end_str = range_str.split("-")
                    start = int(start_str) - 1 - offset
                    end = int(end_str) - offset
                    if start < 0 or end > len(links) or start >= end:
                        print("❌ Invalid range.")
                        continue
                    print(f"🌐 Opening links {start+1+offset} to {end+offset}...")
                    for url in links[start:end]:
                        webbrowser.open_new_tab(url)
                except:
                    print("❌ Usage: goto range <start>-<end>")

            else:
                try:
                    idx = int(arg) - 1 - offset
                    if idx < 0 or idx >= len(links):
                        print("❌ Invalid link number.")
                        continue
                    print(f"🌐 Opening: {links[idx]}")
                    webbrowser.open_new_tab(links[idx])
                except:
                    print("❌ Usage: goto <link_number>, goto all, or goto range x-y")



        elif cmd.startswith("add "):
            url = cmd[4:].strip()
            if url:
                node.setdefault(LINKS_KEY, []).append(url)
                save_data(data)
                print(f"✅ Added: {url}")
            else:
                print("❌ Usage: add <url>")

        elif cmd.startswith("edit "):
            parts = cmd.split(maxsplit=2)
            if len(parts) != 3:
                print("❌ Usage: edit <link_number> <new_url>")
                continue
            try:
                offset = len([k for k in node if k != LINKS_KEY])
                idx = int(parts[1]) - 1 - offset
                new_url = parts[2]
                if idx < 0 or idx >= len(node.get(LINKS_KEY, [])):
                    print("❌ Invalid link number.")
                    continue
                node[LINKS_KEY][idx] = new_url
                save_data(data)
                print(f"✏️ Updated link to: {new_url}")
            except:
                print("❌ Invalid input.")

        elif cmd.startswith("remove "):
            try:
                offset = len([k for k in node if k != LINKS_KEY])
                idx = int(cmd.split()[1]) - 1 - offset
                links = node.get(LINKS_KEY, [])
                if idx < 0 or idx >= len(links):
                    print("❌ Invalid link number.")
                    continue
                removed = links.pop(idx)
                save_data(data)
                print(f"🗑️ Removed: {removed}")
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


        else:
            print("❓ Unknown command. Try: list, open <x>, sub <name>, add <url>, goto <x>, edit <n> <url>, remove <n>, back, exit")

if __name__ == "__main__":
    data = load_data()
    main_loop(data)
