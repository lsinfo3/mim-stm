#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 22 08:28:12 2025

@author: fabian
"""
import pandas as pd
import json
import gzip
import os
import random
import numpy as np
import math
from multiprocessing import Pool, cpu_count
#%%
#read in group-person mappings from json
def json_to_dataframe(json_data):
    # Convert JSON to a DataFrame with group_id, person_ids (list), and group_size
    df = pd.DataFrame({
        "group_id": json_data.keys(),
        "person_ids": json_data.values()
    })
    df["group_size"] = df["person_ids"].apply(len)
    
    return df

def read_compressed_json(file_path):
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    return data

# Example usage
# file_path = "mappings_old/mapping_150.json.gz"  # Replace with actual file path
# output_filepath ="messages/150.csv.gz"
# json_data = read_compressed_json(file_path)
# df = json_to_dataframe(json_data)
# #print(df)


#%%
AT_LEAST_ONE_MESSAGE_PER_CHAT = True #guarantee at least one message per chat if we use the "active contact network" which is defined as having at least one message per chat



#%% #draw message IAT, according to hyperexp (nof paper) 
def inverse_iat_sampling(l, s):
    u = np.random.uniform(0, 1) # Generate uniform random numbers
    return (s - np.log(1 - u)) / l  # Apply inverse CDF transformation

def draw_from_branch(l, s, t_min, t_max):
    while True:
        iat = inverse_iat_sampling(l, s)
        if t_min < iat <= t_max:
            return iat


ps =        [0.7473,        0.2019,         0.0465,                 0.0043]
lambdas =   [0.0480334,     0.00126091,     4.75841878e-05,         0.6303]
ss =        [-0.08860522,  -0.12928196,    -9.72950955e-02,         0.5343]
mins =      [0,             100,            60*60,                  1]
maxs =      [100,           60*60,          60*60*24,               np.inf]
df_hyperexp = pd.DataFrame({"range": ["0s-100s", "101s-1h", "1h-24h", "24h+"], "p": ps, "lambda": lambdas, "s":ss, "t_min": mins, "t_max": maxs })



def draw_24h_iat_for_groups_final(num_groups):
    time = 0
    timestamps = [[] for _ in range(num_groups)]
    
    # Start the simulation loop
    while time < 60 * 60 * 24 * num_groups:  # Run a single sim for the total duration of 24h * num_groups
        # Draw a uniform random number to decide the branch (based on the probability distribution)
        branch_choice = random.choices(df_hyperexp['range'], weights=df_hyperexp['p'], k=1)[0]
    
        # Get the lambda and s values corresponding to the selected branch
        branch = df_hyperexp[df_hyperexp['range'] == branch_choice].iloc[0]
        
        # sample from the hyperexp branch the next inter-arrival time (IAT)
        iat = draw_from_branch(branch["lambda"], branch["s"],branch["t_min"], branch["t_max"])
        if branch_choice == "24h+": #need to convert from days to seconds
            iat = iat*86400
        # Update the time with the new IAT
        time += iat

        if (time > 60 * 60 * 24 * num_groups): break
        
        # Determine which group the timestamp belongs to
        group_index = int(time) // 86400
        
        # Store the timestamp modulo 24h in the corresponding group
        timestamps[group_index].append(time % 86400)
    
    #need to guarantee at least one message?
    if AT_LEAST_ONE_MESSAGE_PER_CHAT:
        timestamps = [lst if len(lst) > 0 else [np.random.uniform(0, 86400)] for lst in timestamps]    
    return timestamps


#%% assign sender to each message

#%%#assign message according to participation distribution (4c)

data = data = {
    '1': [1.0, 0.5504449314953347, 0.49933300232976713, 0.41534150638988354, 0.36637339321082907, 0.35433097176899536, 0.3336614951841645, 0.3264768854808429, 0.2965216175797816, 0.2732466785753908, 0.22635174898110505, 0.13131430067700217],
    '2': [0.0, 0.44955506850466537, 0.31253306098350225, 0.2883037448251664, 0.2627983018595241, 0.2452045452633708, 0.22085774188250346, 0.20691182633260274, 0.20203959570071775, 0.1968008078745602, 0.15051699597420728, 0.08133802324126005],
    '3': [0.0, 0.0, 0.1881339366867306, 0.18898707003802667, 0.19184990010702116, 0.1751401536288871, 0.16694227236054196, 0.15185910644384612, 0.15227730083696317, 0.14946696835619014, 0.11513388885517198, 0.06412765283331638],
    'other': [0.0, 0.0, 0.0, 0.10736767874692332, 0.17897840482262561, 0.2253243293387467, 0.2785384905727901, 0.31475218174270814, 0.34916148588253737, 0.3804855451938589, 0.5079973661895159, 0.7232200232484215]
}

df_participation = pd.DataFrame(data)

#dataframe information is for group sizes 1,2,3,4...,10, 11-30, >30
def get_participation_index(group_size):
    """Returns the correct index in df_participation based on group size."""
    if group_size <= 10:
        return group_size - 1  # Zero-based index
    elif 11 <= group_size <= 30:
        return 10  # The row for group sizes 11-30
    else:
        return 11  # The row for group sizes >30

#draw random persons for, 2nd most, 3rd most messages according to 4c), watch out for group size when doing this
def assign_participation(row):
    group_size = row['group_size']
    person_ids = row['person_ids'].copy()
    # Ensure there are enough participants for 1, 2, and 3
    random.shuffle(person_ids)
    
    # Initialize participation_dict
    participation_dict = {}
    
    # Assign participants based on the group size
    participation_dict[1] = person_ids[0]
    if group_size >= 2:
        participation_dict[2] = person_ids[1]
    if group_size >= 3:
        participation_dict[3] = person_ids[2]
    # Assign the rest of the participants to 'other'
    if group_size >3: 
        participation_dict['other'] = person_ids[3:group_size]
    
    return participation_dict

# Apply the function to the dataframe

#df['participation_dict'] = df.apply(assign_participation, axis=1)
    

def assign_sender_to_messages(row):
    senders = []
    
    # Get participation dictionary and group size
    participation_dict = row['participation_dict']
    group_size = row['group_size']
    
    # Get the correct row from df_participation based on group size
    participation_index = get_participation_index(group_size)
    participation_probs = df_participation.iloc[participation_index]  # Select row
    
    # Iterate over each message (timestamp)
    for _ in row["timestamps"]:
        rand = random.random()
        sender = None
        
        # Assign sender based on probabilities
        if rand < participation_probs['1']:  # Most contributing person
            sender = participation_dict.get(1, None)
        elif rand < participation_probs['1'] + participation_probs['2']:  # Second-most
            sender = participation_dict.get(2, None)
        elif rand < participation_probs['1'] + participation_probs['2'] + participation_probs['3']:  # Third-most
            sender = participation_dict.get(3, None)
        else:  # Assign to 'other' category
            other_participants = participation_dict.get('other', [])
            sender = random.choice(other_participants) if other_participants else None
        
        senders.append(sender)
    
    return senders


#%% #draw media type, with or without respect for previous message media type? state machine? from Share&Multiply figure 3b), 

# Manually initialize the DataFrame from Share and Multiply publication Figure 3b), then normalize since we have omit some media types
# Define reduced labels
labels = ["text", "image", "audio", "video"]

# Original transition matrix (before normalization)
data = [
    [0.9526811337524821, 0.031908507659135985, 0.008941875382526561, 0.004074231053029658],
    [0.6638926827198749, 0.3053128319602113, 0.009854985909793305, 0.017154643078012587],
    [0.5776086479792573, 0.03770591194644032, 0.3771003986016692, 0.006016434256524038],
    [0.6668320580785, 0.14622124148016608, 0.0142845950957094, 0.1665186848771316]
]

df_transitions = pd.DataFrame(data, index=labels, columns=labels)

# Normalize rows to sum to 1
df_transitions = df_transitions.div(df_transitions.sum(axis=1), axis=0)

#derive the probability to be within a certain state (stationairy distribution)
def get_stationary_distribution(df_transitions):
    P = df_transitions.values.T  # Transpose matrix
    eigvals, eigvecs = np.linalg.eig(P)
    stationary = np.real(eigvecs[:, np.argmin(np.abs(eigvals - 1))])
    return stationary / stationary.sum()  # Normalize

# Get stationairry distribution for start
stationary_distribution = get_stationary_distribution(df_transitions)

#Alternative, works same result: use power method to arrive at the stationairy distribution via power method
# def get_stationary_distribution_power_method(df_transitions, tol=1e-9, max_iter=10000):
#     """
#     Computes the stationary distribution using the power method.

