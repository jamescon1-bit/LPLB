"""
Cambridge NY Commercial Operations - Crew Workload Balancer

Balances workload across maintenance crews considering:
- Number of client locations per crew
- Square footage coverage
- Plant count management
- Travel time between locations  
- Skill requirements matching
- Even workload distribution
- Overtime minimization

Optimizes crew assignments to maximize efficiency while ensuring
equitable work distribution and maintaining service quality standards.
"""

from datetime import datetime, timedelta, time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set, Union
from enum import Enum
import math
import statistics


class SkillLevel(Enum):
    """Skill proficiency levels."""
    NOVICE = 1
    INTERMEDIATE = 2  
    ADVANCED = 3
    EXPERT = 4


class WorkloadMetric(Enum):
    """Metrics for measuring workload."""
    HOURS_PER_WEEK = "hours_per_week"
    LOCATIONS_COUNT = "locations_count"
    PLANT_COUNT = "plant_count"
    SQUARE_FOOTAGE = "square_footage"
    TRAVEL_TIME = "travel_time"
    COMPLEXITY_SCORE = "complexity_score"


@dataclass
class CrewSkillProfile:
    """Detailed skill profile for crew members."""
    plant_care: SkillLevel
    holiday_decor: SkillLevel
    landscaping: SkillLevel
    floral_design: SkillLevel
    heavy_lifting: SkillLevel
    nyc_driving: SkillLevel
    customer_service: SkillLevel
    equipment_operation: SkillLevel


@dataclass
class CrewMemberProfile:
    """Enhanced crew member profile for workload balancing."""
    id: str
    name: str
    skills: CrewSkillProfile
    hourly_rate: float
    max_hours_per_week: float
    current_utilization: float  # 0.0 to 1.0
    preferred_boroughs: List[str]
    availability_windows: Dict[str, List[Tuple[time, time]]]  # day -> [(start, end)]
    certification_expiry: Dict[str, datetime]
    performance_rating: float  # 1.0 to 5.0
    overtime_preference: float  # 0.0 (avoid) to 1.0 (willing)


@dataclass
class ClientWorkload:
    """Workload profile for a client location."""
    client_id: str
    location_name: str
    address: str
    borough: str
    coordinates: Tuple[float, float]
    square_footage: float
    plant_count: int
    service_frequency: str  # "weekly", "biweekly", "monthly"
    estimated_hours_per_visit: float
    required_skills: Dict[str, SkillLevel]  # skill_name -> minimum_level
    complexity_factors: Dict[str, float]  # factor_name -> multiplier
    access_restrictions: List[str]  # e.g., ["security_clearance", "after_hours"]
    seasonal_adjustments: Dict[str, float]  # season -> hours_multiplier


@dataclass
class WorkloadAssignment:
    """Assignment of crew to client workloads."""
    crew_member: CrewMemberProfile
    assigned_clients: List[ClientWorkload]
    total_weekly_hours: float
    total_locations: int
    total_plants: int
    total_square_footage: float
    estimated_travel_time: timedelta
    workload_score: float
    utilization_rate: float


@dataclass
class BalancingConstraints:
    """Constraints for workload balancing."""
    max_utilization_rate: float = 0.85  # Maximum crew utilization
    min_utilization_rate: float = 0.60  # Minimum for efficiency
    max_locations_per_crew: int = 15    # Maximum locations per crew member
    max_travel_time_per_day: timedelta = timedelta(hours=2)
    skill_matching_strictness: float = 0.8  # How strict skill matching is
    workload_variance_tolerance: float = 0.15  # Acceptable variance in workload


