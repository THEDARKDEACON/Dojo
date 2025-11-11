#!/usr/bin/env python3
"""
Train Agent: Training script for RL navigation policies

This script trains PPO or SAC agents for robot navigation using the
NavigationEnv gymnasium environment. It includes curriculum learning,
checkpoint saving, and training monitoring.
"""

import os
import argparse
from datetime import datetime
from typing import Optional
import numpy as np

# RL libraries
try:
    from stable_baselines3 import PPO, SAC
    from stable_baselines3.common.callbacks import (
        CheckpointCallback,
        EvalCallback,
        CallbackList
    )
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    from stable_baselines3.common.monitor import Monitor
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    print("Warning: stable-baselines3 not installed. Install with: pip install stable-baselines3")

# ROS2
import rclpy

# Local imports
from robot_rl_navigation.navigation_env import NavigationEnv


class CurriculumCallback:
    """
    Callback for curriculum learning.
    
    Gradually increases difficulty by:
    - Increasing goal distance
    - Reducing goal threshold
    - Adding more obstacles (if supported)
    """
    
    def __init__(
        self,
        env,
        initial_goal_distance: float = 5.0,
        final_goal_distance: float = 15.0,
        curriculum_steps: int = 100000
    ):
        self.env = env
        self.initial_goal_distance = initial_goal_distance
        self.final_goal_distance = final_goal_distance
        self.curriculum_steps = curriculum_steps
        self.current_step = 0
        
    def __call__(self, locals_dict, globals_dict):
        """Update curriculum based on training progress."""
        self.current_step += 1
        
        # Calculate curriculum progress (0 to 1)
        progress = min(1.0, self.current_step / self.curriculum_steps)
        
        # Interpolate goal distance
        goal_distance = (
            self.initial_goal_distance +
            (self.final_goal_distance - self.initial_goal_distance) * progress
        )
        
        # Update environment parameters
        # Note: This would need to be implemented in the env
        # For now, we just track progress
        
        return True


class TrainingMonitor:
    """Monitor and log training progress."""
    
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self.episode_rewards = []
        self.episode_lengths = []
        self.success_rate = []
        
    def log_episode(self, reward: float, length: int, success: bool):
        """Log episode statistics."""
        self.episode_rewards.append(reward)
        self.episode_lengths.append(length)
        self.success_rate.append(1.0 if success else 0.0)
        
        # Print statistics every 10 episodes
        if len(self.episode_rewards) % 10 == 0:
            avg_reward = np.mean(self.episode_rewards[-10:])
            avg_length = np.mean(self.episode_lengths[-10:])
            success_rate = np.mean(self.success_rate[-10:]) * 100
            
            print(f"\nEpisode {len(self.episode_rewards)}:")
            print(f"  Avg Reward (last 10): {avg_reward:.2f}")
            print(f"  Avg Length (last 10): {avg_length:.1f}")
            print(f"  Success Rate (last 10): {success_rate:.1f}%")


def make_env(rank: int = 0, seed: int = 0):
    """
    Create and wrap the navigation environment.
    
    Args:
        rank: Environment rank (for parallel envs)
        seed: Random seed
        
    Returns:
        Wrapped environment
    """
    def _init():
        env = NavigationEnv(
            max_episode_steps=1000,
            goal_threshold=0.5,
            collision_threshold=0.3,
            max_linear_vel=1.0,
            max_angular_vel=1.0,
            lidar_rays=64
        )
        env.reset(seed=seed + rank)
        env = Monitor(env)
        return env
    
    return _init


def train_ppo(
    total_timesteps: int = 100000,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
    n_epochs: int = 10,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
    clip_range: float = 0.2,
    save_dir: str = './models',
    checkpoint_freq: int = 10000,
    eval_freq: int = 5000,
    seed: int = 0
):
    """
    Train PPO agent for navigation.
    
    Args:
        total_timesteps: Total training timesteps
        learning_rate: Learning rate
        n_steps: Steps per update
        batch_size: Minibatch size
        n_epochs: Optimization epochs per update
        gamma: Discount factor
        gae_lambda: GAE lambda
        clip_range: PPO clip range
        save_dir: Directory to save models
        checkpoint_freq: Checkpoint frequency
        eval_freq: Evaluation frequency
        seed: Random seed
    """
    if not SB3_AVAILABLE:
        raise ImportError("stable-baselines3 is required for training")
    
    # Create save directory
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = os.path.join(save_dir, f'ppo_{timestamp}')
    os.makedirs(model_dir, exist_ok=True)
    
    print(f"Training PPO agent...")
    print(f"Model directory: {model_dir}")
    print(f"Total timesteps: {total_timesteps}")
    
    # Create environment
    env = DummyVecEnv([make_env(0, seed)])
    env = VecNormalize(env, norm_obs=True, norm_reward=True)
    
    # Create eval environment
    eval_env = DummyVecEnv([make_env(1, seed + 1000)])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False)
    
    # Create PPO model
    model = PPO(
        'MlpPolicy',
        env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        gamma=gamma,
        gae_lambda=gae_lambda,
        clip_range=clip_range,
        verbose=1,
        tensorboard_log=os.path.join(model_dir, 'tensorboard'),
        seed=seed
    )
    
    # Create callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=checkpoint_freq,
        save_path=model_dir,
        name_prefix='ppo_checkpoint'
    )
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=model_dir,
        log_path=model_dir,
        eval_freq=eval_freq,
        deterministic=True,
        render=False
    )
    
    callback_list = CallbackList([checkpoint_callback, eval_callback])
    
    # Train the model
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=callback_list,
            progress_bar=True
        )
        
        # Save final model
        final_model_path = os.path.join(model_dir, 'ppo_final')
        model.save(final_model_path)
        env.save(os.path.join(model_dir, 'vec_normalize.pkl'))
        
        print(f"\nTraining complete!")
        print(f"Final model saved to: {final_model_path}")
        
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        model.save(os.path.join(model_dir, 'ppo_interrupted'))
        env.save(os.path.join(model_dir, 'vec_normalize.pkl'))
        print(f"Model saved to: {model_dir}")
    
    finally:
        env.close()
        eval_env.close()


