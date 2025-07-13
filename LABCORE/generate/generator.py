import pandas as pd
import json
import random
import os

class LotteryGenerator:
    def __init__(self, draws_df, config_core, config_softpool, config_quotas, pool_stats):
        self.draws_df = draws_df
        self.config_core = config_core
        self.config_softpool = config_softpool
        self.config_quotas = config_quotas
        self.pool_stats = pool_stats

        self.base_quota_matrix = {
            "2-2-2|2H-2M-2C": 20.0,
            "3-2-1|3H-2M-1C": 15.0,
            "1-2-3|1H-2M-3C": 10.0,
            "2-3-1|2H-3M-1C": 15.0,
            "1-3-2|1H-3M-2C": 14.0,
            "3-1-2|3H-1M-2C": 12.0,
            "4-1-1|4H-1M-1C": 8.0,
            "1-4-1|1H-4M-1C": 7.0,
            "1-1-4|1H-1M-4C": 6.0,
            "2-1-3|2H-1M-3C": 5.0,
            "3-3-0|3H-3M-0C": 4.0,
            "0-3-3|0H-3M-3C": 3.0
        }
        
        self._ensure_pool_stats_zones()

    def _ensure_pool_stats_zones(self):
        all_numbers = set(range(1, 53))
        for num in all_numbers:
            num_str = str(num)
            if num_str not in self.pool_stats:
                self.pool_stats[num_str] = {
                    "frequency": 0.0, "last_seen": 999, "avg_interval": 0.0,
                    "std_interval": 0.0, "psw": 0.0, "zone": "Sleepy"
                }
            if "zone" not in self.pool_stats[num_str]:
                self.pool_stats[num_str]["zone"] = "Sleepy"


    def get_numbers_by_softpool_zone(self, zone_type):
        if zone_type == "H":
            return self.config_softpool.get("H_zone", [])
        elif zone_type == "M":
            return self.config_softpool.get("M_zone", [])
        elif zone_type == "L":
            return self.config_softpool.get("L_zone", [])
        else:
            return []

    def get_numbers_by_dynamic_zone(self, zone_name):
        numbers = []
        for num_str, stats in self.pool_stats.items():
            if stats.get("zone") == zone_name:
                numbers.append(int(num_str))
        return numbers

    def generate_combinations(self, num_combinations):
        generated_combinations = []
        excluded_numbers = set(self.config_softpool.get("exclude", []))

        all_available_numbers = [n for n in range(1, 53) if n not in excluded_numbers]
        
        if len(all_available_numbers) < 6:
            raise ValueError("Недостаточно доступных чисел для генерации комбинаций после исключения.")

        for _ in range(num_combinations):
            combination = self._generate_single_combination(all_available_numbers)
            generated_combinations.append(combination)
        
        return generated_combinations

    def _generate_single_combination(self, all_available_numbers):
        combination = []
        
        h_quota_percent = self.config_quotas.get("H", 0)
        m_quota_percent = self.config_quotas.get("M", 0)
        c_quota_percent = self.config_quotas.get("C", 0)

        num_h_target = round(6 * (h_quota_percent / 100))
        num_m_target = round(6 * (m_quota_percent / 100))
        num_c_target = 6 - num_h_target - num_m_target

        current_total = num_h_target + num_m_target + num_c_target
        while current_total != 6:
            if current_total > 6:
                if num_h_target > 0 and (num_h_target >= num_m_target and num_h_target >= num_c_target):
                    num_h_target -= 1
                elif num_m_target > 0 and (num_m_target >= num_h_target and num_m_target >= num_c_target):
                    num_m_target -= 1
                elif num_c_target > 0:
                    num_c_target -= 1
            else:
                if num_h_target < 6 and (num_h_target <= num_m_target and num_h_target <= num_c_target):
                    num_h_target += 1
                elif num_m_target < 6 and (num_m_target <= num_h_target and num_m_target <= num_c_target):
                    num_m_target += 1
                elif num_c_target < 6:
                    num_c_target += 1
            current_total = num_h_target + num_m_target + num_c_target
        
        temp_combination = set()
        
        def safe_sample(population, k, chosen_set):
            available = [n for n in population if n not in chosen_set]
            if len(available) >= k:
                return random.sample(available, k)
            else:
                return available

        hot_pool_all = set(self.get_numbers_by_dynamic_zone("Hot")) & set(all_available_numbers)
        warm_pool_all = set(self.get_numbers_by_dynamic_zone("Warm")) & set(all_available_numbers)
        cold_pool_all = set(self.get_numbers_by_dynamic_zone("Cold")) & set(all_available_numbers)
        sleepy_pool_all = set(self.get_numbers_by_dynamic_zone("Sleepy")) & set(all_available_numbers)

        h_candidates = list(hot_pool_all)
        m_candidates = list(warm_pool_all)
        c_candidates = list(cold_pool_all | sleepy_pool_all)
        
        selected_h = safe_sample(h_candidates, num_h_target, temp_combination)
        temp_combination.update(selected_h)
        
        selected_m = safe_sample(m_candidates, num_m_target, temp_combination)
        temp_combination.update(selected_m)

        selected_c = safe_sample(c_candidates, num_c_target, temp_combination)
        temp_combination.update(selected_c)

        remaining_count = 6 - len(temp_combination)
        if remaining_count > 0:
            remaining_available = [n for n in all_available_numbers if n not in temp_combination]
            if len(remaining_available) >= remaining_count:
                temp_combination.update(random.sample(remaining_available, remaining_count))
            else:
                temp_combination.update(remaining_available)
        
        combination = list(temp_combination)
        
        if len(combination) < 6:
            all_possible = list(set(range(1, 53)) - excluded_numbers)
            while len(combination) < 6:
                chosen = random.choice(all_possible)
                if chosen not in combination:
                    combination.append(chosen)

        combination = combination[:6]
        combination.sort()
        return combination