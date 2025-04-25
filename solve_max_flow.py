from pyomo.environ import *
from pyomo.opt import SolverFactory

import networkx as nx
import re
import yaml
import subprocess

import os

from dat_generator import write_problem

import pandas as pd

import networkx as nx
import json
import gzip

#%%

# problem_file= 'generated_data_10.dat'
# solution_file="results_10.yml"


#%%
def run_pyomo(problem_file, solution_file):
    """
    Run the Pyomo solve command with specified problem and solution file.

    Parameters:
    - problem_file: Path to the problem data file (e.g., 'generated_data_10.dat')
    - solution_file: Path to the output solution file (e.g., 'results_10.yml')
    """
    # Define the command as a list of arguments
    command = [
        "pyomo", "solve", 
        "--solver=gurobi", 
        "--solver-options=threads=1", 
        "max_flow.py",  # Assuming the script is in the same directory
        problem_file, 
        f"--save-results={solution_file}"
    ]

    # Run the command
    result = subprocess.run(command, capture_output=True, text=True)

    # Check if the command ran successfully
    if result.returncode == 0:
        print(f"Command executed successfully! Results saved in {solution_file}")
    else:
        print(f"Error: {result.stderr}")

    # Optional: Print the output from the command
    print(result.stdout)
#run_pyomo(problem_file,solution_file)       

#%%
problems_directory = "problems"
solutions_directory= "solutions"#%%problem generation
for i in [10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,160,170,180,190,200,300,400]:
    write_problem(i, f"{problems_directory}/generated_{i}.dat")
    
#%%solve all problems
# List all files in the problems directory
for filename in os.listdir(problems_directory):
    if filename.endswith(".dat"):  # Only process .dat files
        problem_file = os.path.join(problems_directory, filename)
        
        # Dynamically create the solution file name and save it in the "solutions" folder
        solution_file = os.path.join(solutions_directory, f"solution_{filename.split('_')[-1].split('.')[0]}.yml")
        
        # Check if the solution file already exists
        if not os.path.exists(solution_file):
            print(f"Solution file {solution_file} not found. Running Pyomo...")
            # Run pyomo for the current problem file
            run_pyomo(problem_file, solution_file)
        else:
            print(f"Solution file {solution_file} already exists. Skipping...")

        
#%% load problem as graph and solution as graph

def read_dat_to_graph(file_path):
    """
    Reads a .dat file to create a NetworkX graph.
    
    Parameters:
    - file_path (str): Path to the .dat file.
    
    Returns:
    - G (networkx.DiGraph): A directed graph with weights.
    - missing_nodes (list): List of nodes missing from edges or capacities.
    """
    G = nx.DiGraph()
    nodes = set()
    edges = []
    capacities = {}

    with open(file_path, 'r') as file:
        lines = file.readlines()

    reading_nodes = False
    reading_edges = False
    reading_capacities = False

    for line in lines:
        # Parse nodes
        if line.strip().startswith("set N :="):
            reading_nodes = True
            continue
        if reading_nodes:
            reading_nodes = False
            nodes.update(re.findall(r'\w+', line))


        # Parse edges
        elif line.strip().startswith("set A :="):
            reading_edges = True
            continue
        if reading_edges:
            if line.strip().endswith(";"):
                reading_edges = False
                edges.extend(re.findall(r'\((\w+),(\w+)\)', line))
            else:
                edges.extend(re.findall(r'\((\w+),(\w+)\)', line))
        
        # Parse capacities
        elif line.strip().startswith("param c :="):
            reading_capacities = True
            continue
        if reading_capacities:
            if line.strip().endswith(";"):
                reading_capacities = False
                matches = re.findall(r'(\w+)\s+(\w+)\s+(\d+)', line)
                for i, j, cap in matches:
                    capacities[(i, j)] = int(cap)
            else:
                matches = re.findall(r'(\w+)\s+(\w+)\s+(\d+)', line)
                for i, j, cap in matches:
                    capacities[(i, j)] = int(cap)
    
    # Add nodes to the graph
    G.add_nodes_from(nodes)

    # Add edges with capacities
    for i, j in edges:
        G.add_edge(i, j, weight=capacities.get((i, j), 0))
    return G




#%%

def load_flows_and_create_graph(yaml_file_path):
    """
    Reads a YAML file with flow results and creates a directed NetworkX graph.
    
    Parameters:
    - yaml_file_path (str): Path to the YAML file containing flow results.
    
    Returns:
    - G (networkx.DiGraph): Directed graph with edges weighted by flow values.
    """
    # Load the YAML file
    with open(yaml_file_path, 'r') as file:
        result_data = yaml.load(file, Loader=yaml.FullLoader)
    
    # Extract flow variables (f[<i>,<j>])
    flows = {}
    for var in result_data['Solution'][1]['Variable']:
        if 'f' in var:
            flows[var] = result_data['Solution'][1]['Variable'][var]['Value']
    
    # Create a directed graph
    G = nx.DiGraph()

    # Add edges with flow values
    for edge, flow in flows.items():
        i, j = edge[2:-1].split(',')  # Extract nodes from the variable name
        G.add_edge(i, j, weight=flow)
    
    return G
