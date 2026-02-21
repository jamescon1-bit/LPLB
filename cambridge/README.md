# Cambridge NY Commercial Landscaping Modules

AI-powered business modules for Cambridge NY commercial landscaping operations in New York City.

## Overview

This directory contains specialized AI modules designed for a commercial landscaping company based in Cambridge, NY, serving high-end commercial clients throughout New York City. Each module addresses critical business functions with intelligent automation and data-driven insights.

## Modules

### 🏢 Commercial Operations

**crew_balancer.py** - Intelligent Crew Scheduling & Resource Optimization
- AI-powered crew assignment optimization
- Multi-constraint scheduling (skills, certifications, travel time)
- Real-time workload balancing across NYC locations
- Resource utilization analytics and crew performance tracking

**inventory_optimizer.py** - Smart Supply Chain Management  
- Predictive inventory management with seasonal demand forecasting
- Automated reorder point calculations for plants and materials
- Supplier performance analytics and cost optimization
- Weather-aware inventory adjustments

**pricing_engine.py** - Dynamic Commercial Pricing Calculator
- Intelligent pricing for 5 service lines: landscaping, holiday decor, plant maintenance, rentals, lobby flowers
- Real-time cost calculations including materials, labor, travel, and seasonal premiums
- Professional quote generation with itemized breakdowns
- Per-plant pricing database with wholesale/retail/rental rates

## Key Features

### 🎯 NYC Commercial Focus
- Optimized for Manhattan, Brooklyn, Queens commercial districts
- Travel time calculations between Cambridge NY base and client locations
- NYC-specific regulations and permit tracking
- Holiday decor with 40% seasonal premiums (Nov-Jan)

### 💰 Financial Intelligence
- Dynamic pricing based on market conditions and project complexity
- Profit margin analysis and budget variance tracking
- Cost optimization across labor, materials, and transportation
- Professional quote generation with tax calculations (NYC 8.875%)

### 🌿 Industry Specialization
- Commercial plant rental and maintenance programs
- Weekly lobby flower arrangements (Standard $150, Premium $275, Luxury $450)
- Holiday decoration installations for corporate clients
- Interior plant maintenance with bi-weekly service cycles

## Usage Examples

### Pricing Engine
```python
from cambridge.pricing_engine import CambridgePricingEngine, ServiceType, PricingTier

engine = CambridgePricingEngine()

# Calculate plant rental quote
plant_requests = {
    'fiddle_leaf_large': 2,
    'snake_plant_large': 4,
    'pothos_medium': 6
}

rental_items = engine.calculate_plant_rental_quote(
    plant_requests=plant_requests,
    weeks_duration=12,
    distance_miles=25.0,
    maintenance_included=True
)

quote = engine.generate_quote(
    client_name="Madison Square Garden Corp",
    project_name="Executive Offices Plant Rental",
    service_type=ServiceType.PLANT_RENTALS,
    line_items=rental_items
)

print(engine.format_quote(quote))
```

### Crew Balancer
```python
from cambridge.crew_balancer import CrewBalancer

balancer = CrewBalancer()

# Optimize crew assignments for the day
assignments = balancer.optimize_daily_assignments(
    date=date.today(),
    priority_clients=["Goldman Sachs", "One World Trade Center"]
)

print(f"Optimized assignments for {len(assignments)} projects")
```

### Inventory Optimizer
```python
from cambridge.inventory_optimizer import InventoryOptimizer

optimizer = InventoryOptimizer()

# Check reorder requirements
reorder_items = optimizer.check_reorder_points()
print(f"Need to reorder {len(reorder_items)} items")

# Seasonal demand forecast
forecast = optimizer.forecast_seasonal_demand(months_ahead=3)
```

## Integration

These modules integrate with:
- **Project management systems** for scheduling and resource allocation
- **Financial systems** for pricing and invoicing
- **Inventory management** for supply chain optimization
- **Customer relationship management** for client communications

## Data Models

### Plant Catalog
- Botanical names and common names
- Wholesale costs and retail pricing
- Weekly rental rates and maintenance requirements
- Common usage scenarios (lobby, office, low-light)

### Service Categories
- Commercial landscaping design and installation
- Holiday decoration projects (seasonal premium pricing)
- Interior plant maintenance programs
- Plant rental services (short-term and long-term)
- Weekly lobby flower arrangements

### Pricing Tiers
- **Standard**: $150/week lobby arrangements
- **Premium**: $275/week with seasonal rotation
- **Luxury**: $450/week with exotic flowers and premium service

## Technical Requirements

- Python 3.8+
- Dependencies: `dataclasses`, `decimal`, `datetime`, `enum`, `typing`
- Optional: `numpy`, `pandas` for advanced analytics

## Cambridge NY Context

**Location**: Cambridge, Washington County, NY (45 minutes north of Albany)
**Service Area**: New York City commercial district
**Specialization**: High-end commercial landscaping and plant services
**Peak Season**: November-January (holiday decorations with 40% premium)
**Target Clients**: Fortune 500 companies, major real estate developments, prestigious office buildings

## Support

For questions or issues with these modules, contact the Cambridge NY AI development team.