def train_sac(
    total_timesteps: int = 100000,
    learning_rate: float = 3e-4,
    buffer_size: int = 100000,
    learning_starts: int = 1000,
    batch_size: int = 256,
    tau: float = 0.005,
    gamma: float = 0.99,
    save_dir: str = './models',
    checkpoint_freq: int = 10000,
    eval_freq: int = 5000,
    seed: int = 0
):
    """
    Train SAC agent for navigation.
    
    Args:
        total_timesteps: Total training timesteps
        learning_rate: Learning rate
        buffer_size: Replay buffer size
        learning_starts: Steps before learning starts
        batch_size: Minibatch size
        tau: Target network update rate
        gamma: Discount factor
        save_dir: Directory to save models
        checkpoint_freq: Checkpoint frequency
        eval_freq: Evaluation frequency
        seed: Random seed
    """
    if not SB3_AVAILABLE:
        raise ImportError("stable-baselines3 is required for training")
    
    # Create save directory
    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = os.path.join(save_dir, f'sac_{timestamp}')
    os.makedirs(model_dir, exist_ok=True)
    
    print(f"Training SAC agent...")
    print(f"Model directory: {model_dir}")
    print(f"Total timesteps: {total_timesteps}")
    
    # Create environment
    env = DummyVecEnv([make_env(0, seed)])
    env = VecNormalize(env, norm_obs=True, norm_reward=True)
    
    # Create eval environment
    eval_env = DummyVecEnv([make_env(1, seed + 1000)])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False)
    
    # Create SAC model
    model = SAC(
        'MlpPolicy',
        env,
        learning_rate=learning_rate,
        buffer_size=buffer_size,
        learning_starts=learning_starts,
        batch_size=batch_size,
        tau=tau,
        gamma=gamma,
        verbose=1,
        tensorboard_log=os.path.join(model_dir, 'tensorboard'),
        seed=seed
    )
    
    # Create callbacks
    checkpoint_callback = CheckpointCallback(
        save_freq=checkpoint_freq,
        save_path=model_dir,
        name_prefix='sac_checkpoint'
    )
    
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=model_dir,
        log_path=model_dir,
        eval_freq=eval_freq,
        deterministic=True,
        render=False
    )
    
    callback_list = CallbackList([checkpoint_callback, eval_callback])
    
    # Train the model
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=callback_list,
            progress_bar=True
        )
        
        # Save final model
        final_model_path = os.path.join(model_dir, 'sac_final')
        model.save(final_model_path)
        env.save(os.path.join(model_dir, 'vec_normalize.pkl'))
        
        print(f"\nTraining complete!")
        print(f"Final model saved to: {final_model_path}")
        
    except KeyboardInterrupt:
        print("\nTraining interrupted by user")
        model.save(os.path.join(model_dir, 'sac_interrupted'))
        env.save(os.path.join(model_dir, 'vec_normalize.pkl'))
        print(f"Model saved to: {model_dir}")
    
    finally:
        env.close()
        eval_env.close()


def main():
    """Main training function."""
    parser = argparse.ArgumentParser(description='Train RL navigation agent')
    parser.add_argument(
        '--algorithm',
        type=str,
        default='ppo',
        choices=['ppo', 'sac'],
        help='RL algorithm to use'
    )
    parser.add_argument(
        '--timesteps',
        type=int,
        default=100000,
        help='Total training timesteps'
    )
    parser.add_argument(
        '--learning-rate',
        type=float,
        default=3e-4,
        help='Learning rate'
    )
    parser.add_argument(
        '--save-dir',
        type=str,
        default='./models',
        help='Directory to save models'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=0,
        help='Random seed'
    )
    
    args = parser.parse_args()
    
    # Initialize ROS2
    rclpy.init()
    
    try:
        if args.algorithm == 'ppo':
            train_ppo(
                total_timesteps=args.timesteps,
                learning_rate=args.learning_rate,
                save_dir=args.save_dir,
                seed=args.seed
            )
        elif args.algorithm == 'sac':
            train_sac(
                total_timesteps=args.timesteps,
                learning_rate=args.learning_rate,
                save_dir=args.save_dir,
                seed=args.seed
            )
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()
