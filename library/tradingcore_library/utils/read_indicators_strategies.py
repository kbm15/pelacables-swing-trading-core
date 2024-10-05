import os
import importlib
import sys
from typing import Dict

def get_indicators_strategies(folder_path: str) -> Dict[str, list]:
    indicators = {}
    cwd = os.getcwd()
    indicators_folder = os.path.join(cwd, folder_path)

    # Add indicators folder to sys.path to enable relative imports
    sys.path.append(cwd)

    # Iterate over files in the indicators folder
    for filename in os.listdir(indicators_folder):
        if filename.endswith('.py') and filename != '__init__.py':  # Consider only Python files, exclude __init__.py
            module_name = filename[:-3]  # Remove .py extension
            try:
                # Import the module dynamically
                module = importlib.import_module(f"{folder_path}.{module_name}")

                # Dictionary to store strategies for the current module
                module_strategies = {}

                # Iterate through all attributes in the module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # Check if attr is a class and not a built-in type
                    if isinstance(attr, type):
                        # Check if the class has POSSIBLE_STRATEGIES attribute
                        if hasattr(attr, 'POSSIBLE_STRATEGIES'):
                            # Exclude None strategy if present
                            strategies = [s for s in attr.POSSIBLE_STRATEGIES if s is not None]
                            # Store strategies in the dictionary
                            module_strategies[attr_name] = strategies

                # Add module strategies to indicators dictionary
                if module_strategies:
                    indicators[module_name] = module_strategies

            except ImportError as e:
                print(f"Failed to import module {module_name}: {str(e)}")

    return indicators

# Example usage:
if __name__ == "__main__":
    indicators_folder_path = 'indicators'  # Relative path to the indicators folder
    indicators_strategies = get_indicators_strategies(indicators_folder_path)
    print("Indicators and their strategies:")
    print("{")
    for indicator, class_strategies in indicators_strategies.items():
        for class_name, strategies in class_strategies.items():
            print(f"  \"{class_name}\": {strategies},")

    print("}")