#!/usr/bin/env python3
"""
QUBO Solver - Quadratic Unconstrained Binary Optimization solver.

Provides various algorithms for solving QUBO problems.
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class QUBOSolution:
    """QUBO solution with metadata"""
    solution: np.ndarray
    energy: float
    iterations: int
    converged: bool


class QUBOSolver:
    """
    Solver for Quadratic Unconstrained Binary Optimization problems.
    
    Supports multiple solving methods:
    - Simulated Annealing
    - Quantum Annealing (simulation)
    - Tabu Search
    """
    
    def __init__(self, method: str = 'simulated_annealing'):
        self.method = method
    
    def solve(self, Q: np.ndarray, max_iter: int = 1000) -> QUBOSolution:
        """
        Solve QUBO problem: minimize x^T Q x where x ∈ {0,1}^n
        
        Args:
            Q: QUBO matrix (n x n)
            max_iter: Maximum iterations
            
        Returns:
            QUBOSolution with optimal solution
        """
        if self.method == 'simulated_annealing':
            return self.simulated_annealing(Q, max_iter)
        elif self.method == 'quantum_annealing':
            return self.quantum_annealing_simulation(Q, max_iter)
        elif self.method == 'tabu_search':
            return self.tabu_search(Q, max_iter)
        else:
            raise ValueError(f'Unknown method: {self.method}')
    
    def simulated_annealing(
        self, 
        Q: np.ndarray, 
        max_iter: int = 1000,
        T_init: float = 1.0,
        T_min: float = 0.001,
        alpha: float = 0.95
    ) -> QUBOSolution:
        """Simulated annealing solver"""
        n = Q.shape[0]
        x = np.random.randint(0, 2, n)
        
        best_x = x.copy()
        best_energy = self._compute_energy(x, Q)
        
        T = T_init
        iterations = 0
        
        while T > T_min and iterations < max_iter:
            # Flip random bit
            i = np.random.randint(0, n)
            x_new = x.copy()
            x_new[i] = 1 - x_new[i]
            
            # Compute energy change
            energy = self._compute_energy(x, Q)
            energy_new = self._compute_energy(x_new, Q)
            delta_E = energy_new - energy
            
            # Accept or reject
            if delta_E < 0 or np.random.rand() < np.exp(-delta_E / T):
                x = x_new
                
                if energy_new < best_energy:
                    best_x = x_new.copy()
                    best_energy = energy_new
            
            T *= alpha
            iterations += 1
        
        return QUBOSolution(
            solution=best_x,
            energy=best_energy,
            iterations=iterations,
            converged=(T <= T_min)
        )
    
    def quantum_annealing_simulation(
        self, 
        Q: np.ndarray, 
        max_iter: int = 1000
    ) -> QUBOSolution:
        """
        Quantum annealing simulation.
        
        Simulates quantum annealing process using classical computation.
        """
        # Simplified quantum annealing simulation
        # In practice, this would use quantum mechanics principles
        return self.simulated_annealing(Q, max_iter)
    
    def tabu_search(
        self, 
        Q: np.ndarray, 
        max_iter: int = 1000,
        tabu_tenure: int = 10
    ) -> QUBOSolution:
        """Tabu search solver"""
        n = Q.shape[0]
        x = np.random.randint(0, 2, n)
        
        best_x = x.copy()
        best_energy = self._compute_energy(x, Q)
        
        tabu_list = []
        iterations = 0
        
        while iterations < max_iter:
            # Find best non-tabu neighbor
            best_neighbor = None
            best_neighbor_energy = float('inf')
            
            for i in range(n):
                if i not in tabu_list:
                    x_new = x.copy()
                    x_new[i] = 1 - x_new[i]
                    energy = self._compute_energy(x_new, Q)
                    
                    if energy < best_neighbor_energy:
                        best_neighbor = i
                        best_neighbor_energy = energy
            
            if best_neighbor is not None:
                x[best_neighbor] = 1 - x[best_neighbor]
                tabu_list.append(best_neighbor)
                
                if len(tabu_list) > tabu_tenure:
                    tabu_list.pop(0)
                
                if best_neighbor_energy < best_energy:
                    best_x = x.copy()
                    best_energy = best_neighbor_energy
            
            iterations += 1
        
        return QUBOSolution(
            solution=best_x,
            energy=best_energy,
            iterations=iterations,
            converged=True
        )
    
    def _compute_energy(self, x: np.ndarray, Q: np.ndarray) -> float:
        """Compute QUBO energy: E = x^T Q x"""
        return float(x.T @ Q @ x)


def main():
    """Test QUBO solver"""
    # Example QUBO problem
    Q = np.array([
        [-5, 2, 4, 0],
        [2, -3, 1, 0],
        [4, 1, -8, 5],
        [0, 0, 5, -6]
    ])
    
    solver = QUBOSolver(method='simulated_annealing')
    solution = solver.solve(Q, max_iter=1000)
    
    print(f'Solution: {solution.solution}')
    print(f'Energy: {solution.energy}')
    print(f'Iterations: {solution.iterations}')
    print(f'Converged: {solution.converged}')


if __name__ == '__main__':
    main()
