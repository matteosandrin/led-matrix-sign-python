import random
import numpy as np
from scipy.ndimage import convolve
from numpy.typing import NDArray


class GameOfLife:
    def __init__(self, width: int, height: int, density: float = 0.3) -> None:
        self.width = width
        self.height = height
        self.grid: NDArray[np.bool_] = np.zeros((height, width), dtype=bool)
        self.generation = 0
        self.stable_count = 0
        self.max_stable_generations = 50
        self.density = density
        self._initialize_random_grid()
    
    def _initialize_random_grid(self) -> None:
        """Initialize grid with random living cells based on density."""
        for y in range(self.height):
            for x in range(self.width):
                self.grid[y, x] = random.random() < self.density
        self.generation = 0
        self.stable_count = 0
    
    def step(self) -> bool:
        """Advance the game by one generation. Returns True if grid changed."""
        kernel = np.array([[1, 1, 1],
                          [1, 0, 1], 
                          [1, 1, 1]])
        # Count neighbors for all cells using convolution with wraparound
        neighbor_count = convolve(self.grid.astype(int), kernel, mode='wrap')
        survives = self.grid & ((neighbor_count == 2) | (neighbor_count == 3))
        births = (~self.grid) & (neighbor_count == 3)
        new_grid = survives | births
        
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
    
    def reset(self) -> None:
        """Reset the game with a new random configuration."""
        self._initialize_random_grid()
    
    def get_grid(self) -> NDArray[np.bool_]:
        """Get the current grid state."""
        return self.grid.copy()
    
    def get_generation(self) -> int:
        """Get the current generation number."""
        return self.generation