class CrewWorkloadBalancer:
    """
    Workload balancing system for Cambridge NY maintenance crews.
    
    Distributes client assignments across crew members to optimize:
    - Even workload distribution
    - Skill matching
    - Travel efficiency
    - Crew utilization rates
    - Overtime minimization
    """
    
    def __init__(self, constraints: Optional[BalancingConstraints] = None):
        self.constraints = constraints or BalancingConstraints()
        self.crew_members: List[CrewMemberProfile] = []
        self.client_workloads: List[ClientWorkload] = []
        self.current_assignments: List[WorkloadAssignment] = []
        
        # Travel time matrix between NYC boroughs (minutes)
        self.travel_times = {
            ("Manhattan", "Manhattan"): 20,
            ("Manhattan", "Brooklyn"): 35,
            ("Manhattan", "Queens"): 45,
            ("Manhattan", "Bronx"): 40,
            ("Manhattan", "Staten Island"): 60,
            ("Brooklyn", "Brooklyn"): 25,
            ("Brooklyn", "Queens"): 30,
            ("Brooklyn", "Bronx"): 50,
            ("Brooklyn", "Staten Island"): 45,
            ("Queens", "Queens"): 30,
            ("Queens", "Bronx"): 35,
            ("Queens", "Staten Island"): 55,
            ("Bronx", "Bronx"): 25,
            ("Bronx", "Staten Island"): 70,
            ("Staten Island", "Staten Island"): 20,
        }
        
        # Make travel times symmetric
        for (a, b), time_val in list(self.travel_times.items()):
            if (b, a) not in self.travel_times:
                self.travel_times[(b, a)] = time_val
    
    def add_crew_member(self, crew_member: CrewMemberProfile):
        """Add a crew member to the balancing system."""
        self.crew_members.append(crew_member)
    
    def add_client_workload(self, client_workload: ClientWorkload):
        """Add a client workload to be assigned."""
        self.client_workloads.append(client_workload)
    
    def calculate_skill_match_score(self, crew_member: CrewMemberProfile, 
                                  client: ClientWorkload) -> float:
        """
        Calculate how well a crew member's skills match client requirements.
        
        Returns:
            Score from 0.0 (poor match) to 1.0 (perfect match)
        """
        if not client.required_skills:
            return 1.0  # No specific requirements
        
        total_score = 0.0
        skills_evaluated = 0
        
        # Map client skill requirements to crew skills
        skill_mapping = {
            "plant_care": crew_member.skills.plant_care,
            "holiday_decor": crew_member.skills.holiday_decor,
            "landscaping": crew_member.skills.landscaping,
            "floral_design": crew_member.skills.floral_design,
            "heavy_lifting": crew_member.skills.heavy_lifting,
            "nyc_driving": crew_member.skills.nyc_driving,
            "customer_service": crew_member.skills.customer_service,
            "equipment_operation": crew_member.skills.equipment_operation,
        }
        
        for skill_name, required_level in client.required_skills.items():
            if skill_name in skill_mapping:
                crew_level = skill_mapping[skill_name]
                
                if crew_level.value >= required_level.value:
                    # Bonus for exceeding requirements
                    score = 1.0 + (crew_level.value - required_level.value) * 0.1
                    total_score += min(score, 1.2)  # Cap at 1.2
                else:
                    # Penalty for not meeting requirements
                    deficit = required_level.value - crew_level.value
                    score = max(0.0, 1.0 - deficit * 0.3)
                    total_score += score
                
                skills_evaluated += 1
        
        return total_score / max(skills_evaluated, 1)
    
    def calculate_travel_efficiency(self, crew_member: CrewMemberProfile,
                                  assigned_clients: List[ClientWorkload]) -> float:
        """
        Calculate travel efficiency for a crew member's client assignments.
        
        Returns:
            Efficiency score from 0.0 (poor) to 1.0 (excellent)
        """
        if not assigned_clients:
            return 1.0
        
        # Group clients by borough
        borough_groups = {}
        for client in assigned_clients:
            borough = client.borough
            if borough not in borough_groups:
                borough_groups[borough] = []
            borough_groups[borough].append(client)
        
        # Calculate travel penalties
        total_travel_time = 0
        inter_borough_trips = 0
        
        # If crew member has preferred boroughs, check alignment
        borough_preference_bonus = 0.0
        if crew_member.preferred_boroughs:
            for borough in borough_groups.keys():
                if borough in crew_member.preferred_boroughs:
                    borough_preference_bonus += 0.1
        
        # Calculate inter-borough travel
        borough_list = list(borough_groups.keys())
        for i, borough_a in enumerate(borough_list):
            for borough_b in borough_list[i+1:]:
                travel_time = self.travel_times.get((borough_a, borough_b), 45)
                total_travel_time += travel_time
                inter_borough_trips += 1
        
        # Efficiency factors
        borough_concentration = len(borough_groups) / max(len(assigned_clients), 1)
        travel_penalty = min(total_travel_time / 120, 1.0)  # Penalty for >2 hours travel
        
        efficiency = (1.0 - travel_penalty) * (1.0 - borough_concentration * 0.3) + borough_preference_bonus
        return max(0.0, min(efficiency, 1.0))
    
    def calculate_workload_complexity(self, client: ClientWorkload) -> float:
        """Calculate complexity score for a client workload."""
        base_complexity = 1.0
        
        # Size complexity
        if client.square_footage > 5000:
            base_complexity += 0.3
        elif client.square_footage > 2000:
            base_complexity += 0.1
        
        # Plant count complexity
        if client.plant_count > 100:
            base_complexity += 0.4
        elif client.plant_count > 50:
            base_complexity += 0.2
        
        # Access restrictions add complexity
        if client.access_restrictions:
            base_complexity += len(client.access_restrictions) * 0.1
        
        # Frequency adjustments
        frequency_multipliers = {
            "weekly": 1.0,
            "biweekly": 0.8,
            "monthly": 0.6
        }
        base_complexity *= frequency_multipliers.get(client.service_frequency, 1.0)
        
        # Apply custom complexity factors
        for factor, multiplier in client.complexity_factors.items():
            base_complexity *= multiplier
        
        return base_complexity
    
    def calculate_workload_score(self, assignment: WorkloadAssignment) -> float:
        """
        Calculate overall workload score for an assignment.
        
        Lower scores indicate better-balanced assignments.
        """
        # Utilization penalty (too high or too low)
        target_utilization = (self.constraints.max_utilization_rate + 
                            self.constraints.min_utilization_rate) / 2
        utilization_penalty = abs(assignment.utilization_rate - target_utilization)
        
        # Travel efficiency (higher is better, so subtract from penalty)
        clients = assignment.assigned_clients
        travel_efficiency = self.calculate_travel_efficiency(assignment.crew_member, clients)
        
        # Location count penalty
        max_locations = self.constraints.max_locations_per_crew
        location_penalty = max(0, assignment.total_locations - max_locations) * 0.1
        
        # Complexity penalty
        total_complexity = sum(self.calculate_workload_complexity(client) for client in clients)
        complexity_penalty = max(0, total_complexity - 10) * 0.05  # Penalty for >10 complexity units
        
        # Skill mismatch penalty
        skill_penalties = []
        for client in clients:
            skill_match = self.calculate_skill_match_score(assignment.crew_member, client)
            if skill_match < self.constraints.skill_matching_strictness:
                skill_penalties.append(self.constraints.skill_matching_strictness - skill_match)
        skill_penalty = sum(skill_penalties)
        
        # Combine penalties
        total_penalty = (utilization_penalty * 2.0 +  # Utilization is most important
                        (1.0 - travel_efficiency) * 1.5 +  # Travel efficiency is important
                        location_penalty * 1.0 +
                        complexity_penalty * 0.8 +
                        skill_penalty * 1.2)
        
        return total_penalty
    
    def balance_workloads(self) -> List[WorkloadAssignment]:
        """
        Balance workloads across all crew members.
        
        Uses a combination of greedy assignment and local optimization
        to achieve balanced workload distribution.
        
        Returns:
            List of optimized workload assignments
        """
        if not self.crew_members or not self.client_workloads:
            return []
        
        # Initialize assignments
        assignments = []
        for crew_member in self.crew_members:
            assignment = WorkloadAssignment(
                crew_member=crew_member,
                assigned_clients=[],
                total_weekly_hours=0.0,
                total_locations=0,
                total_plants=0,
                total_square_footage=0.0,
                estimated_travel_time=timedelta(),
                workload_score=0.0,
                utilization_rate=0.0
            )
            assignments.append(assignment)
        
        # Sort clients by complexity (most complex first)
        sorted_clients = sorted(
            self.client_workloads,
            key=lambda c: self.calculate_workload_complexity(c),
            reverse=True
        )
        
        # Assign clients using greedy algorithm
        for client in sorted_clients:
            best_assignment = self._find_best_assignment(client, assignments)
            if best_assignment:
                self._assign_client_to_crew(client, best_assignment)
        
        # Optimize assignments through local search
        assignments = self._optimize_assignments(assignments)
        
        # Update final scores and metrics
        for assignment in assignments:
            self._update_assignment_metrics(assignment)
        
        self.current_assignments = assignments
        return assignments
    
    def _find_best_assignment(self, client: ClientWorkload,
                            assignments: List[WorkloadAssignment]) -> Optional[WorkloadAssignment]:
        """Find the best crew assignment for a client."""
        best_assignment = None
        best_score = float('inf')
        
        for assignment in assignments:
            # Check constraints
            if not self._can_assign_client(client, assignment):
                continue
            
            # Calculate potential score if client is assigned
            temp_assignment = self._simulate_assignment(client, assignment)
            score = self.calculate_workload_score(temp_assignment)
            
            if score < best_score:
                best_score = score
                best_assignment = assignment
        
        return best_assignment
    
    def _can_assign_client(self, client: ClientWorkload,
                          assignment: WorkloadAssignment) -> bool:
        """Check if a client can be assigned to a crew member."""
        crew = assignment.crew_member
        
        # Check skill requirements
        skill_score = self.calculate_skill_match_score(crew, client)
        if skill_score < self.constraints.skill_matching_strictness:
            return False
        
        # Check capacity constraints
        additional_hours = client.estimated_hours_per_visit
        if client.service_frequency == "weekly":
            weekly_hours = additional_hours
        elif client.service_frequency == "biweekly":
            weekly_hours = additional_hours * 0.5
        else:  # monthly
            weekly_hours = additional_hours * 0.25
        
        new_utilization = (assignment.total_weekly_hours + weekly_hours) / crew.max_hours_per_week
        if new_utilization > self.constraints.max_utilization_rate:
            return False
        
        # Check location limit
        if assignment.total_locations >= self.constraints.max_locations_per_crew:
            return False
        
        return True
    
    def _simulate_assignment(self, client: ClientWorkload,
                           assignment: WorkloadAssignment) -> WorkloadAssignment:
        """Simulate assigning a client to an assignment."""
        # Create a copy of the assignment with the new client
        simulated_assignment = WorkloadAssignment(
            crew_member=assignment.crew_member,
            assigned_clients=assignment.assigned_clients + [client],
            total_weekly_hours=assignment.total_weekly_hours,
            total_locations=assignment.total_locations + 1,
            total_plants=assignment.total_plants + client.plant_count,
            total_square_footage=assignment.total_square_footage + client.square_footage,
            estimated_travel_time=assignment.estimated_travel_time,
            workload_score=0.0,
            utilization_rate=0.0
        )
        
        # Update metrics
        self._update_assignment_metrics(simulated_assignment)
        
        return simulated_assignment
    
    def _assign_client_to_crew(self, client: ClientWorkload,
                             assignment: WorkloadAssignment):
        """Actually assign a client to a crew assignment."""
        assignment.assigned_clients.append(client)
        assignment.total_locations += 1
        assignment.total_plants += client.plant_count
        assignment.total_square_footage += client.square_footage
        
        self._update_assignment_metrics(assignment)
    
    def _update_assignment_metrics(self, assignment: WorkloadAssignment):
        """Update calculated metrics for an assignment."""
        total_hours = 0.0
        
        for client in assignment.assigned_clients:
            hours = client.estimated_hours_per_visit
            
            # Adjust for frequency
            if client.service_frequency == "weekly":
                weekly_hours = hours
            elif client.service_frequency == "biweekly":
                weekly_hours = hours * 0.5
            else:  # monthly
                weekly_hours = hours * 0.25
            
            total_hours += weekly_hours
        
        assignment.total_weekly_hours = total_hours
        assignment.utilization_rate = total_hours / assignment.crew_member.max_hours_per_week
        assignment.workload_score = self.calculate_workload_score(assignment)
        
        # Estimate travel time
        if assignment.assigned_clients:
            # Simplified travel time estimation
            unique_boroughs = set(c.borough for c in assignment.assigned_clients)
            daily_travel_minutes = len(unique_boroughs) * 30  # 30 min per borough
            assignment.estimated_travel_time = timedelta(minutes=daily_travel_minutes * 5)  # 5 days
    
    def _optimize_assignments(self, assignments: List[WorkloadAssignment]) -> List[WorkloadAssignment]:
        """Optimize assignments through local search."""
        improved = True
        iterations = 0
        max_iterations = 100
        
        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            
            # Try swapping clients between assignments
            for i in range(len(assignments)):
                for j in range(i + 1, len(assignments)):
                    if self._try_swap_clients(assignments[i], assignments[j]):
                        improved = True
            
            # Try moving clients between assignments
            for i in range(len(assignments)):
                for j in range(len(assignments)):
                    if i != j and self._try_move_client(assignments[i], assignments[j]):
                        improved = True
        
        return assignments
    
    def _try_swap_clients(self, assignment1: WorkloadAssignment,
                         assignment2: WorkloadAssignment) -> bool:
        """Try swapping clients between two assignments."""
        if not assignment1.assigned_clients or not assignment2.assigned_clients:
            return False
        
        # Try swapping each client from assignment1 with each from assignment2
        for client1 in assignment1.assigned_clients[:]:
            for client2 in assignment2.assigned_clients[:]:
                # Calculate current scores
                current_score = assignment1.workload_score + assignment2.workload_score
                
                # Simulate swap
                assignment1_temp = assignment1.assigned_clients[:]
                assignment2_temp = assignment2.assigned_clients[:]
                
                assignment1_temp.remove(client1)
                assignment1_temp.append(client2)
                assignment2_temp.remove(client2)
                assignment2_temp.append(client1)
                
                # Check if swap is feasible
                if (self._can_assign_client(client2, assignment1) and
                    self._can_assign_client(client1, assignment2)):
                    
                    # Calculate new scores
                    temp_assignment1 = WorkloadAssignment(
                        crew_member=assignment1.crew_member,
                        assigned_clients=assignment1_temp,
                        total_weekly_hours=0, total_locations=0, total_plants=0,
                        total_square_footage=0, estimated_travel_time=timedelta(),
                        workload_score=0, utilization_rate=0
                    )
                    temp_assignment2 = WorkloadAssignment(
                        crew_member=assignment2.crew_member,
                        assigned_clients=assignment2_temp,
                        total_weekly_hours=0, total_locations=0, total_plants=0,
                        total_square_footage=0, estimated_travel_time=timedelta(),
                        workload_score=0, utilization_rate=0
                    )
                    
                    self._update_assignment_metrics(temp_assignment1)
                    self._update_assignment_metrics(temp_assignment2)
                    
                    new_score = temp_assignment1.workload_score + temp_assignment2.workload_score
                    
                    if new_score < current_score:
                        # Perform the swap
                        assignment1.assigned_clients = assignment1_temp
                        assignment2.assigned_clients = assignment2_temp
                        self._update_assignment_metrics(assignment1)
                        self._update_assignment_metrics(assignment2)
                        return True
        
        return False
    
    def _try_move_client(self, from_assignment: WorkloadAssignment,
                        to_assignment: WorkloadAssignment) -> bool:
        """Try moving a client from one assignment to another."""
        if not from_assignment.assigned_clients:
            return False
        
        for client in from_assignment.assigned_clients[:]:
            # Calculate current scores
            current_score = from_assignment.workload_score + to_assignment.workload_score
            
            # Check if move is feasible
            if self._can_assign_client(client, to_assignment):
                # Simulate move
                from_temp = from_assignment.assigned_clients[:]
                to_temp = to_assignment.assigned_clients[:]
                
                from_temp.remove(client)
                to_temp.append(client)
                
                # Calculate new scores
                temp_from = WorkloadAssignment(
                    crew_member=from_assignment.crew_member,
                    assigned_clients=from_temp,
                    total_weekly_hours=0, total_locations=0, total_plants=0,
                    total_square_footage=0, estimated_travel_time=timedelta(),
                    workload_score=0, utilization_rate=0
                )
                temp_to = WorkloadAssignment(
                    crew_member=to_assignment.crew_member,
                    assigned_clients=to_temp,
                    total_weekly_hours=0, total_locations=0, total_plants=0,
                    total_square_footage=0, estimated_travel_time=timedelta(),
                    workload_score=0, utilization_rate=0
                )
                
                self._update_assignment_metrics(temp_from)
                self._update_assignment_metrics(temp_to)
                
                new_score = temp_from.workload_score + temp_to.workload_score
                
                if new_score < current_score:
                    # Perform the move
                    from_assignment.assigned_clients = from_temp
                    to_assignment.assigned_clients = to_temp
                    self._update_assignment_metrics(from_assignment)
                    self._update_assignment_metrics(to_assignment)
                    return True
        
        return False
    
    def get_workload_balance_metrics(self) -> Dict[str, float]:
        """Get metrics about workload balance across the team."""
        if not self.current_assignments:
            return {}
        
        utilization_rates = [a.utilization_rate for a in self.current_assignments]
        workload_scores = [a.workload_score for a in self.current_assignments]
        hours_per_crew = [a.total_weekly_hours for a in self.current_assignments]
        locations_per_crew = [a.total_locations for a in self.current_assignments]
        
        return {
            "avg_utilization": statistics.mean(utilization_rates),
            "utilization_std_dev": statistics.stdev(utilization_rates) if len(utilization_rates) > 1 else 0.0,
            "avg_workload_score": statistics.mean(workload_scores),
            "avg_hours_per_crew": statistics.mean(hours_per_crew),
            "hours_std_dev": statistics.stdev(hours_per_crew) if len(hours_per_crew) > 1 else 0.0,
            "avg_locations_per_crew": statistics.mean(locations_per_crew),
            "locations_std_dev": statistics.stdev(locations_per_crew) if len(locations_per_crew) > 1 else 0.0,
            "balance_quality": self._calculate_balance_quality()
        }
    
    def _calculate_balance_quality(self) -> float:
        """Calculate overall balance quality score (0.0 to 1.0)."""
        if not self.current_assignments:
            return 0.0
        
        utilization_rates = [a.utilization_rate for a in self.current_assignments]
        
        # Check if utilizations are within acceptable range
        in_range_count = sum(
            1 for rate in utilization_rates
            if self.constraints.min_utilization_rate <= rate <= self.constraints.max_utilization_rate
        )
        
        range_score = in_range_count / len(utilization_rates)
        
        # Check variance in utilization
        if len(utilization_rates) > 1:
            variance = statistics.variance(utilization_rates)
            variance_score = max(0.0, 1.0 - variance / self.constraints.workload_variance_tolerance)
        else:
            variance_score = 1.0
        
        # Average workload scores (lower is better)
        avg_workload_score = statistics.mean(a.workload_score for a in self.current_assignments)
        workload_score_normalized = max(0.0, 1.0 - avg_workload_score / 5.0)  # Normalize to 0-1
        
        # Weighted combination
        balance_quality = (range_score * 0.4 + 
                          variance_score * 0.35 + 
                          workload_score_normalized * 0.25)
        
        return balance_quality