#     Parameters:
#     - df_transitions: Pandas DataFrame, the transition matrix where rows sum to 1.
#     - tol: Tolerance for convergence (default: 1e-9).
#     - max_iter: Maximum number of iterations (default: 10,000).

#     Returns:
#     - A NumPy array representing the stationary distribution.
#     """
#     P = df_transitions.values
#     num_states = P.shape[0]

#     # Start with a uniform probability distribution
#     v = np.ones(num_states) / num_states  

#     for _ in range(max_iter):
#         v_next = np.dot(v, P)  # Multiply current distribution by the transition matrix
#         if np.linalg.norm(v_next - v, ord=1) < tol:  # Check for convergence (L1 norm)
#             break
#         v = v_next  # Update for next iteration

#     return v / v.sum()  # Ensure normalization
# stationairy_distribution_power = get_stationary_distribution(df_transitions)





def assign_types_to_group_messages(row):
    num_messages = len(row["timestamps"])
    media_types = []
    #get first value from overall probability distribution
    if num_messages != 0:
        media_types.append(random.choices(labels, weights=stationary_distribution, k=1)[0])
    for i in range(1, num_messages):
        next_media = random.choices(labels, weights=df_transitions.loc[media_types[-1]], k=1)[0]
        media_types.append(next_media)
    return media_types


