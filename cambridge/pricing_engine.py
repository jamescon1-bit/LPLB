"""
Cambridge NY Commercial Landscaping - Dynamic Pricing Engine
Handles pricing calculations for plant services, maintenance, rentals, and landscaping across NYC boroughs.
"""

from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math

class ServiceType(Enum):
    INTERIOR_PLANT_MAINTENANCE = "interior_plant_maintenance"
    PLANT_RENTALS = "plant_rentals"
    HOLIDAY_DECOR = "holiday_decor"
    WEEKLY_LOBBY_FLOWERS = "weekly_lobby_flowers"
    COMMERCIAL_LANDSCAPING = "commercial_landscaping"

class ServiceTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver" 
    GOLD = "gold"

class Borough(Enum):
    MANHATTAN = "manhattan"
    BROOKLYN = "brooklyn"
    QUEENS = "queens"
    BRONX = "bronx"
    STATEN_ISLAND = "staten_island"

@dataclass
class QuoteLineItem:
    description: str
    quantity: int
    unit_price: float
    total: float
    category: str

@dataclass
class QuoteBreakdown:
    line_items: List[QuoteLineItem]
    subtotal: float
    tax_rate: float
    tax_amount: float
    delivery_fee: float
    seasonal_premium: float
    total: float
    service_tier: ServiceTier
    valid_until: date

