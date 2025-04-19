import pulp

# --- 1. Data Definition ---
# (Using dictionaries for better readability and generalization)

destinations = ["Shanghai", "Xian", "Qingdao", "Chengde"]

# Parameters for each destination
params = {
    "Shanghai": {"U": 9, "D": 5},
    "Xian":     {"U": 8, "D": 4},
    "Qingdao":  {"U": 6, "D": 3},
    "Chengde":  {"U": 4, "D": 2},
}

# Outbound Trip Data (using trip IDs for clarity)
# Times are in hours from May 1st 00:00
outbound_trips = {
    "Shanghai": {
        "SH_G1": {"dep_time": 8,  "arr_time": 12.5, "cost": 550},
        "SH_G7": {"dep_time": 14, "arr_time": 18.5, "cost": 560},
    },
    "Xian": {
        "XA_G651": {"dep_time": 7,  "arr_time": 11.5, "cost": 515},
        "XA_G657": {"dep_time": 15, "arr_time": 19.5, "cost": 520},
    },
    "Qingdao": {
        "QD_G205": {"dep_time": 9,  "arr_time": 13,   "cost": 314},
        "QD_G209": {"dep_time": 16, "arr_time": 20,   "cost": 320},
    },
    "Chengde": {
        "CD_G3681": {"dep_time": 10, "arr_time": 11.5, "cost": 110},
        "CD_G3685": {"dep_time": 17, "arr_time": 18.5, "cost": 115},
    },
}

# Return Trip Data
return_trips = {
    "Shanghai": {
        "SH_G8": {"dep_time": 82, "arr_time": 86.5, "cost": 550}, # May 4th 10:00
        "SH_G2": {"dep_time": 111,"arr_time": 115.5,"cost": 570}, # May 5th 15:00
    },
    "Xian": {
        "XA_G658": {"dep_time": 83, "arr_time": 87.5, "cost": 515}, # May 4th 11:00
        "XA_G652": {"dep_time": 105,"arr_time": 109.5,"cost": 525}, # May 5th 09:00
    },
    "Qingdao": {
        "QD_G210": {"dep_time": 88, "arr_time": 92,   "cost": 314}, # May 4th 16:00
        "QD_G206": {"dep_time": 111,"arr_time": 115,  "cost": 325}, # May 5th 15:00
    },
    "Chengde": {
        "CD_G3682": {"dep_time": 81, "arr_time": 82.5, "cost": 110}, # May 4th 09:00
        "CD_G3686": {"dep_time": 110,"arr_time": 111.5,"cost": 120}, # May 5th 14:00
    },
}

# Other Parameters
alpha = 1.0      # Difficulty weight
budget = 1200    # Max budget
min_stay = 48    # Min stay in hours
max_stay = 96    # Max stay in hours
W_out_start = 0  # May 1st 00:00
W_out_end = 24   # May 2nd 00:00 (exclusive or inclusive depending on definition, check data)
W_ret_start = 72 # May 4th 00:00
W_ret_end = 120  # May 6th 00:00
M = 10000        # Big M for constraints

# --- 2. Create the LP Problem ---
prob = pulp.LpProblem("TrainTicketOptimization", pulp.LpMaximize)

# --- 3. Define Decision Variables ---

# x_j: Choose destination j (Binary)
x = pulp.LpVariable.dicts("ChooseDest", destinations, cat='Binary')

# y_jt: Choose outbound trip t for destination j (Binary)
# Create a list of tuples (destination, trip_id) for valid y variables
y_keys = [(j, tout) for j in destinations for tout in outbound_trips[j]]
y = pulp.LpVariable.dicts("OutboundTrip", y_keys, cat='Binary')

# z_jt: Choose return trip t for destination j (Binary)
# Create a list of tuples (destination, trip_id) for valid z variables
z_keys = [(j, tret) for j in destinations for tret in return_trips[j]]
z = pulp.LpVariable.dicts("ReturnTrip", z_keys, cat='Binary')

# --- 4. Define Objective Function ---
prob += pulp.lpSum((params[j]['U'] - alpha * params[j]['D']) * x[j] for j in destinations), "Total_Weighted_Utility"

# --- 5. Define Constraints ---

# Constraint 1: Choose exactly one destination
prob += pulp.lpSum(x[j] for j in destinations) == 1, "Exactly_One_Destination"

# Constraint 2: Link outbound trip selection to destination selection
for j in destinations:
    prob += pulp.lpSum(y[(j, tout)] for tout in outbound_trips[j]) == x[j], f"Link_Outbound_{j}"

# Constraint 3: Link return trip selection to destination selection
for j in destinations:
    prob += pulp.lpSum(z[(j, tret)] for tret in return_trips[j]) == x[j], f"Link_Return_{j}"

