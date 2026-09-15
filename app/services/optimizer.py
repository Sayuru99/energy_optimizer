from datetime import time
from typing import List, Dict
import pulp
from app.models.machine import Machine
from app.models.tariff import Tariff

def time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute

def minutes_to_time(m: int) -> time:
    h = m // 60
    mi = m % 60
    if h >= 24:
        h = h % 24
    return time(h, mi)

def get_rate_at(minute: int, tariffs: List[Tariff]) -> float:
    for tariff in tariffs:
        start = time_to_minutes(tariff.start_time)
        end = time_to_minutes(tariff.end_time)
        if start < end:
            if start <= minute < end:
                return tariff.rate_per_kwh
        else:
            if minute >= start or minute < end:
                return tariff.rate_per_kwh
    return 25.0

def optimize_schedule(
    machines: List[Machine],
    tariffs: List[Tariff],
    factory_start: time,
    factory_end: time,
    slot_minutes: int = 30
) -> List[Dict]:
    results = []
    factory_start_m = time_to_minutes(factory_start)
    factory_end_m = time_to_minutes(factory_end)

    for machine in machines:
        total_power = machine.quantity * machine.power_kw
        required_slots = int(round(machine.required_hours * 60 / slot_minutes))
        if required_slots <= 0:
            continue

        avail_start = max(time_to_minutes(machine.available_start), factory_start_m)
        avail_end = min(time_to_minutes(machine.available_end), factory_end_m)

        possible_starts = list(range(avail_start, avail_end - required_slots * slot_minutes + 1, slot_minutes))
        if not possible_starts:
            continue

        prob = pulp.LpProblem(f"opt_machine_{machine.id}", pulp.LpMinimize)
        start_vars = pulp.LpVariable.dicts("start", possible_starts, cat="Binary")
        prob += pulp.lpSum([start_vars[s] for s in possible_starts]) == 1

        cost_terms = []
        for s in possible_starts:
            cost = 0.0
            for i in range(required_slots):
                minute = s + i * slot_minutes
                rate = get_rate_at(minute, tariffs)
                cost += total_power * (slot_minutes / 60.0) * rate
            cost_terms.append(cost * start_vars[s])
        prob += pulp.lpSum(cost_terms)

        status = prob.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=10))
        if pulp.LpStatus[status] != "Optimal":
            continue

        chosen = None
        for s in possible_starts:
            if pulp.value(start_vars[s]) is not None and pulp.value(start_vars[s]) > 0.5:
                chosen = s
                break
        if chosen is None:
            continue

        start_t = minutes_to_time(chosen)
        end_t = minutes_to_time(chosen + required_slots * slot_minutes)
        energy = round(total_power * machine.required_hours, 2)
        cost = 0.0
        for i in range(required_slots):
            minute = chosen + i * slot_minutes
            rate = get_rate_at(minute, tariffs)
            cost += total_power * (slot_minutes / 60.0) * rate

        results.append({
            "machine_id": machine.id,
            "machine_name": machine.name,
            "scheduled_start": start_t,
            "scheduled_end": end_t,
            "energy_kwh": energy,
            "cost": round(cost, 2),
            "total_power_kw": total_power,
            "required_hours": machine.required_hours
        })
    return results