class PricingEngine:
    """Dynamic pricing calculator for Cambridge NY commercial landscaping services."""
    
    # Base crew rates (per hour)
    CREW_RATES = {
        ServiceTier.BRONZE: 45.00,
        ServiceTier.SILVER: 55.00,
        ServiceTier.GOLD: 65.00
    }
    
    # NYC travel time between boroughs (in hours)
    TRAVEL_TIMES = {
        Borough.MANHATTAN: {
            Borough.BROOKLYN: 0.75,
            Borough.QUEENS: 1.0,
            Borough.BRONX: 0.5,
            Borough.STATEN_ISLAND: 1.5
        },
        Borough.BROOKLYN: {
            Borough.MANHATTAN: 0.75,
            Borough.QUEENS: 1.25,
            Borough.BRONX: 1.5,
            Borough.STATEN_ISLAND: 1.0
        },
        Borough.QUEENS: {
            Borough.MANHATTAN: 1.0,
            Borough.BROOKLYN: 1.25,
            Borough.BRONX: 1.0,
            Borough.STATEN_ISLAND: 1.75
        },
        Borough.BRONX: {
            Borough.MANHATTAN: 0.5,
            Borough.BROOKLYN: 1.5,
            Borough.QUEENS: 1.0,
            Borough.STATEN_ISLAND: 2.0
        },
        Borough.STATEN_ISLAND: {
            Borough.MANHATTAN: 1.5,
            Borough.BROOKLYN: 1.0,
            Borough.QUEENS: 1.75,
            Borough.BRONX: 2.0
        }
    }
    
    # Base service pricing templates
    SERVICE_PRICING = {
        ServiceType.INTERIOR_PLANT_MAINTENANCE: {
            "base_monthly": 200,  # For 10-15 plants
            "per_plant": 15,
            "max_monthly": 800,
            "labor_hours": 2.0
        },
        ServiceType.PLANT_RENTALS: {
            "small_plant_monthly": 35,
            "medium_plant_monthly": 55, 
            "large_plant_monthly": 85,
            "premium_plant_monthly": 125,
            "setup_fee": 50,
            "labor_hours": 1.0
        },
        ServiceType.HOLIDAY_DECOR: {
            "base_installation": 500,
            "per_sq_ft": 8,
            "premium_materials": 15,  # per sq ft
            "labor_hours": 6.0,
            "seasonal_markup": 0.4  # 40% markup Nov-Jan
        },
        ServiceType.WEEKLY_LOBBY_FLOWERS: {
            "bronze_weekly": 150,
            "silver_weekly": 275,
            "gold_weekly": 500,
            "labor_hours": 0.75
        },
        ServiceType.COMMERCIAL_LANDSCAPING: {
            "design_fee": 750,
            "per_sq_ft": 12,
            "maintenance_monthly": 300,
            "labor_hours": 8.0
        }
    }
    
    def __init__(self, base_location: Borough = Borough.MANHATTAN):
        """Initialize pricing engine with base location (Cambridge NY serves NYC from here)."""
        self.base_location = base_location
        self.tax_rate = 0.08875  # NYC sales tax rate
        
    def _is_holiday_season(self, quote_date: date = None) -> bool:
        """Check if date falls in holiday season (Nov-Jan)."""
        if not quote_date:
            quote_date = date.today()
        return quote_date.month in [11, 12, 1]
    
    def _calculate_travel_cost(self, target_borough: Borough, service_tier: ServiceTier) -> float:
        """Calculate travel cost based on distance and crew rate."""
        if target_borough == self.base_location:
            return 0.0
        
        travel_hours = self.TRAVEL_TIMES[self.base_location].get(target_borough, 1.0)
        crew_rate = self.CREW_RATES[service_tier]
        return travel_hours * crew_rate
    
    def _calculate_delivery_fee(self, target_borough: Borough, service_value: float) -> float:
        """Calculate delivery fee based on location and order value."""
        base_fee = 75.0
        
        if target_borough == self.base_location:
            base_fee = 25.0
        elif target_borough in [Borough.BROOKLYN, Borough.QUEENS]:
            base_fee = 50.0
        
        # Free delivery for orders over $500
        if service_value > 500:
            base_fee *= 0.5
        
        return base_fee
    
    def calculate_interior_plant_maintenance(self, 
                                           plant_count: int,
                                           service_tier: ServiceTier,
                                           target_borough: Borough,
                                           monthly_visits: int = 4) -> QuoteBreakdown:
        """Calculate monthly interior plant maintenance pricing."""
        pricing = self.SERVICE_PRICING[ServiceType.INTERIOR_PLANT_MAINTENANCE]
        
        # Base pricing calculation
        if plant_count <= 15:
            base_cost = pricing["base_monthly"]
        else:
            base_cost = min(pricing["base_monthly"] + (plant_count - 15) * pricing["per_plant"], 
                           pricing["max_monthly"])
        
        # Tier multipliers
        tier_multipliers = {
            ServiceTier.BRONZE: 1.0,
            ServiceTier.SILVER: 1.3,
            ServiceTier.GOLD: 1.6
        }
        service_cost = base_cost * tier_multipliers[service_tier]
        
        # Labor cost
        labor_hours = pricing["labor_hours"] * monthly_visits
        crew_rate = self.CREW_RATES[service_tier]
        labor_cost = labor_hours * crew_rate
        
        # Travel cost  
        travel_cost = self._calculate_travel_cost(target_borough, service_tier) * monthly_visits
        
        line_items = [
            QuoteLineItem(f"Plant Maintenance ({service_tier.value.title()} Tier) - {plant_count} plants", 
                         1, service_cost, service_cost, "Service"),
            QuoteLineItem(f"Labor ({labor_hours} hours @ ${crew_rate}/hr)", 
                         1, labor_cost, labor_cost, "Labor"),
            QuoteLineItem(f"Travel to {target_borough.value.title()}", 
                         monthly_visits, travel_cost/monthly_visits, travel_cost, "Travel")
        ]
        
        subtotal = sum(item.total for item in line_items)
        delivery_fee = self._calculate_delivery_fee(target_borough, subtotal)
        tax_amount = subtotal * self.tax_rate
        
        return QuoteBreakdown(
            line_items=line_items,
            subtotal=subtotal,
            tax_rate=self.tax_rate,
            tax_amount=tax_amount,
            delivery_fee=delivery_fee,
            seasonal_premium=0.0,
            total=subtotal + tax_amount + delivery_fee,
            service_tier=service_tier,
            valid_until=date.today().replace(day=1, month=date.today().month + 1) if date.today().month < 12 else date.today().replace(year=date.today().year + 1, month=1, day=1)
        )
    
    def calculate_plant_rentals(self,
                               plant_sizes: Dict[str, int],  # {"small": 5, "medium": 3, "large": 2}
                               service_tier: ServiceTier,
                               target_borough: Borough,
                               rental_months: int = 12) -> QuoteBreakdown:
        """Calculate plant rental pricing."""
        pricing = self.SERVICE_PRICING[ServiceType.PLANT_RENTALS]
        
        tier_multipliers = {
            ServiceTier.BRONZE: 1.0,
            ServiceTier.SILVER: 1.2,
            ServiceTier.GOLD: 1.5
        }
        
        line_items = []
        monthly_total = 0
        
        size_pricing = {
            "small": pricing["small_plant_monthly"],
            "medium": pricing["medium_plant_monthly"],
            "large": pricing["large_plant_monthly"],
            "premium": pricing["premium_plant_monthly"]
        }
        
        for size, count in plant_sizes.items():
            if count > 0:
                monthly_rate = size_pricing.get(size, size_pricing["medium"])
                adjusted_rate = monthly_rate * tier_multipliers[service_tier]
                monthly_cost = adjusted_rate * count
                total_cost = monthly_cost * rental_months
                monthly_total += monthly_cost
                
                line_items.append(
                    QuoteLineItem(f"{size.title()} Plant Rental ({count} plants @ ${adjusted_rate:.2f}/month)", 
                                 rental_months, monthly_cost, total_cost, "Rental")
                )
        
        # Setup fee (one-time)
        total_plants = sum(plant_sizes.values())
        setup_fee = pricing["setup_fee"] * total_plants
        line_items.append(
            QuoteLineItem(f"Setup & Installation ({total_plants} plants)", 
                         1, setup_fee, setup_fee, "Setup")
        )
        
        # Labor for ongoing maintenance
        labor_hours = pricing["labor_hours"] * total_plants * rental_months
        crew_rate = self.CREW_RATES[service_tier]
        labor_cost = labor_hours * crew_rate
        line_items.append(
            QuoteLineItem(f"Maintenance Labor ({labor_hours} hours @ ${crew_rate}/hr)", 
                         1, labor_cost, labor_cost, "Labor")
        )
        
        # Travel cost
        travel_cost = self._calculate_travel_cost(target_borough, service_tier) * rental_months
        if travel_cost > 0:
            line_items.append(
                QuoteLineItem(f"Travel to {target_borough.value.title()}", 
                             rental_months, travel_cost/rental_months, travel_cost, "Travel")
            )
        
        subtotal = sum(item.total for item in line_items)
        delivery_fee = self._calculate_delivery_fee(target_borough, subtotal)
        tax_amount = subtotal * self.tax_rate
        
        return QuoteBreakdown(
            line_items=line_items,
            subtotal=subtotal,
            tax_rate=self.tax_rate,
            tax_amount=tax_amount,
            delivery_fee=delivery_fee,
            seasonal_premium=0.0,
            total=subtotal + tax_amount + delivery_fee,
            service_tier=service_tier,
            valid_until=date.today().replace(day=1, month=date.today().month + 2) if date.today().month < 11 else date.today().replace(year=date.today().year + 1, month=1, day=1)
        )
    
    def calculate_holiday_decor(self,
                               square_footage: float,
                               premium_materials: bool,
                               service_tier: ServiceTier,
                               target_borough: Borough,
                               quote_date: date = None) -> QuoteBreakdown:
        """Calculate holiday decoration installation pricing."""
        pricing = self.SERVICE_PRICING[ServiceType.HOLIDAY_DECOR]
        
        base_installation = pricing["base_installation"]
        per_sq_ft = pricing["premium_materials"] if premium_materials else pricing["per_sq_ft"]
        
        # Tier adjustments
        tier_multipliers = {
            ServiceTier.BRONZE: 1.0,
            ServiceTier.SILVER: 1.25,
            ServiceTier.GOLD: 1.6
        }
        
        installation_cost = base_installation * tier_multipliers[service_tier]
        material_cost = square_footage * per_sq_ft * tier_multipliers[service_tier]
        
        # Labor cost
        labor_hours = pricing["labor_hours"] + (square_footage / 100) * 2  # Extra time for large spaces
        crew_rate = self.CREW_RATES[service_tier]
        labor_cost = labor_hours * crew_rate
        
        # Travel cost
        travel_cost = self._calculate_travel_cost(target_borough, service_tier)
        
        line_items = [
            QuoteLineItem(f"Holiday Decor Installation ({service_tier.value.title()} Tier)", 
                         1, installation_cost, installation_cost, "Installation"),
            QuoteLineItem(f"Materials ({'Premium' if premium_materials else 'Standard'}) - {square_footage} sq ft", 
                         1, material_cost, material_cost, "Materials"),
            QuoteLineItem(f"Labor ({labor_hours:.1f} hours @ ${crew_rate}/hr)", 
                         1, labor_cost, labor_cost, "Labor")
        ]
        
        if travel_cost > 0:
            line_items.append(
                QuoteLineItem(f"Travel to {target_borough.value.title()}", 
                             1, travel_cost, travel_cost, "Travel")
            )
        
        subtotal = sum(item.total for item in line_items)
        
        # Seasonal premium for holiday season
        seasonal_premium = 0.0
        if self._is_holiday_season(quote_date):
            seasonal_premium = subtotal * pricing["seasonal_markup"]
        
        delivery_fee = self._calculate_delivery_fee(target_borough, subtotal)
        tax_amount = (subtotal + seasonal_premium) * self.tax_rate
        
        return QuoteBreakdown(
            line_items=line_items,
            subtotal=subtotal,
            tax_rate=self.tax_rate,
            tax_amount=tax_amount,
            delivery_fee=delivery_fee,
            seasonal_premium=seasonal_premium,
            total=subtotal + tax_amount + delivery_fee + seasonal_premium,
            service_tier=service_tier,
            valid_until=date.today().replace(day=1, month=date.today().month + 1) if date.today().month < 12 else date.today().replace(year=date.today().year + 1, month=1, day=1)
        )
    
    def calculate_weekly_lobby_flowers(self,
                                     service_tier: ServiceTier,
                                     target_borough: Borough,
                                     weeks: int = 52) -> QuoteBreakdown:
        """Calculate weekly lobby flower service pricing."""
        pricing = self.SERVICE_PRICING[ServiceType.WEEKLY_LOBBY_FLOWERS]
        
        weekly_rates = {
            ServiceTier.BRONZE: pricing["bronze_weekly"],
            ServiceTier.SILVER: pricing["silver_weekly"],
            ServiceTier.GOLD: pricing["gold_weekly"]
        }
        
        weekly_rate = weekly_rates[service_tier]
        service_cost = weekly_rate * weeks
        
        # Labor cost
        labor_hours = pricing["labor_hours"] * weeks
        crew_rate = self.CREW_RATES[service_tier]
        labor_cost = labor_hours * crew_rate
        
        # Travel cost
        travel_cost = self._calculate_travel_cost(target_borough, service_tier) * weeks
        
        line_items = [
            QuoteLineItem(f"Weekly Lobby Flowers ({service_tier.value.title()} Tier)", 
                         weeks, weekly_rate, service_cost, "Service"),
            QuoteLineItem(f"Delivery & Setup Labor ({labor_hours} hours @ ${crew_rate}/hr)", 
                         1, labor_cost, labor_cost, "Labor")
        ]
        
        if travel_cost > 0:
            line_items.append(
                QuoteLineItem(f"Travel to {target_borough.value.title()}", 
                             weeks, travel_cost/weeks, travel_cost, "Travel")
            )
        
        subtotal = sum(item.total for item in line_items)
        delivery_fee = 0  # Included in weekly rate
        tax_amount = subtotal * self.tax_rate
        
        return QuoteBreakdown(
            line_items=line_items,
            subtotal=subtotal,
            tax_rate=self.tax_rate,
            tax_amount=tax_amount,
            delivery_fee=delivery_fee,
            seasonal_premium=0.0,
            total=subtotal + tax_amount,
            service_tier=service_tier,
            valid_until=date.today().replace(day=1, month=date.today().month + 1) if date.today().month < 12 else date.today().replace(year=date.today().year + 1, month=1, day=1)
        )
    
    def calculate_commercial_landscaping(self,
                                       square_footage: float,
                                       include_design: bool,
                                       maintenance_months: int,
                                       service_tier: ServiceTier,
                                       target_borough: Borough) -> QuoteBreakdown:
        """Calculate commercial landscaping project pricing."""
        pricing = self.SERVICE_PRICING[ServiceType.COMMERCIAL_LANDSCAPING]
        
        tier_multipliers = {
            ServiceTier.BRONZE: 1.0,
            ServiceTier.SILVER: 1.3,
            ServiceTier.GOLD: 1.7
        }
        
        line_items = []
        
        # Design fee (optional)
        if include_design:
            design_cost = pricing["design_fee"] * tier_multipliers[service_tier]
            line_items.append(
                QuoteLineItem(f"Landscape Design ({service_tier.value.title()} Tier)", 
                             1, design_cost, design_cost, "Design")
            )
        
        # Installation cost
        per_sq_ft_rate = pricing["per_sq_ft"] * tier_multipliers[service_tier]
        installation_cost = square_footage * per_sq_ft_rate
        line_items.append(
            QuoteLineItem(f"Landscape Installation - {square_footage} sq ft @ ${per_sq_ft_rate:.2f}/sq ft", 
                         1, installation_cost, installation_cost, "Installation")
        )
        
        # Labor cost
        labor_hours = pricing["labor_hours"] + (square_footage / 500) * 4  # Extra time for large projects
        crew_rate = self.CREW_RATES[service_tier]
        labor_cost = labor_hours * crew_rate
        line_items.append(
            QuoteLineItem(f"Installation Labor ({labor_hours:.1f} hours @ ${crew_rate}/hr)", 
                         1, labor_cost, labor_cost, "Labor")
        )
        
        # Ongoing maintenance (if specified)
        if maintenance_months > 0:
            monthly_maintenance = pricing["maintenance_monthly"] * tier_multipliers[service_tier]
            maintenance_cost = monthly_maintenance * maintenance_months
            line_items.append(
                QuoteLineItem(f"Maintenance Service ({maintenance_months} months @ ${monthly_maintenance:.2f}/month)", 
                             maintenance_months, monthly_maintenance, maintenance_cost, "Maintenance")
            )
        
        # Travel cost
        travel_multiplier = 1 + (maintenance_months * 0.1)  # More travel for ongoing maintenance
        travel_cost = self._calculate_travel_cost(target_borough, service_tier) * travel_multiplier
        if travel_cost > 0:
            line_items.append(
                QuoteLineItem(f"Travel to {target_borough.value.title()}", 
                             1, travel_cost, travel_cost, "Travel")
            )
        
        subtotal = sum(item.total for item in line_items)
        delivery_fee = self._calculate_delivery_fee(target_borough, subtotal)
        tax_amount = subtotal * self.tax_rate
        
        return QuoteBreakdown(
            line_items=line_items,
            subtotal=subtotal,
            tax_rate=self.tax_rate,
            tax_amount=tax_amount,
            delivery_fee=delivery_fee,
            seasonal_premium=0.0,
            total=subtotal + tax_amount + delivery_fee,
            service_tier=service_tier,
            valid_until=date.today().replace(day=1, month=date.today().month + 2) if date.today().month < 11 else date.today().replace(year=date.today().year + 1, month=3, day=1)
        )
    
    def generate_quote_report(self, quote: QuoteBreakdown, client_name: str, project_name: str = "") -> str:
        """Generate a formatted quote report."""
        report = []
        report.append("=" * 60)
        report.append("CAMBRIDGE NY COMMERCIAL LANDSCAPING")
        report.append("Professional Quote")
        report.append("=" * 60)
        report.append(f"Client: {client_name}")
        if project_name:
            report.append(f"Project: {project_name}")
        report.append(f"Service Tier: {quote.service_tier.value.title()}")
        report.append(f"Quote Date: {date.today().strftime('%B %d, %Y')}")
        report.append(f"Valid Until: {quote.valid_until.strftime('%B %d, %Y')}")
        report.append("")
        
        # Line items by category
        categories = {}
        for item in quote.line_items:
            if item.category not in categories:
                categories[item.category] = []
            categories[item.category].append(item)
        
        for category, items in categories.items():
            report.append(f"{category.upper()}:")
            for item in items:
                if item.quantity == 1:
                    report.append(f"  {item.description:<45} ${item.total:>8.2f}")
                else:
                    report.append(f"  {item.description:<45}")
                    report.append(f"    {item.quantity} x ${item.unit_price:.2f} = ${item.total:>8.2f}")
            report.append("")
        
        report.append("-" * 60)
        report.append(f"{'Subtotal':<50} ${quote.subtotal:>8.2f}")
        
        if quote.seasonal_premium > 0:
            report.append(f"{'Holiday Season Premium':<50} ${quote.seasonal_premium:>8.2f}")
        
        report.append(f"{'Sales Tax ({:.3%})'.format(quote.tax_rate):<50} ${quote.tax_amount:>8.2f}")
        
        if quote.delivery_fee > 0:
            report.append(f"{'Delivery Fee':<50} ${quote.delivery_fee:>8.2f}")
        
        report.append("-" * 60)
        report.append(f"{'TOTAL':<50} ${quote.total:>8.2f}")
        report.append("=" * 60)
        
        return "\n".join(report)

# Example usage and testing
if __name__ == "__main__":
    engine = PricingEngine(Borough.MANHATTAN)
    
    # Example: Interior plant maintenance quote
    maintenance_quote = engine.calculate_interior_plant_maintenance(
        plant_count=25,
        service_tier=ServiceTier.SILVER,
        target_borough=Borough.BROOKLYN,
        monthly_visits=4
    )
    
    print(engine.generate_quote_report(maintenance_quote, "ABC Corporation", "Office Plant Maintenance"))
    print("\n" + "="*60 + "\n")
    
    # Example: Holiday decor quote
    holiday_quote = engine.calculate_holiday_decor(
        square_footage=2500,
        premium_materials=True,
        service_tier=ServiceTier.GOLD,
        target_borough=Borough.MANHATTAN,
        quote_date=date(2024, 12, 1)
    )
    
    print(engine.generate_quote_report(holiday_quote, "XYZ Hotel", "Holiday Lobby Decor"))