# Constraint 4: Budget Limit
prob += (pulp.lpSum(outbound_trips[j][tout]['cost'] * y[(j, tout)] for j, tout in y_keys) +
         pulp.lpSum(return_trips[j][tret]['cost'] * z[(j, tret)] for j, tret in z_keys) <= budget), "Budget_Limit"

# Constraint 5: Outbound Time Window (Using Big M)
# Note: Our sample data fits, but the constraints are formally needed
for j, tout in y_keys:
    prob += outbound_trips[j][tout]['dep_time'] >= W_out_start - M * (1 - y[(j, tout)]), f"OutWindowStart_{j}_{tout}"
    prob += outbound_trips[j][tout]['dep_time'] <= W_out_end + M * (1 - y[(j, tout)]), f"OutWindowEnd_{j}_{tout}" # Use '<=' for pulp constraint

# Constraint 6: Return Time Window (Using Big M)
for j, tret in z_keys:
    prob += return_trips[j][tret]['dep_time'] >= W_ret_start - M * (1 - z[(j, tret)]), f"RetWindowStart_{j}_{tret}"
    prob += return_trips[j][tret]['dep_time'] <= W_ret_end + M * (1 - z[(j, tret)]), f"RetWindowEnd_{j}_{tret}" # Use '<=' for pulp constraint

# Constraint 7: Minimum Stay Duration (Using Big M)
for j in destinations:
    for tout in outbound_trips[j]:
        for tret in return_trips[j]:
            # Constraint only active if both y and z are 1
            prob += (return_trips[j][tret]['dep_time'] - outbound_trips[j][tout]['arr_time'] >=
                     min_stay - M * (2 - y[(j, tout)] - z[(j, tret)])), f"MinStay_{j}_{tout}_{tret}"

# Constraint 8: Maximum Stay Duration (Using Big M)
for j in destinations:
    for tout in outbound_trips[j]:
        for tret in return_trips[j]:
            # Constraint only active if both y and z are 1
            prob += (return_trips[j][tret]['dep_time'] - outbound_trips[j][tout]['arr_time'] <=
                     max_stay + M * (2 - y[(j, tout)] - z[(j, tret)])), f"MaxStay_{j}_{tout}_{tret}"


# --- 6. Solve the Problem ---
# prob.writeLP("TrainTicketModel.lp") # Optional: write the model to a file for inspection
prob.solve()

# --- 7. Print the Results ---
print("Status:", pulp.LpStatus[prob.status])

if pulp.LpStatus[prob.status] == 'Optimal':
    print("\nOptimal Solution Found:")
    selected_dest = ""
    selected_out_trip = ""
    selected_ret_trip = ""
    total_cost = 0

    for j in destinations:
        if x[j].varValue > 0.9: # Check if destination is selected (use tolerance)
            selected_dest = j
            print(f"- Destination: {j}")
            for tout in outbound_trips[j]:
                if y[(j, tout)].varValue > 0.9:
                    selected_out_trip = tout
                    print(f"  - Outbound Trip: {tout} (Cost: {outbound_trips[j][tout]['cost']})")
                    total_cost += outbound_trips[j][tout]['cost']
            for tret in return_trips[j]:
                if z[(j, tret)].varValue is not None and z[(j, tret)].varValue > 0.9:
                    selected_ret_trip = tret
                    print(f"  - Return Trip: {tret} (Cost: {return_trips[j][tret]['cost']})")
                    total_cost += return_trips[j][tret]['cost']
            break # Since only one destination is chosen

    print(f"\nTotal Ticket Cost: {total_cost}")
    print(f"Optimal Objective Value (Weighted Utility): {pulp.value(prob.objective)}")

    # Verification (Optional but good practice)
    if selected_dest and selected_out_trip and selected_ret_trip:
        stay_duration = return_trips[selected_dest][selected_ret_trip]['dep_time'] - outbound_trips[selected_dest][selected_out_trip]['arr_time']
        print(f"Calculated Stay Duration: {stay_duration} hours (Min: {min_stay}, Max: {max_stay})")
        if not (min_stay <= stay_duration <= max_stay):
            print("!!! Warning: Stay duration constraint might not be perfectly met due to edge cases or Big M limitations.")
        if total_cost > budget:
             print("!!! Warning: Budget constraint violated.")

elif pulp.LpStatus[prob.status] == 'Infeasible':
    print("\nThe problem is infeasible. No solution satisfies all constraints.")
    print("Check your budget, time windows, stay durations, and available trips.")
else:
    print("\nSolver failed to find an optimal solution. Status:", pulp.LpStatus[prob.status])
