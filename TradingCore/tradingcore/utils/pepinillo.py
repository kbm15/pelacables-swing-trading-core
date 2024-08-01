import pickle
import sys
import argparse
from typing import Any

def create_pickle(filename: str, content: Any):
    """Create a pickle file with the given content."""
    with open(filename, 'wb') as file:
        pickle.dump(content, file)
    print(f"Data successfully pickled to {filename}")

def read_pickle(filename: str) -> Any:
    """Read and return the content of a pickle file."""
    with open(filename, 'rb') as file:
        content = pickle.load(file)
    print(f"Data successfully read from {filename}")
    return content

def update_pickle(filename: str, content: Any):
    """Update the content of a pickle file."""
    with open(filename, 'wb') as file:
        pickle.dump(content, file)
    print(f"Data successfully updated in {filename}")

def delete_pickle(filename: str):
    """Delete a pickle file."""
    try:
        os.remove(filename)
        print(f"Pickle file {filename} successfully deleted")
    except FileNotFoundError:
        print(f"Pickle file {filename} not found")

def main():
    parser = argparse.ArgumentParser(description="Handle CRUD operations for pickling and unpickling Python objects")
    parser.add_argument('operation', choices=['create', 'read', 'update', 'delete'], help="The CRUD operation to perform")
    parser.add_argument('filename', help="The filename with path for the pickle file")
    parser.add_argument('--content', nargs='+', help="The content to store in the pickle file (only for create and update operations)")

    args = parser.parse_args()

    if args.operation in ['create', 'update'] and args.content is None:
        print("Error: Content is required for create and update operations.")
        sys.exit(1)

    if args.operation == 'create':
        create_pickle(args.filename, args.content)
    elif args.operation == 'read':
        content = read_pickle(args.filename)
        print("Content of the pickle file:", content)
    elif args.operation == 'update':
        update_pickle(args.filename, args.content)
    elif args.operation == 'delete':
        delete_pickle(args.filename)

if __name__ == "__main__":
    main()
