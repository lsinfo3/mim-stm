from pyomo.environ import *
from pyomo.opt import SolverFactory

import networkx as nx
import re
import yaml
import subprocess
import os
import pandas as pd
import json
import gzip

from dat_generator import write_problem

from multiprocessing import Pool
# Number of runs per problem size
N_RUNS = 30
parallel = True
new_problems = False

# Define directories
problems_directory = "problems_n30"
solutions_directory = "solutions_30"
mappings_directory = "mappings_n30"

# Ensure directories exist
os.makedirs(problems_directory, exist_ok=True)
os.makedirs(solutions_directory, exist_ok=True)
os.makedirs(mappings_directory, exist_ok=True)

# Problem sizes to test
problem_sizes = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 350, 400, 450, 500,600,700,800,900,1000]
# Generate problems for each size and each run
def generate_problem(size):
    size_dir = os.path.join(problems_directory, f"size_{size}")
    os.makedirs(size_dir, exist_ok=True)
    for run in range(N_RUNS):
        problem_file = os.path.join(size_dir, f"generated_{size}_run_{run}.dat")
        write_problem(size, problem_file)

if new_problems:
    if parallel:
        with Pool() as pool:
            pool.map(generate_problem, problem_sizes)
    else:
        for size in problem_sizes:
            generate_problem(size)
# Function to run Pyomo solver
def run_pyomo(problem_file: str, solution_file: str) -> None:
    """
    Runs the Pyomo solver on a given problem file and saves the solution.
    
    Parameters:
        problem_file (str): Path to the .dat problem file.
        solution_file (str): Path to save the solution output.
    """
    command = [
        "pyomo", "solve", 
        "--solver=gurobi", 
        "--solver-options=threads=1", 
        "max_flow.py",  
        problem_file, 
        f"--save-results={solution_file}"
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Success: {solution_file}")
    else:
        print(f"Error: {result.stderr}")
    print(result.stdout)

# Solve all problems
def solve_problem(args):
    size, run = args
    size_problem_dir = os.path.join(problems_directory, f"size_{size}")
    size_solution_dir = os.path.join(solutions_directory, f"size_{size}")
    os.makedirs(size_solution_dir, exist_ok=True)

    problem_file = os.path.join(size_problem_dir, f"generated_{size}_run_{run}.dat")
    solution_file = os.path.join(size_solution_dir, f"solution_{size}_run_{run}.yml")
    if not os.path.exists(solution_file):
        print(f"Solving problem size {size}, run {run}")
        run_pyomo(problem_file, solution_file)

if parallel:
    with Pool() as pool:
        pool.map(solve_problem, [(size, run) for size in problem_sizes for run in range(N_RUNS)])
else:
    for size in problem_sizes:
        for run in range(N_RUNS):
            solve_problem((size, run))

# Function to read .dat file into a graph
def read_dat_to_graph(file_path: str) -> nx.DiGraph:
    """
    Reads a .dat file and constructs a directed graph with capacities.
    
    Parameters:
        file_path (str): Path to the .dat file.
    
    Returns:
        nx.DiGraph: A directed graph representing the problem.
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
        if line.strip().startswith("set N :="):
            reading_nodes = True
            continue
        if reading_nodes:
            reading_nodes = False
            nodes.update(re.findall(r'\w+', line))
        elif line.strip().startswith("set A :="):
            reading_edges = True
            continue
        if reading_edges:
            if line.strip().endswith(";"):
                reading_edges = False
                edges.extend(re.findall(r'\((\w+),(\w+)\)', line))
            else:
                edges.extend(re.findall(r'\((\w+),(\w+)\)', line))
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
    
    G.add_nodes_from(nodes)
    for i, j in edges:
        G.add_edge(i, j, weight=capacities.get((i, j), 0))
    return G

# Function to extract total objective from YAML
def extract_total_objective_from_yml(yml_file: str) -> float:
    """
    Extracts the total objective value from a YAML solution file.
    
    Parameters:
        yml_file (str): Path to the YAML solution file.
    
    Returns:
        float: The extracted objective value.
    """
    with open(yml_file, 'r') as file:
        data = yaml.safe_load(file)
    return data.get("Solution", [{}])[1].get("Objective", {}).get("total", {}).get("Value", None)

# Function to calculate total flow
def calculate_total_flow(G: nx.DiGraph, source: str, prefix: str) -> int:
    """
    Calculates the total flow in the network from the source node.
    
    Parameters:
        G (nx.DiGraph): The network graph.
        source (str): The source node.
        prefix (str): The prefix used to identify flow nodes.
    
    Returns:
        int: The total flow value.
    """
    total_flow = 0
    for node in G.nodes:
        if node.startswith(prefix) and G.has_edge(source, node):
            total_flow += G[source][node]["weight"]
    return total_flow

# Collect and store results
results = []
for size in problem_sizes:
    size_solution_dir = os.path.join(solutions_directory, f"size_{size}")
    for run in range(N_RUNS):
        solution_file = os.path.join(size_solution_dir, f"solution_{size}_run_{run}.yml")
        problem_file = os.path.join(problems_directory, f"size_{size}", f"generated_{size}_run_{run}.dat")
        if os.path.exists(solution_file):
            try:
                total_objective = extract_total_objective_from_yml(solution_file)
                graph = read_dat_to_graph(problem_file)
                calculated_flow = calculate_total_flow(graph, source="S", prefix="P")
                print(f"Size: {size}, Run: {run}, Total Flow: {calculated_flow}, Achieved Flow: {total_objective}")
                results.append({
                    "problem_size": size,
                    "run": run,
                    "total_flow": calculated_flow,
                    "achieved_flow": total_objective
                })
            except ValueError as e:
                print(e)
                continue

# Save results
results_df = pd.DataFrame(results)
results_df.to_csv("comparison_results.csv", index=False)
#print(results_df)


# Function to parse person-group mappings
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
# Function to save mappings
def save_compressed_json(data, filename):
    with gzip.open(f"{filename}.json.gz", "wt", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

# Process solution files
def process_solution_file(args):
    size, run = args
    size_solution_dir = os.path.join(solutions_directory, f"size_{size}")
    solution_file = os.path.join(size_solution_dir, f"solution_{size}_run_{run}.yml")

    if not os.path.exists(solution_file):
        print(f"Warning: Solution file {solution_file} not found, skipping.")
        return

    file_number = f"{size}_run_{run}"  # Include size and run for uniqueness
    output_filename = f"mapping_{file_number}"

    mapping_data = parse_person_group_mapping(solution_file)
    save_compressed_json(mapping_data, os.path.join(mappings_directory, output_filename))
    print(f"Processed {solution_file} -> {output_filename}.json.gz")


if parallel:
    solution_files = [(size, run) for size in problem_sizes for run in range(N_RUNS)]
    with Pool() as pool:
        pool.map(process_solution_file, solution_files)
else:
    for size in problem_sizes:
        for run in range(N_RUNS):
            process_solution_file((size, run))
