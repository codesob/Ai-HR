def calculate_net_salary(annual_base: float) -> tuple[float, float, float]:
    gross_monthly = annual_base / 12
    # Simple progressive tax logic stub
    if gross_monthly < 3000:
        tax_rate = 0.1
    elif gross_monthly < 7000:
        tax_rate = 0.2
    else:
        tax_rate = 0.3
        
    tax_deduction = gross_monthly * tax_rate
    net_amount = gross_monthly - tax_deduction
    return gross_monthly, tax_deduction, net_amount