#%%
#need text char and emoji distribution from Share and Multiply Fig. 3c)
#go for data driven approach

# Load the data from CSV
df_char = pd.read_csv("data/char_cdf_data.csv")
df_emoji = pd.read_csv("data/emoji_cdf_data.csv")

def reverse_sample_cdf(qe, pe):
    # Generate a single uniform random number between 0 and 1
    random_prob = np.random.uniform(0, 1)
    
    # Find the index where pe is greater than or equal to the drawn value
    idx = np.argmax(pe >= random_prob)
    reverse_sample = qe[idx]
        
    return reverse_sample

def draw_raw_message_length_byte():
    bs = 0
    # Sample from the character distribution
    cs = reverse_sample_cdf(df_char["qe_char"].values, df_char["pe_char"].values)
    # 1 char = 1 byte
    bs += cs

    # Sample from the emoji distribution
    es = reverse_sample_cdf(df_emoji["qe_emoj"].values, df_emoji["pe_emoj"].values)
    # Emoji takes between 2 to 7 bytes each
    bs += sum([np.random.randint(2, 8) for i in range(int(es))])
      
    return bs


# Lambdas to generate media size in MB
l_image = 4.686  # Lambda for image file size (in MB)
l_audio = 11.278  # Lambda for audio file size (in MB)
l_video = 0.159  # Lambda for video file size (in MB)

def draw_exp(lambda_media):
    """
    Draw a sample from an exponential distribution with a given lambda (rate parameter).
    """
    # Generate a random sample from the exponential distribution
    return np.random.exponential(scale=1/lambda_media)

def draw_media_file_size_byte(media_type):
    """
    Draw a random (compressed) media file size in bytes for a given media type.
    """
    size_mb = 0 
    if media_type == "image":
        size_mb = draw_exp(l_image)
    elif media_type == "audio":
        size_mb = draw_exp(l_audio)
    elif media_type == "video":
        size_mb = draw_exp(l_video)
    else:
        raise Exception("Unknown media type")
    
    # Convert size from MB to Bytes
    size_byte = size_mb * 10**6
    return round(size_byte)

#ToDo: do here the stuff to get the message size in kB


def assign_message_size_byte(row):
    m_types = row["media_types"]
    m_sizes= []
    for m_t in m_types:
        if m_t == "text":
            m_sizes.append(round(draw_raw_message_length_byte()))
        else:
            m_sizes.append(round(draw_media_file_size_byte(m_t)))
    return m_sizes

#df["message_sizes"] = df.apply(assign_message_size_byte, axis=1)


#%%


#%%network load and message replication


#now calculate the final payload per message


#add application-specific message overhead
# Adding WhatsApp-specific overheads (in kB)
oh_text =  0.74 *1000  # B
oh_image = 1.84 *1000  # B
oh_video = 6.56 *1000 # B
oh_audio = 3.03 *1000 # B

def get_overhead(message_type):
    """
    Get the overhead for a specific message type in kB.
    """
    if message_type == "text":
        return oh_text
    elif message_type == "image":
        return oh_image
    elif message_type == "video":
        return oh_video
    elif message_type == "audio":
        return oh_audio
    else:
        raise Exception("Unknown message type")