def create_sample_balancer_data() -> Tuple[List[CrewMemberProfile], List[ClientWorkload]]:
    """Create sample data for testing crew workload balancing."""
    
    # Sample crew members
    crew_members = [
        CrewMemberProfile(
            id="crew001",
            name="Maria Rodriguez",
            skills=CrewSkillProfile(
                plant_care=SkillLevel.EXPERT,
                holiday_decor=SkillLevel.INTERMEDIATE,
                landscaping=SkillLevel.INTERMEDIATE,
                floral_design=SkillLevel.ADVANCED,
                heavy_lifting=SkillLevel.INTERMEDIATE,
                nyc_driving=SkillLevel.ADVANCED,
                customer_service=SkillLevel.ADVANCED,
                equipment_operation=SkillLevel.INTERMEDIATE
            ),
            hourly_rate=32.0,
            max_hours_per_week=40.0,
            current_utilization=0.0,
            preferred_boroughs=["Manhattan", "Queens"],
            availability_windows={
                "monday": [(time(8, 0), time(16, 0))],
                "tuesday": [(time(8, 0), time(16, 0))],
                "wednesday": [(time(8, 0), time(16, 0))],
                "thursday": [(time(8, 0), time(16, 0))],
                "friday": [(time(8, 0), time(16, 0))]
            },
            certification_expiry={},
            performance_rating=4.5,
            overtime_preference=0.7
        ),
        CrewMemberProfile(
            id="crew002",
            name="James Chen",
            skills=CrewSkillProfile(
                plant_care=SkillLevel.ADVANCED,
                holiday_decor=SkillLevel.EXPERT,
                landscaping=SkillLevel.ADVANCED,
                floral_design=SkillLevel.INTERMEDIATE,
                heavy_lifting=SkillLevel.ADVANCED,
                nyc_driving=SkillLevel.EXPERT,
                customer_service=SkillLevel.INTERMEDIATE,
                equipment_operation=SkillLevel.ADVANCED
            ),
            hourly_rate=35.0,
            max_hours_per_week=40.0,
            current_utilization=0.0,
            preferred_boroughs=["Brooklyn", "Manhattan"],
            availability_windows={
                "monday": [(time(7, 0), time(15, 0))],
                "tuesday": [(time(7, 0), time(15, 0))],
                "wednesday": [(time(7, 0), time(15, 0))],
                "thursday": [(time(7, 0), time(15, 0))],
                "friday": [(time(7, 0), time(15, 0))]
            },
            certification_expiry={},
            performance_rating=4.2,
            overtime_preference=0.5
        ),
        CrewMemberProfile(
            id="crew003",
            name="Sarah Williams",
            skills=CrewSkillProfile(
                plant_care=SkillLevel.ADVANCED,
                holiday_decor=SkillLevel.NOVICE,
                landscaping=SkillLevel.EXPERT,
                floral_design=SkillLevel.INTERMEDIATE,
                heavy_lifting=SkillLevel.INTERMEDIATE,
                nyc_driving=SkillLevel.ADVANCED,
                customer_service=SkillLevel.ADVANCED,
                equipment_operation=SkillLevel.EXPERT
            ),
            hourly_rate=30.0,
            max_hours_per_week=40.0,
            current_utilization=0.0,
            preferred_boroughs=["Queens", "Bronx"],
            availability_windows={
                "tuesday": [(time(9, 0), time(17, 0))],
                "wednesday": [(time(9, 0), time(17, 0))],
                "thursday": [(time(9, 0), time(17, 0))],
                "friday": [(time(9, 0), time(17, 0))],
                "saturday": [(time(8, 0), time(12, 0))]
            },
            certification_expiry={},
            performance_rating=4.8,
            overtime_preference=0.3
        )
    ]
    
    # Sample client workloads
    client_workloads = [
        ClientWorkload(
            client_id="client001",
            location_name="Weill Cornell Medical Center",
            address="1300 York Ave, New York, NY 10065",
            borough="Manhattan",
            coordinates=(40.7648, -73.9536),
            square_footage=3500.0,
            plant_count=125,
            service_frequency="weekly",
            estimated_hours_per_visit=3.5,
            required_skills={"plant_care": SkillLevel.ADVANCED, "customer_service": SkillLevel.INTERMEDIATE},
            complexity_factors={"healthcare_environment": 1.2, "high_traffic": 1.1},
            access_restrictions=["security_clearance"],
            seasonal_adjustments={"spring": 1.1, "summer": 1.0, "fall": 1.0, "winter": 0.9}
        ),
        ClientWorkload(
            client_id="client002",
            location_name="Brooklyn Corporate Plaza",
            address="123 Brooklyn Heights Promenade, Brooklyn, NY 11201",
            borough="Brooklyn",
            coordinates=(40.6922, -73.9969),
            square_footage=2800.0,
            plant_count=85,
            service_frequency="weekly",
            estimated_hours_per_visit=2.5,
            required_skills={"plant_care": SkillLevel.INTERMEDIATE, "floral_design": SkillLevel.INTERMEDIATE},
            complexity_factors={"corporate_environment": 1.0},
            access_restrictions=[],
            seasonal_adjustments={"spring": 1.2, "summer": 1.0, "fall": 1.1, "winter": 0.8}
        ),
        ClientWorkload(
            client_id="client003",
            location_name="Queens University Campus",
            address="65-30 Kissena Blvd, Flushing, NY 11367",
            borough="Queens",
            coordinates=(40.7362, -73.8181),
            square_footage=4200.0,
            plant_count=95,
            service_frequency="biweekly",
            estimated_hours_per_visit=4.0,
            required_skills={"plant_care": SkillLevel.INTERMEDIATE, "landscaping": SkillLevel.ADVANCED},
            complexity_factors={"educational_environment": 1.1, "large_space": 1.2},
            access_restrictions=["after_hours"],
            seasonal_adjustments={"spring": 1.3, "summer": 1.1, "fall": 1.2, "winter": 0.7}
        ),
        ClientWorkload(
            client_id="client004", 
            location_name="Bronx Hospital Center",
            address="1650 Grand Concourse, Bronx, NY 10457",
            borough="Bronx",
            coordinates=(40.8424, -73.9142),
            square_footage=2200.0,
            plant_count=65,
            service_frequency="weekly",
            estimated_hours_per_visit=2.0,
            required_skills={"plant_care": SkillLevel.ADVANCED, "customer_service": SkillLevel.ADVANCED},
            complexity_factors={"healthcare_environment": 1.3, "sterile_requirements": 1.1},
            access_restrictions=["security_clearance", "health_screening"],
            seasonal_adjustments={"spring": 1.0, "summer": 1.0, "fall": 1.0, "winter": 1.0}
        ),
        ClientWorkload(
            client_id="client005",
            location_name="Staten Island Ferry Terminal",
            address="4 S St, New York, NY 10004",
            borough="Staten Island",
            coordinates=(40.6430, -74.0748),
            square_footage=1800.0,
            plant_count=45,
            service_frequency="monthly",
            estimated_hours_per_visit=3.0,
            required_skills={"plant_care": SkillLevel.INTERMEDIATE, "heavy_lifting": SkillLevel.INTERMEDIATE},
            complexity_factors={"public_space": 1.2, "weather_exposure": 1.1},
            access_restrictions=["municipal_clearance"],
            seasonal_adjustments={"spring": 1.1, "summer": 1.2, "fall": 1.1, "winter": 0.9}
        )
    ]
    
    return crew_members, client_workloads


