"""
Cambridge NY Commercial Operations - Inventory Optimization System

Optimizes plant and material inventory for Cambridge NY operations:
- Predicts demand based on client contracts and seasonal needs
- Tracks plant replacement rates and mortality patterns  
- Manages greenhouse and supplier relationships
- Minimizes dead stock while ensuring availability
- Optimizes reorder points and quantities
- Handles seasonal demand fluctuations

Integrates with supplier APIs, tracks inventory levels, and provides
automated reordering recommendations to maintain optimal stock levels.
"""

from datetime import datetime, timedelta, date
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Union
from enum import Enum
import math
import statistics


class InventoryCategory(Enum):
    """Categories of inventory items."""
    LIVE_PLANTS = "live_plants"
    HOLIDAY_DECOR = "holiday_decor" 
    CONTAINERS_POTS = "containers_pots"
    SOIL_MEDIA = "soil_media"
    FERTILIZERS = "fertilizers"
    TOOLS_EQUIPMENT = "tools_equipment"
    SEASONAL_MATERIALS = "seasonal_materials"
    DELIVERY_SUPPLIES = "delivery_supplies"


class SeasonalDemand(Enum):
    """Seasonal demand patterns."""
    CONSISTENT = "consistent"     # Steady year-round
    SPRING_PEAK = "spring_peak"  # Peak in spring
    HOLIDAY_PEAK = "holiday_peak" # Peak during holidays
    SUMMER_HIGH = "summer_high"   # Higher in summer
    FALL_FOCUS = "fall_focus"     # Focus in fall


