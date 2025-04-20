import pulp
from tabulate import tabulate
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

def load_json_and_solve(json_path):
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        destinations = data["destinations"]
        params = data["params"]
        outbound_trips = data["outbound_trips"]
        return_trips = data["return_trips"]

        # --- 检查数据完整性 ---
        missing_stay_info = False
        for j in destinations:
            if 'min_stay_hours' not in params[j] or 'max_stay_hours' not in params[j]:
                print(f"警告：目的地 '{j}' 在 'params' 中缺少 'min_stay_hours' 或 'max_stay_hours' 信息。")
                missing_stay_info = True
        if missing_stay_info:
            print("将为缺少信息的目标使用默认值 0 和 M (非常宽松)")


        # --- Other Parameters ---
        global alpha, budget, W_out_start, W_out_end, W_ret_start, W_ret_end
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

            # Define Constraints
            # Constraint 1: Choose exactly one destination
            prob += pulp.lpSum(x[j] for j in destinations) == 1, "Exactly_One_Destination"
            # Constraint 2: Link outbound trip selection to destination selection
            for j in destinations:
                prob += pulp.lpSum(y[(j, tout)] for tout in outbound_trips[j]) == x[j], f"Link_Outbound_{j}"
            # Constraint 3: Link return trip selection to destination selection
            for j in destinations:
                prob += pulp.lpSum(z[(j, tret)] for tret in return_trips[j]) == x[j], f"Link_Return_{j}"
            # Constraint 4: Budget Limit (Traffic Cost)
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

            # Constraint 7 & 8: Destination-Specific Stay Duration (Using Big M)
            for j in destinations:
                # 获取目的地 j 特定 的最短和最长停留时间
                # 添加 .get() 以处理可能缺失键的情况，提供默认值
                min_stay_j = params[j].get('min_stay_hours', 0) # 默认最短0小时
                max_stay_j = params[j].get('max_stay_hours', M) # 默认最长 M 小时 (非常宽松)

                for tout in outbound_trips[j]:
                    for tret in return_trips[j]:
                        # Constraint 7: Minimum Stay Duration
                        prob += (return_trips[j][tret]['dep_time'] - outbound_trips[j][tout]['arr_time'] >=
                                min_stay_j - M * (2 - y[(j, tout)] - z[(j, tret)])), f"MinStay_{j}_{tout}_{tret}"
                        # Constraint 8: Maximum Stay Duration
                        prob += (return_trips[j][tret]['dep_time'] - outbound_trips[j][tout]['arr_time'] <=
                                max_stay_j + M * (2 - y[(j, tout)] - z[(j, tret)])), f"MaxStay_{j}_{tout}_{tret}"

            # Return the problem and variables for modification
            return prob, x, y, z

        # --- Iterative Solving Process ---
        prob, x, y, z = create_model()
        optimal_solutions = []
        solution_count = 0
        target_objective_value = None

        while True:
            prob.solve(pulp.PULP_CBC_CMD(msg=0))
            if pulp.LpStatus[prob.status] == 'Optimal':
                current_objective_value = pulp.value(prob.objective)
                if target_objective_value is None:
                    target_objective_value = current_objective_value
                    print(f"找到初始最优目标值: {target_objective_value}")

                if abs(current_objective_value - target_objective_value) < 1e-5:
                    solution_count += 1
                    print(f"\n--- 找到最优解 #{solution_count} ---")
                    solution_details = {'destination': None, 'outbound': None, 'return': None, 'cost': 0, 'objective': current_objective_value, 'stay': None}
                    vars_in_solution = []
                    selected_dest = None # 记录选中的目的地
                    selected_out_trip = None
                    selected_ret_trip = None

                    for j in destinations:
                        if x[j].varValue > 0.9:
                            solution_details['destination'] = j
                            selected_dest = j # 记录
                            vars_in_solution.append(x[j])
                            print(f"- 目的地: {j}")
                            cost = 0
                            for tout in outbound_trips[j]:
                                if y[(j, tout)].varValue > 0.9:
                                    solution_details['outbound'] = (tout, outbound_trips[j][tout]['cost'])
                                    selected_out_trip = tout # 记录
                                    vars_in_solution.append(y[(j, tout)])
                                    print(f"  - 去程车次: {tout} (成本: {outbound_trips[j][tout]['cost']})")
                                    cost += outbound_trips[j][tout]['cost']
                            for tret in return_trips[j]:
                                if z[(j, tret)].varValue > 0.9:
                                    solution_details['return'] = (tret, return_trips[j][tret]['cost'])
                                    selected_ret_trip = tret # 记录
                                    vars_in_solution.append(z[(j, tret)])
                                    print(f"  - 返程车次: {tret} (成本: {return_trips[j][tret]['cost']})")
                                    cost += return_trips[j][tret]['cost']
                            solution_details['cost'] = cost
                            print(f"总交通成本: {cost}")
                            # 计算并存储停留时间
                            if selected_out_trip and selected_ret_trip:
                                stay_duration = return_trips[j][selected_ret_trip]['dep_time'] - outbound_trips[j][selected_out_trip]['arr_time']
                                solution_details['stay'] = stay_duration
                                print(f"停留时间: {stay_duration} 小时")

                    optimal_solutions.append(solution_details)
                    prob += pulp.lpSum(v for v in vars_in_solution) <= (len(vars_in_solution) - 1), f"Exclude_Solution_{solution_count}"
                else:
                    print(f"\n找到次优解，目标值 {current_objective_value}。停止搜索。")
                    break
            else:
                print(f"\n求解器状态: {pulp.LpStatus[prob.status]}。未找到更多最优解。")
                break

        # --- Final Summary ---
        print("\n=============================================")
        if target_objective_value is not None:
            print(f"搜索完成。找到 {len(optimal_solutions)} 个最优解，目标值 {target_objective_value}")
        else:
            print("搜索完成。未找到可行解。")
        print("=============================================")

        # 表格化输出所有最优解
        table = []
        headers = ["目的地", "去程车次", "去程票价", "返程车次", "返程票价", "总交通成本", "停留时间(h)", "成本合规", "停留合规", "目标值"]
        for sol in optimal_solutions:
            dest = sol['destination']
            out_trip, out_cost = sol['outbound'] if sol['outbound'] else ("-", 0)
            ret_trip, ret_cost = sol['return'] if sol['return'] else ("-", 0)
            total_cost = sol['cost']
            stay = sol['stay'] if sol['stay'] is not None else "-"

            # 成本合规性检查
            cost_ok = "√" if total_cost <= budget else "×"

            # 停留时间合规性检查
            stay_ok = "×"
            if dest and stay != "-":
                min_stay_j = params[dest].get('min_stay_hours', 0)
                max_stay_j = params[dest].get('max_stay_hours', M)
                if min_stay_j <= stay <= max_stay_j:
                    stay_ok = "√"

            # 计算目标值 U - alpha * D
            objective = params[dest]['U'] - alpha * params[dest]['D']
            table.append([dest, out_trip, out_cost, ret_trip, ret_cost, total_cost, stay, cost_ok, stay_ok, f"{objective:.2f}"])

        # 额外验证信息
        print("\n--- 额外验证信息 ---")
        if not optimal_solutions:
            print("无最优解可供验证。")

        for idx, sol in enumerate(optimal_solutions, 1):
            dest = sol['destination']
            total_cost = sol['cost']
            stay = sol['stay']

            if total_cost > budget:
                print(f"警告：解{idx} ({dest}) 总交通成本 {total_cost} 超出预算 {budget}！")

            if dest and stay is not None:
                min_stay_j = params[dest].get('min_stay_hours', 0)
                max_stay_j = params[dest].get('max_stay_hours', M)
                if not (min_stay_j <= stay <= max_stay_j):
                    print(f"警告：解{idx} ({dest}) 停留时间 {stay:.1f}h 不在允许区间 [{min_stay_j}h, {max_stay_j}h]！")
            elif dest and stay is None and sol['outbound'] and sol['return']:
                print(f"警告：解{idx} ({dest}) 无法计算停留时间（可能缺少车次信息？）")

        if target_objective_value is not None:
            print(f"\n最优目标值（Weighted Utility）：{target_objective_value}")
        else:
            print("\n未找到最优目标值。")

        return table, headers

    except FileNotFoundError:
        messagebox.showerror("错误", f"找不到文件：{json_path}")
        return None, None
    except json.JSONDecodeError:
        messagebox.showerror("错误", f"JSON文件格式无效：{json_path}")
        return None, None
    except KeyError as e:
        messagebox.showerror("错误", f"JSON文件缺少必需的键: {e}")
        return None, None
    except Exception as e:
        messagebox.showerror("错误", f"处理文件时发生错误：{e}")
        return None, None

