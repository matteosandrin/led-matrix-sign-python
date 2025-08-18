import random
import numpy as np
from typing import Tuple, List


class GameOfLife:
    def __init__(self, width: int, height: int, density: float = 0.3):
        self.width = width
        self.height = height
        self.grid = np.zeros((height, width), dtype=bool)
        self.generation = 0
        self.stable_count = 0
        self.max_stable_generations = 50
        self.density = density
        self._initialize_random_grid()
    
    def _initialize_random_grid(self):
        """Initialize grid with random living cells based on density."""
        for y in range(self.height):
            for x in range(self.width):
                self.grid[y, x] = random.random() < self.density
        self.generation = 0
        self.stable_count = 0
    
    def _count_neighbors(self, x: int, y: int) -> int:
        """Count living neighbors for a cell at position (x, y)."""
        count = 0
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = (x + dx) % self.width, (y + dy) % self.height
                if self.grid[ny, nx]:
                    count += 1
        return count
    
    def step(self) -> bool:
        """Advance the game by one generation. Returns True if grid changed."""
        new_grid = np.zeros_like(self.grid)
        
        for y in range(self.height):
            for x in range(self.width):
                neighbors = self._count_neighbors(x, y)
                
                if self.grid[y, x]:  # Cell is alive
                    # Survives with 2 or 3 neighbors
                    new_grid[y, x] = neighbors in [2, 3]
                else:  # Cell is dead
                    # Born with exactly 3 neighbors
                    new_grid[y, x] = neighbors == 3
        
        # Check if grid changed
        changed = not np.array_equal(self.grid, new_grid)
        self.grid = new_grid
        self.generation += 1
        
        if not changed:
            self.stable_count += 1
        else:
            self.stable_count = 0
            
        return changed
    
    def is_stable_or_empty(self) -> bool:
        """Check if the game has reached a stable state or is empty."""
        return (self.stable_count >= self.max_stable_generations or 
                not np.any(self.grid))
    
    def reset(self):
        """Reset the game with a new random configuration."""
        self._initialize_random_grid()
    
    def get_grid(self) -> np.ndarray:
        """Get the current grid state."""
        return self.grid.copy()
    
    def get_generation(self) -> int:
        """Get the current generation number."""
        return self.generation
    
    def add_pattern(self, pattern: List[Tuple[int, int]], x_offset: int = 0, y_offset: int = 0):
        """Add a specific pattern to the grid at the given offset."""
        for x, y in pattern:
            grid_x = (x + x_offset) % self.width
            grid_y = (y + y_offset) % self.height
            self.grid[grid_y, grid_x] = True


class GameOfLifePatterns:
    """Collection of classic Game of Life patterns."""
    
    @staticmethod
    def glider() -> List[Tuple[int, int]]:
        """Classic glider pattern."""
        return [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]
    
    @staticmethod
    def block() -> List[Tuple[int, int]]:
        """Still life block pattern."""
        return [(0, 0), (0, 1), (1, 0), (1, 1)]
    
    @staticmethod
    def blinker() -> List[Tuple[int, int]]:
        """Oscillating blinker pattern."""
        return [(0, 1), (1, 1), (2, 1)]
    
    @staticmethod
    def toad() -> List[Tuple[int, int]]:
        """Oscillating toad pattern."""
        return [(1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1)]
    
    @staticmethod
    def beacon() -> List[Tuple[int, int]]:
        """Oscillating beacon pattern."""
        return [(0, 0), (1, 0), (0, 1), (3, 2), (2, 3), (3, 3)]
    
    @staticmethod
    def r_pentomino() -> List[Tuple[int, int]]:
        """Chaotic R-pentomino pattern."""
        return [(1, 0), (2, 0), (0, 1), (1, 1), (1, 2)]