if __name__ == "__main__":
    # Example usage
    crew_members, client_workloads = create_sample_balancer_data()
    
    # Initialize balancer
    constraints = BalancingConstraints(
        max_utilization_rate=0.85,
        min_utilization_rate=0.60,
        max_locations_per_crew=12,
        skill_matching_strictness=0.75
    )
    
    balancer = CrewWorkloadBalancer(constraints)
    
    # Add crew members and workloads
    for crew_member in crew_members:
        balancer.add_crew_member(crew_member)
    
    for workload in client_workloads:
        balancer.add_client_workload(workload)
    
    print("=== Cambridge NY Crew Workload Balancer Demo ===")
    print(f"Crew members: {len(crew_members)}")
    print(f"Client locations: {len(client_workloads)}")
    
    # Balance workloads
    assignments = balancer.balance_workloads()
    
    print(f"\n=== Workload Assignments ===")
    for assignment in assignments:
        print(f"\n{assignment.crew_member.name} (ID: {assignment.crew_member.id}):")
        print(f"  Utilization: {assignment.utilization_rate:.1%}")
        print(f"  Weekly hours: {assignment.total_weekly_hours:.1f}")
        print(f"  Locations: {assignment.total_locations}")
        print(f"  Plants: {assignment.total_plants}")
        print(f"  Square footage: {assignment.total_square_footage:,.0f}")
        print(f"  Workload score: {assignment.workload_score:.2f}")
        print(f"  Clients:")
        
        for client in assignment.assigned_clients:
            print(f"    - {client.location_name} ({client.borough})")
            print(f"      {client.service_frequency}, {client.estimated_hours_per_visit}h per visit")
    
    # Show balance metrics
    print(f"\n=== Balance Metrics ===")
    metrics = balancer.get_workload_balance_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            if key.endswith('_std_dev') or key.startswith('avg_'):
                print(f"{key}: {value:.2f}")
            else:
                print(f"{key}: {value:.1%}")
    
    print(f"\nBalance quality: {metrics['balance_quality']:.1%}")