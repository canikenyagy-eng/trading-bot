"""
Strategy Versioning & Research Mode - Continuous Improvement System.

Tracks strategy versions and enables research mode.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StrategyVersion:
    """Strategy version record."""
    
    version: str
    created_at: datetime
    description: str
    
    # Metrics
    trade_count: int = 0
    winrate: float = 0.5
    avg_r: float = 0.0
    profit_factor: float = 1.0
    max_drawdown: float = 0.0
    
    # Active status
    is_active: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "metrics": {
                "trade_count": self.trade_count,
                "winrate": self.winrate,
                "avg_r": self.avg_r,
                "profit_factor": self.profit_factor,
                "max_drawdown": self.max_drawdown,
            },
            "is_active": self.is_active,
        }


class StrategyVersioning:
    """Strategy versioning system."""
    
    def __init__(self):
        self.versions: Dict[str, StrategyVersion] = {}
        
        # Current version
        self.current_version = "v1.0.0"
        self.version_counter = 1
        
        # Create initial version
        self._create_version("v1.0.0", "Initial strategy")
        
        # Research mode
        self.research_mode = False
        self.research_start: Optional[datetime] = None
    
    def _create_version(self, version: str, description: str) -> StrategyVersion:
        """Create new version."""
        v = StrategyVersion(
            version=version,
            created_at=datetime.now(),
            description=description,
            is_active=True
        )
        
        self.versions[version] = v
        return v
    
    def get_current_version(self) -> str:
        """Get current version string."""
        return self.current_version
    
    def update_metrics(
        self,
        version: str,
        trade_count: int,
        winrate: float,
        avg_r: float,
        pf: float,
        dd: float
    ) -> None:
        """Update metrics for version."""
        if version in self.versions:
            v = self.versions[version]
            v.trade_count = trade_count
            v.winrate = winrate
            v.avg_r = avg_r
            v.profit_factor = pf
            v.max_drawdown = dd
    
    def create_new_version(
        self,
        description: str,
        base_version: str = None
    ) -> str:
        """Create new version."""
        base = base_version or self.current_version
        
        # Increment
        parts = base.split(".")
        major = int(parts[0][1:])
        minor = int(parts[1])
        patch = int(parts[2]) + 1
        
        new_version = f"v{major}.{minor}.{patch}"
        
        self._create_version(new_version, description)
        
        # Deactivate old
        if base in self.versions:
            self.versions[base].is_active = False
        
        self.current_version = new_version
        
        return new_version
    
    def get_version_history(self) -> List[Dict]:
        """Get version history."""
        return [v.to_dict() for v in self.versions.values()]
    
    def enter_research_mode(self) -> None:
        """Enter research mode."""
        self.research_mode = True
        self.research_start = datetime.now()
        
        # Create research version
        self.create_new_version("Research mode enabled")
    
    def exit_research_mode(self) -> bool:
        """Exit research mode, return to stable."""
        if self.research_mode:
            self.research_mode = False
            
            # Create stable version
            new_ver = self.create_new_version("Post-research stable")
            
            self.research_start = None
            
            return True
        
        return False
    
    def is_research_mode(self) -> bool:
        """Check if in research mode."""
        return self.research_mode
    
    def get_drift_score(self) -> float:
        """Calculate drift score (performance change)."""
        if self.versions:
            current = self.versions.get(self.current_version)
            
            if current and current.trade_count > 50:
                # Compare recent vs older
                # Simplified: check if performance declining
                if current.max_drawdown > 0.10:
                    return 0.8
                elif current.profit_factor < 1.2:
                    return 0.5
        
        return 0.0
    
    def should_trigger_research(self) -> bool:
        """Check if research mode should trigger."""
        drift = self.get_drift_score()
        return drift > 0.6


# Strategy Versioning End