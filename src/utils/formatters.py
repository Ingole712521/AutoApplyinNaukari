from __future__ import annotations
import json
from typing import Any

def format_salary(value: Any) -> str:
    if value is None:
        return 'Not disclosed'
    if isinstance(value, str):
        return value.strip() or 'Not disclosed'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        if value.get('hideSalary'):
            return 'Not disclosed'
        mn = value.get('minimumSalary') or 0
        mx = value.get('maximumSalary') or 0
        currency = value.get('currency', 'INR')
        if mn and mx and (mn != mx):
            return f'{mn}-{mx} {currency}'
        if mx:
            return f'{mx} {currency}'
        if mn:
            return f'{mn} {currency}'
        return 'Not disclosed'
    return str(value)

def excel_cell_value(value: Any) -> str | int | float | bool | None:
    if value is None:
        return ''
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        if 'minimumSalary' in value or 'maximumSalary' in value or 'hideSalary' in value:
            return format_salary(value)
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple, set)):
        return ', '.join((str(v) for v in value))
    return str(value)
