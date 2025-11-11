#!/usr/bin/env python3
"""
PolicyManager: Utility for managing RL policies

This module provides utilities for:
- Loading and saving policies
- Policy evaluation
- Model comparison
- Policy deployment
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    from stable_baselines3 import PPO, SAC
    from stable_baselines3.common.vec_env import VecNormalize, DummyVecEnv
    from stable_baselines3.common.evaluation import evaluate_policy
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False


class PolicyManager:
    """
    Manager for RL policies.
    
    Features:
    - Load/save policies
    - Evaluate policy performance
    - Compare multiple policies
    - Track policy metadata
    """
    
    def __init__(self, models_dir: str = './models'):
        """
        Initialize policy manager.
        
        Args:
            models_dir: Directory containing model checkpoints
        """
        self.models_dir = models_dir
        os.makedirs(models_dir, exist_ok=True)
        
        self.metadata_file = os.path.join(models_dir, 'policies.json')
        self.metadata = self.load_metadata()
    
    def load_metadata(self) -> Dict:
        """Load policy metadata from JSON file."""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_metadata(self):
        """Save policy metadata to JSON file."""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def register_policy(
        self,
        policy_name: str,
        algorithm: str,
        model_path: str,
        training_timesteps: int,
        performance_metrics: Optional[Dict] = None
    ):
        """
        Register a new policy in the metadata.
        
        Args:
            policy_name: Unique name for the policy
            algorithm: Algorithm used (ppo, sac)
            model_path: Path to model checkpoint
            training_timesteps: Number of training timesteps
            performance_metrics: Optional performance metrics
        """
        self.metadata[policy_name] = {
            'algorithm': algorithm,
            'model_path': model_path,
            'training_timesteps': training_timesteps,
            'created_at': datetime.now().isoformat(),
            'performance_metrics': performance_metrics or {}
        }
        self.save_metadata()
    
    def load_policy(
        self,
        policy_name: str
    ) -> Tuple[Optional[object], Optional[VecNormalize]]:
        """
        Load a policy by name.
        
        Args:
            policy_name: Name of the policy to load
            
        Returns:
            Tuple of (model, vec_normalize) or (None, None) if not found
        """
        if not SB3_AVAILABLE:
            print("Error: stable-baselines3 not available")
            return None, None
        
        if policy_name not in self.metadata:
            print(f"Error: Policy '{policy_name}' not found")
            return None, None
        
        policy_info = self.metadata[policy_name]
        model_path = policy_info['model_path']
        algorithm = policy_info['algorithm']
        
        try:
            # Load model
            if algorithm == 'ppo':
                model = PPO.load(model_path)
            elif algorithm == 'sac':
                model = SAC.load(model_path)
            else:
                print(f"Error: Unknown algorithm '{algorithm}'")
                return None, None
            
            # Load normalization stats if available
            vec_normalize_path = os.path.join(
                os.path.dirname(model_path),
                'vec_normalize.pkl'
            )
            vec_normalize = None
            if os.path.exists(vec_normalize_path):
                vec_normalize = VecNormalize.load(
                    vec_normalize_path,
                    DummyVecEnv([lambda: None])
                )
                vec_normalize.training = False
                vec_normalize.norm_reward = False
            
            print(f"Loaded policy '{policy_name}' successfully")
            return model, vec_normalize
            
        except Exception as e:
            print(f"Error loading policy: {e}")
            return None, None
    
    def evaluate_policy_performance(
        self,
        policy_name: str,
        env,
        n_eval_episodes: int = 10
    ) -> Dict:
        """
        Evaluate policy performance.
        
        Args:
            policy_name: Name of the policy to evaluate
            env: Environment to evaluate in
            n_eval_episodes: Number of episodes to evaluate
            
        Returns:
            Dictionary with performance metrics
        """
        if not SB3_AVAILABLE:
            return {}
        
        model, vec_normalize = self.load_policy(policy_name)
        if model is None:
            return {}
        
        # Wrap environment with normalization if available
        if vec_normalize is not None:
            env = VecNormalize(env, training=False, norm_reward=False)
            env.obs_rms = vec_normalize.obs_rms
            env.ret_rms = vec_normalize.ret_rms
        
        # Evaluate policy
        mean_reward, std_reward = evaluate_policy(
            model,
            env,
            n_eval_episodes=n_eval_episodes,
            deterministic=True
        )
        
        metrics = {
            'mean_reward': float(mean_reward),
            'std_reward': float(std_reward),
            'n_eval_episodes': n_eval_episodes,
            'evaluated_at': datetime.now().isoformat()
        }
        
        # Update metadata
        if policy_name in self.metadata:
            self.metadata[policy_name]['performance_metrics'] = metrics
            self.save_metadata()
        
        return metrics
    
    def list_policies(self) -> List[str]:
        """
        List all registered policies.
        
        Returns:
            List of policy names
        """
        return list(self.metadata.keys())
    
    def get_policy_info(self, policy_name: str) -> Optional[Dict]:
        """
        Get information about a policy.
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            Policy information dictionary or None
        """
        return self.metadata.get(policy_name)
    
    def compare_policies(
        self,
        policy_names: List[str],
        env,
        n_eval_episodes: int = 10
    ) -> Dict:
        """
        Compare multiple policies.
        
        Args:
            policy_names: List of policy names to compare
            env: Environment to evaluate in
            n_eval_episodes: Number of episodes per policy
            
        Returns:
            Dictionary with comparison results
        """
        results = {}
        
        for policy_name in policy_names:
            print(f"\nEvaluating {policy_name}...")
            metrics = self.evaluate_policy_performance(
                policy_name,
                env,
                n_eval_episodes
            )
            results[policy_name] = metrics
        
        # Print comparison
        print("\n" + "="*60)
        print("POLICY COMPARISON")
        print("="*60)
        print(f"{'Policy':<20} {'Mean Reward':<15} {'Std Reward':<15}")
        print("-"*60)
        
        for policy_name, metrics in results.items():
            mean_reward = metrics.get('mean_reward', 0.0)
            std_reward = metrics.get('std_reward', 0.0)
            print(f"{policy_name:<20} {mean_reward:<15.2f} {std_reward:<15.2f}")
        
        print("="*60)
        
        return results
    
    def get_best_policy(self) -> Optional[str]:
        """
        Get the best performing policy based on mean reward.
        
        Returns:
            Name of best policy or None
        """
        best_policy = None
        best_reward = float('-inf')
        
        for policy_name, info in self.metadata.items():
            metrics = info.get('performance_metrics', {})
            mean_reward = metrics.get('mean_reward', float('-inf'))
            
            if mean_reward > best_reward:
                best_reward = mean_reward
                best_policy = policy_name
        
        return best_policy
    
    def delete_policy(self, policy_name: str):
        """
        Delete a policy from metadata.
        
        Note: This does not delete the actual model files.
        
        Args:
            policy_name: Name of the policy to delete
        """
        if policy_name in self.metadata:
            del self.metadata[policy_name]
            self.save_metadata()
            print(f"Deleted policy '{policy_name}' from metadata")
        else:
            print(f"Policy '{policy_name}' not found")


def main():
    """CLI for policy management."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage RL policies')
    parser.add_argument(
        'command',
        choices=['list', 'info', 'register', 'delete', 'best'],
        help='Command to execute'
    )
    parser.add_argument(
        '--name',
        type=str,
        help='Policy name'
    )
    parser.add_argument(
        '--algorithm',
        type=str,
        choices=['ppo', 'sac'],
        help='Algorithm used'
    )
    parser.add_argument(
        '--model-path',
        type=str,
        help='Path to model checkpoint'
    )
    parser.add_argument(
        '--timesteps',
        type=int,
        help='Training timesteps'
    )
    parser.add_argument(
        '--models-dir',
        type=str,
        default='./models',
        help='Models directory'
    )
    
    args = parser.parse_args()
    
    manager = PolicyManager(models_dir=args.models_dir)
    
    if args.command == 'list':
        policies = manager.list_policies()
        print(f"\nRegistered policies ({len(policies)}):")
        for policy in policies:
            print(f"  - {policy}")
    
    elif args.command == 'info':
        if not args.name:
            print("Error: --name required")
            return
        
        info = manager.get_policy_info(args.name)
        if info:
            print(f"\nPolicy: {args.name}")
            print(f"  Algorithm: {info['algorithm']}")
            print(f"  Model Path: {info['model_path']}")
            print(f"  Training Timesteps: {info['training_timesteps']}")
            print(f"  Created: {info['created_at']}")
            
            if info.get('performance_metrics'):
                metrics = info['performance_metrics']
                print(f"  Performance:")
                print(f"    Mean Reward: {metrics.get('mean_reward', 'N/A')}")
                print(f"    Std Reward: {metrics.get('std_reward', 'N/A')}")
        else:
            print(f"Policy '{args.name}' not found")
    
    elif args.command == 'register':
        if not all([args.name, args.algorithm, args.model_path, args.timesteps]):
            print("Error: --name, --algorithm, --model-path, and --timesteps required")
            return
        
        manager.register_policy(
            args.name,
            args.algorithm,
            args.model_path,
            args.timesteps
        )
        print(f"Registered policy '{args.name}'")
    
    elif args.command == 'delete':
        if not args.name:
            print("Error: --name required")
            return
        
        manager.delete_policy(args.name)
    
    elif args.command == 'best':
        best = manager.get_best_policy()
        if best:
            print(f"\nBest policy: {best}")
            info = manager.get_policy_info(best)
            if info and info.get('performance_metrics'):
                metrics = info['performance_metrics']
                print(f"  Mean Reward: {metrics.get('mean_reward', 'N/A')}")
        else:
            print("No policies with performance metrics found")


if __name__ == '__main__':
    main()
