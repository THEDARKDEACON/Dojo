#!/usr/bin/env python3
"""
Spiking Neural Network Processor.

Implements brain-inspired spiking neural networks for event-based processing.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
import numpy as np
from typing import List, Tuple
from dataclasses import dataclass


@dataclass
class LIFNeuron:
    """Leaky Integrate-and-Fire neuron model"""
    membrane_potential: float = 0.0
    threshold: float = 1.0
    leak_rate: float = 0.1
    refractory_period: int = 0
    
    def update(self, input_current: float, dt: float = 0.001) -> bool:
        """
        Update neuron state and check for spike.
        
        Args:
            input_current: Input current
            dt: Time step
            
        Returns:
            True if neuron spikes
        """
        if self.refractory_period > 0:
            self.refractory_period -= 1
            return False
        
        # Leaky integration
        self.membrane_potential += input_current * dt
        self.membrane_potential *= (1 - self.leak_rate * dt)
        
        # Check for spike
        if self.membrane_potential >= self.threshold:
            self.membrane_potential = 0.0
            self.refractory_period = 5  # 5ms refractory period
            return True
        
        return False


class SpikingNeuralNetwork:
    """
    Spiking Neural Network for event-based processing.
    
    Uses Leaky Integrate-and-Fire (LIF) neurons with
    spike-timing-dependent plasticity (STDP) for learning.
    """
    
    def __init__(self, input_size: int, hidden_size: int, output_size: int):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size
        
        # Create neurons
        self.input_neurons = [LIFNeuron() for _ in range(input_size)]
        self.hidden_neurons = [LIFNeuron() for _ in range(hidden_size)]
        self.output_neurons = [LIFNeuron() for _ in range(output_size)]
        
        # Synaptic weights
        self.weights_ih = np.random.randn(hidden_size, input_size) * 0.1
        self.weights_ho = np.random.randn(output_size, hidden_size) * 0.1
        
        # Spike history for STDP
        self.spike_history = []
    
    def forward(self, input_spikes: np.ndarray, dt: float = 0.001) -> np.ndarray:
        """
        Forward pass through the network.
        
        Args:
            input_spikes: Binary array of input spikes
            dt: Time step
            
        Returns:
            Binary array of output spikes
        """
        # Input layer
        input_currents = input_spikes.astype(float)
        
        # Hidden layer
        hidden_currents = self.weights_ih @ input_currents
        hidden_spikes = np.array([
            neuron.update(current, dt)
            for neuron, current in zip(self.hidden_neurons, hidden_currents)
        ])
        
        # Output layer
        output_currents = self.weights_ho @ hidden_spikes.astype(float)
        output_spikes = np.array([
            neuron.update(current, dt)
            for neuron, current in zip(self.output_neurons, output_currents)
        ])
        
        # Store spike history for STDP
        self.spike_history.append({
            'input': input_spikes,
            'hidden': hidden_spikes,
            'output': output_spikes
        })
        
        return output_spikes
    
    def stdp_update(self, learning_rate: float = 0.01):
        """
        Update weights using Spike-Timing-Dependent Plasticity.
        
        Args:
            learning_rate: Learning rate for weight updates
        """
        if len(self.spike_history) < 2:
            return
        
        # Simplified STDP: strengthen connections between neurons that spike together
        for i in range(len(self.spike_history) - 1):
            curr = self.spike_history[i]
            next_spike = self.spike_history[i + 1]
            
            # Update input-hidden weights
            for h in range(self.hidden_size):
                if next_spike['hidden'][h]:
                    for inp in range(self.input_size):
                        if curr['input'][inp]:
                            self.weights_ih[h, inp] += learning_rate
            
            # Update hidden-output weights
            for o in range(self.output_size):
                if next_spike['output'][o]:
                    for h in range(self.hidden_size):
                        if curr['hidden'][h]:
                            self.weights_ho[o, h] += learning_rate
        
        # Clear old history
        if len(self.spike_history) > 100:
            self.spike_history = self.spike_history[-100:]


class SNNProcessor(Node):
    """
    ROS2 node for spiking neural network processing.
    
    Processes sensor data using neuromorphic computing principles.
    """
    
    def __init__(self):
        super().__init__('snn_processor')
        
        # Declare parameters
        self.declare_parameters(
            namespace='',
            parameters=[
                ('input_size', 64),
                ('hidden_size', 128),
                ('output_size', 10),
                ('enable_learning', True),
            ]
        )
        
        # Get parameters
        input_size = self.get_parameter('input_size').value
        hidden_size = self.get_parameter('hidden_size').value
        output_size = self.get_parameter('output_size').value
        self.enable_learning = self.get_parameter('enable_learning').value
        
        # Create SNN
        self.snn = SpikingNeuralNetwork(input_size, hidden_size, output_size)
        
        # Publishers
        self.output_pub = self.create_publisher(String, '/snn/output', 10)
        
        # Subscribers
        self.input_sub = self.create_subscription(
            String, '/snn/input', self.input_callback, 10
        )
        
        # Timer for STDP updates
        if self.enable_learning:
            self.create_timer(1.0, self.learning_update)
        
        self.get_logger().info('SNN Processor initialized')
    
    def input_callback(self, msg: String):
        """Process input through SNN"""
        try:
            # Convert input to spike train
            input_data = np.frombuffer(msg.data.encode(), dtype=np.uint8)
            input_spikes = (input_data > 128).astype(int)
            
            # Pad or truncate to input size
            if len(input_spikes) < self.snn.input_size:
                input_spikes = np.pad(input_spikes, (0, self.snn.input_size - len(input_spikes)))
            else:
                input_spikes = input_spikes[:self.snn.input_size]
            
            # Forward pass
            output_spikes = self.snn.forward(input_spikes)
            
            # Publish output
            output_msg = String()
            output_msg.data = str(output_spikes.tolist())
            self.output_pub.publish(output_msg)
            
        except Exception as e:
            self.get_logger().error(f'Error processing input: {e}')
    
    def learning_update(self):
        """Periodic STDP learning update"""
        self.snn.stdp_update()
        self.get_logger().debug('STDP update applied')


def main(args=None):
    rclpy.init(args=args)
    node = SNNProcessor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
