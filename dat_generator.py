#%%Generate Input Lists
import numpy as np


def draw_number_of_contacts():
    """
    Generate the number of contacts for a single person according to  F(x) = 1-e^ (-0.0021 x) from the paper

    numpy.random.exponential uses scale parameter which is 1/lambda
    scale = 1/lambda

    
    Returns:
    - Number of contacts for a person, cut off at our observed maximum of 2962
    
    """
    #scale = 489.6
    #scale_weekly_active = 489.6* 0.35537964381332926
    #scale_daily_active =  489.6 * 0.20574915282430015
    num_contacts = int(np.random.exponential(489.6 * 0.20574915282430015))
    if (num_contacts < 1): 
        num_contacts = 1
    if num_contacts > 2962: 
        return draw_number_of_contacts()
    
    return num_contacts


# Define the inverse CDF for -0.49 * np.exp(-0.53 * x)+1 from paper
def inverse_cdf_contacts(u):
    return -1 / 0.53 * np.log((1 - u) / 0.49)
    
def draw_number_of_chats_with_contact():
    u = np.random.uniform(0, 1)  # Generate uniform random number
    sample = int(inverse_cdf_contacts(u))        # Transform using the inverse CDF, round down to next int
    if sample < 1: sample = 1 #our CDF is at 70.76% for x=1, they at least need one connection. this is fine
    return sample

    

def generate_SCE_for_N(N):
    """
    Generate the total number of shared chats for a population of size N.

    Parameters:
    - N (int): The size of the population.

    Returns:
    - List of length N, where each value represents the total number of shared chats for each individual.
    """
    # Initialize an empty list to store the result
    result = []

    # Loop over each individual in the population
    for _ in range(N):
        # Draw the number of contacts (c_n) for this individual
        c_n = draw_number_of_contacts()

        
        total_shared_chats = 0
        
        # For each contact, draw a number of shared chats (sc), and ensure each is at least 1
        for _ in range(c_n):
            sc = draw_number_of_chats_with_contact()

            total_shared_chats += sc  # Accumulate shared chats, ("sce" from paper)
        
        # Append the total number of shared chats for this individual to the result list
        result.append(total_shared_chats)

    return result

# # Example usage
# filename="generated_data_500.dat"
# N = 500
# ps = generate_SCE_for_N(N)
#%%draw groups as needed
# Define the inverse CDF for -0.6559 * np.exp(-0.508 * x)+0.9705 , R2 = 0.9404 fitted from whatsanalyzer data 
def inverse_cdf_group(u):
    return -1 / 0.508 * np.log((0.9705 - u) / 0.6559)
    
def draw_group_size():
    #first draw according to the amount of 1-on-1 chats from our contacts study
    dyadic = np.random.uniform(0,1)
    if(dyadic<0.4041):
        return 2
    else:
        return draw_from_group_distribution()

def draw_from_group_distribution():
    #generate according to the group size distributions from our whatsanalyzer data set, omit samples if they are <=2 since we got that covered in draw_group_size    
    u = np.random.uniform(0, 1)  # Generate uniform random number
    sample = int(inverse_cdf_contacts(u))        # Transform using the inverse CDF, round down to next int
    if sample <= 2 or sample > 256: 
        return draw_from_group_distribution()
    return sample
#draw iteratively enough groups until the group sizes support the demand based on the persons
def draw_group_sizes(ps):
    sum_ps = sum(ps)
    gs=[]
    sum_gs = 0
    while sum_gs <= sum_ps:
        new_size = draw_group_size()
        new_size = np.floor(new_size).astype(int)
        gs.append(new_size)
        sum_gs += (new_size*(new_size -1))
    return gs

# # Example usage
# gs = draw_group_sizes(ps)


def write_problem(N, filename):
    """
    Generate a .dat file for the max flow problem with the given persons and groups data.

    Parameters:
    - Population size N
    - filename: The name of the file where the data will be written.
    """
    persons = generate_SCE_for_N(N)
    groups = draw_group_sizes(persons)
    
    # Prepare nodes
    P_nodes = [f"P{i}" for i in range(1, len(persons) + 1)]
    G_nodes = [f"G{j}" for j in range(1, len(groups) + 1)]
    nodes = ["S", "T"] + P_nodes + G_nodes

    # Prepare arcs
    arcs = []
    arc_capacities = {}

    # S -> P arcs
    for i, p_capacity in enumerate(persons):
        arcs.append(("S", P_nodes[i]))
        arc_capacities[("S", P_nodes[i])] = p_capacity

    # G -> T arcs
    for j, g_capacity in enumerate(groups):
        capacity = g_capacity * (g_capacity - 1)
        arcs.append((G_nodes[j], "T"))
        arc_capacities[(G_nodes[j], "T")] = capacity

    # P -> G arcs
    for i in range(len(P_nodes)):
        for j in range(len(G_nodes)):
            capacity = groups[j] - 1
            arcs.append((P_nodes[i], G_nodes[j]))
            arc_capacities[(P_nodes[i], G_nodes[j])] = capacity

    # Generate .dat content
    dat_content = "# Define the set of nodes\n\n"
    dat_content += "set N := " + " ".join(nodes) + ";\n\n"
    dat_content += "param s := S;\n\n"
    dat_content += "param t := T;\n\n"
    dat_content += "# Define the set of edges (arcs)\n\n"
    dat_content += "set A :=\n"
    dat_content += "\n".join(f"({arc[0]},{arc[1]})" for arc in arcs) + ";\n\n"
    dat_content += "# Define the capacity parameter for each edge\n\n"
    dat_content += "param c :=\n"
    dat_content += "\n".join(f"{arc[0]} {arc[1]} {arc_capacities[arc]}" for arc in arcs) + ";\n"

    # Write to file
    with open(filename, "w") as file:
        file.write(dat_content)

    print(f"Data file '{filename}' has been created.")
