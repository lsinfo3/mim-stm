This is a source traffic generator for mobile instant messaging traffic which generates for a given population size a contact network, i.e. a mapping of persons to groups via a max-flow problem.
Then, those mappings are used to populate group chats with messages, media types, and the payload of the messages.

solve_max_flow.py or solve_max_flow_n_runs.py are used for generating N repetitions for each population size in problem_sizes:
- dat_generator.py generates for a given population size a pyomo input file as problem statement.
- max_flow.py contains the pyomo max-flow problem definition with all constraints.
- The resulting flow statistics are obtained in comparison_result.csv where the achieved and optimum flow are listed for each run for analysis.
- From the results a mapping is saved into the mappings folder which is a json dictionairy.


draw_messages.py:
- reads the json mapping
- generates a dataframe where each line is a chat
- columns: 
	- timestamps: message timestamps
	- num_messages: number of total messages 
	- participation_dict: mapping of person ids to group participation
	- senders: sender_id of each message
	- media_types: media type of each message
	- message_sizes: message sizes in byte
	- message_payload: after compression with overhead in megabyte
	- sum_message_payloads_MB: sum of all message_payload of a chat
	- network_[scope]_MB: total network load when sending the message to the server and replicating it to each recipient within the scope

