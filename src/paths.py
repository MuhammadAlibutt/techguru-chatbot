import os 



ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# to src folder 
SRC_DIR = os.path.join(ROOT_DIR , 'src')

# to src/conn filer 
CONN_DIR = os.path.join(SRC_DIR, 'conn') 

# src/services/
SERVICE_DIR = os.path.join(SRC_DIR , 'services')


# individual files paths
CONFIG_PATH = os.path.join(CONN_DIR  , 'config.py')
INSTRUCTION_PATH = os.path.join(CONN_DIR, 'agent_instruction.txt')

def print_all_paths():
    print(f"ROOT_DIR         : {ROOT_DIR}")
    print(f"SRC_DIR          : {SRC_DIR}")
    print(f"CONN_DIR         : {CONN_DIR}")
    print(f"CONFIG_PATH      : {CONFIG_PATH}")
    print(f"INSTRUCTION_PATH : {INSTRUCTION_PATH}")
    print(f"Config exists    : {os.path.exists(CONFIG_PATH)}")
    print(f"Instruction exists: {os.path.exists(INSTRUCTION_PATH)}")