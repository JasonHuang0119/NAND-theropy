import re
import os
from collections import defaultdict

def extract_position(text):
    """提取 Ch, CE, Block, Plane, WL 資訊"""
    pattern = r"Ch=(\w+),CE=(\w+),Block=(\w+),Plane=(\w+),WL=(\w+)"
    match = re.search(pattern, text)
    if match:
        return {
            'Ch': match.group(1), 'CE': match.group(2),
            'Block': match.group(3), 'Plane': match.group(4),
            'WL': match.group(5), 'RawText': text
        }
    return None

def process_single_file(input_file):
    """處理單一檔案並依據 TOP & Plane 03 & WL 1089 區分四個區段統計 FFFF"""
    if not os.path.exists(input_file):
        print(f"錯誤：找不到輸入檔案 '{input_file}'")
        return None

    results_lines = []
    ffff_intervals = [] # 儲存四個區間的統計結果
    plane_data = []
    
    # 區間暫存計數器
    current_interval_ffff = 0 
    interval_id = 0

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 只處理包含數據的有效區塊
        if "MinFBC_SAR_order" in line:
            chunk = lines[i:i+3]
            if len(chunk) < 3: break
            
            chunk_cleaned = [l.strip() for l in chunk]
            results_lines.append("\n".join(chunk_cleaned))
            
            # 1. 統計這 3 行內的 FFFF 次數並累計到當前區間
            chunk_text = "".join(chunk_cleaned)
            current_interval_ffff += chunk_text.count("FFFF")
            
            second_line = chunk_cleaned[1]
            pos = extract_position(second_line)
            
            if pos:
                # 2. 判斷區間結算條件：TOP & Plane 03 & WL 1089
                if "TOP" in second_line and pos['Plane'] == "03" and pos['WL'] == "1089":
                    interval_id += 1
                    # 紀錄該區間結果
                    ffff_intervals.append({
                        'Interval': interval_id,
                        'EndPos': f"Ch:{pos['Ch']}, CE:{pos['CE']}, Block:{pos['Block']}, Plane:{pos['Plane']}, WL:{pos['WL']}",
                        'Count': current_interval_ffff
                    })
                    # --- 重要：結算後重置區間計數器 ---
                    current_interval_ffff = 0 

                # 3. 收集 Plane 數據用於 Worst WL 分析
                if "TOP" in second_line:
                    third_line = chunk_cleaned[2]
                    err_match = re.search(r"RawErrBit\s*:\s*ECC\s*=\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+)", third_line)
                    if err_match:
                        errors = [int(err_match.group(j)) for j in range(1, 5)]
                        plane_data.append({
                            'Plane': int(pos['Plane']),
                            'WL': pos['WL'],
                            'MaxErr': max(errors),
                            'AllErr': errors,
                            'Source': os.path.basename(input_file)
                        })
            i += 3
        else:
            i += 1
            
    return results_lines, ffff_intervals, plane_data

def merge_and_analyze_multiple_files(file_list, top_n=10):
    all_results_lines = []
    all_ffff_summary = []
    global_plane_groups = defaultdict(list)
    
    # 建立輸出目錄與檔名
    output_dir = os.path.dirname(file_list[0])
    merged_output_file = os.path.join(output_dir, "Merged_Analysis_Report.txt")

    print(f"--- 開始合併解析 {len(file_list)} 個檔案 ---")

    for file_path in file_list:
        file_data = process_single_file(file_path)
        if file_data:
            res_lines, intervals, p_data = file_data
            all_results_lines.extend(res_lines)
            
            # 整理區間數據到總表
            for inter in intervals:
                inter['FileName'] = os.path.basename(file_path)
                all_ffff_summary.append(inter)

            for item in p_data:
                global_plane_groups[item['Plane']].append(item)
            
            print(f"已完成讀取: {os.path.basename(file_path)}，共偵測到 {len(intervals)} 個區間。")

    # --- 寫入合併後的總檔案 ---
    with open(merged_output_file, 'w', encoding='utf-8') as f_out:
        f_out.write("=== [區間 FFFF 統計報告] ===\n")
        f_out.write(f"{'來源檔案':<34} | {'區間':<3} | {'FFFF 次數':<8} | {'結算位置'}\n")
        f_out.write("-" * 90 + "\n")
        
        total_sum = 0
        for item in all_ffff_summary:
            f_out.write(f"{item['FileName']:<30} | {item['Interval']:<5} | {item['Count']:<10} | {item['EndPos']}\n")
            total_sum += item['Count']
        
        f_out.write("-" * 90 + "\n")
        f_out.write(f"所有檔案累計 FFFF 總計: {total_sum} 次\n\n")

        f_out.write("=== 完整過濾數據清單 ===\n")
        f_out.write("\n".join(all_results_lines))

    # --- Console 總結報告 ---
    print(f"\n[合併解析完成]")
    print(f"1. 總合併報告已儲存至: {merged_output_file}")

    if global_plane_groups:
        print(f"\n{'='*80}")
        print(f"   Combined Worst {top_n} WL Per Plane (Across All Files)")
        print(f"{'='*80}")
        for plane in sorted(global_plane_groups.keys()):
            print(f"\n[ Plane {plane} ]")
            print(f"{'-'*80}")
            print(f"{'Rank':<5} | {'WL (Dec)':<8} | {'Max Err':<7} | {'ECC Details'}")
            print(f"{'-'*80}")
            
            sorted_data = sorted(global_plane_groups[plane], key=lambda x: x['MaxErr'], reverse=True)
            for rank, data in enumerate(sorted_data[:top_n], 1):
                err_str = ", ".join(f"{x:3}" for x in data['AllErr'])
                print(f"#{rank:<4} | {data['WL']:<8} | {data['MaxErr']:<7} | [{err_str}]")
        print(f"{'='*80}")

if __name__ == "__main__":
    target_files = [
        r"C:\Users\Robbie\Desktop\Default_Read_levle\BRD_SAR\SAR\BRD_EOL\80k\DIC65666768\BRD80k_dic65666768_total.txt"
    ]
    
    merge_and_analyze_multiple_files(target_files, top_n=10)