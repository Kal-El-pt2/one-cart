## OneCart
**OneCart** is a command-line tool that allows you to organize and manage product links with **infinite nesting** capabilities. You can categorize your links, add descriptions, and open them directly from the terminal.

---

## ✨ Features

- **📁 Infinite Nesting:** Organize links in deeply nested categories and subcategories.
- **🔗 Link Management:** Add, edit, and remove links with descriptions.
- **🚀 Bulk Opening:** Open all links or a specific range in browser tabs.
- **🧱 Category Management:** Create, rename, and delete categories or subcategories.
- **💾 Persistent Storage:** All data is stored in `template.json` for future use.

## Getting Started
Prerequisites
Python 3.x

### Installation
1.Save the provided Python code as a .py file (e.g., link_manager.py).

2. Ensure the following modules are available (all standard in Python):
   - `webbrowser`
   - `json`
   - `os`

# Usage
Open your terminal or command prompt.

Navigate to the directory where you saved link_manager.py.

Run the application using:

```bash
python main.py
```

# Commands
Here's a list of available commands:

📁 Category Navigation
`list`

Lists all subcategories and links in the current view.

`open <x>`

Opens subcategory number x. Use the number displayed next to the subcategory when you run list.

Example: open 1

`back`

Goes back to the parent category.

`new <name>`

Creates a new top-level category.

Example: new Electronics

`sub <name>`

Creates a new subcategory within the current category.

Example: sub Smartphones

`rename <x> <new_name>`

Renames category or subcategory number x to <new_name>.

Example: rename 1 Computers

`delcat <x>`

Deletes category or subcategory number x and all its contents. Use with caution!

Example: delcat 2

🔗 Link Management
`add <url> <description>`

Adds a new link with an optional description.

Example: add https://example.com "Great Product"

`edit <x> <new_url> <new_description>`

Edits an existing link at position x with a new URL and optional new description.

Example: edit 3 https://newsite.com "Updated Product"

`remove <x>`

Removes link number x.

Example: remove 1

`goto <x>`

Opens link number x in your default web browser.

Example: goto 1

`goto all`

Opens all links in the current category in new browser tabs.

`goto range x-y`

Opens links from x to y (inclusive) in new browser tabs.

Example: goto range 1-3

❓ Other
`exit` or `quit`

Exits the application.

# Data Storage
The application stores all your categories and links in a file named template.json in the same directory as the script. Do not modify this file manually unless you know what you're doing, as it could corrupt your data.

# Contributing
Feel free to fork this project and submit pull requests with any improvements or bug fixes.