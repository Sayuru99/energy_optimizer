from typing import List, Dict
from app.models.machine import Machine
from app.models.tariff import Tariff
from app.services.optimizer import get_rate_at, time_to_minutes

def calculate_current_cost(
    machines: List[Machine],
    current_schedules: List[Dict],
    tariffs: List[Tariff]
) -> float:
    total = 0.0
    for schedule in current_schedules:
        machine = next((m for m in machines if m.id == schedule["machine_id"]), None)
        if not machine:
            continue
        total_power = machine.quantity * machine.power_kw
        start_m = time_to_minutes(schedule["start"])
        end_m = time_to_minutes(schedule["end"])
        duration_h = (end_m - start_m) / 60
        for minute in range(start_m, end_m, 30):
            rate = get_rate_at(minute, tariffs)
            total += total_power * 0.5 * rate
    return round(total, 2)