def assign_overhead(row):
    m_types = row["media_types"]
    m_sizes = row["message_sizes"]
    m_payloads = [
    (m_sizes[i] * 1.33 + get_overhead(m_types[i])) if m_types[i] == "text" 
    else 
    (m_sizes[i] + get_overhead(m_types[i]))
    for i in range(len(m_types))
    ]
    return m_payloads


def assign_sum_payloads_messages(row):
    return sum(row.message_payloads) / 10**6 #from Byte to MB



#%%
#thin out for proximity scope
import pandas as pd
import numpy as np
#import matplotlib.pyplot as plt
import json

# Load the dataset and rename columns
df_proximity = pd.read_csv("data/df_active_group_info.csv").rename(
    columns={
        'activeGroupSizeSameRoom': "room",
        'activeGroupSizeSameBuilding': "building",
        'activeGroupSizeSameCity': "city",
        'activeGroupSizeSameCountry': "country"
    }
)
# # Plot CDF for each numerical column
# plt.figure(figsize=(8, 6))
# for col in numerical_cols:
#     sorted_data = np.sort(df_proximity[col].dropna())
#     cdf = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
#     plt.plot(sorted_data, cdf, label=col)

# plt.xlabel("Value")
# plt.ylabel("Cumulative Probability")
# plt.title("CDF of Numerical Columns")
# plt.legend()
# plt.grid()
# plt.show()
# Compute original CDFs and store in cdf_data



#%%
def assign_users_within_proximity(row, df_proximity):
    sample = df_proximity.sample()
    proximities = sample.values[0]
    within_prox = [min( (round(i * (row.group_size-1))+1), row.group_size) for i in proximities]
    return pd.Series(within_prox)



#%%
input_folder = "./mappings_n30"  # Replace with actual file path
output_folder ="./messages_1000"


# Ensure output directory exists
os.makedirs(output_folder, exist_ok=True)

filenames = os.listdir(input_folder)

def process_file(filename, j):
    parts = filename.split("_")
    problem_size = parts[1]
    run_i = parts[3].split(".")[0]  # Extract run number from filename
    
    input_filepath = os.path.join(input_folder, filename)
    output_filepath = os.path.join(output_folder, f"messages_{problem_size}_run{run_i}_messagerun_{j}.csv.gz")

    # Read mapping data
    json_data = read_compressed_json(input_filepath)
    df = json_to_dataframe(json_data)
    # Generate timestamps
    df["timestamps"] = draw_24h_iat_for_groups_final(df.shape[0])
    df["num_messages"] = df["timestamps"].apply(lambda x: len(x) if isinstance(x, list) else 0)

    
    df['participation_dict'] = df.apply(assign_participation, axis=1)

    df["senders"] = df.apply(assign_sender_to_messages, axis=1)


    # Assign media types
    df["media_types"] = df.apply(assign_types_to_group_messages, axis=1)
    
    df["message_sizes"] = df.apply(assign_message_size_byte, axis=1)

    df["message_payloads"]= df.apply(assign_overhead, axis=1)
    df["sum_message_payloads_MB"] = df.apply(assign_sum_payloads_messages, axis=1)
    
    df[["within_room","within_building", "within_city","within_country"]]= df.apply(lambda x: assign_users_within_proximity(x, df_proximity), axis=1)

    #total network load = uplink and downlink, uplink = sender, downlink = receivers within proximity
    df["network_room_MB"] = df.apply(lambda x: x.sum_message_payloads_MB * (x.within_room), axis=1)
    df["network_building_MB"] = df.apply(lambda x: x.sum_message_payloads_MB * (x.within_building), axis=1)
    df["network_city_MB"] = df.apply(lambda x: x.sum_message_payloads_MB * (x.within_city), axis=1)
    df["network_country_MB"] = df.apply(lambda x: x.sum_message_payloads_MB * (x.within_country), axis=1)
    df["network_total_MB"] = df.apply(lambda x: x.sum_message_payloads_MB * (x.group_size), axis=1)
    
    # Save to CSV
    df.to_csv(output_filepath, index=False, compression="gzip")
    print(f"Generated: {output_filepath}")


if __name__ == "__main__":
    
    runs_per_contact_graph = 30  # Adjust this as needed
    
    # Filter relevant files before passing to Pool
    filenames = [f for f in os.listdir(input_folder) if f.startswith("mapping_1000_") and f.endswith(".json.gz")]
    # Create list of (filename, j) tuples for parallel processing
    tasks = [(f, j) for f in filenames for j in range(runs_per_contact_graph)]
    
    with Pool(processes=cpu_count()) as pool:
        pool.starmap(process_file, tasks)

