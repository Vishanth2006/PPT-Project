def get_default_cartridge_specs():
    """
    Returns default specs for CMYK cartridges:
    - Price ($)
    - Volume (ml)
    """
    return {
        "cyan": {"price": 19.99, "volume": 12.0},
        "magenta": {"price": 19.99, "volume": 12.0},
        "yellow": {"price": 19.99, "volume": 12.0},
        "black": {"price": 29.99, "volume": 18.0}
    }

def calculate_page_ink_usage(page_area_m2, cyan_cov, mag_cov, yel_cov, blk_cov, cartridge_specs, consumption_rate_ml_m2=1.5):
    """
    Calculates the ink usage in ml and cost in $ for a single page.
    
    Formula:
    Ink Volume (ml) = Area (m2) * (Coverage % / 100) * Ink Consumption Rate (ml/m2)
    Ink Cost ($) = Ink Volume (ml) * (Cartridge Price / Cartridge Volume)
    """
    usages = {}
    costs = {}
    
    channels = {
        "cyan": cyan_cov,
        "magenta": mag_cov,
        "yellow": yel_cov,
        "black": blk_cov
    }
    
    for chan, cov in channels.items():
        spec = cartridge_specs.get(chan, {"price": 20.0, "volume": 15.0})
        price = spec["price"]
        vol_capacity = spec["volume"]
        
        # Calculate volume in ml
        vol_used = page_area_m2 * (cov / 100.0) * consumption_rate_ml_m2
        usages[chan] = vol_used
        
        # Calculate cost
        cost = vol_used * (price / vol_capacity) if vol_capacity > 0 else 0.0
        costs[chan] = cost
        
    total_vol = sum(usages.values())
    total_cost = sum(costs.values())
    
    return {
        "usages": usages,
        "costs": costs,
        "total_volume": total_vol,
        "total_cost": total_cost
    }

def estimate_document_printing_costs(page_results, cartridge_specs, consumption_rate_ml_m2=1.5):
    """
    Iterates over all page results and calculates costs/volumes for each page and overall.
    Updates page_results in-place or returns stats dictionaries.
    """
    detailed_costs = []
    
    doc_totals = {
        "cyan_vol": 0.0, "magenta_vol": 0.0, "yellow_vol": 0.0, "black_vol": 0.0,
        "cyan_cost": 0.0, "magenta_cost": 0.0, "yellow_cost": 0.0, "black_cost": 0.0,
        "total_vol": 0.0,
        "total_cost": 0.0
    }
    
    for page in page_results:
        metrics = calculate_page_ink_usage(
            page_area_m2=page["area_m2"],
            cyan_cov=page["cyan"],
            mag_cov=page["magenta"],
            yel_cov=page["yellow"],
            blk_cov=page["black"],
            cartridge_specs=cartridge_specs,
            consumption_rate_ml_m2=consumption_rate_ml_m2
        )
        
        page_metrics = {
            "page_num": page["page_num"],
            "cyan_vol": metrics["usages"]["cyan"],
            "magenta_vol": metrics["usages"]["magenta"],
            "yellow_vol": metrics["usages"]["yellow"],
            "black_vol": metrics["usages"]["black"],
            "cyan_cost": metrics["costs"]["cyan"],
            "magenta_cost": metrics["costs"]["magenta"],
            "yellow_cost": metrics["costs"]["yellow"],
            "black_cost": metrics["costs"]["black"],
            "total_vol": metrics["total_volume"],
            "total_cost": metrics["total_cost"]
        }
        
        detailed_costs.append(page_metrics)
        
        # Add to document totals
        doc_totals["cyan_vol"] += page_metrics["cyan_vol"]
        doc_totals["magenta_vol"] += page_metrics["magenta_vol"]
        doc_totals["yellow_vol"] += page_metrics["yellow_vol"]
        doc_totals["black_vol"] += page_metrics["black_vol"]
        
        doc_totals["cyan_cost"] += page_metrics["cyan_cost"]
        doc_totals["magenta_cost"] += page_metrics["magenta_cost"]
        doc_totals["yellow_cost"] += page_metrics["yellow_cost"]
        doc_totals["black_cost"] += page_metrics["black_cost"]
        
        doc_totals["total_vol"] += page_metrics["total_vol"]
        doc_totals["total_cost"] += page_metrics["total_cost"]
        
    return detailed_costs, doc_totals
