import pulp
from tabulate import tabulate

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
W_out_start = 0
W_out_end = 24
W_ret_start = 72
W_ret_end = 120
M = 10000

# --- Function to create the basic model ---
def create_model():
    prob = pulp.LpProblem("TrainTicketOptimization", pulp.LpMaximize)
    # Define Decision Variables
    x = pulp.LpVariable.dicts("ChooseDest", destinations, cat='Binary')
    y_keys = [(j, tout) for j in destinations for tout in outbound_trips[j]]
    y = pulp.LpVariable.dicts("OutboundTrip", y_keys, cat='Binary')
    z_keys = [(j, tret) for j in destinations for tret in return_trips[j]]
    z = pulp.LpVariable.dicts("ReturnTrip", z_keys, cat='Binary')

    # Define Objective Function
    prob += pulp.lpSum((params[j]['U'] - alpha * params[j]['D']) * x[j] for j in destinations), "Total_Weighted_Utility"

    # Define Constraints (Copy constraints 1-8 from the previous code)
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
    for j, tout in y_keys:
        prob += outbound_trips[j][tout]['dep_time'] >= W_out_start - M * (1 - y[(j, tout)]), f"OutWindowStart_{j}_{tout}"
        prob += outbound_trips[j][tout]['dep_time'] <= W_out_end + M * (1 - y[(j, tout)]), f"OutWindowEnd_{j}_{tout}"
    # Constraint 6: Return Time Window (Using Big M)
    for j, tret in z_keys:
        prob += return_trips[j][tret]['dep_time'] >= W_ret_start - M * (1 - z[(j, tret)]), f"RetWindowStart_{j}_{tret}"
        prob += return_trips[j][tret]['dep_time'] <= W_ret_end + M * (1 - z[(j, tret)]), f"RetWindowEnd_{j}_{tret}"
    # Constraint 7: Minimum Stay Duration (Using Big M)
    for j in destinations:
        for tout in outbound_trips[j]:
            for tret in return_trips[j]:
                prob += (return_trips[j][tret]['dep_time'] - outbound_trips[j][tout]['arr_time'] >=
                         min_stay - M * (2 - y[(j, tout)] - z[(j, tret)])), f"MinStay_{j}_{tout}_{tret}"
    # Constraint 8: Maximum Stay Duration (Using Big M)
    for j in destinations:
        for tout in outbound_trips[j]:
            for tret in return_trips[j]:
                prob += (return_trips[j][tret]['dep_time'] - outbound_trips[j][tout]['arr_time'] <=
                         max_stay + M * (2 - y[(j, tout)] - z[(j, tret)])), f"MaxStay_{j}_{tout}_{tret}"

    # Return the problem and variables for modification
    return prob, x, y, z

# --- Iterative Solving Process ---
prob, x, y, z = create_model()
all_vars = list(x.values()) + list(y.values()) + list(z.values()) # Get all variable objects

optimal_solutions = []
solution_count = 0
target_objective_value = None

while True:
    # Solve the current problem
    # Suppress solver messages for cleaner output in the loop
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    # Check if a solution was found
    if pulp.LpStatus[prob.status] == 'Optimal':
        current_objective_value = pulp.value(prob.objective)

        # Set the target objective value on the first successful solve
        if target_objective_value is None:
            target_objective_value = current_objective_value
            print(f"Found initial optimal objective value: {target_objective_value}")

        # Check if the current solution is optimal (matches the target value)
        # Use a small tolerance for floating point comparison
        if abs(current_objective_value - target_objective_value) < 1e-5:
            solution_count += 1
            print(f"\n--- Found Optimal Solution #{solution_count} ---")

            # Store and print the current solution details
            solution_details = {'destination': None, 'outbound': None, 'return': None, 'cost': 0, 'objective': current_objective_value}
            vars_in_solution = [] # Store variable objects for the exclusion cut

            for j in destinations:
                if x[j].varValue > 0.9:
                    solution_details['destination'] = j
                    vars_in_solution.append(x[j])
                    print(f"- Destination: {j}")
                    cost = 0
                    for tout in outbound_trips[j]:
                        if y[(j, tout)].varValue > 0.9:
                            solution_details['outbound'] = (tout, outbound_trips[j][tout]['cost'])
                            vars_in_solution.append(y[(j, tout)])
                            print(f"  - Outbound Trip: {tout} (Cost: {outbound_trips[j][tout]['cost']})")
                            cost += outbound_trips[j][tout]['cost']
                    for tret in return_trips[j]:
                        if z[(j, tret)].varValue > 0.9:
                             solution_details['return'] = (tret, return_trips[j][tret]['cost'])
                             vars_in_solution.append(z[(j, tret)])
                             print(f"  - Return Trip: {tret} (Cost: {return_trips[j][tret]['cost']})")
                             cost += return_trips[j][tret]['cost']
                    solution_details['cost'] = cost
                    print(f"Total Ticket Cost: {cost}")
            optimal_solutions.append(solution_details)

            # Add the integer cut to exclude this specific solution
            # Constraint: sum(v for v in vars_in_solution) <= len(vars_in_solution) - 1
            prob += pulp.lpSum(v for v in vars_in_solution) <= (len(vars_in_solution) - 1), f"Exclude_Solution_{solution_count}"

        else:
            # Found a suboptimal solution, means no more solutions with the target objective exist
            print(f"\nFound suboptimal solution with objective {current_objective_value}. Stopping search.")
            break
    else:
        # Problem became Infeasible or other status, means no more solutions exist
        print(f"\nSolver status: {pulp.LpStatus[prob.status]}. No more optimal solutions found.")
        break

# --- Final Summary ---
print("\n=============================================")
print(f"Search complete. Found {len(optimal_solutions)} optimal solution(s) with objective value {target_objective_value}")
print("=============================================")

# 表格化输出所有最优解
table = []
headers = ["目的地", "去程车次", "去程票价", "返程车次", "返程票价", "总成本", "停留时间(h)", "成本合规", "停留合规"]
for sol in optimal_solutions:
    dest = sol['destination']
    out_trip, out_cost = sol['outbound'] if sol['outbound'] else ("-", 0)
    ret_trip, ret_cost = sol['return'] if sol['return'] else ("-", 0)
    total_cost = sol['cost']
    # 计算停留时间
    if sol['outbound'] and sol['return']:
        stay = return_trips[dest][ret_trip]['dep_time'] - outbound_trips[dest][out_trip]['arr_time']
    else:
        stay = "-"
    cost_ok = "√" if total_cost <= budget else "×"
    stay_ok = "√" if (stay != "-" and min_stay <= stay <= max_stay) else "×"
    table.append([dest, out_trip, out_cost, ret_trip, ret_cost, total_cost, stay, cost_ok, stay_ok])

if table:
    print(tabulate(table, headers, tablefmt="grid", stralign="center"))
else:
    print("未找到可行解。")

# 额外验证信息
for idx, sol in enumerate(optimal_solutions, 1):
    dest = sol['destination']
    out_trip, _ = sol['outbound'] if sol['outbound'] else ("-", 0)
    ret_trip, _ = sol['return'] if sol['return'] else ("-", 0)
    total_cost = sol['cost']
    if sol['outbound'] and sol['return']:
        stay = return_trips[dest][ret_trip]['dep_time'] - outbound_trips[dest][out_trip]['arr_time']
    else:
        stay = "-"
    if total_cost > budget:
        print(f"警告：解{idx} 总成本超预算！")
    if stay != "-" and not (min_stay <= stay <= max_stay):
        print(f"警告：解{idx} 停留时间不合规！")

print(f"\n最优目标值（Weighted Utility）：{target_objective_value}")