#read in original graph
OG = read_dat_to_graph(problem_file)
G = load_flows_and_create_graph(solution_file)

#%%
def extract_total_objective_from_yml(yml_file):
    """
    Extracts the total objective value from a Pyomo solution .yml file.

    Parameters:
    - yml_file (str): Path to the .yml file.

    Returns:
    - total (float): The total objective value.
    """
    with open(yml_file, 'r') as file:
        data = yaml.safe_load(file)

    # Extract the objective value under "Solution"
    total = data.get("Solution", [{}])[1].get("Objective", {}).get("total", {}).get("Value", None)
    if total is None:
        raise ValueError(f"Objective value not found in {yml_file}.")
    return total

#%%
def calculate_total_flow(G, source, prefix):
    """
    Calculates the total flow from the source node to nodes with the specified prefix.

    Parameters:
    - G (networkx.DiGraph): The graph.
    - source (str): The source node.
    - prefix (str): Prefix to filter target nodes.

    Returns:
    - total_flow (int): The total flow.
    """
    total_flow = 0
    for node in G.nodes:
        if node.startswith(prefix) and G.has_edge(source, node):
            total_flow += G[source][node]["weight"]
    return total_flow
#%% write results to CSV

# Paths to directories
problems_directory = "problems"
solutions_directory = "solutions"

# Ensure the solutions directory exists
os.makedirs(solutions_directory, exist_ok=True)


# Initialize an empty list to store results
results = []

# Compare results for each problem
for filename in os.listdir(problems_directory):
    if filename.endswith(".dat"):
        # Paths
        problem_file = os.path.join(problems_directory, filename)
        solution_file = os.path.join(solutions_directory, f"solution_{filename.split('_')[-1].split('.')[0]}.yml")

        # Extract problem size from the filename
        problem_size = int(re.search(r"generated_(\d+)\.dat", filename).group(1))

        # Read the graph
        graph = read_dat_to_graph(problem_file)

        # Calculate flow from 'S' to nodes starting with 'P'
        calculated_flow = calculate_total_flow(graph, source="S", prefix="P")

        # Extract total objective from solution
        try:
            total_objective = extract_total_objective_from_yml(solution_file)
        except ValueError as e:
            print(e)
            continue

        # Append the results as a dictionary
        results.append({
            "problem_size": problem_size,
            "total_flow": calculated_flow,
            "achieved_flow": total_objective
        })

# Convert results to a pandas DataFrame
results_df = pd.DataFrame(results)
results_df = results_df.sort_values("problem_size")

# Display or save the DataFrame
print(results_df)
results_df.to_csv("comparison_results.csv", index=False)

#%%Generate and save mapping

# Paths to directories
problems_directory = "problems"
solutions_directory = "solutions"
mappings_directory = "mappings"

def parse_person_group_mapping(file_path):
    mapping = {}
    multi_line_buffer = ""
    
    with open(file_path, 'r') as file:
        for line in file:
            multi_line_buffer += line.strip()  # Remove leading/trailing spaces
            
            # Check if we have both parts of the mapping
            if "Value:" in multi_line_buffer:
                # Now try to match the full pattern in the buffer
                match = re.match(r"y\[P(\d+),G(\d+)\]:\s*Value:\s*(\d+)", multi_line_buffer)
                if match:
                    person_id, group_id, value = match.groups()
                    if int(value) == 1:  # Only consider assignments where Value is 1
                        if group_id not in mapping:
                            mapping[group_id] = []
                        mapping[group_id].append(person_id)
                
                # Clear the buffer after processing
                multi_line_buffer = ""

    return mapping



def save_compressed_json(data, filename):
    """
    Save data as a compressed JSON file.

    Args:
        data (dict): The data to save.
        filename (str): The name of the file (without extension).
    """
    with gzip.open(f"{filename}.json.gz", "wt", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def process_solutions_directory(solutions_directory, mappings_directory):
    """
    Processes all .yml files in the solutions directory, computes group-to-persons mappings,
    and saves them as compressed JSON files in the mappings directory.

    Args:
        solutions_directory (str): Directory containing the .dat files.
        mappings_directory (str): Directory to save the mapping .json.gz files.
    """
    # Ensure the mappings directory exists
    os.makedirs(mappings_directory, exist_ok=True)

    # List all .yml files in the solutions directory
    solution_files = [
        f for f in os.listdir(solutions_directory) if f.endswith(".yml")
    ]

    for solution_file in solution_files:
        # Full path of the input file
        input_file_path = os.path.join(solutions_directory, solution_file)

        # Determine the output file name (e.g., mapping_X.json.gz for solution_X.dat)
        file_number = solution_file.split("_")[-1].split(".")[0]  # Extract the number X
        output_filename = f"mapping_{file_number}"

        # Get the mapping result from the function
        mapping_data = parse_person_group_mapping(input_file_path)  # FIXED LINE

        # Save the mapping to the mappings directory as a compressed JSON file
        save_compressed_json(mapping_data, os.path.join(mappings_directory, output_filename))
        print(f"Processed {solution_file} -> {output_filename}.json.gz")

# Generate the mappings and save as zipped JSON
process_solutions_directory(solutions_directory, mappings_directory)