def show_result_in_window(table_data, headers):
    if not table_data or not headers:
        return
        
    win = tk.Tk()
    win.title("优化结果")
    
    # 添加参数设置区域
    param_frame = tk.LabelFrame(win, text="参数设置", padx=10, pady=5)
    param_frame.pack(fill="x", padx=10, pady=5)
    
    # 创建参数输入框
    params = {
        'alpha': tk.DoubleVar(value=1.0),
        'budget': tk.IntVar(value=1200),
        'W_out_start': tk.IntVar(value=0),
        'W_out_end': tk.IntVar(value=24),
        'W_ret_start': tk.IntVar(value=72),
        'W_ret_end': tk.IntVar(value=120)
    }
    
    # 第一行参数
    row1 = tk.Frame(param_frame)
    row1.pack(fill="x", pady=2)
    tk.Label(row1, text="惩罚系数(α):").pack(side="left")
    tk.Entry(row1, textvariable=params['alpha'], width=8).pack(side="left", padx=5)
    tk.Label(row1, text="交通预算:").pack(side="left", padx=(20,0))
    tk.Entry(row1, textvariable=params['budget'], width=8).pack(side="left", padx=5)
    
    # 第二行参数
    row2 = tk.Frame(param_frame)
    row2.pack(fill="x", pady=2)
    tk.Label(row2, text="出发时间窗口:").pack(side="left")
    tk.Entry(row2, textvariable=params['W_out_start'], width=4).pack(side="left", padx=2)
    tk.Label(row2, text="至").pack(side="left")
    tk.Entry(row2, textvariable=params['W_out_end'], width=4).pack(side="left", padx=2)
    tk.Label(row2, text="小时").pack(side="left")
    
    # 第三行参数
    row3 = tk.Frame(param_frame)
    row3.pack(fill="x", pady=2)
    tk.Label(row3, text="返程时间窗口:").pack(side="left")
    tk.Entry(row3, textvariable=params['W_ret_start'], width=4).pack(side="left", padx=2)
    tk.Label(row3, text="至").pack(side="left")
    tk.Entry(row3, textvariable=params['W_ret_end'], width=4).pack(side="left", padx=2)
    tk.Label(row3, text="小时").pack(side="left")
    
    # 添加文件选择框和按钮
    file_frame = tk.Frame(win)
    file_frame.pack(padx=10, pady=5, fill="x")
    
    tk.Label(file_frame, text="选择JSON数据文件:").pack(side="left")
    json_path_var = tk.StringVar(value="edited_travel_data.json")
    entry = tk.Entry(file_frame, textvariable=json_path_var, width=40)
    entry.pack(side="left", padx=5)
    
    def browse():
        path = filedialog.askopenfilename(filetypes=[("JSON文件", "*.json")])
        if path:
            json_path_var.set(path)
            
    def solve():
        try:
            # 获取参数值
            global alpha, budget, W_out_start, W_out_end, W_ret_start, W_ret_end
            alpha = params['alpha'].get()
            budget = params['budget'].get()
            W_out_start = params['W_out_start'].get()
            W_out_end = params['W_out_end'].get()
            W_ret_start = params['W_ret_start'].get()
            W_ret_end = params['W_ret_end'].get()
            
            # 参数验证
            if not (0 <= W_out_start < W_out_end <= 24):
                raise ValueError("出发时间窗口无效")
            if not (0 <= W_ret_start < W_ret_end <= 168):  # 一周168小时
                raise ValueError("返程时间窗口无效")
            if alpha < 0:
                raise ValueError("惩罚系数必须为非负数")
            if budget <= 0:
                raise ValueError("预算必须为正数")
                
            table, headers = load_json_and_solve(json_path_var.get())
            if table and headers:
                # 清除现有内容
                for item in tree.get_children():
                    tree.delete(item)
                # 插入新数据
                for row in table:
                    tree.insert("", tk.END, values=row)
        except ValueError as e:
            messagebox.showerror("参数错误", str(e))
        except Exception as e:
            messagebox.showerror("错误", f"求解过程出错：{str(e)}")
    
    tk.Button(file_frame, text="浏览", command=browse).pack(side="left", padx=5)
    tk.Button(file_frame, text="求解", command=solve).pack(side="left", padx=5)
    
    # 创建表格
    tree = ttk.Treeview(win, columns=headers, show="headings", height=min(20, len(table_data)+1))
    for h in headers:
        tree.heading(h, text=h)
        tree.column(h, width=110, anchor="center")
    for row in table_data:
        tree.insert("", tk.END, values=row)
    tree.pack(expand=True, fill="both", padx=10, pady=5)
    
    # 关闭按钮
    btn = tk.Button(win, text="关闭", command=win.destroy)
    btn.pack(pady=8)
    
    win.mainloop()

# 全局变量初始化
alpha = 1.0      # Difficulty weight
budget = 1200    # Max **交通** budget
W_out_start = 0
W_out_end = 24
W_ret_start = 72
W_ret_end = 120

if __name__ == "__main__":
    # 默认加载edited_travel_data.json
    table, headers = load_json_and_solve("edited_travel_data.json")
    if table and headers:
        try:
            table_str = tabulate(table, headers, tablefmt="grid", stralign="center")
            print(table_str)
            show_result_in_window(table, headers)
        except Exception as e:
            print(f"\n输出结果时发生错误: {e}")
            print("尝试仅在控制台打印原始数据:")
            for row in table:
                print(row)