class SupplierReliability(Enum):
    """Supplier reliability ratings."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair" 
    POOR = "poor"


@dataclass
class InventoryItem:
    """Individual inventory item with characteristics."""
    sku: str
    name: str
    category: InventoryCategory
    unit_cost: float
    selling_price: float
    current_stock: int
    reorder_point: int
    reorder_quantity: int
    max_stock_level: int
    lead_time_days: int
    shelf_life_days: Optional[int] = None  # None for non-perishable
    seasonal_pattern: SeasonalDemand = SeasonalDemand.CONSISTENT
    storage_requirements: List[str] = field(default_factory=list)
    supplier_id: str = ""
    last_ordered: Optional[date] = None
    last_received: Optional[date] = None


@dataclass
class PlantInventory(InventoryItem):
    """Specialized inventory for live plants."""
    species: str
    size_category: str  # "small", "medium", "large", "extra_large"
    pot_size: str
    care_difficulty: int  # 1=easy, 5=very difficult  
    expected_lifespan_months: int
    mortality_rate: float  # 0.0 to 1.0
    preferred_environments: List[str]
    growing_season_start: int  # Month number (1-12)
    growing_season_end: int    # Month number (1-12)


@dataclass
class Supplier:
    """Supplier information and performance tracking."""
    id: str
    name: str
    contact_info: Dict[str, str]
    specialties: List[InventoryCategory]
    reliability_rating: SupplierReliability
    lead_time_average: int
    lead_time_variance: int
    quality_rating: float  # 1.0 to 5.0
    price_competitiveness: float  # 1.0 to 5.0
    minimum_order: float
    payment_terms: str
    seasonal_availability: Dict[int, float]  # month -> availability (0.0-1.0)
    performance_history: Dict[str, List[float]] = field(default_factory=dict)


@dataclass
class DemandForecast:
    """Demand forecast for an inventory item."""
    item_sku: str
    forecast_period_start: date
    forecast_period_end: date
    predicted_demand: int
    confidence_level: float  # 0.0 to 1.0
    seasonal_factor: float
    trend_factor: float
    client_contract_factor: float
    historical_accuracy: float


@dataclass
class ClientContract:
    """Client contract affecting inventory demand."""
    client_id: str
    client_name: str
    contract_start: date
    contract_end: date
    plant_types_required: Dict[str, int]  # species -> quantity
    service_frequency: str
    replacement_allowance: float  # percentage extra for replacements
    seasonal_adjustments: Dict[str, float]
    budget_allocation: Dict[InventoryCategory, float]


@dataclass
class InventoryAlert:
    """Alert for inventory management action needed."""
    alert_type: str  # "low_stock", "expiring", "dead_stock", "reorder"
    item_sku: str
    message: str
    priority: int  # 1=urgent, 5=low
    recommended_action: str
    created_date: datetime


class InventoryOptimizer:
    """
    Inventory optimization system for Cambridge NY operations.
    
    Manages plant and material inventory to minimize dead stock while
    ensuring availability for client contracts. Includes demand forecasting,
    supplier management, and automated reordering recommendations.
    """
    
    def __init__(self):
        self.inventory_items: Dict[str, InventoryItem] = {}
        self.plant_inventory: Dict[str, PlantInventory] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.client_contracts: List[ClientContract] = []
        self.demand_forecasts: Dict[str, DemandForecast] = {}
        self.inventory_alerts: List[InventoryAlert] = []
        
        # Historical demand tracking
        self.demand_history: Dict[str, List[Tuple[date, int]]] = {}  # sku -> [(date, quantity)]
        
        # Initialize default seasonal patterns
        self.seasonal_multipliers = {
            SeasonalDemand.CONSISTENT: {i: 1.0 for i in range(1, 13)},
            SeasonalDemand.SPRING_PEAK: {
                1: 0.7, 2: 0.8, 3: 1.2, 4: 1.5, 5: 1.3, 6: 1.0,
                7: 0.9, 8: 0.8, 9: 0.9, 10: 1.0, 11: 0.8, 12: 0.7
            },
            SeasonalDemand.HOLIDAY_PEAK: {
                1: 1.2, 2: 1.3, 3: 0.8, 4: 0.9, 5: 0.8, 6: 0.7,
                7: 0.7, 8: 0.8, 9: 0.9, 10: 1.1, 11: 1.4, 12: 1.8
            },
            SeasonalDemand.SUMMER_HIGH: {
                1: 0.6, 2: 0.7, 3: 0.9, 4: 1.1, 5: 1.3, 6: 1.5,
                7: 1.4, 8: 1.3, 9: 1.0, 10: 0.8, 11: 0.7, 12: 0.6
            },
            SeasonalDemand.FALL_FOCUS: {
                1: 0.7, 2: 0.7, 3: 0.8, 4: 0.9, 5: 0.8, 6: 0.8,
                7: 0.9, 8: 1.0, 9: 1.3, 10: 1.5, 11: 1.2, 12: 0.8
            }
        }
    
    def add_inventory_item(self, item: InventoryItem):
        """Add an inventory item to the system."""
        self.inventory_items[item.sku] = item
        
        if isinstance(item, PlantInventory):
            self.plant_inventory[item.sku] = item
        
        # Initialize demand history if not exists
        if item.sku not in self.demand_history:
            self.demand_history[item.sku] = []
    
    def add_supplier(self, supplier: Supplier):
        """Add a supplier to the system."""
        self.suppliers[supplier.id] = supplier
    
    def add_client_contract(self, contract: ClientContract):
        """Add a client contract affecting demand."""
        self.client_contracts.append(contract)
    
    def record_demand(self, sku: str, quantity: int, demand_date: date = None):
        """Record actual demand for an item."""
        if demand_date is None:
            demand_date = date.today()
        
        if sku in self.demand_history:
            self.demand_history[sku].append((demand_date, quantity))
            
            # Keep only last 2 years of history
            cutoff_date = demand_date - timedelta(days=730)
            self.demand_history[sku] = [
                (d, q) for d, q in self.demand_history[sku] if d >= cutoff_date
            ]
    
    def calculate_seasonal_factor(self, sku: str, target_month: int) -> float:
        """Calculate seasonal demand factor for an item in a specific month."""
        if sku in self.inventory_items:
            item = self.inventory_items[sku]
            pattern = item.seasonal_pattern
            return self.seasonal_multipliers[pattern][target_month]
        return 1.0
    
    def calculate_client_contract_demand(self, sku: str, start_date: date, 
                                       end_date: date) -> int:
        """Calculate demand from client contracts for a specific period."""
        total_demand = 0
        
        for contract in self.client_contracts:
            # Check if contract overlaps with forecast period
            if (contract.contract_end >= start_date and 
                contract.contract_start <= end_date):
                
                # Find demand for this SKU in contract
                if sku in self.inventory_items:
                    item = self.inventory_items[sku]
                    
                    if isinstance(item, PlantInventory):
                        # Check if plant species matches contract requirements
                        contract_demand = contract.plant_types_required.get(item.species, 0)
                        
                        if contract_demand > 0:
                            # Calculate period overlap
                            overlap_start = max(contract.contract_start, start_date)
                            overlap_end = min(contract.contract_end, end_date)
                            overlap_days = (overlap_end - overlap_start).days + 1
                            
                            # Calculate demand based on service frequency and replacement rate
                            frequency_multiplier = {
                                "weekly": 52,
                                "biweekly": 26,
                                "monthly": 12,
                                "quarterly": 4
                            }.get(contract.service_frequency, 12)
                            
                            annual_replacements = contract_demand * item.mortality_rate * frequency_multiplier
                            period_replacements = annual_replacements * (overlap_days / 365)
                            
                            # Apply replacement allowance
                            total_demand += int(period_replacements * (1 + contract.replacement_allowance))
        
        return total_demand
    
    def calculate_trend_factor(self, sku: str) -> float:
        """Calculate trend factor based on historical demand."""
        if sku not in self.demand_history or len(self.demand_history[sku]) < 12:
            return 1.0
        
        history = self.demand_history[sku]
        history.sort(key=lambda x: x[0])
        
        # Calculate 3-month moving averages
        recent_avg = sum(q for _, q in history[-3:]) / 3
        older_avg = sum(q for _, q in history[-12:-9]) / 3
        
        if older_avg > 0:
            trend = recent_avg / older_avg
            # Cap trend factor between 0.5 and 2.0
            return max(0.5, min(2.0, trend))
        
        return 1.0
    
    def forecast_demand(self, sku: str, forecast_months: int = 3) -> DemandForecast:
        """
        Forecast demand for an inventory item.
        
        Args:
            sku: Item SKU to forecast
            forecast_months: Number of months to forecast ahead
            
        Returns:
            Demand forecast with confidence level
        """
        start_date = date.today()
        end_date = start_date + timedelta(days=30 * forecast_months)
        
        # Base demand from historical average
        base_demand = 0
        if sku in self.demand_history and self.demand_history[sku]:
            recent_history = self.demand_history[sku][-12:]  # Last 12 records
            if recent_history:
                base_demand = int(statistics.mean(q for _, q in recent_history) * forecast_months)
        
        # Apply seasonal factor
        current_month = start_date.month
        seasonal_factor = self.calculate_seasonal_factor(sku, current_month)
        
        # Apply trend factor
        trend_factor = self.calculate_trend_factor(sku)
        
        # Client contract demand
        contract_demand = self.calculate_client_contract_demand(sku, start_date, end_date)
        
        # Combine factors
        predicted_demand = int((base_demand * seasonal_factor * trend_factor) + contract_demand)
        
        # Calculate confidence level
        confidence = self._calculate_forecast_confidence(sku)
        
        # Historical accuracy (simplified)
        historical_accuracy = 0.8  # Default 80% accuracy
        
        forecast = DemandForecast(
            item_sku=sku,
            forecast_period_start=start_date,
            forecast_period_end=end_date,
            predicted_demand=predicted_demand,
            confidence_level=confidence,
            seasonal_factor=seasonal_factor,
            trend_factor=trend_factor,
            client_contract_factor=contract_demand / max(predicted_demand, 1),
            historical_accuracy=historical_accuracy
        )
        
        self.demand_forecasts[sku] = forecast
        return forecast
    
    def _calculate_forecast_confidence(self, sku: str) -> float:
        """Calculate confidence level for demand forecast."""
        base_confidence = 0.5
        
        # More historical data increases confidence
        if sku in self.demand_history:
            history_length = len(self.demand_history[sku])
            history_bonus = min(0.3, history_length / 50)  # Up to 30% bonus
            base_confidence += history_bonus
        
        # Consistent demand patterns increase confidence
        if sku in self.demand_history and len(self.demand_history[sku]) > 5:
            quantities = [q for _, q in self.demand_history[sku][-12:]]
            if len(quantities) > 1:
                coefficient_variation = statistics.stdev(quantities) / statistics.mean(quantities)
                consistency_bonus = max(0, 0.2 - coefficient_variation)  # Up to 20% bonus
                base_confidence += consistency_bonus
        
        # Client contracts increase confidence
        contract_coverage = len([c for c in self.client_contracts 
                               if any(sku in self.inventory_items and
                                     isinstance(self.inventory_items[sku], PlantInventory) and
                                     self.inventory_items[sku].species in c.plant_types_required
                                     for c in self.client_contracts)])
        
        if contract_coverage > 0:
            base_confidence += min(0.2, contract_coverage * 0.05)
        
        return min(1.0, base_confidence)
    
    def optimize_reorder_points(self) -> Dict[str, Tuple[int, int]]:
        """
        Optimize reorder points and quantities for all items.
        
        Returns:
            Dictionary mapping SKU to (reorder_point, reorder_quantity)
        """
        optimized_levels = {}
        
        for sku, item in self.inventory_items.items():
            # Forecast demand for lead time period
            lead_time_months = math.ceil(item.lead_time_days / 30)
            demand_forecast = self.forecast_demand(sku, lead_time_months)
            
            # Calculate safety stock
            safety_stock = self._calculate_safety_stock(sku, demand_forecast)
            
            # Reorder point = Lead time demand + Safety stock
            reorder_point = demand_forecast.predicted_demand + safety_stock
            
            # Calculate Economic Order Quantity (EOQ)
            reorder_quantity = self._calculate_eoq(sku, demand_forecast)
            
            optimized_levels[sku] = (reorder_point, reorder_quantity)
            
            # Update item with new levels
            item.reorder_point = reorder_point
            item.reorder_quantity = reorder_quantity
        
        return optimized_levels
    
    def _calculate_safety_stock(self, sku: str, demand_forecast: DemandForecast) -> int:
        """Calculate safety stock level for an item."""
        if sku not in self.inventory_items:
            return 0
        
        item = self.inventory_items[sku]
        
        # Base safety stock on demand variability and forecast confidence
        base_safety = demand_forecast.predicted_demand * 0.2  # 20% of forecasted demand
        
        # Adjust for forecast confidence
        confidence_factor = 1.5 - demand_forecast.confidence_level  # Lower confidence = more safety stock
        
        # Adjust for item criticality
        criticality_factor = 1.0
        if item.category in [InventoryCategory.LIVE_PLANTS]:
            criticality_factor = 1.3  # Plants are critical
        
        # Adjust for supplier reliability
        supplier_factor = 1.0
        if item.supplier_id in self.suppliers:
            supplier = self.suppliers[item.supplier_id]
            if supplier.reliability_rating == SupplierReliability.POOR:
                supplier_factor = 1.4
            elif supplier.reliability_rating == SupplierReliability.FAIR:
                supplier_factor = 1.2
            elif supplier.reliability_rating == SupplierReliability.EXCELLENT:
                supplier_factor = 0.9
        
        safety_stock = int(base_safety * confidence_factor * criticality_factor * supplier_factor)
        
        return max(1, safety_stock)  # Minimum safety stock of 1
    
    def _calculate_eoq(self, sku: str, demand_forecast: DemandForecast) -> int:
        """Calculate Economic Order Quantity for an item."""
        if sku not in self.inventory_items:
            return 10  # Default
        
        item = self.inventory_items[sku]
        
        # Annual demand (extrapolate from forecast)
        forecast_months = (demand_forecast.forecast_period_end - 
                          demand_forecast.forecast_period_start).days / 30
        annual_demand = demand_forecast.predicted_demand * (12 / forecast_months)
        
        # Estimated ordering cost (fixed cost per order)
        ordering_cost = 50.0  # $50 per order
        
        # Holding cost (percentage of item cost per year)
        holding_cost_rate = 0.15  # 15% of item cost per year
        holding_cost = item.unit_cost * holding_cost_rate
        
        # EOQ formula: sqrt((2 * D * S) / H)
        # D = annual demand, S = ordering cost, H = holding cost
        if holding_cost > 0 and annual_demand > 0:
            eoq = math.sqrt((2 * annual_demand * ordering_cost) / holding_cost)
        else:
            eoq = annual_demand / 12  # Default to monthly supply
        
        # Apply constraints
        min_order = 1
        max_order = item.max_stock_level
        
        # Check supplier minimum orders
        if item.supplier_id in self.suppliers:
            supplier = self.suppliers[item.supplier_id]
            supplier_min = int(supplier.minimum_order / max(item.unit_cost, 1))
            min_order = max(min_order, supplier_min)
        
        return max(min_order, min(int(eoq), max_order))
    
    def check_inventory_alerts(self) -> List[InventoryAlert]:
        """Check for inventory alerts and recommendations."""
        alerts = []
        current_date = datetime.now()
        
        for sku, item in self.inventory_items.items():
            # Low stock alert
            if item.current_stock <= item.reorder_point:
                alert = InventoryAlert(
                    alert_type="low_stock",
                    item_sku=sku,
                    message=f"{item.name} is at reorder point. Current: {item.current_stock}, Reorder at: {item.reorder_point}",
                    priority=2,
                    recommended_action=f"Order {item.reorder_quantity} units",
                    created_date=current_date
                )
                alerts.append(alert)
            
            # Critical stock alert
            if item.current_stock <= item.reorder_point * 0.5:
                alert = InventoryAlert(
                    alert_type="critical_stock",
                    item_sku=sku,
                    message=f"{item.name} is critically low. Current: {item.current_stock}",
                    priority=1,
                    recommended_action=f"URGENT: Order {item.reorder_quantity} units immediately",
                    created_date=current_date
                )
                alerts.append(alert)
            
            # Expiring items (for perishables)
            if item.shelf_life_days and item.last_received:
                days_since_received = (current_date.date() - item.last_received).days
                days_remaining = item.shelf_life_days - days_since_received
                
                if days_remaining <= 7:  # Expiring within a week
                    alert = InventoryAlert(
                        alert_type="expiring",
                        item_sku=sku,
                        message=f"{item.name} expires in {days_remaining} days",
                        priority=2,
                        recommended_action="Use or discount soon-to-expire inventory",
                        created_date=current_date
                    )
                    alerts.append(alert)
            
            # Dead stock alert (high inventory, low demand)
            if item.current_stock > item.max_stock_level * 0.8:
                # Check recent demand
                recent_demand = sum(
                    q for d, q in self.demand_history.get(sku, [])
                    if (current_date.date() - d).days <= 90
                )
                
                if recent_demand == 0:
                    alert = InventoryAlert(
                        alert_type="dead_stock",
                        item_sku=sku,
                        message=f"{item.name} has high stock but no recent demand",
                        priority=3,
                        recommended_action="Consider discontinuing or finding alternative uses",
                        created_date=current_date
                    )
                    alerts.append(alert)
            
            # Plant-specific alerts
            if isinstance(item, PlantInventory):
                # Seasonal ordering reminder
                current_month = current_date.month
                if (item.growing_season_start <= current_month <= item.growing_season_end and
                    item.current_stock < item.reorder_point * 1.5):
                    
                    alert = InventoryAlert(
                        alert_type="seasonal_ordering",
                        item_sku=sku,
                        message=f"{item.name} is in growing season - consider increasing stock",
                        priority=3,
                        recommended_action=f"Consider ordering extra {item.reorder_quantity // 2} units for season",
                        created_date=current_date
                    )
                    alerts.append(alert)
        
        self.inventory_alerts = alerts
        return alerts
    
    def get_supplier_performance(self, supplier_id: str) -> Dict[str, float]:
        """Get performance metrics for a supplier."""
        if supplier_id not in self.suppliers:
            return {}
        
        supplier = self.suppliers[supplier_id]
        
        # Calculate metrics from performance history
        metrics = {
            "reliability_score": self._supplier_reliability_score(supplier.reliability_rating),
            "quality_rating": supplier.quality_rating,
            "price_competitiveness": supplier.price_competitiveness,
            "average_lead_time": supplier.lead_time_average,
            "lead_time_variance": supplier.lead_time_variance
        }
        
        # Calculate on-time delivery rate
        delivery_history = supplier.performance_history.get("on_time_delivery", [])
        if delivery_history:
            metrics["on_time_delivery_rate"] = statistics.mean(delivery_history)
        
        # Calculate quality consistency
        quality_history = supplier.performance_history.get("quality_scores", [])
        if quality_history:
            metrics["quality_consistency"] = 1.0 - (statistics.stdev(quality_history) / 5.0)
        
        return metrics
    
    def _supplier_reliability_score(self, rating: SupplierReliability) -> float:
        """Convert supplier reliability rating to numeric score."""
        scores = {
            SupplierReliability.EXCELLENT: 0.95,
            SupplierReliability.GOOD: 0.85,
            SupplierReliability.FAIR: 0.70,
            SupplierReliability.POOR: 0.50
        }
        return scores.get(rating, 0.70)
    
    def recommend_supplier_diversification(self) -> Dict[str, List[str]]:
        """Recommend supplier diversification for risk management."""
        recommendations = {}
        
        # Group items by category
        category_items = {}
        for sku, item in self.inventory_items.items():
            category = item.category
            if category not in category_items:
                category_items[category] = []
            category_items[category].append(sku)
        
        # Check supplier concentration risk
        for category, items in category_items.items():
            supplier_concentration = {}
            for sku in items:
                item = self.inventory_items[sku]
                supplier_id = item.supplier_id
                if supplier_id:
                    if supplier_id not in supplier_concentration:
                        supplier_concentration[supplier_id] = 0
                    supplier_concentration[supplier_id] += 1
            
            # If one supplier has >70% of category items, recommend diversification
            total_items = len(items)
            for supplier_id, count in supplier_concentration.items():
                if count / total_items > 0.7:
                    # Find alternative suppliers
                    alternative_suppliers = [
                        s.id for s in self.suppliers.values()
                        if (category in s.specialties and 
                            s.id != supplier_id and
                            s.reliability_rating in [SupplierReliability.GOOD, SupplierReliability.EXCELLENT])
                    ]
                    
                    if alternative_suppliers:
                        recommendations[category.value] = alternative_suppliers
        
        return recommendations
    
    def generate_inventory_report(self) -> Dict[str, any]:
        """Generate comprehensive inventory status report."""
        total_value = sum(item.current_stock * item.unit_cost for item in self.inventory_items.values())
        total_items = len(self.inventory_items)
        
        # Category breakdown
        category_stats = {}
        for item in self.inventory_items.values():
            category = item.category.value
            if category not in category_stats:
                category_stats[category] = {"count": 0, "value": 0, "stock_level": 0}
            
            category_stats[category]["count"] += 1
            category_stats[category]["value"] += item.current_stock * item.unit_cost
            category_stats[category]["stock_level"] += item.current_stock
        
        # Alert summary
        alerts = self.check_inventory_alerts()
        alert_summary = {}
        for alert in alerts:
            alert_type = alert.alert_type
            if alert_type not in alert_summary:
                alert_summary[alert_type] = 0
            alert_summary[alert_type] += 1
        
        # Turnover analysis (simplified)
        turnover_items = []
        for sku, item in self.inventory_items.items():
            if sku in self.demand_history and self.demand_history[sku]:
                recent_demand = sum(q for _, q in self.demand_history[sku][-12:])
                if item.current_stock > 0:
                    turnover_rate = recent_demand / item.current_stock
                    turnover_items.append((sku, item.name, turnover_rate))
        
        turnover_items.sort(key=lambda x: x[2], reverse=True)
        
        report = {
            "report_date": datetime.now(),
            "total_inventory_value": total_value,
            "total_unique_items": total_items,
            "category_breakdown": category_stats,
            "alert_summary": alert_summary,
            "top_turnover_items": turnover_items[:10],
            "total_alerts": len(alerts),
            "suppliers_count": len(self.suppliers),
            "active_contracts": len(self.client_contracts)
        }
        
        return report


def create_sample_inventory_data() -> Tuple[List[InventoryItem], List[Supplier], List[ClientContract]]:
    """Create sample data for testing inventory optimization."""
    
    # Sample plant inventory items
    inventory_items = [
        PlantInventory(
            sku="PLT001",
            name="Dracaena marginata - Medium",
            category=InventoryCategory.LIVE_PLANTS,
            unit_cost=35.00,
            selling_price=52.50,
            current_stock=25,
            reorder_point=10,
            reorder_quantity=20,
            max_stock_level=50,
            lead_time_days=14,
            shelf_life_days=None,
            seasonal_pattern=SeasonalDemand.SPRING_PEAK,
            storage_requirements=["greenhouse", "temperature_controlled"],
            supplier_id="SUP001",
            species="Dracaena marginata",
            size_category="medium",
            pot_size="6-inch",
            care_difficulty=2,
            expected_lifespan_months=18,
            mortality_rate=0.15,
            preferred_environments=["office", "lobby"],
            growing_season_start=3,
            growing_season_end=8
        ),
        PlantInventory(
            sku="PLT002",
            name="Pothos - Small",
            category=InventoryCategory.LIVE_PLANTS,
            unit_cost=18.00,
            selling_price=27.00,
            current_stock=45,
            reorder_point=20,
            reorder_quantity=30,
            max_stock_level=80,
            lead_time_days=10,
            seasonal_pattern=SeasonalDemand.CONSISTENT,
            storage_requirements=["greenhouse"],
            supplier_id="SUP001",
            species="Pothos",
            size_category="small",
            pot_size="4-inch",
            care_difficulty=1,
            expected_lifespan_months=24,
            mortality_rate=0.08,
            preferred_environments=["office", "healthcare"],
            growing_season_start=1,
            growing_season_end=12
        ),
        PlantInventory(
            sku="PLT003", 
            name="Poinsettia - Holiday",
            category=InventoryCategory.LIVE_PLANTS,
            unit_cost=12.00,
            selling_price=20.00,
            current_stock=5,
            reorder_point=15,
            reorder_quantity=25,
            max_stock_level=60,
            lead_time_days=21,
            shelf_life_days=90,
            seasonal_pattern=SeasonalDemand.HOLIDAY_PEAK,
            storage_requirements=["greenhouse", "climate_controlled"],
            supplier_id="SUP002",
            species="Poinsettia",
            size_category="medium",
            pot_size="5-inch",
            care_difficulty=4,
            expected_lifespan_months=2,
            mortality_rate=0.35,
            preferred_environments=["lobby", "retail"],
            growing_season_start=10,
            growing_season_end=12
        ),
        InventoryItem(
            sku="POT001",
            name="Ceramic Pot 6-inch - White",
            category=InventoryCategory.CONTAINERS_POTS,
            unit_cost=8.50,
            selling_price=15.00,
            current_stock=30,
            reorder_point=15,
            reorder_quantity=40,
            max_stock_level=100,
            lead_time_days=21,
            seasonal_pattern=SeasonalDemand.SPRING_PEAK,
            storage_requirements=["warehouse"],
            supplier_id="SUP003"
        ),
        InventoryItem(
            sku="DEC001",
            name="Christmas Garland - Premium",
            category=InventoryCategory.HOLIDAY_DECOR,
            unit_cost=25.00,
            selling_price=45.00,
            current_stock=8,
            reorder_point=20,
            reorder_quantity=15,
            max_stock_level=40,
            lead_time_days=30,
            shelf_life_days=365,
            seasonal_pattern=SeasonalDemand.HOLIDAY_PEAK,
            storage_requirements=["warehouse", "climate_controlled"],
            supplier_id="SUP004"
        )
    ]
    
    # Sample suppliers
    suppliers = [
        Supplier(
            id="SUP001",
            name="NYC Plant Wholesale",
            contact_info={"phone": "718-555-0101", "email": "orders@nycplantwholesale.com"},
            specialties=[InventoryCategory.LIVE_PLANTS],
            reliability_rating=SupplierReliability.EXCELLENT,
            lead_time_average=12,
            lead_time_variance=3,
            quality_rating=4.5,
            price_competitiveness=4.2,
            minimum_order=500.00,
            payment_terms="Net 30",
            seasonal_availability={i: 0.9 for i in range(1, 13)},
            performance_history={
                "on_time_delivery": [0.92, 0.94, 0.91, 0.95, 0.93],
                "quality_scores": [4.4, 4.6, 4.5, 4.5, 4.3]
            }
        ),
        Supplier(
            id="SUP002",
            name="Seasonal Specialties Inc",
            contact_info={"phone": "516-555-0202", "email": "seasonal@specialties.com"},
            specialties=[InventoryCategory.LIVE_PLANTS, InventoryCategory.SEASONAL_MATERIALS],
            reliability_rating=SupplierReliability.GOOD,
            lead_time_average=18,
            lead_time_variance=7,
            quality_rating=4.0,
            price_competitiveness=3.8,
            minimum_order=300.00,
            payment_terms="Net 15",
            seasonal_availability={
                1: 0.3, 2: 0.2, 3: 0.4, 4: 0.6, 5: 0.8, 6: 0.7,
                7: 0.6, 8: 0.5, 9: 0.7, 10: 0.9, 11: 1.0, 12: 1.0
            },
            performance_history={
                "on_time_delivery": [0.85, 0.88, 0.82, 0.87, 0.84],
                "quality_scores": [4.1, 3.9, 4.2, 4.0, 3.8]
            }
        ),
        Supplier(
            id="SUP003",
            name="Garden Container Supply",
            contact_info={"phone": "201-555-0303", "email": "sales@gardencontainer.com"},
            specialties=[InventoryCategory.CONTAINERS_POTS, InventoryCategory.SOIL_MEDIA],
            reliability_rating=SupplierReliability.GOOD,
            lead_time_average=21,
            lead_time_variance=5,
            quality_rating=3.8,
            price_competitiveness=4.5,
            minimum_order=200.00,
            payment_terms="Net 45",
            seasonal_availability={i: 0.8 for i in range(1, 13)},
            performance_history={
                "on_time_delivery": [0.78, 0.82, 0.80, 0.85, 0.79],
                "quality_scores": [3.7, 3.9, 3.8, 3.8, 3.6]
            }
        )
    ]
    
    # Sample client contracts
    contracts = [
        ClientContract(
            client_id="client001",
            client_name="Weill Cornell Medical Center",
            contract_start=date(2026, 1, 1),
            contract_end=date(2026, 12, 31),
            plant_types_required={
                "Dracaena marginata": 15,
                "Pothos": 25,
                "Snake Plant": 10
            },
            service_frequency="weekly",
            replacement_allowance=0.20,
            seasonal_adjustments={
                "spring": 1.1,
                "summer": 1.0,
                "fall": 1.0,
                "winter": 0.9
            },
            budget_allocation={
                InventoryCategory.LIVE_PLANTS: 0.70,
                InventoryCategory.CONTAINERS_POTS: 0.20,
                InventoryCategory.SOIL_MEDIA: 0.10
            }
        ),
        ClientContract(
            client_id="client002",
            client_name="Brooklyn Corporate Plaza",
            contract_start=date(2026, 3, 1),
            contract_end=date(2027, 2, 28),
            plant_types_required={
                "Pothos": 20,
                "Poinsettia": 8,
                "Boston Fern": 12
            },
            service_frequency="biweekly",
            replacement_allowance=0.15,
            seasonal_adjustments={
                "spring": 1.2,
                "summer": 1.0,
                "fall": 1.1,
                "winter": 1.3
            },
            budget_allocation={
                InventoryCategory.LIVE_PLANTS: 0.60,
                InventoryCategory.HOLIDAY_DECOR: 0.25,
                InventoryCategory.CONTAINERS_POTS: 0.15
            }
        )
    ]
    
    return inventory_items, suppliers, contracts


if __name__ == "__main__":
    # Example usage
    inventory_items, suppliers, contracts = create_sample_inventory_data()
    
    # Initialize optimizer
    optimizer = InventoryOptimizer()
    
    # Add data to optimizer
    for item in inventory_items:
        optimizer.add_inventory_item(item)
    
    for supplier in suppliers:
        optimizer.add_supplier(supplier)
    
    for contract in contracts:
        optimizer.add_client_contract(contract)
    
    print("=== Cambridge NY Inventory Optimizer Demo ===")
    print(f"Inventory items: {len(inventory_items)}")
    print(f"Suppliers: {len(suppliers)}")
    print(f"Client contracts: {len(contracts)}")
    
    # Generate demand forecasts
    print(f"\n=== Demand Forecasts ===")
    for item in inventory_items[:3]:  # First 3 items
        forecast = optimizer.forecast_demand(item.sku, forecast_months=3)
        print(f"\n{item.name}:")
        print(f"  Predicted demand (3 months): {forecast.predicted_demand}")
        print(f"  Confidence level: {forecast.confidence_level:.1%}")
        print(f"  Seasonal factor: {forecast.seasonal_factor:.2f}")
        print(f"  Trend factor: {forecast.trend_factor:.2f}")
    
    # Optimize reorder points
    print(f"\n=== Optimized Reorder Levels ===")
    optimized = optimizer.optimize_reorder_points()
    for sku, (reorder_point, reorder_qty) in list(optimized.items())[:3]:
        item = optimizer.inventory_items[sku]
        print(f"\n{item.name}:")
        print(f"  Current stock: {item.current_stock}")
        print(f"  Optimized reorder point: {reorder_point}")
        print(f"  Optimized reorder quantity: {reorder_qty}")
    
    # Check alerts
    print(f"\n=== Inventory Alerts ===")
    alerts = optimizer.check_inventory_alerts()
    print(f"Total alerts: {len(alerts)}")
    
    for alert in alerts[:5]:  # Show first 5 alerts
        print(f"\n{alert.alert_type.upper()}: {alert.message}")
        print(f"  Priority: {alert.priority}")
        print(f"  Action: {alert.recommended_action}")
    
    # Generate report
    print(f"\n=== Inventory Report Summary ===")
    report = optimizer.generate_inventory_report()
    print(f"Total inventory value: ${report['total_inventory_value']:,.2f}")
    print(f"Unique items: {report['total_unique_items']}")
    print(f"Active alerts: {report['total_alerts']}")
    print(f"Suppliers: {report['suppliers_count']}")
    
    print(f"\nCategory breakdown:")
    for category, stats in report['category_breakdown'].items():
        print(f"  {category}: {stats['count']} items, ${stats['value']:,.2f}")